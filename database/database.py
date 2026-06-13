import os
from sqlalchemy import create_engine, text  # type: ignore

MYSQL_BASE_URI = "mysql+pymysql://root:@localhost"
DB_NAME = "bi_customer"
MYSQL_URI = f"{MYSQL_BASE_URI}/{DB_NAME}"
SQLITE_URI = "sqlite:///d:/Project/customer_churn_bi/database/bi_customer.db"

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
    db_dir = "d:/Project/customer_churn_bi/database"
    os.makedirs(db_dir, exist_ok=True)
    engine = create_engine(SQLITE_URI)
    db_type = "SQLite (Fallback)"
    db_uri = SQLITE_URI

def get_db_status():
    """Mengembalikan jenis database aktif dan URI-nya"""
    return db_type, db_uri