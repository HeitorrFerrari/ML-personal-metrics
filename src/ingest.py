import sqlite3
from datetime import datetime, timedelta, timezone

from src.db import get_connection, init_db
from src.ml_client import get_me, get_orders

RECURSO = "pedidos"
JANELA_REPROCESSO = timedelta(days=7)

def _iso(dt: datetime) -> str:
    return dt.isoformat(timespec="milliseconds")

def _ler_ultima_sync(conn: sqlite3.Connection) -> str | None:
    row