# Sistem & Alur Kerja Lengkap — Customer Churn BI

Dokumen ini menjelaskan secara lengkap bagaimana sistem Customer Churn BI bekerja, peran tiap file, apa yang dilakukan di ETL, alur halaman (3 halaman), dan langkah-langkah instalasi serta cara menjalankan sistem di Windows PowerShell.

Isi dokumen:
- Gambaran umum sistem
- Penjelasan per-file (apa fungsi `ETL/etl_process.py` vs `views/page_etl.py` dll.)
- Rincian langkah-langkah ETL (fungsi & transformasi)
- Alur UI (3 halaman) dan tanggung jawab masing-masing halaman
- Langkah persiapan lingkungan & instalasi (PowerShell)
- Cara menjalankan (manual & terjadwal)
- Operasional, monitoring, dan catatan penting


# Sistem & Alur Data — Customer Churn BI

Dokumen ini adalah laporan lengkap (untuk keperluan dokumentasi dan laporan) tentang seluruh sistem Customer Churn BI yang ada di workspace.
Saya sudah membaca semua kode utama dan dataset. Dokumen ini menjelaskan dari awal: data collecting → ETL (sangat lengkap, dengan referensi kode) → skema database → bagaimana dashboard dibangun (fungsi tiap bagian, KPI, fitur filter/slicer/drill-down) → insight yang dapat diambil → langkah menjalankan dan rekomendasi.

Path project (root): D:/Project/customer_churn_bi

Isi ringkas dokumen:
- Gambaran singkat arsitektur
- Detail dataset sumber (kolom & contoh)
- ETL: langkah demi langkah & penjelasan kode (file: `ETL/etl_process.py`)
- Database: engine selection & DDL (file: `database/database.py`, `database/bi_customer.sql`)
- Dashboard & Customer Analysis: struktur halaman, fungsi, KPI, fitur interaktif (files: `views/*.py`, `utils_bi.py`)
- Cara menjalankan (PowerShell) dan verifikasi
- Insight contoh dan rekomendasi teknis / analitik

---

## 1. Gambaran arsitektur singkat

- Sumber data: CSV mentah di `data/dataset_TelcoCustomerChurn.csv` (IBM Watson Telco dataset).
- ETL: `ETL/etl_process.py` (fungsi utama: `run_etl(log_callback=None)` + `init_tables(log_callback=None)`).
- Data Warehouse (DWH): MySQL jika tersedia, jika tidak aplikasi otomatis fallback ke SQLite file `database/bi_customer.db`. Koneksi dan logika pemilihan ada di `database/database.py` (fungsi: `get_db_status()`).
- Aplikasi BI: Streamlit entrypoint `app.py` yang merender tiga halaman: Dashboard, Customer Analysis, ETL & Pipeline (folder `views/`).
- Utilitas: styling, helper query, dan loader BI ada di `utils_bi.py` (fungsi penting: `load_bi_data()`, `check_db_ready()`).

## 2. Dataset sumber — detail kolom & catatan

- File: `data/dataset_TelcoCustomerChurn.csv`
- Delimiter: `;` (semicolon). Dibaca di ETL dengan pd.read_csv(..., sep=';').
- Baris total: ~7.045 (file contoh menunjukkan ~7045 baris).

Header / kolom (urut sesuai file):
- customerID
- gender
- SeniorCitizen
- Partner
- Dependents
- tenure
- PhoneService
- MultipleLines
- InternetService
- OnlineSecurity
- OnlineBackup
- DeviceProtection
- TechSupport
- StreamingTV
- StreamingMovies
- Contract
- PaperlessBilling
- PaymentMethod
- MonthlyCharges
- TotalCharges
- Churn

Catatan tipe & arti kolom:
- `customerID`: string, natural key untuk pelanggan (digunakan sebagai unique identifier sebelum dimensi)
- `SeniorCitizen`: numeric 0/1 di sumber — ETL memetakan menjadi 'No'/'Yes'.
- `tenure`: integer jumlah bulan berlangganan
- `MonthlyCharges`, `TotalCharges`: numeric, `TotalCharges` raw bisa berisi string kosong sehingga ETL melakukan to_numeric(coerce) dan mengisi NaN.
- `Churn`: 'Yes'/'No' diubah menjadi `churnFlag` (1/0).

Mengapa penting: transformasi ini membentuk business features (contract risk, payment category, serviceCount, tenure buckets) yang menjadi dasar KPI dan segmen di dashboard.

