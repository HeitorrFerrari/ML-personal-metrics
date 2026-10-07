import os

for _chave in ("ML_CLIENT_ID", "ML_SECRET_KEY", "ML_URL_REDIRECT"):
    os.environ.setdefault(_chave, "teste")
