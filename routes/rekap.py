"""Route halaman rekap."""
from starlette.routing import Route

import auth
import config
import web
from services import berkas as svc_berkas, kendali as svc_kendali
from services import objek as svc_objek, rekap as svc


def _prioritas(request):
    """Baca penyaring prioritas dari query string. Dipakai semua halaman rekap."""
    return web.teks_atau_none(request.query_params.get("prioritas"))


@auth.butuh_masuk
async def kendali(request):
    """Papan kendali per korwil — 8 kolom, satu periode bulanan."""
    pengguna = request.state.pengguna
    periode = svc_kendali.periode_sah(request.query_params.get("periode"))
    wilayah_id = web.int_atau(request.query_params.get("wilayah_id"))
    prioritas = _prioritas(request)
    return web.render(request, "rekap/kendali.html", {
        "papan": svc_kendali.papan_kendali(periode, wilayah_id, pengguna, prioritas),
        "periode": periode, "daftar_periode": svc_kendali.daftar_periode(),
        "wilayah_id": wilayah_id, "wilayah": svc_berkas.daftar_wilayah(),
        "prioritas": prioritas,
    })


@auth.butuh_masuk
async def harian(request):
    pengguna = request.state.pengguna
    tanggal = web.teks_atau_none(request.query_params.get("tanggal")) or config.hari_ini_iso()
    wilayah_id = web.int_atau(request.query_params.get("wilayah_id"))
    prioritas = _prioritas(request)
    return web.render(request, "rekap/harian.html", {
        "rekap": svc.rekap_harian(tanggal, wilayah_id, pengguna, prioritas),
        "tanggal": tanggal, "wilayah_id": wilayah_id,
        "wilayah": svc_berkas.daftar_wilayah(), "prioritas": prioritas,
    })


@auth.butuh_masuk
async def tahapan(request):
    pengguna = request.state.pengguna
    wilayah_id = web.int_atau(request.query_params.get("wilayah_id"))
    prioritas = _prioritas(request)
    return web.render(request, "rekap/tahapan.html", {
        "rekap": svc.rekap_tahapan(wilayah_id, pengguna, prioritas),
        "wilayah_id": wilayah_id, "wilayah": svc_berkas.daftar_wilayah(),
        "prioritas": prioritas,
    })


@auth.butuh_masuk
async def potensi(request):
    pengguna = request.state.pengguna
    wilayah_id = web.int_atau(request.query_params.get("wilayah_id"))
    prioritas = _prioritas(request)
    baris = svc.rekap_potensi_kecamatan(pengguna, wilayah_id, prioritas)
    return web.render(request, "rekap/potensi.html", {
        "baris": baris,
        "wilayah_rekap": svc.rekap_wilayah(pengguna, prioritas),
        "wilayah_id": wilayah_id, "wilayah": svc_berkas.daftar_wilayah(),
        "prioritas": prioritas,
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
    prioritas = _prioritas(request)
    baris = svc.rekap_tipologi(kecamatan_id, pengguna, prioritas)
    return web.render(request, "rekap/tipologi.html", {
        "baris": baris,
        "kosong": svc.tipologi_kosong(kecamatan_id, pengguna, prioritas),
        "kecamatan_id": kecamatan_id, "prioritas": prioritas,
        "kecamatan": svc_objek.daftar_kecamatan(pengguna),
        "total": sum(b["jumlah"] or 0 for b in baris),
    })


@auth.butuh_masuk
async def penyerahan(request):
    pengguna = request.state.pengguna
    tanggal = web.teks_atau_none(request.query_params.get("tanggal")) or config.hari_ini_iso()
    prioritas = _prioritas(request)
    return web.render(request, "rekap/penyerahan.html", {
        "rekap": svc.rekap_penyerahan(tanggal, pengguna, prioritas),
        "tanggal": tanggal, "prioritas": prioritas,
    })


@auth.butuh_masuk
async def macet(request):
    pengguna = request.state.pengguna
    hari = web.int_atau(request.query_params.get("hari"), 14) or 14
    prioritas = _prioritas(request)
    return web.render(request, "rekap/macet.html", {
        "baris": svc.berkas_macet(hari, pengguna, prioritas=prioritas),
        "hari": hari, "prioritas": prioritas,
    })


rute = [
    Route("/rekap/kendali", kendali),
    Route("/rekap/harian", harian),
    Route("/rekap/tahapan", tahapan),
    Route("/rekap/potensi", potensi),
    Route("/rekap/tipologi", tipologi),
    Route("/rekap/penyerahan", penyerahan),
    Route("/rekap/macet", macet),
]
