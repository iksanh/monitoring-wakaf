"""Route halaman rekap."""
from starlette.routing import Route

import auth
import config
import web
from services import berkas as svc_berkas, objek as svc_objek, rekap as svc


@auth.butuh_masuk
async def harian(request):
    pengguna = request.state.pengguna
    tanggal = web.teks_atau_none(request.query_params.get("tanggal")) or config.hari_ini_iso()
    wilayah_id = web.int_atau(request.query_params.get("wilayah_id"))
    return web.render(request, "rekap/harian.html", {
        "rekap": svc.rekap_harian(tanggal, wilayah_id, pengguna),
        "tanggal": tanggal, "wilayah_id": wilayah_id,
        "wilayah": svc_berkas.daftar_wilayah(),
    })


@auth.butuh_masuk
async def tahapan(request):
    pengguna = request.state.pengguna
    wilayah_id = web.int_atau(request.query_params.get("wilayah_id"))
    return web.render(request, "rekap/tahapan.html", {
        "rekap": svc.rekap_tahapan(wilayah_id, pengguna),
        "wilayah_id": wilayah_id, "wilayah": svc_berkas.daftar_wilayah(),
    })


@auth.butuh_masuk
async def potensi(request):
    pengguna = request.state.pengguna
    wilayah_id = web.int_atau(request.query_params.get("wilayah_id"))
    baris = svc.rekap_potensi_kecamatan(pengguna, wilayah_id)
    return web.render(request, "rekap/potensi.html", {
        "baris": baris,
        "wilayah_rekap": svc.rekap_wilayah(pengguna),
        "wilayah_id": wilayah_id, "wilayah": svc_berkas.daftar_wilayah(),
        "total": {
            "baru": sum(b["baru"] or 0 for b in baris),
            "ada_hak": sum(b["ada_hak"] or 0 for b in baris),
            "isbat": sum(b["isbat"] or 0 for b in baris),
            "total": sum(b["total"] or 0 for b in baris),
        },
    })


@auth.butuh_masuk
async def tipologi(request):
    pengguna = request.state.pengguna
    kecamatan_id = web.int_atau(request.query_params.get("kecamatan_id"))
    baris = svc.rekap_tipologi(kecamatan_id, pengguna)
    return web.render(request, "rekap/tipologi.html", {
        "baris": baris,
        "kosong": svc.tipologi_kosong(kecamatan_id, pengguna),
        "kecamatan_id": kecamatan_id,
        "kecamatan": svc_objek.daftar_kecamatan(pengguna),
        "total": sum(b["jumlah"] or 0 for b in baris),
    })


@auth.butuh_masuk
async def penyerahan(request):
    pengguna = request.state.pengguna
    tanggal = web.teks_atau_none(request.query_params.get("tanggal")) or config.hari_ini_iso()
    return web.render(request, "rekap/penyerahan.html", {
        "rekap": svc.rekap_penyerahan(tanggal, pengguna), "tanggal": tanggal,
    })


@auth.butuh_masuk
async def macet(request):
    pengguna = request.state.pengguna
    hari = web.int_atau(request.query_params.get("hari"), 14) or 14
    return web.render(request, "rekap/macet.html", {
        "baris": svc.berkas_macet(hari, pengguna), "hari": hari,
    })


rute = [
    Route("/rekap/harian", harian),
    Route("/rekap/tahapan", tahapan),
    Route("/rekap/potensi", potensi),
    Route("/rekap/tipologi", tipologi),
    Route("/rekap/penyerahan", penyerahan),
    Route("/rekap/macet", macet),
]
