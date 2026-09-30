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
    
    """