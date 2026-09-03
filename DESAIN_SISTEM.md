# Desain Sistem — Aplikasi Sertipikasi Tanah Wakaf
**Kantor Pertanahan Kabupaten Bone Bolango** · nama kerja: `app-wakaf`

---

## 1. Hasil Analisa Dua File Excel

### 1.1 `Rekapan_Wakaf_Bone_bolango.xlsx` — 20 sheet

| Kelompok | Sheet | Isi |
|---|---|---|
| Ringkasan | `POTENSI WAKAF` | Rekap 17 kecamatan: Baru / Ada Hak / Isbat Wakaf → total **133** |
| Ringkasan | `Total Potensi Wilayah` | Pembagian Wilayah I–IV + susunan tim + potensi per wilayah → total **155** |
| Referensi | `TIPOLOGI` | Kamus T1–T7 (kode, kategori, nama, deskripsi, kompleksitas) |
| **Data inti** | 17 sheet kecamatan | **346 baris objek wakaf** |

Kolom baku sheet kecamatan (posisinya bergeser antar sheet, namanya sama):

```
No · Nama Objek · DESA · KECAMATAN · KABUPATEN · Nama Wakif · Nama Nadzir ·
AIW/APAIW · TIPEHAK · NIB · LUAS PERSIL · KECAMATAN KKP · KELURAHAN/DESA KKP ·
KETERANGAN · RTRW · TIPOLOGI PERMASALAHAN (T1..T7, 7 kolom centang "√") ·
REKOMENDASI ISBAT · File Sertifikat Wakaf · Catatan KUA · Titik Lokasi · UPDATE
```

Sebaran tipologi dari 346 baris: T1=14, T2=54, T3=38, T4=18, T5=8, T6=55, T7=6 → **193 terisi, 153 kosong**.

### 1.2 `Sekretariat_Wakaf_Bonbol_2026.xlsx` — 3 sheet

| Sheet | Isi | Peran di aplikasi |
|---|---|---|
| `Kontrol` | Ceklis persyaratan (2 jalur: Pendaftaran Pertama Kali vs Tanah Terdaftar) + daftar 6 tahapan berkas | **Master ceklis + master tahapan** |
| `Penyerahan 24 Sept` | Rekap per Wilayah I–IV + Rutin: Wakaf Pertama Kali / Sudah Sertipikat / Alih Media → total 41 | **Contoh output rekap**, bukan sumber data |
| `Jadwal Sosialisasi` | 8 jadwal, 11–22 Sep 2026, per kecamatan sasaran | **Modul sosialisasi** |

Enam tahapan berkas (ini tulang punggung "rekapan pertahapan"):

```
1 Permohonan (Sudah Daftar Loket) → 2 Pengukuran → 3 Pemeriksaan Tanah (Panitia A)
→ 4 Pemeriksaan Yuridis → 5 Penerbitan → 6 Penyerahan
```

### 1.3 Masalah data yang harus diselesaikan saat migrasi

1. **Tiga angka "potensi" berbeda**: 346 baris data vs 133 (sheet ringkasan) vs 155 (sheet wilayah). Aplikasi harus punya **satu definisi** — usul: semua 346 masuk sebagai `objek_wakaf`, lalu flag `is_potensi` menentukan mana yang dihitung sebagai target sertipikasi. Angka rekap jadi hasil hitung, bukan ketikan tangan.
2. **Layout tidak seragam**: sheet `Suwawa` header di baris 1, 16 sheet lain di baris 3. Importer wajib **cari header berdasarkan nama kolom**, bukan posisi.
3. **Blok tempelan**: `Suwawa Selatan`, `Bone Pantai`, `Bulango Ulu` punya blok "HASIL REKAPAN DATA GMAPS X KKP" di kolom AB–AU yang **tidak sebaris** dengan data utama. Ini dataset terpisah (sumber Kemenag) — impor ke tabel `referensi_kemenag`, jangan digabung paksa.
4. **Ejaan tidak konsisten**: `Bone Bolango` / `Kabupaten Bone bolango` / `Kabupaten Bone Bolango`; `Bonepantai` vs `Bone Pantai`. Butuh tabel master + normalisasi saat impor.
5. **Tipe data campur**: `LUAS PERSIL` ada yang teks (`'264'`), float (`410.0`), dan kosong. `Latitude=511079.0` jelas rusak (format DMS tanpa pemisah).
6. **169 baris tanpa Kecamatan KKP, 235 baris tanpa nomor AIW** — bukan bug, ini memang pekerjaan yang belum selesai. Aplikasi harus bisa menyimpan record tidak lengkap dan menandainya.
7. **Nama objek duplikat sah** (mis. Ponpes Sadiyah Maesaroh muncul 3× untuk 3 bidang berbeda). Kunci unik jangan pakai nama — pakai kode sistem `WKF-<kec>-<urut>`.

