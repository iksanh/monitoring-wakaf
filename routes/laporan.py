"""Route unduh Excel dan cetak PDF."""
from starlette.responses import PlainTextResponse, Response
from starlette.routing import Route

import auth
import config
import web
from services import (berkas as svc_berkas, ceklis as svc_ceklis,
                      ekspor_excel, objek as svc_objek, pdf as svc_pdf,
                      rekap as svc_rekap, tahapan as svc_tahapan)

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _unduh(isi: bytes, nama: str, tipe: str) -> Response:
    return Response(isi, media_type=tipe,
                    headers={"Content-Disposition": f'attachment; filename="{nama}"'})


def _pdf(isi: bytes, nama: str) -> Response:
    return Response(isi, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="{nama}"'})


@auth.butuh_masuk
async def indeks(request):
    return web.render(request, "laporan/indeks.html", {"hari_ini": config.hari_ini_iso()})


@auth.butuh_masuk
async def objek_xlsx(request):
    pengguna = request.state.pengguna
    p = request.query_params
    saring = {
        "kecamatan_id": web.int_atau(p.get("kecamatan_id")),
        "tipologi_kode": web.teks_atau_none(p.get("tipologi_kode")),
        "status_sertipikat": web.teks_atau_none(p.get("status_sertipikat")),
        "aiw": web.teks_atau_none(p.get("aiw")),
        "q": web.teks_atau_none(p.get("q")),
    }
    hasil = svc_objek.cari(pengguna, saring, 1, per_halaman=100000)
    return _unduh(ekspor_excel.daftar_objek(hasil["baris"]),
                  ekspor_excel.nama_berkas("daftar_objek_wakaf"), XLSX)


@auth.butuh_masuk
async def harian_xlsx(request):
    pengguna = request.state.pengguna
    tanggal = web.teks_atau_none(request.query_params.get("tanggal")) or config.hari_ini_iso()
    rekap = svc_rekap.rekap_harian(tanggal, pengguna=pengguna)
    return _unduh(ekspor_excel.rekap_harian(rekap),
                  ekspor_excel.nama_berkas("rekap_harian", tanggal), XLSX)


@auth.butuh_masuk
async def tahapan_xlsx(request):
    pengguna = request.state.pengguna
    rekap = svc_rekap.rekap_tahapan(pengguna=pengguna)
    return _unduh(ekspor_excel.rekap_tahapan(rekap),
                  ekspor_excel.nama_berkas("rekap_tahapan"), XLSX)


@auth.butuh_masuk
async def potensi_xlsx(request):
    pengguna = request.state.pengguna
    baris = svc_rekap.rekap_potensi_kecamatan(pengguna)
    return _unduh(ekspor_excel.rekap_potensi(baris),
                  ekspor_excel.nama_berkas("rekap_potensi"), XLSX)


@auth.butuh_masuk
async def harian_pdf(request):
    pengguna = request.state.pengguna
    tanggal = web.teks_atau_none(request.query_params.get("tanggal")) or config.hari_ini_iso()
    rekap = svc_rekap.rekap_harian(tanggal, pengguna=pengguna)
    return _pdf(svc_pdf.rekap_harian(rekap), f"rekap_harian_{tanggal}.pdf")


@auth.butuh_masuk
async def potensi_pdf(request):
    pengguna = request.state.pengguna
    baris = svc_rekap.rekap_potensi_kecamatan(pengguna)
    return _pdf(svc_pdf.rekap_potensi(baris), "rekap_potensi.pdf")


@auth.butuh_masuk
async def kendali_pdf(request):
    pengguna = request.state.pengguna
    berkas = svc_berkas.ambil(int(request.path_params["id"]))
    if not berkas or not svc_berkas.boleh_akses(pengguna, berkas):
        return PlainTextResponse("403 — Tidak berhak.", 403)
    isi = svc_pdf.daftar_kendali(berkas, svc_tahapan.riwayat(berkas["id"]),
                                 svc_ceklis.per_berkas(berkas["id"]))
    return _pdf(isi, f"kendali_berkas_{berkas['id']}.pdf")


@auth.butuh_peran("admin", "sekretariat")
async def berita_acara_pdf(request):
    berkas = svc_berkas.ambil(int(request.path_params["id"]))
    if not berkas:
        return PlainTextResponse("404 — Berkas tidak ditemukan.", 404)
    penerima = web.teks_atau_none(request.query_params.get("penerima")) or ""
    return _pdf(svc_pdf.berita_acara(berkas, penerima),
                f"berita_acara_{berkas['id']}.pdf")


rute = [
    Route("/laporan", indeks),
    Route("/laporan/objek.xlsx", objek_xlsx),
    Route("/laporan/rekap-harian.xlsx", harian_xlsx),
    Route("/laporan/rekap-tahapan.xlsx", tahapan_xlsx),
    Route("/laporan/rekap-potensi.xlsx", potensi_xlsx),
    Route("/laporan/rekap-harian.pdf", harian_pdf),
    Route("/laporan/rekap-potensi.pdf", potensi_pdf),
    Route("/laporan/berkas/{id:int}/kendali.pdf", kendali_pdf),
    Route("/laporan/berkas/{id:int}/berita-acara.pdf", berita_acara_pdf),
]
