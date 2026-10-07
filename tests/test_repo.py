import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import src.db as db
import src.repo as repo
from tests.base import BancoTemporario


class TestCustos(BancoTemporario):
    def setUp(self):
        super().setUp()
        conn = db.get_connection()
        conn.execute("INSERT INTO produtos (id,titulo) VALUES ('A','Fone')")
        conn.commit()
        conn.close()

    def test_sem_custo_ate_cadastrar(self):
        self.assertEqual([p["id"] for p in repo.listar_produtos_sem_custo()], ["A"])
        repo.adicionar_custo("A", 50, "2026-01-01")
        self.assertEqual(repo.listar_produtos_sem_custo(), [])

    def test_historico_e_preservado(self):
        repo.adicionar_custo("A", 50, "2026-01-01")
        repo.adicionar_custo("A", 60, "2026-10-01")
        self.assertEqual([c["custo_unitario"] for c in repo.listar_custos("A")], [60, 50])

    def test_produto_inexistente(self):
        with self.assertRaisesRegex(ValueError, "não existe"):
            repo.adicionar_custo("ZZZ", 10)

    def test_valida_custo_e_data(self):
        with self.assertRaises(ValueError):
            repo.adicionar_custo("A", -1)
        with self.assertRaises(ValueError):
            repo.adicionar_custo("A", 10, "01/10/2026")
        self.assertEqual(self.conta("custos"), 0)


class TestMigracao(unittest.TestCase):
    def test_banco_antigo_ganha_colunas_novas(self):
        with tempfile.TemporaryDirectory() as d, \
             patch.object(db, "DB_PATH", Path(d) / "antigo.db"):
            conn = sqlite3.connect(db.DB_PATH)
            conn.execute("CREATE TABLE pedidos (id TEXT PRIMARY KEY, data_pedido TEXT NOT NULL, "
                         "status TEXT NOT NULL, comprador_id TEXT)")
            conn.commit()
            conn.close()

            db.init_db()
            db.init_db()  # idempotente

            conn = db.get_connection()
            colunas = {r["name"] for r in conn.execute("PRAGMA table_info(pedidos)")}
            conn.close()
            self.assertTrue({"valor_total", "frete_vendedor"} <= colunas)


if __name__ == "__main__":
    unittest.main()