---

## 3. ETL — uraian sangat lengkap (kode & logika)

File utama: `ETL/etl_process.py`

Fungsi kunci:
- run_etl(log_callback=None): eksekusi penuh pipeline (extract → transform → init schema → load dims → load fact → return (True/False, message)).
- init_tables(log_callback=None): buat ulang skema (MySQL DDL dari `database/bi_customer.sql` atau DDL SQLite yang ada di fungsi ini).

Flow rinci dan referensi ke kode (urut eksekusi dalam run_etl):

1) Extract (pembacaan sumber)
- Path file dibangun dari PROJECT_ROOT / "data" dan nama `dataset_TelcoCustomerChurn.csv`.
- Kode: df = pd.read_csv(csv_path, sep=';')
- Error handling: bila file tidak ada, raise FileNotFoundError.

2) Transform (Pembersihan & Feature Engineering)
- Trim whitespace: loop di seluruh kolom bertipe object — setiap nilai dikonversi ke str lalu strip()
- TotalCharges: df['TotalCharges'] = pd.to_numeric(df['TotalCharges'], errors='coerce') lalu df['TotalCharges'].fillna(df['MonthlyCharges'])
  - ETL mencatat jumlah baris yang mempunyai TotalCharges kosong (variabel missing_total).
- SeniorCitizen: map 0/1 (atau '0'/'1') menjadi 'No'/'Yes' via map({0:'No',1:'Yes', '0':'No', '1':'Yes'}).fillna('No')
- contractRiskLevel: fungsi determine_contract_risk di ETL:
  - 'Month-to-month' => 'High', 'One year' => 'Medium', else 'Low'.
- paymentCategory: deteksi kata 'automatic' di PaymentMethod (case-insensitive) → 'Automatic' atau 'Manual'.
- serviceCount: hitung jumlah kolom layanan yang bernilai 'Yes' pada daftar service_cols = ['PhoneService','MultipleLines','InternetService','OnlineSecurity','OnlineBackup','DeviceProtection','TechSupport','StreamingTV','StreamingMovies']
  - Implementasi: df['serviceCount'] = df[service_cols].apply(lambda row: sum(1 for val in row if str(val).lower()=='yes'), axis=1)
- tenureBucket & tenureCategory: fungsi get_tenure_bucket/get_tenure_cat membagi tenure ke '0-12 Bulan','13-24 Bulan','25-48 Bulan','49+ Bulan' dan category Short/Medium/Long Term.
- churnFlag: df['churnFlag'] = df['Churn'].apply(lambda x: 1 if str(x).lower()=='yes' else 0)

Catatan: transformasi ini dilakukan in-memory pada DataFrame sebelum dimuat ke DB.

3) Init schema (init_tables)
- Kode memeriksa jenis DB via get_db_status() dari `database.database`.
- Jika db_type == 'MySQL':
  - Baca file `database/bi_customer.sql` seluruhnya, split(';') menjadi statements, lalu eksekusi setiap DDL statement lewat engine.connect().execute(text(stmt)).
  - Prosedur juga menonaktifkan FOREIGN_KEY_CHECKS sementara untuk DROP TABLE IF EXISTS semua tabel fact/dim sebelum mengeksekusi CREATE.
- Jika bukan MySQL (fallback SQLite):
  - ETL mengeksekusi daftar sqlite_ddl yang berisi DROP TABLE IF EXISTS ... dan CREATE TABLE ... untuk dim_customer, dim_contract, dim_payment, dim_services, dim_tenure, fact_churn.

4) Load Dimensions (dengan to_sql append)
- Cara kerja untuk tiap dimensi (pattern yang sama dipakai di semua dimensi):
  - Buat df_dim = df[[kolom relevant]].drop_duplicates().copy()
  - Rename kolom ke nama yang sesuai tabel dimensi (mis. df_cust.columns = ['customer','gender','seniorCitizen','partner','dependents'])
  - df_dim.to_sql('dim_customer', con=engine, if_exists='append', index=False)
  - Lalu baca kembali tabel dimensi via pd.read_sql("SELECT ... FROM dim_customer", con=engine)
  - Buat mapping (dict) dari natural key(s) ke surrogate key (contoh: cust_map = dict(zip(db_cust['customer'], db_cust['customer_id'])))
  - Tambahkan kolom surrogate pada df utama: df['customer_id'] = df['customerID'].map(cust_map)

  - Untuk `dim_contract` dan `dim_payment` dan `dim_services` mapping key menggunakan tuple composite (mis. (contract, contractRiskLevel, paperlessBilling)) agar unik.

