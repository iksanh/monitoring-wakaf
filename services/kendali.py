"""Papan kendali per korwil — pengganti tabel 'Dashboard Control' di Excel.

Delapan kolom, tidak satu pun disimpan sebagai total (aturan domain #2):

  1. Berkas Selesai       arus  — status 'selesai', tanggal_selesai di periode
  2. Berkas dalam Proses  stok  — aktif, sudah lewat loket
  3. Berkas akan didaftar stok  — aktif di tahapan 'pra_daftar'
  4. Penetapan Pengadilan stok  — objek perlu_isbat, penetapan belum terbit
  5. Alih media           arus  — jenis 'alih_media' yang selesai di periode
  6. Total Capaian        = 1+2+3+4+5
  7. Catatan ditarik      arus  — catatan_ditarik=1, tanggal_ditarik di periode
  8. Selisih              = 5 - 7  (negatif = tarikan belum selesai dialihmediakan)

Kelima ember dijaga saling lepas supaya Total Capaian tidak menghitung berkas dua
kali: alih media hanya di kolom 5, berkas yang masih menunggu penetapan hanya di
kolom 4, sisanya di kolom 1-3. Begitu penetapan terbit berkas keluar dari kolom 4
dan masuk kolom 2/3; kalau sudah rampung ia masuk kolom 1 — capaiannya tidak
pernah hilang. Kolom 2-4 adalah posisi sekarang (stok), kolom 1/5/7 adalah
kejadian dalam periode (arus) — sama seperti cara papan kendali ini diisi manual
selama ini.
"""
import re

import config
import db
from auth import PERAN_TERBATAS_WILAYAH

POLA_PERIODE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")

BULAN = ("Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli",
         "Agustus", "September", "Oktober", "November", "Desember")

# Berkas yang perkaranya masih di Pengadilan Agama: objeknya ditandai perlu isbat
# dan penetapannya belum terbit. Dipakai kolom 4, dan dikecualikan dari kolom 2-3.
_MENUNGGU_PENETAPAN = "(o.perlu_isbat = 1 AND b.tanggal_penetapan IS NULL)"

# Kolom yang dijumlahkan menjadi Total Capaian Per Korwil.
KOLOM_CAPAIAN = ("selesai", "proses", "akan_didaftar", "penetapan", "alih_media")


def periode_sekarang() -> str:
    return config.hari_ini_iso()[:7]


def periode_sah(periode: str | None) -> str:
    """Kembalikan periode 'YYYY-MM' yang valid, atau bulan berjalan."""
    periode = (periode or "").strip()
    return periode if POLA_PERIODE.match(periode) else periode_sekarang()


def label_periode(periode: str) -> str:
    tahun, bulan = periode.split("-")
    return f"{BULAN[int(bulan) - 1]} {tahun}"


def daftar_periode(jumlah: int = 12) -> list[dict]:
    """Dua belas bulan terakhir, terbaru dulu, untuk penyaring di halaman."""
    tahun, bulan = (int(x) for x in periode_sekarang().split("-"))
    hasil = []
    for _ in range(jumlah):
        kode = f"{tahun:04d}-{bulan:02d}"
        hasil.append({"kode": kode, "label": label_periode(kode)})
        bulan -= 1
        if bulan == 0:
            tahun, bulan = tahun - 1, 12
    return hasil


def _prioritas(nilai) -> str:
    """Fragment SQL penyaring prioritas. Nilainya tidak pernah masuk SQL."""
    if nilai == "ya":
        return " AND o.is_prioritas = 1 "
    if nilai == "tidak":
        return " AND o.is_prioritas = 0 "
    return ""


def _batas(pengguna, wilayah_id=None) -> tuple[str, list]:
    """Filter wilayah: dipaksa untuk korwil/petugas, opsional untuk peran lain."""
    if pengguna and pengguna["peran"] in PERAN_TERBATAS_WILAYAH:
        return (" AND w.id = ? ", [pengguna["wilayah_id"] or -1])
    if wilayah_id:
        return (" AND w.id = ? ", [wilayah_id])
    return ("", [])


_HITUNG = """
    SELECT w.id, w.nama AS wilayah,
           SUM(CASE WHEN b.jenis_permohonan_kode <> 'alih_media'
                     AND b.status = 'selesai'
                     AND substr(b.tanggal_selesai, 1, 7) = ?
                    THEN 1 ELSE 0 END) AS selesai,
           SUM(CASE WHEN b.jenis_permohonan_kode <> 'alih_media'
                     AND b.status = 'aktif'
                     AND b.tahapan_kode <> 'pra_daftar'
                     AND NOT {tunggu}
                    THEN 1 ELSE 0 END) AS proses,
           SUM(CASE WHEN b.jenis_permohonan_kode <> 'alih_media'
                     AND b.status = 'aktif'
                     AND b.tahapan_kode = 'pra_daftar'
                     AND NOT {tunggu}
                    THEN 1 ELSE 0 END) AS akan_didaftar,
           SUM(CASE WHEN b.jenis_permohonan_kode <> 'alih_media'
                     AND b.status = 'aktif'
                     AND {tunggu}
                    THEN 1 ELSE 0 END) AS penetapan,
           SUM(CASE WHEN b.jenis_permohonan_kode = 'alih_media'
                     AND b.status = 'selesai'
                     AND substr(b.tanggal_selesai, 1, 7) = ?
                    THEN 1 ELSE 0 END) AS alih_media,
           SUM(CASE WHEN b.catatan_ditarik = 1
                     AND substr(b.tanggal_ditarik, 1, 7) = ?
                    THEN 1 ELSE 0 END) AS catatan_ditarik
      FROM wilayah w
      LEFT JOIN kecamatan k ON k.wilayah_id = w.id
      LEFT JOIN objek_wakaf o
             ON o.kecamatan_id = k.id AND o.is_aktif = 1 {saring}
      LEFT JOIN berkas b ON b.objek_wakaf_id = o.id
     WHERE 1=1 {batas}
     GROUP BY w.id ORDER BY w.urutan
"""


def _lengkapi(baris: dict) -> dict:
    """Isi kolom turunan. Dihitung di sini, tidak pernah disimpan."""
    baris = {k: (v or 0) if k not in ("id", "wilayah") else v for k, v in baris.items()}
    baris["total_capaian"] = sum(baris[k] for k in KOLOM_CAPAIAN)
    baris["selisih"] = baris["alih_media"] - baris["catatan_ditarik"]
    return baris


def papan_kendali(periode: str | None = None, wilayah_id=None, pengguna=None,
                  prioritas=None) -> dict:
    """Satu baris per wilayah plus baris TOTAL, untuk satu periode 'YYYY-MM'."""
    periode = periode_sah(periode)
    batas, p = _batas(pengguna, wilayah_id)
    baris = [
        _lengkapi(b)
        for b in db.ambil_semua(
            _HITUNG.format(batas=batas, tunggu=_MENUNGGU_PENETAPAN,
                           saring=_prioritas(prioritas)),
            tuple([periode, periode, periode] + p)
        )
    ]
    kolom = KOLOM_CAPAIAN + ("catatan_ditarik",)
    total = {k: sum(b[k] for b in baris) for k in kolom}
    total["wilayah"] = "TOTAL"
    total = _lengkapi(total)
    return {"periode": periode, "label_periode": label_periode(periode),
            "baris": baris, "total": total}
