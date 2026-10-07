from src.db import get_connection

STATUS_VALIDOS = ("paid",)

TAXA_SQL = "ii.taxa_ml * ii.quantidade"

# Custo vigente na data da venda: o mais recente com vigente_desde <= data do pedido.
# Compara como texto ISO 8601, então vigente_desde deve estar em 'YYYY-MM-DD'.
CUSTO_SQL = """
    (SELECT c.custo_unitario FROM custos c
     WHERE c.produto_id = ii.produto_id AND c.vigente_desde <= p.data_pedido
     ORDER BY c.vigente_desde DESC LIMIT 1)
"""


def _linhas_cte() -> str:
    """CTE com uma linha por item vendido, já com receita, taxa e custo calculados."""
    marcadores = ",".join("?" * len(STATUS_VALIDOS))
    return f"""
        WITH linhas AS (
            SELECT
                p.id                                 AS pedido_id,
                p.data_pedido                        AS data_pedido,
                ii.produto_id                        AS produto_id,
                pr.titulo                            AS titulo,
                ii.quantidade                        AS quantidade,
                ii.quantidade * ii.preco_unitario    AS receita,
                {TAXA_SQL}                           AS taxa,
                {CUSTO_SQL}                          AS custo_unitario
            FROM itens_pedido ii
            JOIN pedidos  p  ON p.id  = ii.pedido_id
            JOIN produtos pr ON pr.id = ii.produto_id
            WHERE p.status IN ({marcadores})
              AND p.data_pedido >= ? AND p.data_pedido < ?
        )
    """


def _consultar(sql: str, params: tuple) -> list[dict]:
    conn = get_connection()
    try:
        return [dict(row) for row in conn.execute(sql, params).fetchall()]
    finally:
        conn.close()


def _params(desde: str, ate: str) -> tuple:
    return (*STATUS_VALIDOS, desde, ate)


def resumo(desde: str = "0000", ate: str = "9999") -> dict:
    """KPIs do período [desde, ate). Datas em 'YYYY-MM-DD'.

    Margem considera só itens com custo cadastrado; os demais vão em itens_sem_custo.
    """
    sql = _linhas_cte() + """
        SELECT
            COALESCE(SUM(receita), 0)                       AS receita,
            COUNT(DISTINCT pedido_id)                       AS pedidos,
            COALESCE(SUM(quantidade), 0)                    AS unidades,
            COALESCE(SUM(taxa), 0)                          AS taxas,
            COALESCE(SUM(CASE WHEN custo_unitario IS NOT NULL
                         THEN receita END), 0)              AS receita_com_custo,
            COALESCE(SUM(CASE WHEN custo_unitario IS NOT NULL
                         THEN receita - taxa - custo_unitario * quantidade END), 0) AS margem,
            COALESCE(SUM(custo_unitario IS NULL), 0)        AS itens_sem_custo
        FROM linhas
    """
    r = _consultar(sql, _params(desde, ate))[0]
    r["ticket_medio"] = r["receita"] / r["pedidos"] if r["pedidos"] else 0.0
    r["margem_pct"] = (
        r["margem"] / r["receita_com_custo"] * 100 if r["receita_com_custo"] else None
    )
    return r


def receita_diaria(desde: str = "0000", ate: str = "9999") -> list[dict]:
    sql = _linhas_cte() + """
        SELECT substr(data_pedido, 1, 10) AS dia,
               SUM(receita)               AS receita,
               COUNT(DISTINCT pedido_id)  AS pedidos
        FROM linhas
        GROUP BY dia
        ORDER BY dia
    """
    return _consultar(sql, _params(desde, ate))


def top_produtos(desde: str = "0000", ate: str = "9999", limite: int = 10) -> list[dict]:
    sql = _linhas_cte() + """
        SELECT produto_id, titulo,
               SUM(quantidade) AS unidades,
               SUM(receita)    AS receita,
               SUM(CASE WHEN custo_unitario IS NOT NULL
                   THEN receita - taxa - custo_unitario * quantidade END) AS margem
        FROM linhas
        GROUP BY produto_id, titulo
        ORDER BY receita DESC
        LIMIT ?
    """
    return _consultar(sql, (*_params(desde, ate), limite))


def posicao_preco() -> list[dict]:
    """Seu preço mais recente contra o menor e a média dos concorrentes na última coleta."""
    sql = """
        SELECT * FROM (
            SELECT
                pr.id     AS produto_id,
                pr.titulo AS titulo,
                (SELECT preco FROM precos_proprios
                 WHERE produto_id = pr.id ORDER BY coletado_em DESC LIMIT 1) AS meu_preco,
                (SELECT MIN(preco) FROM precos_concorrentes c
                 WHERE c.produto_id = pr.id AND c.coletado_em =
                    (SELECT MAX(coletado_em) FROM precos_concorrentes
                     WHERE produto_id = pr.id)) AS menor_concorrente,
                (SELECT AVG(preco) FROM precos_concorrentes c
                 WHERE c.produto_id = pr.id AND c.coletado_em =
                    (SELECT MAX(coletado_em) FROM precos_concorrentes
                     WHERE produto_id = pr.id)) AS media_concorrentes
            FROM produtos pr
        )
        WHERE meu_preco IS NOT NULL
        ORDER BY titulo
    """
    return _consultar(sql, ())


if __name__ == "__main__":
    print(resumo())
