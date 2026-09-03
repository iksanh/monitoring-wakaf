"""Entrypoint aplikasi sertipikasi tanah wakaf."""
import contextlib
import secrets

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.responses import PlainTextResponse
from starlette.routing import Mount
from starlette.staticfiles import StaticFiles

import auth
import config
import db
from routes import (akun, berkas, dashboard, impor, laporan, master, objek,
                    rekap, sosialisasi, tahapan)

rute = [
    *dashboard.rute,
    *akun.rute,
    *objek.rute,
    *berkas.rute,
    *tahapan.rute,
    *rekap.rute,
    *laporan.rute,
    *sosialisasi.rute,
    *master.rute,
    *impor.rute,
    Mount("/static", StaticFiles(directory=str(config.AKAR / "static")), name="static"),
]

_kunci = config.SECRET_KEY or secrets.token_hex(32)

middleware = [
    Middleware(
        SessionMiddleware,
        secret_key=_kunci,
        session_cookie="wakaf_sesi",
        max_age=12 * 3600,
        same_site="lax",
        https_only=not config.DEBUG,
    )
]


async def galat_404(request, exc):
    return PlainTextResponse("404 — Halaman tidak ditemukan.", status_code=404)


@contextlib.asynccontextmanager
async def daur_hidup(app):
    """Dijalankan sekali saat startup: migrasi, akun admin, folder unggahan."""
    baru = db.siapkan()
    if baru:
        print("Migrasi dijalankan:", ", ".join(baru))
    sandi = auth.pastikan_admin()
    if sandi:
        print(f"Akun admin dibuat. username: admin  sandi: {sandi}")
        print("Simpan sandi ini sekarang, tidak akan ditampilkan lagi.")
    config.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    for masalah in config.periksa():
        print("PERINGATAN KONFIGURASI:", masalah)
    yield


app = Starlette(
    debug=config.DEBUG,
    routes=rute,
    middleware=middleware,
    lifespan=daur_hidup,
    exception_handlers={404: galat_404},
)
