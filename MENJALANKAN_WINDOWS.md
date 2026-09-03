# Menjalankan Aplikasi di Windows

Untuk pemakaian lokal (laptop/PC kantor) dan uji coba. Untuk server produksi
Ubuntu, tetap pakai `DEPLOY.md`.

## Syarat

Python 3.11+ dari <https://www.python.org/downloads/windows/> — saat memasang,
centang **"Add python.exe to PATH"**. Tidak ada yang lain; semua dependensi
dipasang otomatis ke folder `venv\` di dalam proyek.

## Jalankan

Klik dua kali **`jalankan.bat`** (atau dari terminal: `.\jalankan.bat`).

Saat pertama kali dijalankan, skrip akan:

1. membuat `venv\`,
2. memasang paket dari `requirements.txt` (beberapa menit, sekali saja),
3. membuat `.env` berisi `SECRET_KEY` acak dan `DEBUG=1`,
4. menjalankan migrasi + membuat akun `admin`,
5. menyalakan server dan membuka <http://127.0.0.1:8000/> di browser.

> **Sandi admin dicetak sekali di jendela hitam** saat database masih kosong —
> catat sebelum jendela ditutup. Sesudah masuk, ganti lewat `/ganti-sandi`.
> Kalau sandinya sudah telanjur hilang, tutup server, hapus `wakaf.db`, dan
> jalankan lagi (semua data ikut hilang — hanya aman kalau belum ada isinya).

Hentikan server dengan **Ctrl+C** di jendela itu.

### Pilihan

```bat
jalankan.bat --port 8080        :: ganti port
jalankan.bat --jaringan         :: bisa dibuka dari HP yang satu wifi
jalankan.bat --tanpa-browser    :: jangan buka browser otomatis
jalankan.bat --tanpa-reload     :: matikan auto-reload (pemakaian biasa)
jalankan.bat --pasang-ulang     :: pasang ulang dependensi
jalankan.bat --bantuan
```

`--jaringan` membuat server mendengarkan di `0.0.0.0` dan mencetak alamat
`http://192.168.x.x:8000/` yang bisa dibuka dari HP di jaringan yang sama.
Kalau tidak bisa dibuka, izinkan Python di Windows Defender Firewall untuk
jaringan Private. Jangan pakai ini di wifi publik — belum ada TLS.

## Berkas lain

| Berkas | Guna |
| --- | --- |
| `jalankan.bat` | menyiapkan lingkungan lalu menjalankan server |
| `tes.bat` | `python -m unittest discover tests` |
| `impor.bat` | impor Excel: `impor.bat "C:\path\Rekapan.xlsx" --dry-run` |
| `siapkan-lingkungan.bat` | dipanggil ketiganya; venv + dependensi + `.env` |

`impor.bat` selalu dijalankan dengan `--dry-run` dulu untuk melihat pratinjau;
tanpa flag itu, hasilnya langsung ditulis ke database.

## Berkas `.env`

Dibuat otomatis, masuk `.gitignore`, **jangan dikirim ke repo**. Isinya bisa
disunting dengan Notepad; perubahan berlaku setelah server dijalankan ulang.

| Kunci | Catatan |
| --- | --- |
| `SECRET_KEY` | 64 karakter hex acak. Kalau diganti, semua sesi login putus. |
| `DEBUG` | Harus `1` untuk jalan lokal lewat `http://`. Kalau `0`, cookie sesi dikunci `https_only` dan login selalu gagal tanpa HTTPS. |
| `DB_PATH` | Bawaan `wakaf.db` di folder proyek. |
| `UPLOAD_DIR` | Bawaan `data_berkas\`. |
| `ADMIN_PASSWORD` | Hanya dipakai sekali saat tabel pengguna masih kosong. Biarkan kosong supaya sandi acak dicetak ke konsol. |

## Cadangan

Cukup salin `wakaf.db` beserta `wakaf.db-wal` dan `wakaf.db-shm` (kalau ada)
saat server **berhenti**, plus isi folder `data_berkas\`.

## Kalau Bermasalah

| Gejala | Penyebab dan obatnya |
| --- | --- |
| `Python tidak ditemukan` | Python belum dipasang atau tidak masuk PATH. Pasang ulang dan centang "Add python.exe to PATH". Kalau yang muncul Microsoft Store, matikan alias di *Settings → Apps → Advanced app settings → App execution aliases*. |
| Pemasangan dependensi gagal | Periksa internet/proxy, lalu `jalankan.bat --pasang-ulang`. |
| `[Errno 10048] address already in use` | Port 8000 sudah dipakai. Pakai `jalankan.bat --port 8080`. |
| Login memantul balik ke halaman masuk | `DEBUG` di `.env` bernilai `0`. Ubah ke `1` untuk pemakaian lewat `http://`. |
| Jendela langsung tertutup | Jalankan dari PowerShell (`.\jalankan.bat`) supaya pesan galatnya terbaca. |
| Ada perubahan skema tidak terpakai | Migrasi jalan otomatis saat startup; cukup jalankan ulang `jalankan.bat`. |
