"""Dados que são seus, não do ML: custos dos produtos."""
from datetime import date

from src.db import get_connection


def adicionar_custo(produto_id: str, custo_unitario: float, vigente_desde: str | None = None) -> None:
    """Registra um custo a partir de `vigente_desde` ('YYYY-MM-DD', padrão: hoje).

    Não sobrescreve o histórico: um custo novo vale da data dele em diante, e as
    vendas anteriores continuam usando o custo da época.
    """
    if custo_unitario < 0:
        raise ValueError("custo_unitario não pode ser negativo")

    vigente_desde = vigente_desde or date.today().isoformat()
    date.fromisoformat(vigente_desde)

    conn = get_connection()
    try:
        with conn:
            existe = conn.execute(
                "SELECT 1 FROM produtos WHERE id = ?", (produto_id,)
            ).fetchone()
            if not existe:
                raise ValueError(f"Produto {produto_id} não existe")
            conn.execute(
                "INSERT INTO custos (produto_id, custo_unitario, vigente_desde) VALUES (?, ?, ?)",
                (produto_id, custo_unitario, vigente_desde),
            )
    finally:
        conn.close()


def listar_produtos_sem_custo() -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT p.id, p.titulo, p.sku
            FROM produtos p
            WHERE NOT EXISTS (SELECT 1 FROM custos c WHERE c.produto_id = p.id)
            ORDER BY p.titulo
            """
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def listar_custos(produto_id: str) -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT custo_unitario, vigente_desde FROM custos
            WHERE produto_id = ? ORDER BY vigente_desde DESC
            """,
            (produto_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


if __name__ == "__main__":
    import sys

    if len(sys.argv) >= 3:
        adicionar_custo(sys.argv[1], float(sys.argv[2]), *sys.argv[3:4])
        print(f"Custo de {sys.argv[1]} registrado")
    else:
        sem_custo = listar_produtos_sem_custo()
        print(f"{len(sem_custo)} produtos sem custo")
        for p in sem_custo:
            print(f"  {p['id']}  {p['titulo']}")
        print("\nUso: python -m src.repo <produto_id> <custo> [AAAA-MM-DD]")