5) Load Fact
- Setelah semua surrogate keys ada, susun df_fact = df[['customer_id','contract_id','payment_id','service_id','tenure_id','churnFlag','MonthlyCharges','TotalCharges']]
- Rename kolom menjadi sesuai schema fact (lowercase/format yang dipakai di DDL) lalu df_fact.to_sql('fact_churn', con=engine, if_exists='append', index=False)

6) Return / Logging
- run_etl mengembalikan (True, 'Success') jika tidak ada exception; jika terjadi exception, mengembalikan (False, str(e)).
- Parameter log_callback (opsional) diteruskan ke fungsi-fungsi internal untuk menampilkan log secara streaming di UI `views/page_etl.py`.

Edge cases yang ditangani di ETL:
- TotalCharges non-numeric → di-coerce lalu diisi dengan MonthlyCharges.
- Nilai null/NaN pada kolom numerik dipantau (missing_total) dan di-log.
- Jika file `database/bi_customer.sql` tidak ditemukan saat MySQL dipilih, ETL memberi peringatan dan menggunakan tabel yg sudah ada.
- Mapping keys: jika mapping gagal, kolom surrogate bisa bernilai NaN; sebaiknya diperiksa sebelum load fact.

---

## 4. Skema Database (star schema) — DDL & penjelasan

Lokasi DDL: `database/bi_customer.sql` (digunakan saat MySQL aktif). Jika SQLite dipakai, ETL membuat tabel serupa secara langsung.

Ringkasan tabel (nama kolom penting):
- dim_customer
  - customer_id (PK autoinc), customer (unique), gender, seniorCitizen, partner, dependents
- dim_contract
  - contract_id (PK autoinc), contract, contractRiskLevel, paperlessBilling
- dim_payment
  - payment_id (PK autoinc), paymentMethod, paymentCategory
- dim_services
  - service_id (PK autoinc), phoneService, multipleLines, internetService, onlineSecurity, onlineBackup, deviceProtection, techSupport, streamingTV, streamingMovies, serviceCount
- dim_tenure
  - tenure_id (PK autoinc), tenure, tenureBucket, tenureCategory
- fact_churn
  - fact_id (PK autoinc), customer_id, contract_id, payment_id, service_id, tenure_id, churnFlag (int 0/1), monthlyCharges (decimal), totalCharges (decimal)

Constraint & integrity:
- Pada DDL MySQL, `fact_churn` memiliki foreign key constraints ke setiap dimensi (`fact_churn_ibfk_1` ... `ibfk_5`).
- Untuk SQLite, ETL menjalankan CREATE TABLE tanpa nama constraint eksplisit selain kolom PK/FK; behavior FK di SQLite berbeda — perhatikan pengaturan PRAGMA jika ingin enforce.

Mengapa star schema:
- Memisahkan atribut pelanggan (dim_customer) & atribut transaksi/keuangan (fact_churn) membuat query agregasi cepat (fact berisi measures, dim berisi deskriptor).

---

## 5. Dashboard — halaman, fungsi, KPI, dan fitur interaktif

Semua view ada di `views/`.

1) `page_dashboard.py` (Overview / KPI)
- Memanggil `load_bi_data()` dari `utils_bi.py` untuk membaca data hasil ETL.
- Filter bar: 3 selectbox utama — Periode (simulasi bulanan berdasarkan tenure bucket), Contract, InternetService. Implementasi: st.selectbox di kolom fc1..fc3.
- Tombol reset filter: memanggil st.experimental_rerun()/st.rerun() setelah set session_state.

KPI cards (yang ditampilkan dan bagaimana dihitung):
- Total Customer = len(fdf)
- Total Churn = sum(fdf['churnFlag'])
- Churn Rate (%) = (Total Churn / Total Customer) * 100
- Retention Rate (%) = 100 - Churn Rate
- Avg Monthly Charges = fdf['monthlyCharges'].mean()

Grafik & fitur penting:
- TREND CHURN OVER TIME (build_trend_from_real):
  - Karena dataset tidak punya tanggal, halaman membuat simulasi tren bulanan dengan membagi rentang tenure ke 12 segmen (Jan..Des). Fungsi: build_trend_from_real(df) → menghasilkan churn rate per segmen.
