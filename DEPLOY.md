# DEPLOY — Aplikasi Sertipikasi Tanah Wakaf

Mengikuti pola `warkah.service` yang sudah jalan di produksi.
Target: Ubuntu Server, nginx sebagai reverse proxy, TLS lewat certbot.

---

## 1. Siapkan Direktori dan Kode

```bash
sudo mkdir -p /srv/app-wakaf /data/berkas /data/cadangan
sudo chown -R ubuntu:ubuntu /srv/app-wakaf /data

cd /srv/app-wakaf
git clone <url-repo> .
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
```

## 2. Environment

```bash
sudo cp deploy/app-wakaf.env.contoh /etc/app-wakaf.env
sudo nano /etc/app-wakaf.env          # isi SECRET_KEY dan ADMIN_PASSWORD
sudo chown root:root /etc/app-wakaf.env
sudo chmod 600 /etc/app-wakaf.env
```

`SECRET_KEY` dibuat sekali dengan:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

> Jangan pernah menaruh `SECRET_KEY` di dalam kode atau di repo. Kalau `SECRET_KEY`
> kosong, aplikasi tetap jalan tetapi memakai kunci acak per-proses — semua sesi
> putus setiap restart, dan dua worker tidak akan saling mengenali cookie.

## 3. Migrasi dan Akun Admin

Migrasi jalan otomatis saat startup. Untuk menjalankan lebih dulu:

```bash
cd /srv/app-wakaf
set -a && . /etc/app-wakaf.env && set +a
./venv/bin/python -c "import db, auth; print(db.siapkan()); print(auth.pastikan_admin())"
```

Kalau `ADMIN_PASSWORD` dikosongkan, sandi admin acak dicetak sekali ke log —
ambil dengan `journalctl -u wakaf -n 30`. Setelah masuk, segera ganti lewat
`/ganti-sandi`, lalu buat akun per anggota tim di `/master/pengguna`.

## 4. Impor Data Awal

```bash
cd /srv/app-wakaf
set -a && . /etc/app-wakaf.env && set +a
./venv/bin/python -m scripts.impor /path/Rekapan\ Wakaf\ Bone\ bolango.xlsx --dry-run
# periksa laporannya, baru:
./venv/bin/python -m scripts.impor /path/Rekapan\ Wakaf\ Bone\ bolango.xlsx
```

Impor bersifat idempoten — aman dijalankan ulang setelah file sumber diperbaiki.
Bisa juga lewat halaman `/impor` (khusus admin).

## 5. systemd

```bash
sudo cp deploy/wakaf.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now wakaf
sudo systemctl status wakaf
```

## 6. nginx + TLS

```bash
sudo cp deploy/nginx-wakaf.conf /etc/nginx/sites-available/wakaf
sudo nano /etc/nginx/sites-available/wakaf     # ganti server_name
sudo ln -sf /etc/nginx/sites-available/wakaf /etc/nginx/sites-enabled/wakaf
sudo nginx -t && sudo systemctl reload nginx

sudo certbot --nginx -d wakaf.example.go.id
```

`client_max_body_size 10M` harus sama dengan `MAKS_UNGGAH_BYTE` di `config.py`.

## 7. Cadangan Harian

```bash
sudo apt install -y sqlite3 awscli
chmod +x /srv/app-wakaf/deploy/backup.sh
sudo cp deploy/wakaf-backup.service deploy/wakaf-backup.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now wakaf-backup.timer
systemctl list-timers wakaf-backup
```

Kredensial S3 diletakkan di `~ubuntu/.aws/credentials`, bukan di dalam repo.
Uji pemulihan minimal sekali:

```bash
gunzip -c wakaf-YYYYMMDD-HHMM.db.gz > /tmp/uji.db
sqlite3 /tmp/uji.db "PRAGMA integrity_check; SELECT COUNT(*) FROM objek_wakaf;"
```

## 8. Pemeriksaan Setelah Deploy

- [ ] `systemctl status wakaf` aktif, dua worker jalan
- [ ] `https://…/masuk` tampil, bisa login, lalu sandi admin diganti
- [ ] `/objek` menampilkan hasil impor
- [ ] Unggah satu foto ≤10 MB berhasil, file muncul di `/data/berkas/<tahun>/`
- [ ] `/laporan/rekap-potensi.pdf` terunduh dan isinya benar
- [ ] `journalctl -u wakaf` tidak memuat PERINGATAN KONFIGURASI
- [ ] Timer cadangan jalan dan file `.gz` masuk ke S3

## 9. Pembaruan Versi

```bash
cd /srv/app-wakaf
git pull
./venv/bin/pip install -r requirements.txt
sudo systemctl restart wakaf     # migrasi baru jalan sendiri saat startup
```

Migrasi lama tidak pernah diedit — perubahan skema selalu jadi file baru
di `migrations/`.

## 10. Yang Tidak Boleh Ada di Repo

Diperiksa sebelum rilis:

- `SECRET_KEY`, sandi, atau kredensial S3 di dalam kode → semuanya lewat `config.py`
  yang membaca environment variable.
- Path absolut server → `DB_PATH` dan `UPLOAD_DIR` dari environment.
- File `.db`, isi `data_berkas/`, dan Excel sumber → sudah masuk `.gitignore`.
