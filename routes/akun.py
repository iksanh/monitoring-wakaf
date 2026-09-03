"""Route autentikasi: masuk, keluar, ganti sandi."""
from starlette.responses import RedirectResponse
from starlette.routing import Route

import auth
import web


def _tujuan_aman(nilai: str | None) -> str:
    """Hanya izinkan path internal — cegah pengalihan ke situs luar.

    Bentuk protokol-relatif seperti "//situs-lain" tetap lolos
    startswith("/"), begitu juga varian dengan garis miring terbalik —
    keduanya dibuang di sini.
    """
    tujuan = (nilai or "").strip()
    if not tujuan.startswith("/") or tujuan.startswith(("//", "/\\")):
        return "/"
    return tujuan


async def halaman_masuk(request):
    if auth.pengguna_aktif(request):
        return RedirectResponse("/", status_code=303)
    lanjut = _tujuan_aman(request.query_params.get("lanjut"))
    if request.method == "POST":
        form = await request.form()
        username = form.get("username", "").strip()
        lanjut = _tujuan_aman(form.get("lanjut"))
        pengguna = auth.masuk(request, username, form.get("sandi", ""))
        if pengguna:
            return RedirectResponse(lanjut, status_code=303)
        return web.render(
            request, "masuk.html",
            {"galat": "Nama pengguna atau sandi salah.",
             "username": username, "lanjut": lanjut},
            status=401,
        )
    return web.render(request, "masuk.html", {"lanjut": lanjut})


async def halaman_keluar(request):
    auth.keluar(request)
    return RedirectResponse("/masuk", status_code=303)


@auth.butuh_masuk
async def halaman_ganti_sandi(request):
    if request.method == "POST":
        form = await request.form()
        lama = form.get("sandi_lama", "")
        baru = form.get("sandi_baru", "")
        ulang = form.get("sandi_ulang", "")
        akun = auth.cari_pengguna(request.state.pengguna["username"])
        if not auth.periksa_hash(lama, akun["password_hash"]):
            galat = "Sandi lama tidak cocok."
        elif len(baru) < 8:
            galat = "Sandi baru minimal 8 karakter."
        elif baru != ulang:
            galat = "Konfirmasi sandi tidak sama."
        else:
            auth.ganti_sandi(akun["id"], baru)
            web.pesan(request, "Sandi berhasil diganti.")
            return RedirectResponse("/", status_code=303)
        return web.render(request, "ganti_sandi.html", {"galat": galat}, status=400)
    return web.render(request, "ganti_sandi.html", {})


rute = [
    Route("/masuk", halaman_masuk, methods=["GET", "POST"]),
    Route("/keluar", halaman_keluar, methods=["GET", "POST"]),
    Route("/ganti-sandi", halaman_ganti_sandi, methods=["GET", "POST"]),
]
