"""Route master data (read-only untuk verifikasi + kelola pengguna)."""
from starlette.responses import PlainTextResponse, RedirectResponse
from starlette.routing import Route

import auth
import web
from services import master as svc


@auth.butuh_masuk
async def kecamatan(request):
    return web.render(request, "master/kecamatan.html", {"baris": svc.kecamatan()})


@auth.butuh_masuk
async def tipologi(request):
    return web.render(request, "master/tipologi.html", {"baris": svc.tipologi()})


@auth.butuh_masuk
async def syarat(request):
    return web.render(request, "master/syarat.html", {"baris": svc.syarat()})


@auth.butuh_peran("admin")
async def tim(request):
    if request.method == "POST":
        form = await request.form()
        if form.get("aksi") == "semua":
            tim_ids = svc.tim_tanpa_akun()
        else:
            tim_ids = [int(v) for v in form.getlist("tim_id")]
        if not tim_ids:
            web.pesan(request, "Tidak ada anggota tim yang dipilih.")
            return RedirectResponse("/master/tim", status_code=303)
        dibuat = svc.buat_akun_tim(tim_ids, request.state.pengguna["id"])
        if not dibuat:
            web.pesan(request, "Anggota yang dipilih sudah punya akun.")
            return RedirectResponse("/master/tim", status_code=303)
        # Sandi hanya bisa ditampilkan sekali, jadi jangan lewat redirect.
        return web.render(request, "master/akun_baru.html",
                          {"dibuat": dibuat, "baris": svc.tim()})
    return web.render(request, "master/tim.html", {
        "baris": svc.tim(), "belum_punya": len(svc.tim_tanpa_akun()),
    })


@auth.butuh_peran("admin")
async def pengguna(request):
    if request.method == "POST":
        f = await request.form()
        aksi = f.get("aksi")
        if aksi == "tambah":
            galat = svc.tambah_pengguna({
                "username": web.teks_atau_none(f.get("username")),
                "nama": web.teks_atau_none(f.get("nama")),
                "peran": f.get("peran"),
                "wilayah_id": web.int_atau(f.get("wilayah_id")),
                "sandi": f.get("sandi") or "",
            }, request.state.pengguna["id"])
            web.pesan(request, galat or "Pengguna ditambahkan.")
        elif aksi == "aktif":
            galat = svc.set_aktif(int(f["pengguna_id"]), int(f["aktif"]),
                                  request.state.pengguna["id"])
            web.pesan(request, galat or "Status pengguna diperbarui.")
        elif aksi == "reset":
            sandi = svc.reset_sandi(int(f["pengguna_id"]), request.state.pengguna["id"])
            web.pesan(request, f"Sandi baru: {sandi} — catat sekarang.")
        return RedirectResponse("/master/pengguna", status_code=303)
    return web.render(request, "master/pengguna.html", {
        "baris": svc.pengguna(), "wilayah": svc.wilayah(),
        "peran": auth.PERAN_TERSEDIA,
    })


@auth.butuh_peran("admin")
async def ubah_pengguna(request):
    pengguna_id = int(request.path_params["id"])
    orang = svc.ambil_pengguna(pengguna_id)
    if not orang:
        return PlainTextResponse("404 — Pengguna tidak ditemukan.", 404)

    galat = None
    if request.method == "POST":
        f = await request.form()
        nilai = {
            "username": web.teks_atau_none(f.get("username")),
            "nama": web.teks_atau_none(f.get("nama")),
            "peran": f.get("peran"),
            "wilayah_id": web.int_atau(f.get("wilayah_id")),
        }
        galat = svc.ubah_pengguna(pengguna_id, nilai, request.state.pengguna["id"])
        if not galat:
            web.pesan(request, f"Data {nilai['username']} diperbarui.")
            return RedirectResponse("/master/pengguna", status_code=303)
        orang = {**orang, **nilai}   # tahan isian pengguna supaya tidak hilang

    return web.render(request, "master/pengguna_form.html", {
        "orang": orang, "wilayah": svc.wilayah(), "peran": auth.PERAN_TERSEDIA,
        "galat": galat, "diri_sendiri": pengguna_id == request.state.pengguna["id"],
    }, status=400 if galat else 200)


rute = [
    Route("/master/kecamatan", kecamatan),
    Route("/master/tipologi", tipologi),
    Route("/master/syarat", syarat),
    Route("/master/tim", tim, methods=["GET", "POST"]),
    Route("/master/pengguna", pengguna, methods=["GET", "POST"]),
    Route("/master/pengguna/{id:int}/ubah", ubah_pengguna,
          methods=["GET", "POST"]),
]