- Donut distribusi churn vs retained: pie chart Plotly (hole=0.6) dengan annotation total di tengah.
- Bar charts segmented: churn rate by contract, internet, payment, tenure — warna disesuaikan per nilai via fungsi distinct_colors/bar_color_by_val.

Interaktivitas & UX:
- Semua filter mempengaruhi visualisasi dan KPI di halaman.
- Pilihan periode melakukan filtering berdasarkan derived column 'month_segment' (cut pada tenure).

Drill-down dan export:
- Meskipun tidak ada drill-down hierarki otomatis di Plotly, pengguna dapat mensimulasikan drill-down dengan kombinasi filter (Contract + Periode + Internet Service).
- Data tabel pada halaman Customer (link ke page_customer) menyediakan download (st.download_button) CSV dari subset yang terfiltrasi.

2) `page_customer.py` (Analisis per-pelanggan)
- Query utama: `_SQL_LIST` (JOIN fact_churn + semua dimensi) — fungsi load_customer_list() cached via @st.cache_data.
- Fitur:
  - Pencarian Customer ID (text input)
  - Filter status churn (Yes/No), risk level (High/Medium/Low), internet type
  - Dataframe interaktif (st.dataframe) dengan highlight untuk yang churn
  - Download CSV (disp.to_csv) dari hasil filter
  - Detail profil: input Customer ID → get_customer_detail(cid) menjalankan `_SQL_DETAIL` (parametrized query) dan menampilkan card dengan demografi, tagihan, kontrak, layanan aktif dan badge visual untuk tiap layanan

Badge & interpretasi:
- `_svc_badge` di `page_customer.py` menampilkan label visual untuk layanan aktif / tidak tersedia.
- `_risk_badge` menampilkan risk level (High/Medium/Low) yang dipakai untuk menilai prioritas retention.

3) `page_etl.py` (ETL & Data Quality)
- Halaman ini memuat dokumentasi alur ETL (visual steps) dan menyediakan tombol untuk menjalankan ETL: memanggil run_etl(log_callback=append_log).
- Jika DWH terisi (check_db_ready() True), tombol run ETL default tidak muncul kecuali env var `ETL_ALLOW_FORCE=1` (opsi force).

Data Quality metrics:
- Fungsi `_get_dq_metrics()` (cached) menjalankan serangkaian query ke DWH, contoh:
  - SELECT COUNT(*) FROM fact_churn
  - SELECT COUNT(*) FROM fact_churn WHERE totalCharges IS NULL
  - SELECT COUNT(DISTINCT customer_id) FROM fact_churn
  - Checks untuk orphans: LEFT JOIN dim_customer ... WHERE d.customer_id IS NULL
- Dari query di atas, halaman menghitung score per dimensi (completeness, uniqueness, validity, ref_integrity) lalu rata-rata menjadi overall DQ score.

Validasi & kebijakan: halaman juga menampilkan check pass/fail (contoh: apakah ada negative monthlyCharges, apakah churnFlag hanya 0/1, apakah FK orphan > 0).

---

## 6. Penjelasan KPI & Interpretasi (apa arti setiap KPI)

- Total Customer: jumlah baris unik / pelanggan yang dimuat di DWH (asumsi setiap customer satu record di fact per snapshot ini).
- Total Churn: jumlah pelanggan yang bernilai churnFlag == 1.
- Churn Rate: rasio churn dari sample saat ini; gunakan ini untuk memonitor tren dan melihat kenaikan/penurunan antar periode/segmen.
- Retention Rate: complement dari churn rate.
- Average Monthly Charges: rata-rata beban bulanan; bandingkan avg untuk churners vs retained (pada `page_etl` dan `page_customer` ada metric avg_monthly_ch untuk churners/retained).

Tips interpretasi:
- Jika churn rate tinggi pada segment 'Month-to-month' → konfirmasi via `contractRiskLevel` mapping (ETL menetapkan Month-to-month = High Risk).
- ServiceCount tinggi & churn: mungkin cross-sell/up-sell opportunity, atau indikasi bundling yang tidak memuaskan.
- Bandingkan avg monthly charges churners vs retained untuk melihat apakah harga atau paket memengaruhi churn.

---

## 7. Fitur dashboard (filter, slicer, drill-down, export) — implementasi teknis

