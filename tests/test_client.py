import unittest
from unittest.mock import MagicMock, patch

import src.ml_client as c


def resp(code, body=None, headers=None):
    r = MagicMock()
    r.status_code = code
    r.json.return_value = body if body is not None else {}
    r.headers = headers or {}
    r.text = "corpo"
    return r


class TestGet(unittest.TestCase):
    def setUp(self):
        for alvo in (
            patch.object(c, "get_access_token", return_value="t"),
            patch.object(c.time, "sleep"),
        ):
            alvo.start()
            self.addCleanup(alvo.stop)

    def _sessao(self, *respostas):
        p = patch.object(c._session, "get", side_effect=list(respostas))
        m = p.start()
        self.addCleanup(p.stop)
        return m

    def test_sucesso(self):
        self._sessao(resp(200, {"ok": 1}))
        self.assertEqual(c.get("/x"), {"ok": 1})

    def test_401_renova_token_e_repete(self):
        m = self._sessao(resp(401), resp(200, {"ok": 1}))
        self.assertEqual(c.get("/x"), {"ok": 1})
        self.assertEqual(m.call_count, 2)

    def test_401_repetido_vira_erro(self):
        self._sessao(resp(401), resp(401))
        with self.assertRaisesRegex(RuntimeError, "401"):
            c.get("/x")

    def test_429_e_5xx_repetem(self):
        self._sessao(resp(429), resp(500), resp(200, {"ok": 1}))
        self.assertEqual(c.get("/x"), {"ok": 1})

    def test_5xx_esgota_tentativas(self):
        m = self._sessao(*[resp(500)] * c.MAX_TENTATIVAS)
        with self.assertRaisesRegex(RuntimeError, "500"):
            c.get("/x")
        self.assertEqual(m.call_count, c.MAX_TENTATIVAS)

    def test_404_nao_repete(self):
        m = self._sessao(resp(404))
        with self.assertRaises(RuntimeError):
            c.get("/x")
        self.assertEqual(m.call_count, 1)

    def test_respeita_retry_after(self):
        self._sessao(resp(429, headers={"Retry-After": "7"}), resp(200, {}))
        c.get("/x")
        c.time.sleep.assert_called_with(7.0)


class TestPaginacao(unittest.TestCase):
    def test_percorre_todas_as_paginas(self):
        paginas = [
            {"results": [1, 2], "paging": {"total": 5}},
            {"results": [3, 4], "paging": {"total": 5}},
            {"results": [5], "paging": {"total": 5}},
        ]
        with patch.object(c, "get", side_effect=paginas) as g:
            self.assertEqual(list(c.get_paginated("/y", limit=2)), [1, 2, 3, 4, 5])
        self.assertEqual([x.args[1]["offset"] for x in g.call_args_list], [0, 2, 4])

    def test_pagina_vazia_encerra(self):
        with patch.object(c, "get", return_value={"results": [], "paging": {"total": 99}}):
            self.assertEqual(list(c.get_paginated("/y")), [])


class TestItens(unittest.TestCase):
    def test_multiget_descarta_erros(self):
        resposta = [{"code": 200, "body": {"id": "A"}}, {"code": 404, "body": {}}]
        with patch.object(c, "get", return_value=resposta):
            self.assertEqual(c.get_items(["A", "B"]), [{"id": "A"}])

    def test_multiget_limite_de_20(self):
        with self.assertRaises(ValueError):
            c.get_items([str(i) for i in range(21)])


if __name__ == "__main__":
    unittest.main()