---

## 2. Sasaran Aplikasi

Menghapus siklus **print → bawa ke lapangan → coret → ketik ulang ke Excel**.

| Masalah sekarang | Solusi |
|---|---|
| Data harus di-print untuk konfirmasi lapangan | Halaman mobile-first, petugas buka objek langsung dari HP |
| Rekap harian diketik manual | Rekap harian = hasil query dari log pergerakan tahapan |
| Rekap pertahapan tersebar di beberapa sheet | Satu tabel `riwayat_tahapan` → semua rekap turunan darinya |
| File Excel bentrok kalau diedit bareng | Satu database, kunci per record, ada audit log |
| Tidak tahu siapa mengubah apa | `log_audit` + `diubah_oleh` |

**Non-tujuan fase awal:** integrasi API KKP, peta interaktif, aplikasi Android native, tanda tangan digital.

---

## 3. Arsitektur

Mengikuti pola `management-warkah` yang sudah jalan di produksi: monolit Python, server-rendered, SQLite.

```
[HP petugas / PC sekretariat]
            │ HTTPS
     ┌──────▼──────┐
     │    nginx    │  reverse proxy + TLS (certbot)
     └──────┬──────┘
            │ 127.0.0.1:8000
     ┌──────▼──────────────────────────┐
     │ uvicorn — Starlette (app:app)   │
     │  routes/ · services/ · templates│
     └──────┬──────────────────────────┘
            │ sqlite3 (stdlib, WAL mode)
     ┌──────▼──────┐        ┌──────────────┐
     │ /data/      │        │ /data/berkas │ foto & lampiran
     │ wakaf.db    │        └──────────────┘
     └─────────────┘
```

**Stack terkunci pada `requirements.txt`:**

| Paket | Dipakai untuk |
|---|---|
| `starlette` | routing, middleware, request/response |
| `uvicorn` | ASGI server (2 worker, bind 127.0.0.1:8000) |
| `Jinja2` | semua halaman (server-rendered, tanpa SPA) |
| `itsdangerous` | `SessionMiddleware` — cookie login |
| `python-multipart` | form POST + upload foto |
| `reportlab` | cetak PDF: berita acara, daftar kendali, rekap |
| `pandas` + `openpyxl` | impor Excel awal + ekspor rekap ke `.xlsx` |

**Tidak ada** SQLAlchemy di daftar → pakai `sqlite3` stdlib dengan query SQL eksplisit dan `row_factory = sqlite3.Row`. Migrasi pakai file `.sql` bernomor yang dijalankan `db.siapkan()`, sama seperti aplikasi warkah.

> ⚠️ Versi di `requirements.txt` perlu dicek dulu: `starlette==1.1.0`, `reportlab==5.0.1`, dan `pandas==3.0.3` bukan versi yang saya kenal — kemungkinan salah ketik. Jalankan `pip install -r requirements.txt` di venv kosong sebelum mulai; kalau gagal, pin ke versi rilis terbaru yang ada.

---

## 4. Model Data

### 4.1 Master / referensi

```sql
wilayah(id, nama)                              -- Wilayah I..IV, Rutin
kecamatan(id, nama, wilayah_id)                -- 17 kecamatan
desa(id, kecamatan_id, nama)                   -- ~162 desa
tipologi(kode, kategori, nama, deskripsi, kompleksitas)   -- T1..T7
tahapan(kode, urutan, nama, sla_hari)          -- 6 tahapan
jenis_permohonan(kode, nama)                   -- pertama_kali, tanah_terdaftar,
                                               --  alih_media, pemisahan, isbat
syarat(id, jenis_permohonan_kode, urutan, nama, wajib)   -- dari sheet Kontrol
pengguna(id, username, nama, password_hash, peran, wilayah_id, aktif)
tim(id, wilayah_id, pengguna_id, nama, jabatan)          -- Korwil/Anggota/Petugas Ukur
```

### 4.2 Entitas inti