- Filter: implementasi via st.selectbox di `page_dashboard.py`; filter disimpan di session_state (contoh key: "dash_periode", "dash_contract", "dash_inet").
- Reset filter: fungsi _reset_filters() set session_state default dan memanggil st.experimental_rerun() / st.rerun().
- Slicer waktu: karena tidak ada timestamp asli, halaman membuat 'month_segment' dari tenure menggunakan pd.cut (12 bins). Ini adalah simulasi — cocok untuk demo tapi bukan representasi kronologis sesungguhnya.
- Drill-down: tidak ada drill-down native, tetapi kombinasi filter melakukan peran drill-down. Untuk drill-down visual interaktif bisa di-implementasikan dengan Plotly click events + callback (perlu integrasi JS/Streamlit callbacks lebih lanjut).
- Export: di `page_customer.py` ada st.download_button("⬇️ Export CSV", disp.to_csv(...)).

UX penting: tombol ETL hanya muncul untuk user yang menjalankan halaman bila DWH kosong atau jika env var ETL_ALLOW_FORCE=1 — ini mencegah accidental reload di lingkungan bersama.

---

## 8. Insight contoh (analitis) yang bisa langsung diambil dari dashboard

Beberapa insight yang bisa diekstrak dengan cepat:
- Kontrak 'Month-to-month' memiliki churn rate jauh lebih tinggi (ETL memberi label High Risk). Fokus retention (diskon, long-term incentives) dapat menurunkan churn.
- PaymentMethod: jika 'Electronic check' punya churn lebih tinggi dari 'Automatic' payments, pertimbangkan strategi pembayaran otomatis (diskon small) untuk mengurangi churn.
- Tenure bucket 0-12 bulan biasanya memiliki churn rate lebih tinggi — ini adalah window kritis onboarding.
- Segment layanan (internet type, onlineSecurity) yang punya churn tinggi: periksa kualitas layanan (support, SLA) untuk pelanggan fiber optic atau DSL tertentu.

Contoh query cepat untuk investigasi (dijalankan di SQLAlchemy / DB client):
- Top 10 customers churned with highest monthly charges:
  - SELECT dc.customer, fc.monthlyCharges FROM fact_churn fc JOIN dim_customer dc ON fc.customer_id = dc.customer_id WHERE fc.churnFlag=1 ORDER BY fc.monthlyCharges DESC LIMIT 10;

---

## 9. Cara menjalankan & validasi (Windows PowerShell)

1) Aktifkan virtualenv (direkomendasikan):

