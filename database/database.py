from pathlib import Path

from sqlalchemy import create_engine, text

MYSQL_BASE_URI = "mysql+pymysql://root:@localhost"
DB_NAME = "bi_customer"
MYSQL_URI = f"{MYSQL_BASE_URI}/{DB_NAME}"

DB_DIR = Path(__file__).resolve().parent
SQLITE_URI = f"sqlite:///{DB_DIR / 'bi_customer.db'}"

engine = None
db_type = "SQLite (Fallback)"
db_uri = SQLITE_URI

try:
    # Cek apakah server MySQL lokal menyala dengan timeout cepat
    temp_engine = create_engine(MYSQL_BASE_URI, connect_args={"connect_timeout": 2})
    with temp_engine.connect() as conn:
        # Buat database jika belum ada
        conn.execute(text(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}"))
    
    # Hubungkan engine ke database bi_customer
    engine = create_engine(MYSQL_URI)
    with engine.connect() as conn:
        pass
    db_type = "MySQL"
    db_uri = MYSQL_URI
except Exception:
    # Jika MySQL offline, gunakan SQLite lokal di folder database/
    DB_DIR.mkdir(parents=True, exist_ok=True)
    engine = create_engine(SQLITE_URI)
    db_type = "SQLite (Fallback)"
    db_uri = SQLITE_URI

def get_db_status():
    """Mengembalikan jenis database aktif dan URI-nya"""
    return db_type, db_uri