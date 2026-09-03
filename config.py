"""Konfigurasi aplikasi. Semua nilai sensitif dibaca dari environment variable."""
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

AKAR = Path(__file__).resolve().parent

# Zona waktu Asia/Makassar (WITA) — offset tetap UTC+8, tidak ada DST.
ZONA_WAKTU = timezone(timedelta(hours=8), "WITA")
NAMA_ZONA = os.environ.get("TZ", "Asia/Makassar")

DB_PATH = os.environ.get("DB_PATH", str(AKAR / "wakaf.db"))
SECRET_KEY = os.environ.get("SECRET_KEY", "")
UPLOAD_DIR = Path(os.environ.get("UPLOAD_DIR", str(AKAR / "data_berkas")))
DATA_SUMBER_DIR = Path(os.environ.get("DATA_SUMBER_DIR", str(AKAR / "data_master")))

DEBUG = os.environ.get("DEBUG", "0") == "1"
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")

MAKS_UNGGAH_BYTE = 10 * 1024 * 1024
EKSTENSI_DIIZINKAN = {".jpg", ".jpeg", ".png", ".pdf"}
BARIS_PER_HALAMAN = 25

NAMA_KANTOR = os.environ.get("NAMA_KANTOR", "Kantor Pertanahan Kabupaten Bone Bolango")


def sekarang() -> datetime:
    """Waktu saat ini di zona Asia/Makassar."""
    return datetime.now(ZONA_WAKTU)


def hari_ini_iso() -> str:
    return sekarang().strftime("%Y-%m-%d")


def stempel_waktu() -> str:
    return sekarang().strftime("%Y-%m-%d %H:%M:%S")


def periksa() -> list[str]:
    """Kembalikan daftar masalah konfigurasi yang harus dibereskan sebelum produksi."""
    masalah = []
    if not SECRET_KEY:
        masalah.append("SECRET_KEY belum diisi (environment variable).")
    if len(SECRET_KEY) < 32 and SECRET_KEY:
        masalah.append("SECRET_KEY terlalu pendek, minimal 32 karakter.")
    return masalah
