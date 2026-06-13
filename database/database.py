import os
from sqlalchemy import create_engine, text

MYSQL_BASE_URI = "mysql+pymysql://root:@localhost"
DB_NAME = "bi_customer"
MYSQL_URI = f"{MYSQL_BASE_URI}/{DB_NAME}"
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
DB_DIR = os.path.join(ROOT_DIR, "database")
SQLITE_DB_PATH = os.path.join(DB_DIR, "bi_customer.db")
SQLITE_DB_PATH = SQLITE_DB_PATH.replace('\\', '/')
SQLITE_URI = "sqlite:///" + SQLITE_DB_PATH

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
except Exception as e:
    # Jika MySQL offline, gunakan SQLite lokal di folder database/
    os.makedirs(DB_DIR, exist_ok=True)
    engine = create_engine(SQLITE_URI)
    db_type = "SQLite (Fallback)"
    db_uri = SQLITE_URI

def get_db_status():
    """Mengembalikan jenis database aktif dan URI-nya"""
    return db_type, db_uri