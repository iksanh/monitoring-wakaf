"""Beranda: corong tahapan, pergerakan hari ini, berkas macet, potensi per wilayah."""
from starlette.routing import Route

import auth
import config
import web
from services import rekap as svc


@auth.butuh_masuk
async def beranda(request):
    pengguna = request.state.pengguna
    hari_ini = config.hari_ini_iso()
    return web.render(request, "beranda.html", {
        "ringkasan": svc.ringkasan_dashboard(pengguna),
        "corong": svc.rekap_tahapan(pengguna=pengguna),
        "harian": svc.rekap_harian(hari_ini, pengguna=pengguna),
        "macet": svc.berkas_macet(14, pengguna)[:10],
        "wilayah": svc.rekap_wilayah(pengguna),
        "hari_ini": hari_ini,
    })


rute = [Route("/", beranda)]
