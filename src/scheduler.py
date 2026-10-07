"""Roda as sincronizações periodicamente.

    python -m src.scheduler          # loop contínuo
    python -m src.scheduler --once   # uma rodada e sai (para cron/systemd timer)
"""
import fcntl
import logging
import sys
import time
from contextlib import contextmanager

from src.db import DB_PATH, init_db
from src.ingest import sync_anuncios, sync_pedidos
from src.log import configurar_logging

log = logging.getLogger(__name__)

# (nome, função, intervalo em segundos)
JOBS = [
    ("pedidos", sync_pedidos, 15 * 60),
    ("anuncios", sync_anuncios, 24 * 60 * 60),
]
CHECAGEM = 30  # de quanto em quanto tempo o loop vê se algum job venceu


@contextmanager
def _lock():
    """Impede duas execuções ao mesmo tempo (loop + cron, ou sync mais lenta que o intervalo)."""
    caminho = DB_PATH.parent / "scheduler.lock"
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with open(caminho, "w") as f:
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError("Já existe um scheduler/sync rodando") from None
        yield  # o lock cai quando o arquivo fecha


def _executar(nome: str, fn) -> None:
    # uma falha não pode derrubar o loop: loga e tenta de novo na próxima janela
    try:
        fn()
    except Exception:
        log.exception("job %s falhou", nome)


def rodar_uma_vez() -> None:
    with _lock():
        for nome, fn, _ in JOBS:
            _executar(nome, fn)


def rodar_loop() -> None:
    with _lock():
        proximo = {nome: 0.0 for nome, _, _ in JOBS}  # 0 = roda já na partida
        log.info("scheduler iniciado: %s", {n: f"{i}s" for n, _, i in JOBS})
        try:
            while True:
                agora = time.monotonic()
                for nome, fn, intervalo in JOBS:
                    if agora >= proximo[nome]:
                        _executar(nome, fn)
                        proximo[nome] = time.monotonic() + intervalo
                time.sleep(CHECAGEM)
        except KeyboardInterrupt:
            log.info("scheduler encerrado")


if __name__ == "__main__":
    configurar_logging()
    init_db()
    if "--once" in sys.argv:
        rodar_uma_vez()
    else:
        rodar_loop()
