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


## 1) Gambaran umum sistem

Arsitektur dasar:

1. Sumber data: CSV mentah (`data/dataset_TelcoCustomerChurn.csv`).
2. ETL (Extract-Transform-Load): `ETL/etl_process.py` membaca CSV, melakukan pembersihan & feature engineering, membuat/initialisasi schema (star schema), mengisi tabel dimensi & fact table di DWH.
3. Data Warehouse: MySQL (jika tersedia) atau SQLite lokal sebagai fallback (`database/bi_customer.db`). Koneksi & pemilihan DB ditangani oleh `database/database.py`.
4. BI App: Streamlit app (`app.py`) yang merender 3 halaman utama di `views/`:
   - `page_dashboard.py` — visualisasi dan KPI.
   - `page_customer.py` — daftar pelanggan dan detail individual.
   - `page_etl.py` — dokumentasi pipeline, status DWH, validasi post-ETL, dan kontrol eksekusi ETL (UI).
5. Utility & helper: `utils_bi.py` berisi styling, helper query, function check & load data.


## 2) Perbedaan file & tanggung jawab

- `ETL/etl_process.py`:
  - Ini adalah implementasi logic ETL sebenarnya (script). Jika kamu menjalankan `python ETL/etl_process.py` di terminal, kode ini akan mengeksekusi seluruh pipeline: baca CSV → transform → inisialisasi schema → load dimensi → load fact → validasi. File ini tidak berhubungan langsung dengan tampilan (UI), ia hanya menjalankan proses ETL.

- `views/page_etl.py`:
  - Ini adalah halaman di Streamlit yang menampilkan dokumentasi pipeline, status DWH, diagram star schema, dan menyediakan mekanisme untuk memicu `run_etl()` dari UI (tombol). Halaman ini memanggil fungsi `run_etl` yang diekspor oleh `ETL/etl_process.py`.
  - Singkatnya: `ETL/etl_process.py` = logic, `views/page_etl.py` = UI/monitor & trigger.

- `app.py`:
  - Entrypoint Streamlit. Mengatur sidebar menu (3 halaman), page routing, dan menampilkan jenis DB aktif.

- `database/database.py`:
  - Menyiapkan `engine` SQLAlchemy. Mencoba connect ke MySQL (jika tersedia); jika gagal, otomatis membuat/menyambung ke SQLite lokal.

- `utils_bi.py`:
  - Berisi fungsi utilitas untuk styling, pembacaan data dari DB (`load_bi_data`), dan helper lain yang dipakai across views.


## 3) Rincian lengkap apa yang dilakukan ETL (`ETL/etl_process.py`)

Run flow (detail):

1. Validasi & baca file sumber
   - Path: `d:/Project/customer_churn_bi/data/dataset_TelcoCustomerChurn.csv`
   - Membaca dengan `pd.read_csv(..., sep=';')`.
   - Jika file tidak ditemukan: `FileNotFoundError`.

2. Pembersihan & Transformasi (Feature engineering)
   - Trim whitespace di seluruh kolom string.
   - Konversi `TotalCharges` ke numeric (coerce bad values → NaN), lalu isi NaN dengan nilai `MonthlyCharges`.
   - Normalisasi `SeniorCitizen` (0/1 menjadi 'No'/'Yes').
   - Tambah kolom `contractRiskLevel`:
     - 'Month-to-month' -> 'High'
     - 'One year' -> 'Medium'
     - lainnya -> 'Low'
   - Tambah kolom `paymentCategory`:
     - Cek `PaymentMethod` text; jika mengandung 'automatic' → 'Automatic', else 'Manual'.
   - Hitung `serviceCount`: jumlah layanan aktif (menghitung kolom layanan yang bernilai 'Yes').
   - Buat `tenureBucket` dan `tenureCategory` berdasarkan nilai `tenure` (bulan).
   - Konversi `Churn` menjadi `churnFlag` (Yes -> 1, else 0).

3. Inisialisasi Schema (init_tables)
   - Jika MySQL: membaca file `database/bi_customer.sql` dan mengeksekusi DDL (drop/create) di MySQL.
   - Jika SQLite: membuat DDL lokal (drop/create) via SQLAlchemy `engine`.
   - Hasil: 5 tabel dimensi + 1 tabel fakta (star schema):
     - dim_customer, dim_contract, dim_payment, dim_services, dim_tenure, fact_churn

