import logging
import sys


def configurar_logging(nivel: int = logging.INFO) -> None:
    """Chame uma vez, no ponto de entrada (main, scheduler, python -m ...)."""
    logging.basicConfig(
        level=nivel,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stdout,
    )
