import time
from collections.abc import Iterator

import requests

from src.auth import get_access_token

BASE_URL = "https://api.mercadolibre.com"
MAX_TENTATIVAS = 4


_session = requests.Session()

def get(path: str, params: dict = None) -> dict:
    url = f"{BASE_URL}{path}"
    for tentativa in range(MAX_TENTATIVAS):
        resp = _session.get(
            url,
            params=params,
            headers={"Authorization": f"Bearer {get_access_token()}"},
            timeout = 30
        )
        if resp.status_code == 429 or resp.status_code >= 500:
            time.sleep(2 ** tentativa)
        continue
        if resp.status_code == 401:
            raise RuntimeError("401: Token inválido")
        resp.raise_for_status()
        return resp.json()
    raise RuntimeError(f"Falhou apos {MAX_TENTATIVAS} tentativas")

def get_paginated(path: str, params: dict | None = None, limit: int = 50) -> Iterator:
    params = params or {}

