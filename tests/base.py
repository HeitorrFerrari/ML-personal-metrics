import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import src.db as db


class BancoTemporario(unittest.TestCase):
    """Cada teste roda num banco novo e descartável; o data/app.db real nunca é tocado."""

    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.addCleanup(self._dir.cleanup)
        patcher = patch.object(db, "DB_PATH", Path(self._dir.name) / "teste.db")
        patcher.start()
        self.addCleanup(patcher.stop)
        db.init_db()

    def conta(self, tabela: str) -> int:
        conn = db.get_connection()
        try:
            return conn.execute(f"SELECT COUNT(*) FROM {tabela}").fetchone()[0]
        finally:
            conn.close()
