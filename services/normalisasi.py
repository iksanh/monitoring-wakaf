"""Normalisasi nilai mentah dari Excel: nama wilayah, angka, dan koordinat."""
import re

_SPASI = re.compile(r"\s+")

# Ejaan yang ditemukan di file sumber -> bentuk baku.
ALIAS_KECAMATAN = {
    "bonepantai": "Bone Pantai",
    "bone pantai": "Bone Pantai",
    "bulango ulu": "Bulango Ulu",
    "suwawa selatan": "Suwawa Selatan",
    "suwawa tengah": "Suwawa Tengah",
    "suwawa timur": "Suwawa Timur",
    "kabila bone": "Kabila Bone",
    "bulango selatan": "Bulango Selatan",
    "bulango timur": "Bulango Timur",
    "bulango utara": "Bulango Utara",
    "bone raya": "Bone Raya",
    "botupingge": "Botupingge",
    "tilongkabila": "Tilongkabila",
    "bulawa": "Bulawa",
    "kabila": "Kabila",
    "suwawa": "Suwawa",
    "tapa": "Tapa",
    "bone": "Bone",
}

KABUPATEN_BAKU = "Kabupaten Bone Bolango"


def rapikan(nilai) -> str | None:
    """Buang spasi ganda dan spasi pinggir. Kembalikan None kalau kosong."""
    if nilai is None:
        return None
    teks = _SPASI.sub(" ", str(nilai).replace("\xa0", " ")).strip()
    return teks or None


def kapital_nama(nilai) -> str | None:
    teks = rapikan(nilai)
    if not teks:
        return None
    return " ".join(k[:1].upper() + k[1:] if k else k for k in teks.split(" "))


def kecamatan(nilai) -> str | None:
    teks = rapikan(nilai)
    if not teks:
        return None
    kunci = teks.lower()
    if kunci in ALIAS_KECAMATAN:
        return ALIAS_KECAMATAN[kunci]
    return kapital_nama(teks)


def kabupaten(nilai) -> str | None:
    teks = rapikan(nilai)
    if not teks:
        return None
    if "bone bolango" in teks.lower():
        return KABUPATEN_BAKU
    return teks


def desa(nilai) -> str | None:
    teks = rapikan(nilai)
    if not teks:
        return None
    if teks.lower() in {"-", "--", "n/a", "kosong"}:
        return None
    return kapital_nama(teks)


_ANGKA = re.compile(r"-?\d+(?:[.,]\d+)?")


def angka(nilai) -> float | None:
    """Terima str '264', float 410.0, '1.234,5', atau kosong."""
    if nilai is None:
        return None
    if isinstance(nilai, (int, float)) and not isinstance(nilai, bool):
        return float(nilai)
    teks = rapikan(nilai)
    if not teks:
        return None
    teks = teks.replace("m2", "").replace("m²", "").strip()
    # 1.234,56 (gaya Indonesia) -> 1234.56
    if re.fullmatch(r"-?\d{1,3}(\.\d{3})+(,\d+)?", teks):
        teks = teks.replace(".", "").replace(",", ".")
    else:
        teks = teks.replace(",", ".")
    cocok = _ANGKA.search(teks)
    if not cocok:
        return None
    try:
        return float(cocok.group())
    except ValueError:
        return None


def bilangan_bulat(nilai) -> int | None:
    hasil = angka(nilai)
    return None if hasil is None else int(hasil)


_URL_KOORDINAT = re.compile(r"([-+]?\d{1,3}\.\d{3,})\s*,\s*([-+]?\d{1,3}\.\d{3,})")


def koordinat_dari_url(url) -> tuple[float | None, float | None]:
    """Ambil lat/lon dari tautan Google Maps. Kembalikan (None, None) kalau gagal."""
    teks = rapikan(url)
    if not teks:
        return (None, None)
    cocok = _URL_KOORDINAT.search(teks)
    if not cocok:
        return (None, None)
    lat, lon = float(cocok.group(1)), float(cocok.group(2))
    if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
        return (None, None)
    return (lat, lon)


def dicentang(nilai) -> bool:
    """Sel tipologi dianggap tercentang kalau berisi √, v, x, atau 1."""
    teks = rapikan(nilai)
    if not teks:
        return False
    return teks.lower() in {"√", "v", "x", "1", "1.0", "ya", "✓", "✔"}


def url(nilai) -> str | None:
    teks = rapikan(nilai)
    if not teks:
        return None
    return teks if teks.lower().startswith(("http://", "https://")) else None
