"""Perkakas bersama lapisan HTTP: environment Jinja2, helper render, dan filter."""
from starlette.templating import Jinja2Templates

import auth
import config

templates = Jinja2Templates(directory=str(config.AKAR / "templates"))

WARNA_TIPOLOGI = {
    "T1": "hijau",
    "T2": "kuning", "T3": "kuning",
    "T4": "merah", "T5": "merah", "T6": "merah", "T7": "merah",
}


def warna_tipologi(kode: str | None) -> str:
    return WARNA_TIPOLOGI.get((kode or "").upper(), "abu")


def format_angka(nilai, desimal: int = 0) -> str:
    """Format angka gaya Indonesia: 1.234,56"""
    if nilai is None or nilai == "":
        return "—"
    try:
        teks = f"{float(nilai):,.{desimal}f}"
    except (TypeError, ValueError):
        return str(nilai)
    return teks.replace(",", " ").replace(".", ",").replace(" ", ".")


def format_luas(nilai) -> str:
    if nilai is None:
        return "—"
    return format_angka(nilai, 0) + " m²"


BULAN = ["", "Januari", "Februari", "Maret", "April", "Mei", "Juni",
         "Juli", "Agustus", "September", "Oktober", "November", "Desember"]


def format_tanggal(iso: str | None) -> str:
    if not iso:
        return "—"
    bagian = str(iso)[:10].split("-")
    if len(bagian) != 3:
        return str(iso)
    try:
        return f"{int(bagian[2])} {BULAN[int(bagian[1])]} {bagian[0]}"
    except (ValueError, IndexError):
        return str(iso)


def kosong(nilai) -> str:
    return nilai if (nilai not in (None, "")) else "—"


templates.env.filters["angka"] = format_angka
templates.env.filters["luas"] = format_luas
templates.env.filters["tanggal"] = format_tanggal
templates.env.filters["kosong"] = kosong
templates.env.globals["warna_tipologi"] = warna_tipologi
templates.env.globals["LABEL_PERAN"] = auth.LABEL_PERAN
templates.env.globals["NAMA_KANTOR"] = config.NAMA_KANTOR


def render(request, nama: str, konteks: dict | None = None, status: int = 200):
    data = {"request": request, "pengguna": getattr(request.state, "pengguna", None)}
    data.update(konteks or {})
    data.setdefault("pesan", request.session.pop("pesan", None))
    return templates.TemplateResponse(request, nama, data, status_code=status)


def pesan(request, teks: str) -> None:
    """Simpan pesan sekali-tampil di sesi (pola flash)."""
    request.session["pesan"] = teks


def int_atau(nilai, bawaan=None):
    try:
        return int(str(nilai).strip())
    except (TypeError, ValueError):
        return bawaan


def float_atau(nilai, bawaan=None):
    try:
        return float(str(nilai).strip().replace(",", "."))
    except (TypeError, ValueError):
        return bawaan


def teks_atau_none(nilai):
    if nilai is None:
        return None
    teks = str(nilai).strip()
    return teks or None