```sql
objek_wakaf(
  id, kode,                       -- WKF-SWW-001, unik, dibuat sistem
  nama_objek, desa_id, kecamatan_id,
  nama_wakif, nama_nadzir,
  no_aiw, tanggal_aiw, jenis_alas_hak,
  tipe_hak, nib, luas_persil,     -- REAL, dinormalisasi saat impor
  kecamatan_kkp, desa_kkp, rtrw,
  tipologi_kode, rekomendasi_isbat,
  keterangan, catatan_kua,
  latitude, longitude, url_maps, url_dokumen,
  status_sertipikat,              -- belum | proses | sudah
  is_potensi,                     -- 1 = dihitung sebagai target sertipikasi
  sumber_data,                    -- excel_migrasi | lapangan | kemenag
  dibuat_pada, diubah_pada, diubah_oleh
)

berkas(
  id, no_berkas,                  -- nomor loket KKP kalau sudah daftar
  objek_wakaf_id, jenis_permohonan_kode,
  tahapan_kode,                   -- posisi SEKARANG (denormalisasi, untuk kecepatan)
  status,                         -- aktif | selesai | tertunda | batal
  tanggal_daftar, target_penyerahan, tanggal_selesai,
  petugas_id, catatan,
  dibuat_pada, diubah_pada
)

riwayat_tahapan(                  -- ★ SUMBER SEMUA REKAP
  id, berkas_id, tahapan_kode,
  aksi,                           -- masuk | selesai | kendala | mundur
  tanggal,                        -- tanggal kejadian (bukan waktu input)
  catatan, oleh_pengguna_id, dibuat_pada
)

ceklis_berkas(id, berkas_id, syarat_id, terpenuhi, tanggal_penuhi, catatan)
dokumen(id, objek_wakaf_id, berkas_id, jenis, nama_file, path, url_eksternal, diunggah_pada, oleh)
kunjungan(id, objek_wakaf_id, tanggal, oleh_pengguna_id, hasil, latitude, longitude, catatan)
sosialisasi(id, tanggal, jam_mulai, jam_selesai, lokasi, pembina, status, catatan)
sosialisasi_kecamatan(sosialisasi_id, kecamatan_id)
referensi_kemenag(id, nama, kecamatan, desa, kategori, tahun_berdiri, id_kemenag,
                  status_sertipikat, nib, luas, latitude, longitude, objek_wakaf_id)
log_audit(id, pengguna_id, aksi, tabel, ref_id, data_lama, data_baru, waktu)
```

**Aturan yang menjaga rekap tetap benar:** `berkas.tahapan_kode` **tidak boleh** diubah lewat UPDATE langsung. Satu-satunya jalan adalah fungsi `services/tahapan.pindah()` yang menulis `riwayat_tahapan` lalu meng-update `berkas` dalam satu transaksi. Kalau ini dilanggar, rekap harian akan bohong.

### 4.3 Turunan rekap

| Rekap | Sumber query |
|---|---|
| **Harian** | `riwayat_tahapan` di-`GROUP BY tanggal, tahapan_kode, wilayah` |
| **Per tahapan** | `berkas` di-`GROUP BY tahapan_kode` (posisi saat ini / funnel) |
| **Potensi per kecamatan** | `objek_wakaf WHERE is_potensi=1 GROUP BY kecamatan` — pengganti sheet `POTENSI WAKAF` |
| **Per wilayah** | idem, join `kecamatan.wilayah_id` — pengganti sheet `Total Potensi Wilayah` |
| **Tipologi** | `objek_wakaf GROUP BY tipologi_kode` |
| **Penyerahan** | `berkas WHERE tahapan_kode='penyerahan'` di-pivot per jenis permohonan — pengganti sheet `Penyerahan 24 Sept` |
| **Umur berkas / macet** | `julianday('now') - julianday(riwayat terakhir)` > `tahapan.sla_hari` |

---

## 5. Modul & Halaman

| # | Modul | Halaman | Peran |
|---|---|---|---|
| 1 | Auth | login, ganti sandi | semua |
| 2 | Dashboard | ringkasan funnel, pergerakan hari ini, berkas macet | semua |
| 3 | Objek Wakaf | daftar (filter kecamatan/desa/tipologi/status), detail, tambah, ubah | petugas ke atas |
| 4 | Berkas | daftar, detail, buat dari objek, ceklis syarat | sekretariat, korwil |
| 5 | Tahapan | tombol pindah tahapan + catatan, timeline riwayat | sekretariat, korwil |
| 6 | Rekap | harian (pilih tanggal), per tahapan, per kecamatan, per wilayah, tipologi | semua |
| 7 | Laporan | ekspor `.xlsx`, cetak PDF (berita acara, daftar kendali, rekap harian) | sekretariat |
| 8 | Sosialisasi | jadwal, tandai terlaksana, catatan hasil | sekretariat |
| 9 | Master | kecamatan, desa, tim, syarat, pengguna | admin |
| 10 | Impor | unggah Excel, pratinjau, konfirmasi | admin |

