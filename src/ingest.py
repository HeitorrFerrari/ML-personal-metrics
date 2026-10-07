import sqlite3
from datetime import datetime, timedelta, timezone

from src.db import get_connection, init_db
from src.ml_client import get_me, get_orders

RECURSO = "pedidos"
JANELA_REPROCESSO = timedelta(days=7)

def _iso(dt: datetime) -> str:
    return dt.isoformat(timespec="milliseconds")

def _ler_ultima_sync(conn: sqlite3.Connection) -> str | None:
    row = conn.execute(
        "SELECT ultima_sync FROM sync_state WHERE recursos = ?", (RECURSO, )
    ).fetchone()
    return row["ultima_sync"] if row else None

def _gravar_sync(conn: sqlite3.Conncection, quando: str) -> None:
    conn.execute(
        """
        INSERT INTO sync_state (recurso, ultima_sync) VALUES (?, ?)
        ON CONFLICT(recurso) DO UPDATE SET ultima_sync = excluded.ultima_sync
        """,
        (RECURSO, quando),
    )

def _salvar_pedido(conn: sqlite3.Connection, order:dict) -> None:
    pedido_id = str(order["id"])

    conn.execute(
        """
                INSERT INTO pedidos (id, data_pedido, status, valor_total, comprador_id)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    status      = excluded.status,
                    valor_total = excluded.valor_total
                """,
        (
            pedido_id,
            order["data_created"],
            order
        )
    )