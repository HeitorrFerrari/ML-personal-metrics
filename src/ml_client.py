import time
from collections.abc import Iterator

import requests

from src.auth import get_access_token

BASE_URL = "https://api.mercadolibre.com"
MAX_TENTATIVAS = 4
TIMEOUT = 30

_session = requests.Session()


def _espera(resp: requests.Response | None, tentativa: int) -> float:
    """Retry-After se o ML mandou; senão backoff exponencial (1s, 2s, 4s...)."""
    if resp is not None:
        try:
            return float(resp.headers["Retry-After"])
        except (KeyError, ValueError):
            pass
    return 2 ** tentativa


def get(path: str, params: dict | None = None) -> dict:
    url = f"{BASE_URL}{path}"
    forcar_refresh = False
    ja_renovou = False

    for tentativa in range(MAX_TENTATIVAS):
        token = get_access_token(force=forcar_refresh)
        forcar_refresh = False
        ultima = tentativa == MAX_TENTATIVAS - 1

        try:
            resp = _session.get(
                url,
                params=params,
                headers={"Authorization": f"Bearer {token}"},
                timeout=TIMEOUT,
            )
        except (requests.Timeout, requests.ConnectionError):
            if ultima:
                raise
            time.sleep(_espera(None, tentativa))
            continue

        if resp.status_code == 200:
            return resp.json()

        # 401: renova o token e tenta de novo, mas só uma vez
        if resp.status_code == 401 and not ja_renovou:
            forcar_refresh = ja_renovou = True
            continue

        # 429 e 5xx: problema temporário, vale repetir
        if (resp.status_code == 429 or resp.status_code >= 500) and not ultima:
            time.sleep(_espera(resp, tentativa))
            continue

        # qualquer outro caso (400, 403, 404, 401 repetido...) não adianta repetir
        raise RuntimeError(f"GET {path} -> {resp.status_code}: {resp.text}")

    raise RuntimeError(f"GET {path}: falhou após {MAX_TENTATIVAS} tentativas")


def get_paginated(path: str, params: dict | None = None, limit: int = 50) -> Iterator[dict]:
    """Devolve os itens de `results` um a um, paginando com offset/limit."""
    params = dict(params or {})
    offset = 0

    while True:
        data = get(path, {**params, "limit": limit, "offset": offset})
        resultados = data.get("results", [])
        yield from resultados

        offset += limit
        if not resultados or offset >= data.get("paging", {}).get("total", 0):
            break


def get_me() -> dict:
    return get("/users/me")


def get_item(item_id: str) -> dict:
    return get(f"/items/{item_id}")


def get_orders(seller_id: int | str, desde: str | None = None) -> Iterator[dict]:
    """Pedidos do vendedor. `desde` em ISO 8601 com fuso, ex: 2026-10-01T00:00:00.000-03:00"""
    params = {"seller": seller_id, "sort": "date_desc"}
    if desde:
        params["order.date_created.from"] = desde
    return get_paginated("/orders/search", params)
