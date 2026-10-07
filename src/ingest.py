import sqlite3
from datetime import datetime, timedelta, timezone

from src.db import get_connection, init_db
from src.ml_client import get_me, get_orders

RECURSO = "pedidos"
JANELA_REPROCESSO = timedelta(days=7)  # pedidos mudam de status depois de criados


def _iso(dt: datetime) -> str:
    return dt.isoformat(timespec="milliseconds")


def _ler_ultima_sync(conn: sqlite3.Connection) -> str | None:
    row = conn.execute(
        "SELECT ultima_sync FROM sync_state WHERE recurso = ?", (RECURSO,)
    ).fetchone()
    return row["ultima_sync"] if row else None


def _gravar_sync(conn: sqlite3.Connection, quando: str) -> None:
    conn.execute(
        """
        INSERT INTO sync_state (recurso, ultima_sync) VALUES (?, ?)
        ON CONFLICT(recurso) DO UPDATE SET ultima_sync = excluded.ultima_sync
        """,
        (RECURSO, quando),
    )


def _salvar_pedido(conn: sqlite3.Connection, order: dict) -> None:
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
            order["date_created"],
            order["status"],
            order.get("total_amount") or 0,
            str(order["buyer"]["id"]) if order.get("buyer") else None,
        ),
    )

    for oi in order.get("order_items", []):
        item = oi["item"]
        produto_id = str(item["id"])

        # produto antes do item, por causa da FK
        conn.execute(
            """
            INSERT INTO produtos (id, titulo, sku, categoria)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                titulo = excluded.titulo,
                sku    = excluded.sku
            """,
            (
                produto_id,
                item.get("title") or produto_id,
                item.get("seller_sku"),
                item.get("category_id"),
            ),
        )

        conn.execute(
            """
            INSERT INTO itens_pedido
                (pedido_id, produto_id, quantidade, preco_unitario, taxa_ml)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(pedido_id, produto_id) DO UPDATE SET
                quantidade     = excluded.quantidade,
                preco_unitario = excluded.preco_unitario,
                taxa_ml        = excluded.taxa_ml
            """,
            (
                pedido_id,
                produto_id,
                oi["quantity"],
                oi["unit_price"],
                oi.get("sale_fee") or 0,
            ),
        )


def sync_pedidos() -> int:
    inicio = datetime.now(timezone.utc)
    conn = get_connection()
    try:
        ultima = _ler_ultima_sync(conn)
        desde = None
        if ultima:
            desde = _iso(datetime.fromisoformat(ultima) - JANELA_REPROCESSO)

        seller_id = get_me()["id"]
        total = 0
        with conn:  # uma transação: ou grava tudo, ou nada
            for order in get_orders(seller_id, desde=desde):
                _salvar_pedido(conn, order)
                total += 1
            _gravar_sync(conn, _iso(inicio))
        return total
    finally:
        conn.close()


if __name__ == "__main__":
    init_db()
    print(f"{sync_pedidos()} pedidos sincronizados")
