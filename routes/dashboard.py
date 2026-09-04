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
    prioritas = web.teks_atau_none(request.query_params.get("prioritas"))
    return web.render(request, "beranda.html", {
        "ringkasan": svc.ringkasan_dashboard(pengguna, prioritas),
        "corong": svc.rekap_tahapan(pengguna=pengguna, prioritas=prioritas),
        "harian": svc.rekap_harian(hari_ini, pengguna=pengguna, prioritas=prioritas),
        "macet": svc.berkas_macet(14, pengguna, prioritas=prioritas)[:10],
        "wilayah": svc.rekap_wilayah(pengguna, prioritas),
        "prioritas": prioritas,
        "hari_ini": hari_ini,
    })


rute = [Route("/", beranda)]
