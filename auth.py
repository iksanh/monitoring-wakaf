"""Autentikasi: hash sandi (pbkdf2_hmac stdlib), sesi, dan dekorator peran."""
import hashlib
import hmac
import os
import secrets
from functools import wraps

from starlette.responses import RedirectResponse

import config
import db

_ITERASI = 260_000
_ALGO = "sha256"

PERAN_TERSEDIA = ("admin", "sekretariat", "korwil", "petugas", "pimpinan")
LABEL_PERAN = {
    "admin": "Administrator",
    "sekretariat": "Sekretariat",
    "korwil": "Koordinator Wilayah",
    "petugas": "Petugas Lapangan",
    "pimpinan": "Pimpinan",
}
# Peran yang datanya dibatasi wilayahnya sendiri.
PERAN_TERBATAS_WILAYAH = ("korwil", "petugas")


def buat_hash(sandi: str) -> str:
    garam = secrets.token_hex(16)
    turunan = hashlib.pbkdf2_hmac(_ALGO, sandi.encode(), bytes.fromhex(garam), _ITERASI)
    return f"pbkdf2_{_ALGO}${_ITERASI}${garam}${turunan.hex()}"


def periksa_hash(sandi: str, tersimpan: str) -> bool:
    try:
        algo, iterasi, garam, patokan = tersimpan.split("$")
        algo = algo.replace("pbkdf2_", "")
        turunan = hashlib.pbkdf2_hmac(algo, sandi.encode(), bytes.fromhex(garam), int(iterasi))
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(turunan.hex(), patokan)


def cari_pengguna(username: str) -> dict | None:
    return db.ambil_satu(
        """SELECT p.*, w.nama AS wilayah_nama
             FROM pengguna p LEFT JOIN wilayah w ON w.id = p.wilayah_id
            WHERE p.username = ?""",
        (username.strip().lower(),),
    )


def masuk(request, username: str, sandi: str) -> dict | None:
    """Verifikasi kredensial lalu isi sesi. Kembalikan pengguna atau None."""
    pengguna = cari_pengguna(username)
    if not pengguna or not pengguna["aktif"]:
        return None
    if not periksa_hash(sandi, pengguna["password_hash"]):
        return None
    request.session["pengguna_id"] = pengguna["id"]
    request.session["nama"] = pengguna["nama"]
    request.session["peran"] = pengguna["peran"]
    request.session["wilayah_id"] = pengguna["wilayah_id"]
    return pengguna


def keluar(request) -> None:
    request.session.clear()


def pengguna_aktif(request) -> dict | None:
    pid = request.session.get("pengguna_id")
    if not pid:
        return None
    return db.ambil_satu(
        """SELECT p.id, p.username, p.nama, p.peran, p.wilayah_id, p.aktif,
                  w.nama AS wilayah_nama
             FROM pengguna p LEFT JOIN wilayah w ON w.id = p.wilayah_id
            WHERE p.id = ? AND p.aktif = 1""",
        (pid,),
    )


def ganti_sandi(pengguna_id: int, sandi_baru: str) -> None:
    db.jalankan(
        "UPDATE pengguna SET password_hash = ? WHERE id = ?",
        (buat_hash(sandi_baru), pengguna_id),
    )


def butuh_masuk(fungsi):
    @wraps(fungsi)
    async def pembungkus(request):
        pengguna = pengguna_aktif(request)
        if not pengguna:
            return RedirectResponse(f"/masuk?lanjut={request.url.path}", status_code=303)
        request.state.pengguna = pengguna
        return await fungsi(request)

    return pembungkus


def butuh_peran(*peran):
    def dekorator(fungsi):
        @wraps(fungsi)
        async def pembungkus(request):
            pengguna = pengguna_aktif(request)
            if not pengguna:
                return RedirectResponse(f"/masuk?lanjut={request.url.path}", status_code=303)
            if pengguna["peran"] not in peran:
                from starlette.responses import PlainTextResponse

                return PlainTextResponse("403 — Anda tidak berhak membuka halaman ini.", 403)
            request.state.pengguna = pengguna
            return await fungsi(request)

        return pembungkus

    return dekorator


def pastikan_admin() -> str | None:
    """Buat akun admin awal kalau tabel pengguna masih kosong.

    Sandi dibaca dari ADMIN_PASSWORD. Kalau kosong, dibuat acak dan
    dikembalikan supaya bisa dicetak sekali ke konsol saat startup.
    """
    if db.ambil_nilai("SELECT COUNT(*) FROM pengguna", (), 0):
        return None
    sandi = config.ADMIN_PASSWORD or secrets.token_urlsafe(12)
    db.jalankan(
        """INSERT INTO pengguna (username, nama, password_hash, peran, wilayah_id, aktif)
           VALUES ('admin', 'Administrator', ?, 'admin', NULL, 1)""",
        (buat_hash(sandi),),
    )
    return None if config.ADMIN_PASSWORD else sandi
