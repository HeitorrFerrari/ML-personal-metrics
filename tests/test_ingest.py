import unittest
from unittest.mock import patch

import src.db as db
import src.ingest as ing
from tests.base import BancoTemporario

PEDIDO = {
    "id": 1001,
    "date_created": "2026-10-01T10:00:00.000-03:00",
    "status": "paid",
    "total_amount": 200.0,
    "buyer": {"id": 77},
    "order_items": [{
        "item": {"id": "MLB1", "title": "Fone", "seller_sku": "S1", "category_id": "C"},
        "quantity": 2, "unit_price": 100.0, "sale_fee": 12.0,
    }],
}


def sync(pedidos):
    with patch.object(ing, "get_me", return_value={"id": 5}), \
         patch.object(ing, "get_orders", return_value=iter(pedidos)) as go:
        n = ing.sync_pedidos()
    return n, go.call_args.kwargs["desde"]


class TestPedidos(BancoTemporario):
    def test_primeira_sync_sem_filtro_de_data(self):
        n, desde = sync([PEDIDO])
        self.assertEqual((n, desde), (1, None))

    def test_idempotente_e_atualiza_status(self):
        sync([PEDIDO])
        sync([dict(PEDIDO, status="cancelled")])
        self.assertEqual(
            [self.conta(t) for t in ("pedidos", "itens_pedido", "produtos", "sync_state")],
            [1, 1, 1, 1],
        )
        conn = db.get_connection()
        self.assertEqual(conn.execute("SELECT status FROM pedidos").fetchone()[0], "cancelled")
        conn.close()

    def test_segunda_sync_recua_a_janela_de_reprocesso(self):
        sync([PEDIDO])
        _, desde = sync([PEDIDO])
        self.assertIsNotNone(desde)

    def test_falha_no_meio_nao_grava_nada(self):
        quebrado = dict(PEDIDO, id=2, order_items=[{"item": {"id": "X"}}])  # sem quantity
        with self.assertRaises(KeyError):
            sync([PEDIDO, quebrado])
        self.assertEqual((self.conta("pedidos"), self.conta("sync_state")), (0, 0))


ANUNCIO = {"id": "MLB1", "title": "Fone", "seller_custom_field": "S1",
           "category_id": "C", "price": 99.9}


def sync_anuncios(ids, itens):
    with patch.object(ing, "get_me", return_value={"id": 5}), \
         patch.object(ing, "get_user_items", return_value=iter(ids)), \
         patch.object(ing, "get_items", return_value=itens):
        return ing.sync_anuncios()


class TestAnuncios(BancoTemporario):
    def test_grava_produto_e_historico_de_preco(self):
        sync_anuncios(["MLB1"], [ANUNCIO])
        sync_anuncios(["MLB1"], [dict(ANUNCIO, price=89.9)])
        self.assertEqual((self.conta("produtos"), self.conta("precos_proprios")), (1, 2))

    def test_anuncio_que_sumiu_fica_inativo(self):
        sync_anuncios(["MLB1"], [ANUNCIO])
        sync_anuncios([], [])
        conn = db.get_connection()
        self.assertEqual(conn.execute("SELECT ativo FROM produtos").fetchone()[0], 0)
        conn.close()

    def test_sku_nao_e_apagado_por_anuncio_sem_sku(self):
        sync_anuncios(["MLB1"], [ANUNCIO])
        sync_anuncios(["MLB1"], [dict(ANUNCIO, seller_custom_field=None)])
        conn = db.get_connection()
        self.assertEqual(conn.execute("SELECT sku FROM produtos").fetchone()[0], "S1")
        conn.close()


if __name__ == "__main__":
    unittest.main()
