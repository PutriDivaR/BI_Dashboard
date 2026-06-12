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
