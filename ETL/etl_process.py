import os
from pathlib import Path

import pandas as pd
from sqlalchemy import text

from database.database import engine, get_db_status

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DB_DIR = PROJECT_ROOT / "database"

def init_tables(log_callback=None):
    """Membuat ulang tabel schema database jika diperlukan"""
    db_type, _ = get_db_status()
    def log(msg):
        if log_callback:
            log_callback(msg)
        else:
            print(msg)

    log(f"Menginisialisasi skema tabel untuk database: {db_type}")
    
    if db_type == "MySQL":
        sql_path = DB_DIR / "bi_customer.sql"
        if os.path.exists(sql_path):
            log("Membaca file skema bi_customer.sql untuk MySQL...")
            with open(sql_path, "r", encoding="utf-8") as f:
                sql_content = f.read()
            
            statements = sql_content.split(";")
            with engine.connect() as conn:
                # Matikan foreign key checks sementara untuk membersihkan tabel lama
                conn.execute(text("SET FOREIGN_KEY_CHECKS = 0;"))
                conn.execute(text("DROP TABLE IF EXISTS fact_churn;"))
                conn.execute(text("DROP TABLE IF EXISTS dim_customer;"))
                conn.execute(text("DROP TABLE IF EXISTS dim_contract;"))
                conn.execute(text("DROP TABLE IF EXISTS dim_payment;"))
                conn.execute(text("DROP TABLE IF EXISTS dim_services;"))
                conn.execute(text("DROP TABLE IF EXISTS dim_tenure;"))
                
                # Eksekusi script DDL satu per satu
                for statement in statements:
                    stmt = statement.strip()
                    if not stmt:
                        continue
                    if stmt.upper().startswith("CREATE DATABASE") or stmt.upper().startswith("USE "):
                        continue
                    if stmt.upper() in ["START TRANSACTION", "COMMIT", "ROLLBACK"]:
                        continue
                    try:
                        conn.execute(text(stmt))
                    except Exception as e:
                        log(f"Peringatan saat eksekusi DDL MySQL: {str(e)[:150]}")
                
                conn.execute(text("SET FOREIGN_KEY_CHECKS = 1;"))
            log("Skema MySQL berhasil diinisialisasi.")
        else:
            log("Peringatan: File bi_customer.sql tidak ditemukan. Menggunakan tabel yang sudah ada.")
    else:
        # SQLite
        log("Membuat tabel SQLite lokal...")
        sqlite_ddl = [
            "DROP TABLE IF EXISTS fact_churn;",
            "DROP TABLE IF EXISTS dim_customer;",
            "DROP TABLE IF EXISTS dim_contract;",
            "DROP TABLE IF EXISTS dim_payment;",
            "DROP TABLE IF EXISTS dim_services;",
            "DROP TABLE IF EXISTS dim_tenure;",
            """CREATE TABLE dim_customer (
                customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer TEXT UNIQUE,
                gender TEXT,
                seniorCitizen TEXT,
                partner TEXT,
                dependents TEXT
            );""",
            """CREATE TABLE dim_contract (
                contract_id INTEGER PRIMARY KEY AUTOINCREMENT,
                contract TEXT,
                contractRiskLevel TEXT,
                paperlessBilling TEXT
            );""",
            """CREATE TABLE dim_payment (
                payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                paymentMethod TEXT,
                paymentCategory TEXT
            );""",
            """CREATE TABLE dim_services (
                service_id INTEGER PRIMARY KEY AUTOINCREMENT,
                phoneService TEXT,
                multipleLines TEXT,
                internetService TEXT,
                onlineSecurity TEXT,
                onlineBackup TEXT,
                deviceProtection TEXT,
                techSupport TEXT,
                streamingTV TEXT,
                streamingMovies TEXT,
                serviceCount INTEGER
            );""",
            """CREATE TABLE dim_tenure (
                tenure_id INTEGER PRIMARY KEY AUTOINCREMENT,
                tenure INTEGER,
                tenureBucket TEXT,
                tenureCategory TEXT
            );""",
            """CREATE TABLE fact_churn (
                fact_id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_id INTEGER,
                contract_id INTEGER,
                payment_id INTEGER,
                service_id INTEGER,
                tenure_id INTEGER,
                churnFlag INTEGER,
                monthlyCharges REAL,
                totalCharges REAL,
                FOREIGN KEY(customer_id) REFERENCES dim_customer(customer_id),
                FOREIGN KEY(contract_id) REFERENCES dim_contract(contract_id),
                FOREIGN KEY(payment_id) REFERENCES dim_payment(payment_id),
                FOREIGN KEY(service_id) REFERENCES dim_services(service_id),
                FOREIGN KEY(tenure_id) REFERENCES dim_tenure(tenure_id)
            );"""
        ]
        with engine.connect() as conn:
            for stmt in sqlite_ddl:
                conn.execute(text(stmt))
        log("Skema SQLite lokal berhasil diinisialisasi.")

