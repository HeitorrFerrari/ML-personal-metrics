import unittest

import src.db as db
import src.metrics as m
from tests.base import BancoTemporario


class TestMetrics(BancoTemporario):
    def setUp(self):
        super().setUp()
        conn = db.get_connection()
        conn.executescript("""
        INSERT INTO produtos (id,titulo) VALUES ('A','Fone'),('B','Cabo');
        INSERT INTO custos (produto_id,custo_unitario,vigente_desde) VALUES
            ('A',50,'2026-01-01'),('A',60,'2026-10-01');
        INSERT INTO pedidos (id,data_pedido,status,comprador_id) VALUES
            ('1','2026-09-20T10:00:00.000-03:00','paid','x'),
            ('2','2026-10-05T10:00:00.000-03:00','paid','x'),
            ('3','2026-10-06T10:00:00.000-03:00','cancelled','x');
        INSERT INTO itens_pedido (pedido_id,produto_id,quantidade,preco_unitario,taxa_ml) VALUES
            ('1','A',1,100,10), ('2','A',2,100,10), ('2','B',1,30,3), ('3','A',5,100,10);
        INSERT INTO precos_proprios (produto_id,preco,coletado_em) VALUES ('A',100,'2026-10-05');
        INSERT INTO precos_concorrentes (produto_id,concorrente_id,preco,coletado_em) VALUES
            ('A','M1',90,'2026-10-01'),('A','M2',80,'2026-10-05'),('A','M3',120,'2026-10-05');
        """)
        conn.commit()
        conn.close()

    def test_resumo(self):
        r = m.resumo()
        self.assertEqual((r["receita"], r["pedidos"], r["unidades"]), (330, 2, 4))
        self.assertEqual(r["ticket_medio"], 165)
        self.assertEqual(r["itens_sem_custo"], 1)

    def test_margem_usa_o_custo_da_data_da_venda(self):
        # (100-10-50) + (200-20-2*60) = 40 + 60
        self.assertEqual(m.resumo()["margem"], 100)

    def test_cancelado_fica_fora(self):
        self.assertEqual(m.resumo("2026-10-06", "2026-10-07")["receita"], 0)

    def test_filtro_de_periodo(self):
        self.assertEqual(m.resumo("2026-10-01", "2026-10-31")["receita"], 230)

    def test_periodo_vazio_nao_divide_por_zero(self):
        r = m.resumo("2030-01-01", "2030-02-01")
        self.assertEqual((r["ticket_medio"], r["margem_pct"]), (0, None))

    def test_top_produtos_ordena_por_receita(self):
        self.assertEqual([p["produto_id"] for p in m.top_produtos()], ["A", "B"])

    def test_receita_diaria(self):
        self.assertEqual([d["dia"] for d in m.receita_diaria()], ["2026-09-20", "2026-10-05"])

    def test_posicao_usa_so_a_ultima_coleta(self):
        p = m.posicao_preco()[0]
        self.assertEqual((p["menor_concorrente"], p["media_concorrentes"]), (80, 100))


if __name__ == "__main__":
    unittest.main()
