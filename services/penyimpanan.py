"""Penyimpanan berkas unggahan: disk lokal atau bucket S3.

Backend dipilih lewat `config.PENYIMPANAN` dan dibaca setiap panggilan, bukan
saat impor, supaya tes bisa menukarnya di tengah jalan.

Alamat sebuah berkas di sini disebut *kunci*: teks relatif bergaya POSIX,
mis. `2026/17/aiw-desa-uji-3f9a2c10.pdf`. Kunci yang sama dipakai kedua
backend — di disk ia jadi path di bawah UPLOAD_DIR, di S3 jadi objek di bawah
S3_PREFIX. Karena bentuknya sama, pindah backend tidak mengubah kolom
`dokumen.path` sama sekali.
"""
import re
import threading
from pathlib import Path

import config

_KUNCI_SAH = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._\-]*(?:/[A-Za-z0-9][A-Za-z0-9._\-]*)*$")

_klien_s3 = None
_kunci_klien = threading.Lock()


class KunciTidakSah(ValueError):
    """Kunci mengandung karakter atau bentuk yang tidak diizinkan."""


class GagalPenyimpanan(RuntimeError):
    """Backend tidak bisa dihubungi atau menolak permintaan."""


class BerkasHilang(GagalPenyimpanan):
    """Kuncinya sah tapi berkasnya tidak ada — baris database menggantung."""


def aktif() -> str:
    return (config.PENYIMPANAN or "lokal").strip().lower()


def periksa_kunci(kunci: str) -> str:
    """Tolak kunci yang bisa keluar dari folder/prefix (mis. `../`, path absolut).

    Ini penjaga utama terhadap path traversal — dipanggil setiap masuk dan
    keluar, jadi baris `dokumen.path` lama yang bentuknya aneh pun tidak bisa
    dipakai membaca file di luar tempatnya.
    """
    teks = (kunci or "").replace("\\", "/").strip()
    if not teks or not _KUNCI_SAH.match(teks) or ".." in teks.split("/"):
        raise KunciTidakSah(f"Kunci berkas tidak sah: {kunci!r}")
    return teks


# ---------- backend disk lokal ----------

def _path(kunci: str) -> Path:
    return config.UPLOAD_DIR / periksa_kunci(kunci)


def _simpan_lokal(kunci: str, isi: bytes) -> None:
    tujuan = _path(kunci)
    tujuan.parent.mkdir(parents=True, exist_ok=True)
    tujuan.write_bytes(isi)


def _baca_lokal(kunci: str) -> bytes:
    berkas = _path(kunci)
    if not berkas.is_file():
        raise BerkasHilang(f"Berkas {kunci} tidak ada di disk.")
    try:
        return berkas.read_bytes()
    except OSError as galat:
        raise GagalPenyimpanan(f"Gagal membaca {kunci}: {galat}") from galat


# ---------- backend S3 ----------

def _klien():
    """Klien boto3 dibuat sekali dan dipakai ulang; kredensial dari IAM role."""
    global _klien_s3
    if _klien_s3 is not None:
        return _klien_s3
    with _kunci_klien:
        if _klien_s3 is None:
            try:
                import boto3
            except ImportError as galat:  # pragma: no cover - tergantung lingkungan
                raise GagalPenyimpanan(
                    "PENYIMPANAN=s3 tapi paket boto3 belum terpasang. "
                    "Jalankan: pip install -r requirements.txt"
                ) from galat
            _klien_s3 = boto3.client("s3", region_name=config.S3_REGION)
    return _klien_s3


def _kunci_s3(kunci: str) -> str:
    awalan = (config.S3_PREFIX or "").strip("/")
    bersih = periksa_kunci(kunci)
    return f"{awalan}/{bersih}" if awalan else bersih


def _simpan_s3(kunci: str, isi: bytes, tipe_mime: str) -> None:
    try:
        _klien().put_object(
            Bucket=config.S3_BUCKET, Key=_kunci_s3(kunci), Body=isi,
            ContentType=tipe_mime, ServerSideEncryption="AES256",
        )
    except GagalPenyimpanan:
        raise
    except Exception as galat:
        raise GagalPenyimpanan(f"Gagal mengunggah {kunci} ke S3: {galat}") from galat


def _baca_s3(kunci: str) -> bytes:
    klien = _klien()
    try:
        jawab = klien.get_object(Bucket=config.S3_BUCKET, Key=_kunci_s3(kunci))
        return jawab["Body"].read()
    except klien.exceptions.NoSuchKey as galat:
        raise BerkasHilang(f"Berkas {kunci} tidak ada di bucket.") from galat
    except Exception as galat:
        raise GagalPenyimpanan(f"Gagal mengambil {kunci} dari S3: {galat}") from galat


def _ada_s3(kunci: str) -> bool:
    try:
        _klien().head_object(Bucket=config.S3_BUCKET, Key=_kunci_s3(kunci))
        return True
    except GagalPenyimpanan:
        raise
    except Exception:
        return False


# ---------- antarmuka yang dipakai service ----------

def simpan(kunci: str, isi: bytes, tipe_mime: str = "application/octet-stream") -> None:
    if aktif() == "s3":
        _simpan_s3(kunci, isi, tipe_mime)
    else:
        _simpan_lokal(kunci, isi)


def baca(kunci: str) -> bytes:
    return _baca_s3(kunci) if aktif() == "s3" else _baca_lokal(kunci)


def ada(kunci: str) -> bool:
    try:
        if aktif() == "s3":
            return _ada_s3(kunci)
        return _path(kunci).is_file()
    except KunciTidakSah:
        return False


def ukuran(kunci: str) -> int | None:
    """Besar berkas dalam byte, atau None kalau tidak ada. Dipakai skrip pindahan."""
    try:
        if aktif() == "s3":
            try:
                jawab = _klien().head_object(Bucket=config.S3_BUCKET, Key=_kunci_s3(kunci))
            except GagalPenyimpanan:
                raise
            except Exception:
                return None
            return jawab["ContentLength"]
        berkas = _path(kunci)
        return berkas.stat().st_size if berkas.is_file() else None
    except KunciTidakSah:
        return None


def path_lokal(kunci: str) -> Path | None:
    """Path di disk kalau backend-nya lokal — supaya route tetap pakai FileResponse.

    Kembalikan None saat backend S3; pemanggil lalu jatuh ke baca().
    """
    if aktif() == "s3":
        return None
    try:
        berkas = _path(kunci)
    except KunciTidakSah:
        return None
    return berkas if berkas.is_file() else None


def lupakan_klien() -> None:
    """Buang klien yang di-cache. Dipakai tes setelah menukar konfigurasi."""
    global _klien_s3
    _klien_s3 = None
