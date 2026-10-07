import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import src.scheduler as s


class TestScheduler(unittest.TestCase):
    def setUp(self):
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        p = patch.object(s, "DB_PATH", Path(d.name) / "x.db")
        p.start()
        self.addCleanup(p.stop)

    def test_job_que_falha_nao_derruba_os_outros(self):
        quebra, ok = MagicMock(side_effect=RuntimeError("boom")), MagicMock()
        with patch.object(s, "JOBS", [("a", quebra, 1), ("b", ok, 1)]), \
             self.assertLogs("src.scheduler", "ERROR"):
            s.rodar_uma_vez()
        ok.assert_called_once()

    def test_segunda_instancia_e_bloqueada(self):
        with s._lock():
            with self.assertRaisesRegex(RuntimeError, "Já existe"):
                with s._lock():
                    pass

    def test_lock_e_liberado_ao_sair(self):
        with s._lock():
            pass
        with s._lock():
            pass


if __name__ == "__main__":
    unittest.main()
