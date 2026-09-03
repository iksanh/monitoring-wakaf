"""Route modul sosialisasi/penyuluhan."""
from starlette.responses import PlainTextResponse, RedirectResponse
from starlette.routing import Route

import auth
import config
import web
from services import objek as svc_objek, sosialisasi as svc


@auth.butuh_masuk
async def daftar(request):
    return web.render(request, "sosialisasi/daftar.html", {
        "baris": svc.daftar(web.teks_atau_none(request.query_params.get("status"))),
        "status": request.query_params.get("status", ""),
        "hari_ini": config.hari_ini_iso(),
    })


@auth.butuh_peran("admin", "sekretariat")
async def form(request):
    pengguna = request.state.pengguna
    sosialisasi_id = web.int_atau(request.path_params.get("id"))
    data = svc.ambil(sosialisasi_id) if sosialisasi_id else None
    if sosialisasi_id and not data:
        return PlainTextResponse("404 — Jadwal tidak ditemukan.", 404)

    if request.method == "POST":
        f = await request.form()
        nilai = {
            "tanggal": web.teks_atau_none(f.get("tanggal")),
            "jam_mulai": web.teks_atau_none(f.get("jam_mulai")),
            "jam_selesai": web.teks_atau_none(f.get("jam_selesai")),
            "lokasi": web.teks_atau_none(f.get("lokasi")),
            "pembina": web.teks_atau_none(f.get("pembina")),
            "status": web.teks_atau_none(f.get("status")) or "rencana",
            "jumlah_peserta": web.int_atau(f.get("jumlah_peserta")),
            "catatan": web.teks_atau_none(f.get("catatan")),
        }
        kecamatan_ids = [int(v) for v in f.getlist("kecamatan_id")]
        if not nilai["tanggal"]:
            return web.render(request, "sosialisasi/form.html", {
                "nilai": nilai, "kecamatan": svc_objek.daftar_kecamatan(),
                "terpilih": kecamatan_ids, "galat": ["Tanggal wajib diisi."],
            }, status=400)
        baru_id = svc.simpan(sosialisasi_id, nilai, kecamatan_ids, pengguna["id"])
        web.pesan(request, "Jadwal sosialisasi tersimpan.")
        return RedirectResponse(f"/sosialisasi#s{baru_id}", status_code=303)

    return web.render(request, "sosialisasi/form.html", {
        "nilai": data or {"status": "rencana"},
        "kecamatan": svc_objek.daftar_kecamatan(),
        "terpilih": (data or {}).get("kecamatan_ids", []),
    })


rute = [
    Route("/sosialisasi", daftar),
    Route("/sosialisasi/baru", form, methods=["GET", "POST"]),
    Route("/sosialisasi/{id:int}/ubah", form, methods=["GET", "POST"]),
]