### Peran (RBAC)

| Peran | Kemampuan |
|---|---|
| `admin` | semua + master + impor + pengguna |
| `sekretariat` | berkas, tahapan, ceklis, rekap, ekspor, sosialisasi — semua wilayah |
| `korwil` | objek + berkas + tahapan **di wilayahnya saja** |
| `petugas` | objek + kunjungan lapangan **di wilayahnya saja** |
| `pimpinan` | baca semua, tanpa ubah |

---

## 6. Struktur Folder

```
app_wakaf/
├── app.py                    # entrypoint: app = Starlette(routes=..., middleware=...)
├── config.py                 # baca env: DB_PATH, SECRET_KEY, UPLOAD_DIR, TZ
├── db.py                     # koneksi, siapkan(), helper query
├── auth.py                   # login, hash sandi, dekorator butuh_peran()
├── migrations/
│   ├── 001_skema_awal.sql
│   └── 002_seed_master.sql
├── routes/
│   ├── dashboard.py  objek.py  berkas.py  tahapan.py
│   ├── rekap.py      laporan.py  sosialisasi.py  master.py  impor.py
├── services/
│   ├── tahapan.py            # pindah() — satu-satunya penulis riwayat_tahapan
│   ├── rekap.py              # semua query rekap
│   ├── impor_excel.py        # parser sheet kecamatan + normalisasi
│   ├── ekspor_excel.py       # pandas/openpyxl
│   └── pdf.py                # reportlab
├── templates/
│   ├── layout.html  komponen/  objek/  berkas/  rekap/  laporan/
├── static/            css/  js/  img/
├── tests/
├── requirements.txt
└── CLAUDE.md
```

---

## 7. Rencana Fase

| Fase | Isi | Selesai kalau |
|---|---|---|
| **0** | Skeleton: `app.py`, `db.py`, `config.py`, migrasi 001, layout Jinja, login | `uvicorn app:app` jalan, bisa login, halaman kosong tampil |
| **1** | Master + seed (17 kecamatan, 4 wilayah, T1–T7, 6 tahapan, syarat dari sheet Kontrol) | tabel master terisi lewat migrasi |
| **2** | Importer Excel → 346 objek + desa + referensi_kemenag | jumlah baris tersimpan cocok dengan laporan pratinjau |
| **3** | CRUD objek wakaf + daftar berfilter + detail (mobile-first) | petugas bisa buka & ubah objek dari HP |
| **4** | Berkas + `services/tahapan.pindah()` + timeline riwayat | pindah tahapan tercatat di `riwayat_tahapan` |
| **5** | Rekap harian + rekap per tahapan + dashboard | angka rekap cocok dengan riwayat |
| **6** | Ceklis syarat + unggah dokumen/foto geotag | ceklis per jenis permohonan jalan |
| **7** | Ekspor `.xlsx` + cetak PDF (reportlab) | file terunduh & isinya benar |
| **8** | Sosialisasi + kunjungan lapangan | jadwal 8 baris termuat |
| **9** | Deploy: systemd + nginx + certbot + backup S3 | sama pola `warkah.service` |

Setelah fase 9, penambahan fitur cukup: tulis prompt fitur → Claude Code baca `CLAUDE.md` → ikut pola yang sudah ada.

---

## 8. Keputusan yang Perlu Anda Ambil Sebelum Coding

1. **Definisi "potensi"** — 346 / 133 / 155, mana yang jadi angka resmi? (usul: 346 semua masuk, `is_potensi` yang menentukan)
2. **Nomor berkas** — pakai nomor loket KKP, atau nomor internal aplikasi?
3. **Foto & lampiran** — simpan di disk server (`/data/berkas`) atau tetap link Google Drive seperti sekarang?
4. **Offline lapangan** — sinyal di kecamatan pesisir/pegunungan bagaimana? Kalau sering mati, fase 3 perlu form yang tahan hilang koneksi (simpan draft di `localStorage`).
5. **Akun** — satu akun per anggota tim (±25 orang) atau akun bersama per wilayah?