4. Memuat ke tabel dimensi (append)
   - Dimensi dibuat dari kolom-kolom tertentu, `drop_duplicates()` untuk mengurangi duplikasi sebelum insert.
   - Setelah insert, membaca kembali dimensi untuk membangun peta (mapping) dari natural key ke surrogate key (mis. customer -> customer_id).
   - Menambahkan surrogate key ke dataframe utama (customer_id, contract_id, payment_id, service_id, tenure_id).

5. Memuat ke tabel fakta
   - Menyusun `df_fact` hanya dengan foreign keys + measures: churnFlag, monthlyCharges, totalCharges.
   - `to_sql('fact_churn', if_exists='append')` untuk memasukkan data.

6. Validasi sederhana & log
   - Kode di UI (`views/page_etl.py`) memanggil query-count, sum(churnFlag) dan beberapa checks untuk memverifikasi hasil load.


## 4) Alur UI — 3 halaman dan perannya

1. Dashboard (`page_dashboard.py`)
   - Default page: menampilkan KPI, metrik ringkasan, charts (pie, bar, box, heatmap) untuk analisis churn. Mengkonsumsi data via `utils_bi.load_bi_data()`.
   - Jika DWH kosong: menampilkan empty state dan instruksi agar jalankan ETL.

2. Customer Analysis (`page_customer.py`)
   - Menampilkan daftar pelanggan, filter, dan detail profil individual (join fakta+dimensi). Fungsi ini dianggap bagian "data collecting" karena menampilkan atribut customer hasil transformasi.

3. ETL & Data Quality (`page_etl.py`)
   - Menjelaskan alur ETL secara visual, menampilkan status DWH (count, schema info), dan mengevaluasi beberapa pemeriksaan quality post-load.
   - Menyertakan tombol untuk memicu ETL dari UI. (UX sekarang: tombol hanya tampil jika DWH kosong; ada opsi force-run via env var `ETL_ALLOW_FORCE=1`).


## 5) Persiapan lingkungan & langkah instalasi (Windows PowerShell)

Ikuti langkah ini di PowerShell pada mesin development/hosting.

1) Buat virtual environment (direkomendasikan)

```powershell
# dari folder project (d:/Project/customer_churn_bi)
python -m venv .venv
# aktifkan venv
.\.venv\Scripts\Activate.ps1
```

2) Install dependencies (minimal yang diperlukan untuk menjalankan app & ETL)

Berikut daftar paket yang diperlukan (rekomendasi):
- streamlit
- pandas
- sqlalchemy
- pymysql (jika ingin pakai MySQL)
- plotly
- streamlit-option-menu

Untuk menginstall:

```powershell
pip install --upgrade pip
pip install streamlit pandas sqlalchemy pymysql plotly streamlit-option-menu
```


3) (Opsional) Siapkan MySQL server jika mau memakai MySQL produksi

- Pastikan MySQL terinstall dan dapat diakses. Kode `database/database.py` mencoba koneksi ke `mysql+pymysql://root:@localhost` dan membuat database `bi_customer` bila belum ada.
- Alternatif: gunakan konfigurasi environment dan edit `database/database.py` untuk memakai user/password/host yang sesuai.

4) Jalankan Streamlit app (development)

```powershell
# pastikan venv aktif
streamlit run app.py
```

5) Menjalankan ETL manual (CLI)

Jika perlu menjalankan ETL dari terminal (mis. untuk testing atau scheduling), jalankan:

```powershell
python .\ETL\etl_process.py
```

Jika ingin memaksa ETL lewat UI (kapan perlu), set env var sebelum menjalankan Streamlit:

```powershell
#$env:ETL_ALLOW_FORCE = "1"    # PowerShell syntax
setx ETL_ALLOW_FORCE 1
streamlit run app.py
```


## 6) Menjadwalkan ETL (Windows Task Scheduler)

Contoh tugas Task Scheduler untuk menjalankan ETL harian:

- Action command: path to Python executable (mis. d:\Project\customer_churn_bi\.venv\Scripts\python.exe)
- Argument: `d:\Project\customer_churn_bi\ETL\etl_process.py`

Atau menggunakan skrip batch sederhana `run_etl.bat` yang mem-activate venv dan menjalankan script.


## 7) Operasional, monitoring & best-practices