def run_etl(log_callback=None):
    """Menjalankan proses ETL lengkap"""
    def log(msg):
        if log_callback:
            log_callback(msg)
        else:
            print(msg)
            
    try:
        csv_path = DATA_DIR / "dataset_TelcoCustomerChurn.csv"
        log(f"1. Membaca dataset mentah dari: {csv_path}")
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"File data tidak ditemukan di: {csv_path}")
            
        df = pd.read_csv(csv_path, sep=';')
        log(f"Dataset berhasil diekstrak. Total baris: {len(df)}")
        
        log("2. Menjalankan transformasi data (Pembersihan & Feature Engineering)...")
        # Trim whitespace dari kolom teks
        for col in df.select_dtypes(include=['object']).columns:
            df[col] = df[col].astype(str).str.strip()
            
        # Konversi TotalCharges ke angka. Kolom kosong dikonversi ke NaN, lalu diisi nilai MonthlyCharges
        df['TotalCharges'] = pd.to_numeric(df['TotalCharges'], errors='coerce')
        missing_total = df['TotalCharges'].isna().sum()
        log(f"Mengisi {missing_total} baris kosong pada TotalCharges dengan nilai MonthlyCharges.")
        df['TotalCharges'] = df['TotalCharges'].fillna(df['MonthlyCharges'])
        
        # Normalisasi SeniorCitizen (0/1 ke Yes/No)
        df['SeniorCitizen'] = df['SeniorCitizen'].map({0: 'No', 1: 'Yes', '0': 'No', '1': 'Yes'}).fillna('No')
        
        # Fitur Baru: contractRiskLevel
        # Month-to-month (High Risk), One year (Medium Risk), Two year (Low Risk)
        def determine_contract_risk(c):
            if c == 'Month-to-month':
                return 'High'
            elif c == 'One year':
                return 'Medium'
            else:
                return 'Low'
        df['contractRiskLevel'] = df['Contract'].apply(determine_contract_risk)
        
        # Fitur Baru: paymentCategory (Automatic / Manual)
        df['paymentCategory'] = df['PaymentMethod'].apply(
            lambda x: 'Automatic' if 'automatic' in x.lower() else 'Manual'
        )
        
        # Fitur Baru: serviceCount (Jumlah layanan aktif)
        service_cols = [
            'PhoneService', 'MultipleLines', 'InternetService', 
            'OnlineSecurity', 'OnlineBackup', 'DeviceProtection', 
            'TechSupport', 'StreamingTV', 'StreamingMovies'
        ]
        df['serviceCount'] = df[service_cols].apply(
            lambda row: sum(1 for val in row if str(val).lower() == 'yes'), 
            axis=1
        )
        
        # Fitur Baru: tenureBucket & tenureCategory
        def get_tenure_bucket(t):
            if t <= 12: return '0-12 Bulan'
            elif t <= 24: return '13-24 Bulan'
            elif t <= 48: return '25-48 Bulan'
            else: return '49+ Bulan'
            
        def get_tenure_cat(t):
            if t <= 12: return 'Short Term'
            elif t <= 48: return 'Medium Term'
            else: return 'Long Term'
            
        df['tenureBucket'] = df['tenure'].apply(get_tenure_bucket)
        df['tenureCategory'] = df['tenure'].apply(get_tenure_cat)
        
        # Konversi Churn (Yes/No ke 1/0)
        df['churnFlag'] = df['Churn'].apply(lambda x: 1 if str(x).lower() == 'yes' else 0)
        
        log("Proses Transformasi Data selesai.")
        
        # Inisialisasi skema tabel
        init_tables(log_callback)
        
        # 3. Loading data ke Dimension Tables
        log("3. Memasukkan data ke tabel dimensi (Loading Dimension Tables)...")
        
        # dim_customer
        log("- Memuat dim_customer...")
        df_cust = df[['customerID', 'gender', 'SeniorCitizen', 'Partner', 'Dependents']].drop_duplicates().copy()
        df_cust.columns = ['customer', 'gender', 'seniorCitizen', 'partner', 'dependents']
        df_cust.to_sql('dim_customer', con=engine, if_exists='append', index=False)
        db_cust = pd.read_sql("SELECT customer_id, customer FROM dim_customer", con=engine)
        cust_map = dict(zip(db_cust['customer'], db_cust['customer_id']))
        df['customer_id'] = df['customerID'].map(cust_map)
        
        # dim_contract
        log("- Memuat dim_contract...")
        df_contract = df[['Contract', 'contractRiskLevel', 'PaperlessBilling']].drop_duplicates().copy()
        df_contract.columns = ['contract', 'contractRiskLevel', 'paperlessBilling']
        df_contract.to_sql('dim_contract', con=engine, if_exists='append', index=False)
        db_contract = pd.read_sql("SELECT contract_id, contract, contractRiskLevel, paperlessBilling FROM dim_contract", con=engine)
        contract_map = {}
        for _, row in db_contract.iterrows():
            contract_map[(row['contract'], row['contractRiskLevel'], row['paperlessBilling'])] = row['contract_id']
        df['contract_id'] = df.apply(lambda r: contract_map.get((r['Contract'], r['contractRiskLevel'], r['PaperlessBilling'])), axis=1)
        
        # dim_payment
        log("- Memuat dim_payment...")
        df_payment = df[['PaymentMethod', 'paymentCategory']].drop_duplicates().copy()
        df_payment.columns = ['paymentMethod', 'paymentCategory']
        df_payment.to_sql('dim_payment', con=engine, if_exists='append', index=False)
        db_payment = pd.read_sql("SELECT payment_id, paymentMethod, paymentCategory FROM dim_payment", con=engine)
        payment_map = {}
        for _, row in db_payment.iterrows():
            payment_map[(row['paymentMethod'], row['paymentCategory'])] = row['payment_id']
        df['payment_id'] = df.apply(lambda r: payment_map.get((r['PaymentMethod'], r['paymentCategory'])), axis=1)
        
        # dim_services
        log("- Memuat dim_services...")
        df_services = df[['PhoneService', 'MultipleLines', 'InternetService', 'OnlineSecurity', 'OnlineBackup', 'DeviceProtection', 'TechSupport', 'StreamingTV', 'StreamingMovies', 'serviceCount']].drop_duplicates().copy()
        df_services.columns = ['phoneService', 'multipleLines', 'internetService', 'onlineSecurity', 'onlineBackup', 'deviceProtection', 'techSupport', 'streamingTV', 'streamingMovies', 'serviceCount']
        df_services.to_sql('dim_services', con=engine, if_exists='append', index=False)
        db_services = pd.read_sql("SELECT service_id, phoneService, multipleLines, internetService, onlineSecurity, onlineBackup, deviceProtection, techSupport, streamingTV, streamingMovies, serviceCount FROM dim_services", con=engine)
        services_map = {}
        for _, row in db_services.iterrows():
            key = (row['phoneService'], row['multipleLines'], row['internetService'], row['onlineSecurity'], row['onlineBackup'], row['deviceProtection'], row['techSupport'], row['streamingTV'], row['streamingMovies'], row['serviceCount'])
            services_map[key] = row['service_id']
        df['service_id'] = df.apply(lambda r: services_map.get((r['PhoneService'], r['MultipleLines'], r['InternetService'], r['OnlineSecurity'], r['OnlineBackup'], r['DeviceProtection'], r['TechSupport'], r['StreamingTV'], r['StreamingMovies'], r['serviceCount'])), axis=1)
        
        # dim_tenure
        log("- Memuat dim_tenure...")
        df_tenure = df[['tenure', 'tenureBucket', 'tenureCategory']].drop_duplicates().copy()
        df_tenure.columns = ['tenure', 'tenureBucket', 'tenureCategory']
        df_tenure.to_sql('dim_tenure', con=engine, if_exists='append', index=False)
        db_tenure = pd.read_sql("SELECT tenure_id, tenure, tenureBucket, tenureCategory FROM dim_tenure", con=engine)
        tenure_map = {}
        for _, row in db_tenure.iterrows():
            tenure_map[(row['tenure'], row['tenureBucket'], row['tenureCategory'])] = row['tenure_id']
        df['tenure_id'] = df.apply(lambda r: tenure_map.get((r['tenure'], r['tenureBucket'], r['tenureCategory'])), axis=1)
        
        # 4. Loading data ke Fact Table
        log("4. Memasukkan data ke Fact Table (fact_churn)...")
        df_fact = df[['customer_id', 'contract_id', 'payment_id', 'service_id', 'tenure_id', 'churnFlag', 'MonthlyCharges', 'TotalCharges']].copy()
        df_fact.columns = ['customer_id', 'contract_id', 'payment_id', 'service_id', 'tenure_id', 'churnFlag', 'monthlyCharges', 'totalCharges']
        df_fact.to_sql('fact_churn', con=engine, if_exists='append', index=False)
        
        log("Proses ETL selesai seluruhnya! Data Warehouse siap digunakan.")
        return True, "Success"
    except Exception as e:
        log(f"ETL Pipeline Gagal: {str(e)}")
        return False, str(e)

if __name__ == "__main__":
    # Jalankan langsung dari terminal jika file ini dipanggil manual
    print("Memulai ETL Pipeline via script console...")
    run_etl()
