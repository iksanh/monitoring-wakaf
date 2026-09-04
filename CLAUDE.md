# CLAUDE.md — Aplikasi Sertipikasi Tanah Wakaf (app-wakaf)

Letakkan file ini di root proyek. Claude Code membacanya otomatis setiap sesi.

---

## Konteks

Aplikasi internal Kantor Pertanahan Kabupaten Bone Bolango (ATR/BPN) untuk mengelola
sertipikasi tanah wakaf. Menggantikan rekap Excel manual. Pengguna: ±25 pegawai
(sekretariat + 4 tim wilayah), diakses dari HP di lapangan dan PC di kantor.

Baca `DESAIN_SISTEM.md` untuk model data lengkap dan hasil analisa file Excel asal.

---

## Stack — TERKUNCI

Hanya paket di `requirements.txt`. **Jangan tambah dependency tanpa saya minta.**

```
starlette · uvicorn · Jinja2 · itsdangerous · python-multipart
reportlab · pandas · openpyxl
```

Konsekuensi yang harus dipatuhi:

- **Database: `sqlite3` stdlib.** Tidak ada ORM. Tulis SQL eksplisit, pakai
  parameter `?` (jangan pernah f-string ke dalam SQL), `row_factory = sqlite3.Row`.
- **Frontend: Jinja2 server-rendered.** Tidak ada React/Vue/build step.
  JavaScript hanya vanilla untuk hal kecil (toggle, konfirmasi hapus, draft offline).
- **CSS ditulis tangan** di `static/css/`. Tidak ada Tailwind/Bootstrap CDN.
- **Session: `SessionMiddleware`** dari Starlette (backend `itsdangerous`).
- **Hash sandi: `hashlib.pbkdf2_hmac`** dari stdlib (bcrypt tidak ada di requirements).
- **PDF: reportlab `platypus`.** Excel: `pandas` untuk baca, `openpyxl` untuk tulis.

---

## Konvensi Kode

- **Bahasa Indonesia** untuk nama tabel, kolom, route, template, variabel domain,
  dan komentar. Bahasa Inggris hanya untuk istilah teknis baku (`request`, `session`,
  `middleware`, `commit`).
- Satu file route per modul di `routes/`. Route mengurus HTTP saja: validasi input,
  panggil service, render template. **Tidak ada SQL di dalam `routes/`.**
- Semua query ada di `db.py` atau `services/`.
- Fungsi service mengembalikan `dict` / `list[dict]`, bukan objek row mentah.
- Timezone **Asia/Makassar**. Simpan tanggal sebagai teks ISO `YYYY-MM-DD`,
  timestamp sebagai `YYYY-MM-DD HH:MM:SS`.
- Uang/luas: simpan `REAL`, format di template.

## Migrasi

- File SQL bernomor di `migrations/`: `001_skema_awal.sql`, `002_seed_master.sql`, dst.
- `db.siapkan()` jalan sekali saat startup: buat tabel `skema_versi`, jalankan file
  yang belum pernah dijalankan, catat versinya, `PRAGMA journal_mode=WAL`,
  `PRAGMA foreign_keys=ON`.
- **Jangan pernah edit file migrasi yang sudah pernah jalan.** Buat file baru.

## Aturan Domain — WAJIB

1. **`berkas.tahapan_kode` hanya boleh diubah lewat `services/tahapan.pindah()`.**
   Fungsi itu menulis baris ke `riwayat_tahapan` DAN meng-update `berkas` dalam satu
   transaksi. Tidak ada `UPDATE berkas SET tahapan_kode` di tempat lain.
   Semua rekap harian bersandar pada aturan ini.
2. **Semua angka rekap dihitung dari query**, tidak pernah disimpan sebagai kolom
   total yang di-update manual.
3. **Filter wilayah wajib** untuk peran `korwil` dan `petugas` — terapkan di lapisan
   service, bukan hanya menyembunyikan tombol di template.
4. **Objek wakaf tidak pernah dihapus fisik.** Pakai kolom status / `is_aktif`.
5. Setiap perubahan data (create/update/delete) menulis `log_audit`.
6. **Satu objek wakaf = satu berkas permohonan.** Objek yang sudah punya
   berkas tidak boleh dibuatkan berkas lagi. Ditegakkan di
   `services/berkas.buat()` (raise `BerkasGanda`) DAN oleh indeks unik parsial
   `idx_berkas_satu_per_objek`. Berkas berstatus `batal` tidak menghalangi,
   supaya objek yang permohonannya dibatalkan bisa didaftarkan ulang. Daftar
   `/berkas` menyembunyikan yang `batal` kecuali filter Status memintanya —
   objeknya sudah kembali jadi objek wakaf biasa. Pembatalan lewat
   `services/berkas_aksi.batalkan()`, wajib beralasan.
7. **Isbat bukan jenis permohonan.** Isbat terjadi sebelum berkas didaftarkan di
   loket; permohonannya tetap `pertama_kali` dengan salinan penetapan sebagai
   lampiran. Penandanya dua lapis: `objek_wakaf.perlu_isbat` (rencana, dipakai
   Rekap Potensi untuk objek yang belum punya berkas) dan `berkas.no_penetapan` +
   `tanggal_penetapan` (realisasi). Selama `tanggal_penetapan` kosong, perkaranya
   dianggap masih di Pengadilan Agama.