- Logging: tambahkan logging terpusat (file rotating or external) di `ETL/etl_process.py` agar run history tersimpan.
- Metadata: buat tabel `etl_meta` (timestamp, status, duration, message) dan tulis hasil setiap ETL run.
- Idempotency: bila pindah dari drop/create ke incremental, implementasikan unique constraints + upsert behavior untuk dimensi dan fact.
- Backup: jangan jalankan drop/create di production tanpa backup/history. Pertimbangkan approach incremental atau snapshot.


## 8) Catatan penting & edge cases

- Pastikan format CSV sesuai (`sep=';'`) atau sesuaikan `read_csv` jika delimiter berbeda.
- Periksa konsistensi nama kolom (perbedaan uppercase/lowercase ada di ETL script — ETL mengharapkan `customerID`, `Contract`, `PaymentMethod`, dll.).
- Jika migrasi ke MySQL, pastikan user/password dan privileges sesuai; file `database/bi_customer.sql` harus cocok dengan DDL yang diinginkan.


---
Dokumen terakhir diupdate: 2026-06-13
# Sistem & Alur Data — Customer Churn BI

Dokumentasi singkat tentang arsitektur, alur ETL, rekomendasi urutan halaman UI, skenario operasi, dan langkah-langkah lanjutan untuk project Customer Churn BI.

## Ringkasan Singkat dari Kode Saat Ini

- Aplikasi UI menggunakan Streamlit, entrypoint `app.py` dengan 3 halaman utama di `views/`:
  - `page_dashboard` — halaman utama KPI dan visualisasi aggregate.
  - `page_customer` — daftar pelanggan, filter, dan detail individual.
  - `page_etl` — monitor & manual trigger untuk menjalankan ETL.
- ETL di-implementasikan di `ETL/etl_process.py`. Prosesnya: baca CSV → transform → drop/create schema → load 5 dimensi + 1 fact → validasi.
- Database layer ada di `database/database.py` — mencoba koneksi ke MySQL lokal; jika gagal, fallback ke SQLite file lokal.
- Utilitas UI & fungsi helper di `utils_bi.py` (theme, helper query, check_db_ready, load_bi_data).

## Apakah alur UI saat ini sudah 'benar'?

Secara fungsional alur saat ini masuk akal untuk sebuah demo/poc:

- Pengguna diarahkan ke `Dashboard` (index default) yang menampilkan KPI dan visualisasi. Jika DWH kosong, halaman menunjukkan empty state.
- Halaman `ETL & Data Quality` menyediakan dokumentasi pipeline dan tombol untuk menjalankan ETL secara manual. Ini cocok untuk workflow manual dan demo.

Namun untuk penggunaan produksi atau alur operasional yang lebih baik, saya sarankan beberapa perubahan/penajaman di proses dan UX (lebih detail di bagian berikut).

## Rekomendasi Arsitektur & Alur Sistem (disarankan)

1) Sumber Data (CSV mentah) —> 2) Job ETL terjadwal —> 3) Data Warehouse (MySQL atau SQLite fallback) —> 4) BI App (Streamlit)

- ETL otomatis: jadwalkan `run_etl()` (mis. harian, atau setelah ada data baru). Jangan hanya bergantung pada tombol manual.
- Kontrol versi dan idempotency: pipeline saat ini drop/create tabel — ini sederhana dan reproducible, tetapi kehilangan history. Untuk produksi pertimbangkan incremental load atau truncate+upsert pada fact table.
- Environment separation: gunakan MySQL (server) untuk environment bersama/produk; SQLite hanya untuk pengembangan lokal.
- Observability: tambahkan logging yang persist (file/central) dan metrics (durasi ETL, baris diproses, error rate). Tambahkan email/Slack alert saat ETL gagal.

## Rekomendasi Urutan Halaman & UX

- Saat ini `Dashboard` adalah default — itu bagus untuk pengguna akhir (executive/analyst).
- Pertimbangkan menambahkan sebuah banner atau modal di Dashboard (jika data kosong) yang langsung mengarahkan ke halaman ETL atau menampilkan tombol 'Run ETL' bila user terautentikasi sebagai admin.
- Untuk pengguna non-admin sembunyikan tombol eksekusi ETL. Tambahkan role-based check sederhana (mis. env var ADMIN_USERS dan compare username).
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
