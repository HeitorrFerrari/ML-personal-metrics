import _sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR/ "data" / "app.db"

SCHEMA = """
    CREATE TABLE IF NOT EXISTS produtos (
    id TEXT PRIMARY KEY,
    titulo TEXT NOT NULL,
    sku TEXT,
    categoria TEXT,
    ativo INTEGER NOT NULL DEFAULT 1,
    criado_em TEXT NOT NULL DEFAULT (datetime('now'))
    );
    
    CREATE TABLE IF NOT EXISTS custos (
    id TEXT PRIMARY KEY,
    produto_id TEXT NOT NULL,
    custo_unitario REAL NOT NULL,
    vigente_desde TEXT NOT NULL,
    FOREIGN KEY (produto_id) REFERENCES produtos (id)
    );
    
    
    CREATE TABLE IF NOT EXISTS pedidos (
    id TEXT PRIMARY KEY,
    data_pedido TEXT NOT NULL,
    quantidade INTEGER NOT NULL DEFAULT,
    status TEXT NOT NULL,
    comprador_id TEXT,
    );
    
    """