8. Data tidak lengkap **harus boleh disimpan** (235 dari 346 objek belum punya AIW).
   Validasi ketat hanya pada: nama objek, kecamatan, desa.

## UI

- **Mobile-first.** Petugas memakai HP di lapangan. Rancang untuk lebar 360px dulu,
  desktop belakangan. Target sentuh minimal 44px.
- Halaman daftar: kartu di mobile, tabel di desktop (satu template, CSS yang beda).
- Setiap halaman daftar punya filter kecamatan + pencarian nama objek.
- Form pakai `<form method="post">` biasa. Hindari SPA-style fetch kecuali perlu.
- Tampilkan kode tipologi dengan warna: T1 hijau, T2–T3 kuning, T4–T7 merah.

## Testing

- `tests/` pakai `unittest` stdlib. Wajib ada tes untuk:
  `services/tahapan.pindah()`, semua fungsi di `services/rekap.py`,
  dan parser `services/impor_excel.py`.
- Jalankan `python -m unittest discover tests` sebelum bilang selesai.

## Yang JANGAN Dilakukan

- Jangan tambah dependency baru.
- Jangan ganti SQLite ke Postgres/MySQL.
- Jangan bikin REST API JSON kecuali diminta — ini aplikasi server-rendered.
- Jangan refactor besar-besaran tanpa saya setujui dulu.
- Jangan hardcode kredensial, path absolut, atau `SECRET_KEY`. Semua lewat `config.py`
  yang baca environment variable.
- Jangan tulis file lebih dari ~300 baris; pecah jadi modul.

## Perintah

```bash
source venv/bin/activate
python -m uvicorn app:app --reload --port 8000      # dev
python -m unittest discover tests                    # tes
python -m scripts.impor /path/ke/Rekapan.xlsx --dry-run   # pratinjau impor
```

Di Windows dipakai berkas `.bat` di root (lihat `MENJALANKAN_WINDOWS.md`):

```bat
jalankan.bat                                  :: venv + dependensi + server dev
tes.bat                                       :: tes
impor.bat "C:\path\Rekapan.xlsx" --dry-run     :: pratinjau impor
```

## Status Fase

Tandai saat selesai — ini yang membuat sesi berikutnya tahu posisi.

- [x] Fase 0 — Skeleton + auth
- [x] Fase 1 — Master + seed
- [x] Fase 2 — Importer Excel
- [x] Fase 3 — CRUD objek wakaf
- [x] Fase 4 — Berkas + tahapan
- [x] Fase 5 — Rekap + dashboard
- [x] Fase 6 — Ceklis + dokumen
- [x] Fase 7 — Ekspor Excel + PDF
- [x] Fase 8 — Sosialisasi + kunjungan
- [x] Fase 9 — Deploy (berkas siap, belum dijalankan di server)
- [x] Tambahan — Susunan tim + pembuatan akun massal (`/master/tim`)

## Temuan Data yang Mengubah Angka di DESAIN_SISTEM.md

Diverifikasi ulang terhadap file Excel saat Fase 2 — **belum dikonfirmasi ke pemilik data**:

1. **Objek wakaf sebenarnya 223, bukan 346.** Angka 346 menghitung semua sel tidak
   kosong di kolom "Nama Objek", termasuk 123 baris blok legenda dan rekap kecil di
   bawah data tiap sheet ("Tidak bisa ditindaklanjut :", "Total Objek", "REKAP DATA
   WAKAF WILAYAH 1", dst). Baris data asli selalu punya nomor urut — itu yang dipakai
   importer sebagai penyaring.
2. **Sebaran tipologi justru cocok** dengan DESAIN_SISTEM.md: T1=14 T2=54 T3=38 T4=18
   T5=8 T6=55, hanya **T7=5 (bukan 6)** — seluruh workbook memang cuma berisi 5 centang
   T7. Ini bukti tambahan bahwa 123 baris yang dibuang memang bukan data.
3. Konsekuensinya angka lain ikut bergeser: 193 objek punya AIW (30 belum, bukan 235),
   191 punya Kecamatan KKP, 105 desa terbentuk (bukan ~162).
4. Blok Kemenag: 39 baris (Suwawa Selatan 15, Bulango Ulu 7, Bone Pantai 17). Header
   blok di sheet Bone Pantai bergeser satu kolom dari datanya — importer menghitung
   pergeserannya dari letak nyata nilai ID_KEMENAG.

5. **Kolom "Rekomendasi Isbat" di Excel bukan penanda, melainkan catatan bebas.**
   Cuma 2 dari 223 baris terisi, dan salah satunya `LP2B` (Lahan Pertanian Pangan
   Berkelanjutan — catatan tata ruang, bukan isbat). Rekap potensi dulu
   memperlakukan kolom itu sebagai flag sehingga objek LP2B ikut terhitung isbat.
   Sekarang klasifikasi memakai `objek_wakaf.perlu_isbat`; teks `LP2B` dipindah ke
   kolom `keterangan` oleh migrasi 008.

Keputusan sementara yang dipakai (bisa diubah): semua 223 baris masuk sebagai
`objek_wakaf` dengan `is_potensi = 1`.
