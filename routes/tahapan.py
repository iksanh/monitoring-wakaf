"""Route pergerakan tahapan. Semua penulisan lewat services/tahapan.pindah()."""
from starlette.responses import PlainTextResponse, RedirectResponse
from starlette.routing import Route

import auth
import config
import web
from services import berkas as svc_berkas, ceklis as svc_ceklis, tahapan as svc


@auth.butuh_peran("admin", "sekretariat", "korwil")
async def pindah(request):
    pengguna = request.state.pengguna
    berkas = svc_berkas.ambil(int(request.path_params["id"]))
    if not berkas:
        return PlainTextResponse("404 — Berkas tidak ditemukan.", 404)
    if not svc_berkas.boleh_akses(pengguna, berkas):
        return PlainTextResponse("403 — Berkas ini di luar wilayah Anda.", 403)

    form = await request.form()
    tahapan_kode = form.get("tahapan_kode")
    aksi = form.get("aksi") or "masuk"
    tanggal = web.teks_atau_none(form.get("tanggal")) or config.hari_ini_iso()
    catatan = web.teks_atau_none(form.get("catatan"))
    paksa = bool(form.get("paksa"))

    halangan = svc_ceklis.halangan_pindah(berkas["id"], tahapan_kode)
    if halangan and not paksa:
        return web.render(request, "berkas/konfirmasi_pindah.html", {
            "berkas": berkas, "tahapan_kode": tahapan_kode, "aksi": aksi,
            "tanggal": tanggal, "catatan": catatan, "halangan": halangan,
        }, status=400)
    if halangan and paksa and not catatan:
        return web.render(request, "berkas/konfirmasi_pindah.html", {
            "berkas": berkas, "tahapan_kode": tahapan_kode, "aksi": aksi,
            "tanggal": tanggal, "catatan": catatan, "halangan": halangan,
            "galat": "Lanjut paksa wajib disertai alasan tertulis.",
        }, status=400)

    try:
        svc.pindah(berkas["id"], tahapan_kode, aksi=aksi, tanggal=tanggal,
                   catatan=catatan, pengguna_id=pengguna["id"])
        web.pesan(request, "Pergerakan tahapan tercatat.")
    except svc.PindahDitolak as galat:
        web.pesan(request, f"Gagal: {galat}")
    return RedirectResponse(f"/berkas/{berkas['id']}", status_code=303)


rute = [
    Route("/berkas/{id:int}/pindah", pindah, methods=["POST"]),
]
