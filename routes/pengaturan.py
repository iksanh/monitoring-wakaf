"""Route halaman pengaturan aplikasi. Tidak ada SQL di sini."""
from starlette.responses import RedirectResponse
from starlette.routing import Route

import auth
import web
from services import pengaturan as svc


@auth.butuh_peran(*svc.PERAN_PENGATUR)
async def halaman(request):
    if request.method == "POST":
        form = await request.form()
        # Centang yang dilepas tidak ikut terkirim browser, jadi yang ditelusuri
        # adalah setiap kunci yang dikenal — bukan apa yang kebetulan datang.
        berubah = 0
        try:
            for kunci in svc.TERSEDIA:
                if svc.simpan(kunci, form.get(kunci) is not None, request.state.pengguna):
                    berubah += 1
        except svc.GalatPengaturan as galat:
            web.pesan(request, str(galat))
            return RedirectResponse("/pengaturan", status_code=303)

        web.pesan(request, f"{berubah} pengaturan diperbarui." if berubah
                  else "Tidak ada pengaturan yang berubah.")
        return RedirectResponse("/pengaturan", status_code=303)

    return web.render(request, "pengaturan.html", {"daftar": svc.daftar_untuk_halaman()})


rute = [Route("/pengaturan", halaman, methods=["GET", "POST"])]
