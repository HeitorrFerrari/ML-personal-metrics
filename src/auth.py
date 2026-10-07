import json
import os
import time
from urllib.parse import parse_qs, urlencode, urlparse

import requests

from src.config import ML_CLIENT_ID, ML_SECRET_KEY, ML_URL_REDIRECT, TOKEN_PATH

AUTH_URL = "https://auth.mercadolivre.com.br/authorization"
TOKEN_URL = "https://api.mercadolibre.com/oauth/token"
MARGEM_EXPIRACAO = 300


def build_auth_url() -> str:
    params = {
        "response_type": "code",
        "client_id": ML_CLIENT_ID,
        "redirect_uri": ML_URL_REDIRECT,
    }
    return f"{AUTH_URL}?{urlencode(params)}"


def _post_token(data: dict) -> dict:
    resp = requests.post(
        TOKEN_URL,
        data={"client_id": ML_CLIENT_ID, "client_secret": ML_SECRET_KEY, **data},
        headers={"accept": "application/json"},
        timeout=30,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Error {resp.status_code} ao obter token: {resp.text}")
    tokens = resp.json()
    tokens["expires_at"] = time.time() + tokens["expires_in"]
    return tokens

def exchange_code(code: str) -> dict:
    return _post_token({
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": ML_URL_REDIRECT,
    })


def refresh_tokens(refresh_token: str) -> dict:
    return _post_token({
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    })


def save_tokens(tokens: dict) -> None:
    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = TOKEN_PATH.with_suffix(".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        json.dump(tokens, f, indent=2)
    tmp.replace(TOKEN_PATH)


def load_tokens() -> dict:
    if not TOKEN_PATH.exists():
        raise RuntimeError("Token não encontrado. Rode: python -m src.auth")
    return json.loads(TOKEN_PATH.read_text())


def get_access_token(force: bool = False) -> str:
    tokens = load_tokens()
    if force or time.time() > tokens["expires_at"] - MARGEM_EXPIRACAO:
        try:
            tokens = refresh_tokens(tokens["refresh_token"])
        except RuntimeError as e:
            raise RuntimeError(
                f"Refresh falhou ({e}). Rode de novo: python -m src.auth"
            ) from e
        save_tokens(tokens)
    return tokens["access_token"]


def _extract_code(texto: str) -> str:
    texto = texto.strip()
    if not texto.startswith("http"):
        return texto
    qs = parse_qs(urlparse(texto).query)
    if "code" not in qs:
        raise ValueError(f"URL sem 'code': {qs}")
    return qs["code"][0]


if __name__ == "__main__":
    print("1. Abra no navegador e autorize:\n")
    print(build_auth_url())
    colado = input("\n2. Cole a URL para onde foi redirecionado (ou só o code): ")
    tokens = exchange_code(_extract_code(colado))
    save_tokens(tokens)
    print(f"\nTokens salvos em {TOKEN_PATH} (user_id={tokens['user_id']})")
