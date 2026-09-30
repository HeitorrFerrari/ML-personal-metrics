import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "app.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS produtos (
    id              TEXT PRIMARY KEY,
    titulo          TEXT NOT NULL,
    sku             TEXT,
    categoria       TEXT,
    ativo           INTEGER NOT NULL DEFAULT 1,
    criado_em       TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS custos (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    produto_id      TEXT NOT NULL,
    custo_unitario  REAL NOT NULL,
    vigente_desde   TEXT NOT NULL,
    FOREIGN KEY (produto_id) REFERENCES produtos(id)
);

CREATE TABLE IF NOT EXISTS pedidos (
    id              TEXT PRIMARY KEY,
    data_pedido     TEXT NOT NULL,
    status          TEXT NOT NULL,
    valor_total     REAL NOT NULL DEFAULT 0,
    frete_vendedor  REAL NOT NULL DEFAULT 0,
    comprador_id    TEXT
);

CREATE TABLE IF NOT EXISTS itens_pedido (
    pedido_id       TEXT NOT NULL,
    produto_id      TEXT NOT NULL,
    quantidade      INTEGER NOT NULL,
    preco_unitario  REAL NOT NULL,
    taxa_ml         REAL NOT NULL DEFAULT 0,
    PRIMARY KEY (pedido_id, produto_id),
    FOREIGN KEY (pedido_id)  REFERENCES pedidos(id),
    FOREIGN KEY (produto_id) REFERENCES produtos(id)
);

CREATE TABLE IF NOT EXISTS precos_proprios (
    id              INTEGER PRIMARY KEY,
    produto_id      TEXT NOT NULL,
    preco           REAL NOT NULL,
    coletado_em     TEXT NOT NULL,
    FOREIGN KEY (produto_id) REFERENCES produtos(id)
);

CREATE TABLE IF NOT EXISTS precos_concorrentes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    produto_id      TEXT NOT NULL,         -- seu produto comparado
    concorrente_id  TEXT NOT NULL,         -- MLB do concorrente
    vendedor        TEXT,
    preco           REAL NOT NULL,
    coletado_em     TEXT NOT NULL,
    FOREIGN KEY (produto_id) REFERENCES produtos(id)
);

CREATE TABLE IF NOT EXISTS sync_state (
    recurso         TEXT PRIMARY KEY,
    ultima_sync     TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_pedidos_data     ON pedidos(data_pedido);
CREATE INDEX IF NOT EXISTS idx_itens_produto    ON itens_pedido(produto_id);
CREATE INDEX IF NOT EXISTS idx_custos_produto   ON custos(produto_id, vigente_desde);
CREATE INDEX IF NOT EXISTS idx_pp_produto_data  ON precos_proprios(produto_id, coletado_em);
CREATE INDEX IF NOT EXISTS idx_pc_produto_data  ON precos_concorrentes(produto_id, coletado_em);
"""


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")  # desligado por padrão no SQLite
    conn.row_factory = sqlite3.Row  # acesso por nome: row["titulo"]
    return conn


def init_db() -> None:
    conn = get_connection()
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    init_db()
    print(f"Banco criado em {DB_PATH}")