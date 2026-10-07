import logging
import sqlite3
from datetime import datetime, timedelta, timezone

from src.db import get_connection, init_db
from src.log import configurar_logging
from src.ml_client import get_items, get_me, get_orders, get_user_items

log = logging.getLogger(__name__)

RECURSO = "pedidos"
LOTE_ANUNCIOS = 20  # limite do multiget de itens
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
        log.info("pedidos: %d sincronizados (desde=%s)", total, desde)
        return total
    finally:
        conn.close()


def _salvar_anuncio(conn: sqlite3.Connection, item: dict, coletado_em: str) -> None:
    produto_id = str(item["id"])

    conn.execute(
        """
        INSERT INTO produtos (id, titulo, sku, categoria, ativo)
        VALUES (?, ?, ?, ?, 1)
        ON CONFLICT(id) DO UPDATE SET
            titulo    = excluded.titulo,
            sku       = COALESCE(excluded.sku, sku),
            categoria = COALESCE(excluded.categoria, categoria),
            ativo     = 1
        """,
        (
            produto_id,
            item.get("title") or produto_id,
            item.get("seller_custom_field"),
            item.get("category_id"),
        ),
    )

    # histórico: cada coleta é uma linha nova, nunca sobrescreve
    if item.get("price") is not None:
        conn.execute(
            "INSERT INTO precos_proprios (produto_id, preco, coletado_em) VALUES (?, ?, ?)",
            (produto_id, item["price"], coletado_em),
        )


def sync_anuncios() -> int:
    """Atualiza o catálogo com os anúncios ativos e guarda um snapshot do preço de cada um."""
    coletado_em = _iso(datetime.now(timezone.utc))
    ids = [str(i) for i in get_user_items(get_me()["id"])]

    conn = get_connection()
    try:
        with conn:
            # quem não voltar na listagem fica inativo; os que voltarem são reativados abaixo
            conn.execute("UPDATE produtos SET ativo = 0")
            total = 0
            for i in range(0, len(ids), LOTE_ANUNCIOS):
                for item in get_items(ids[i:i + LOTE_ANUNCIOS]):
                    _salvar_anuncio(conn, item, coletado_em)
                    total += 1
        log.info("anuncios: %d sincronizados", total)
        return total
    finally:
        conn.close()


if __name__ == "__main__":
    configurar_logging()
    init_db()
    print(f"{sync_pedidos()} pedidos sincronizados")
    print(f"{sync_anuncios()} anúncios sincronizados")
