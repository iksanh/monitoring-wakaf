"""Route master daerah: kecamatan dan desa. Tidak ada SQL di sini.

Halaman daftar boleh dibaca semua peran — dipakai untuk mencocokkan ejaan nama
desa saat mengisi objek. Semua aksi tulisnya ditolak
`services/daerah._pastikan_boleh()` kalau bukan administrator.
"""
from starlette.responses import PlainTextResponse, RedirectResponse
from starlette.routing import Route

import auth
import web
from services import daerah as svc
from services import master as svc_master


@auth.butuh_masuk
async def kecamatan(request):
    if request.method == "POST":
        f = await request.form()
        try:
            svc.tambah_kecamatan({
                "nama": f.get("nama"),
                "kode_singkat": f.get("kode_singkat"),
                "wilayah_id": web.int_atau(f.get("wilayah_id")),
            }, request.state.pengguna)
            web.pesan(request, f"Kecamatan {f.get('nama')} ditambahkan.")
        except svc.GalatDaerah as galat:
            web.pesan(request, str(galat))
        return RedirectResponse("/master/kecamatan", status_code=303)

    return web.render(request, "master/kecamatan.html", {
        "baris": svc.daftar_kecamatan(),
        "wilayah": svc_master.wilayah(),
        "boleh_kelola": svc.boleh_mengelola(request.state.pengguna),
    })


@auth.butuh_masuk
async def detail_kecamatan(request):
    kecamatan_id = int(request.path_params["id"])
    if not svc.ambil_kecamatan(kecamatan_id):
        return PlainTextResponse("404 — Kecamatan tidak ditemukan.", 404)

    if request.method == "POST":
        f = await request.form()
        aksi = f.get("aksi")
        try:
            if aksi == "ubah":
                svc.ubah_kecamatan(kecamatan_id, {
                    "nama": f.get("nama"),
                    "kode_singkat": f.get("kode_singkat"),
                    "wilayah_id": web.int_atau(f.get("wilayah_id")),
                }, request.state.pengguna)
                web.pesan(request, "Data kecamatan diperbarui.")
            elif aksi == "hapus":
                nama = svc.hapus_kecamatan(kecamatan_id, request.state.pengguna)
                web.pesan(request, f"Kecamatan {nama} dihapus.")
                return RedirectResponse("/master/kecamatan", status_code=303)
            elif aksi == "desa_tambah":
                svc.tambah_desa(kecamatan_id, f.get("nama_desa"),
                                request.state.pengguna)
                web.pesan(request, "Desa ditambahkan.")
            elif aksi == "desa_ubah":
                svc.ubah_desa(int(f["desa_id"]), f.get("nama_desa"),
                              request.state.pengguna)
                web.pesan(request, "Nama desa diperbarui.")
            elif aksi == "desa_hapus":
                nama = svc.hapus_desa(int(f["desa_id"]), request.state.pengguna)
                web.pesan(request, f"Desa {nama} dihapus.")
            else:
                web.pesan(request, "Aksi tidak dikenal.")
        except svc.GalatDaerah as galat:
            web.pesan(request, str(galat))
        return RedirectResponse(f"/master/kecamatan/{kecamatan_id}", status_code=303)

    return web.render(request, "master/kecamatan_detail.html", {
        "kec": svc.ambil_kecamatan(kecamatan_id),
        "desa": svc.daftar_desa(kecamatan_id),
        "wilayah": svc_master.wilayah(),
        "boleh_kelola": svc.boleh_mengelola(request.state.pengguna),
    })


rute = [
    Route("/master/kecamatan", kecamatan, methods=["GET", "POST"]),
    Route("/master/kecamatan/{id:int}", detail_kecamatan, methods=["GET", "POST"]),
]