```powershell
cd D:\Project\customer_churn_bi
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

2) Install dependency (satu baris untuk PowerShell):

```powershell
pip install --upgrade pip; pip install streamlit pandas sqlalchemy pymysql plotly streamlit-option-menu
```

3) Jalankan ETL manual (opsional untuk mem-fill DWH):

```powershell
# Dari root project
python .\ETL\etl_process.py
```

4) Jalankan aplikasi Streamlit:

```powershell
streamlit run app.py
```

5) Verifikasi hasil:
- Buka halaman ETL di aplikasi → cek Data Warehouse count dan Data Quality metrics.
- Buka Dashboard → KPI Total Customer harus sama dengan nilai `total` pada DQ metrics.

---

## 10. Rekomendasi teknis & perbaikan (prioritas)

Daftar saran singkat yang memberi nilai nyata untuk laporan:

1) Tambah tabel `etl_meta` & logging run ETL
   - Simpan timestamp, duration, status, message — panggil saat start/finish ETL.
2) Jangan drop/create di production
   - Implementasikan incremental load atau truncate+upsert untuk fact table.
3) Tambah unit tests / smoke checks
   - Test untuk transform functions (TotalCharges conversion, serviceCount, tenureBucket).
4) Perbaiki representasi waktu (jika tersedia):
   - Jika dataset sumber punya tanggal event, gunakan timestamp nyata untuk trend (jangan simulasikan dari tenure).
5) Observability
   - Write ETL logs to rotating file and surface last-run + link to logs in UI.
6) Role-based control untuk ETL button
   - Hanya admin yang bisa memicu ETL dari UI.

---

## 11. Catatan akhir — file/kode penting yang saya rujuk

- ETL: `ETL/etl_process.py` — fungsi `run_etl`, `init_tables`, transform helper functions (determine_contract_risk, get_tenure_bucket, get_tenure_cat).
- App entry: `app.py` — page router dan navbar styling.
- Dashboard: `views/page_dashboard.py` — fungsi `render()`, `build_trend_from_real()`, filter handling, KPI cards.
- Customer: `views/page_customer.py` — `_SQL_LIST`, `_SQL_DETAIL`, `load_customer_list()`, `get_customer_detail()`.
- ETL page: `views/page_etl.py` — `_get_dq_metrics()` queries, ETL execution UI and DQ score logic.
- Utils: `utils_bi.py` — `load_bi_data()`, `check_db_ready()`, UI primitives (page_header, card_open, etc.) and styling tokens.
- Database engine: `database/database.py` — auto-detect MySQL/SQLite and `get_db_status()`.
- DDL: `database/bi_customer.sql` — CREATE TABLE statements for dim_* and fact_churn (used for MySQL setup).

---

Jika Anda ingin, saya bisa *selanjutnya*:
- 1) Menambahkan implementasi `etl_meta` (DDL + small code change di `ETL/etl_process.py`) dan menampilkan last-run di `views/page_etl.py`.
- 2) Menulis beberapa unit tests kecil (pytest) untuk fungsi transform (TotalCharges handling, serviceCount, tenureBucket).

Beritahu mana yang mau saya lakukan selanjutnya — saya bisa langsung membuat patch kode dan tesnya.

Dokumen terakhir diperbarui: 2026-06-13

- Tambahkan status last-run ETL (timestamp, durasi, status) di halaman `ETL & Data Quality`.

## Operasional & Scheduling

- Untuk development lokal: tetap gunakan tombol manual. Tambahkan perintah CLI untuk menjalankan ETL (`python ETL/etl_process.py`).
- Untuk staging/production:
  - Buat cron job / Windows Task Scheduler untuk menjalankan ETL secara berkala (mis. 02:00 setiap hari).
  - Jalankan ETL di environment yang sama dengan akses ke MySQL (credential via env vars).
  - Simpan log ke file (rotated) dan jalankan health check basic. Kirim alert jika error.

## Validasi & QA

- Tambahkan test smoke setelah ETL: cek row count > 0, cek sum(churnFlag) dalam rentang yang diharapkan, cek foreign key integrity.
- Di file `ETL/etl_process.py` ada beberapa asumsi soal nama kolom CSV (`;` delimiter) — pastikan dataset sumber konsisten.

## Edge Cases yang Perlu Diantisipasi

- File CSV tidak ditemukan: pipeline sudah memunculkan FileNotFoundError — pada scheduler, tangani ini dengan alert.
- Duplikasi dimensi: saat insert ke dimensi pipeline memakai append tanpa dedupe pada DB — saat ini dedupe dilakukan dengan drop/create, tapi jika pindah ke incremental, buat unique keys + upsert.
- Tipe data berbeda (mis. `TotalCharges` tidak bisa di-to_numeric): pipeline sudah handle dengan coercion tapi perlu catat baris bermasalah.

## Langkah Implementasi (Checklist cepat)

1. (Opsional) Tambahkan kolom `etl_last_run` di sebuah tabel `etl_meta` untuk menyimpan status, timestamp, duration, message.
2. Tambahkan logging berkas di `ETL/etl_process.py` (rotating file handler) dan callback yang menulis ke `etl_meta`.
3. Jadwalkan ETL via Task Scheduler (Windows) atau cron (Linux). Contoh command: `python d:/Project/customer_churn_bi/ETL/etl_process.py`.
4. Pada UI: tampilkan last run, status, dan allow manual trigger only for admin.
5. Tambahkan smoke tests / unit tests kecil untuk fungsi kritikal (transformations dan mapping keys).

## Contoh Diagram Sederhana (ASCII)

CSV (data/) -> [ETL Job] -> MySQL (bi_customer) -> Streamlit App (app.py)
                          ↳ etl_meta (status/logs)

## File & Perubahan yang Saya Sarankan (ringkas)

- Tambah `NOTES_SYSTEM_FLOW.md` (file ini) — untuk referensi.
- Tambah `etl_meta` table + logging di `ETL/etl_process.py`.
- Tambah last-run info di `views/page_etl.py`.
- Tambah role-check di `app.py` untuk sembunyikan tombol ETL ke non-admin.

## Penutup

Ini adalah rekomendasi yang memodernkan alur tanpa merombak keseluruhan arsitektur yang sudah bagus untuk PoC. Jika kamu mau, saya bisa langsung implementasikan salah satu langkah kecil: contoh, menambahkan `etl_meta` table dan menulis last-run status ke sana, lalu tampilkan di UI `page_etl.py`.

---
Dokumen dibuat: 2026-06-12
