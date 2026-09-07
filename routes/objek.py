"""Route modul objek wakaf. Tidak ada SQL di sini — semua lewat services/objek.py."""
from starlette.responses import PlainTextResponse, RedirectResponse
from starlette.routing import Route

import auth
import web
from services import audit, berkas as svc_berkas, kunjungan as svc_kunjungan
from services import dokumen as svc_dokumen, objek as svc
from services import pemilahan as svc_pilah


def _saring_dari(request) -> dict:
    p = request.query_params
    return {
        "kecamatan_id": web.int_atau(p.get("kecamatan_id")),
        "desa_id": web.int_atau(p.get("desa_id")),
        "tipologi_kode": web.teks_atau_none(p.get("tipologi_kode")),
        "status_sertipikat": web.teks_atau_none(p.get("status_sertipikat")),
        "aiw": web.teks_atau_none(p.get("aiw")),
        "tindak_lanjut": web.teks_atau_none(p.get("tindak_lanjut")),
        "prioritas": web.teks_atau_none(p.get("prioritas")),
        "q": web.teks_atau_none(p.get("q")),
    }


async def _form_data(request) -> dict:
    form = await request.form()
    ambil = lambda k: web.teks_atau_none(form.get(k))  # noqa: E731
    return {
        "nama_objek": ambil("nama_objek"),
        "kecamatan_id": web.int_atau(form.get("kecamatan_id")),
        "desa_id": web.int_atau(form.get("desa_id")),
        "nama_wakif": ambil("nama_wakif"),
        "nama_nadzir": ambil("nama_nadzir"),
        "no_aiw": ambil("no_aiw"),
        "tanggal_aiw": ambil("tanggal_aiw"),
        "jenis_alas_hak": ambil("jenis_alas_hak"),
        "tipe_hak": ambil("tipe_hak"),
        "nib": ambil("nib"),
        "luas_persil": web.float_atau(form.get("luas_persil")),
        "kecamatan_kkp": ambil("kecamatan_kkp"),
        "desa_kkp": ambil("desa_kkp"),
        "rtrw": ambil("rtrw"),
        "tipologi_kode": ambil("tipologi_kode"),
        "rekomendasi_isbat": ambil("rekomendasi_isbat"),
        "keterangan": ambil("keterangan"),
        "catatan_kua": ambil("catatan_kua"),
        "latitude": web.float_atau(form.get("latitude")),
        "longitude": web.float_atau(form.get("longitude")),
        "url_maps": ambil("url_maps"),
        "url_dokumen": ambil("url_dokumen"),
        "status_sertipikat": ambil("status_sertipikat") or "belum",
        "perlu_isbat": 1 if form.get("perlu_isbat") else 0,
        "is_prioritas": 1 if form.get("is_prioritas") else 0,
    }


@auth.butuh_masuk
async def daftar(request):
    pengguna = request.state.pengguna
    saring = _saring_dari(request)
    halaman = web.int_atau(request.query_params.get("hlm"), 1) or 1
    hasil = svc.cari(pengguna, saring, halaman)
    return web.render(request, "objek/daftar.html", {
        "hasil": hasil,
        "saring": saring,
        "kecamatan": svc.daftar_kecamatan(pengguna),
        "desa": svc.daftar_desa(pengguna),
        "tipologi": svc.daftar_tipologi(),
        "kueri": request.url.query,
        "boleh_pilah": svc_pilah.boleh_memilah(pengguna),
        "LABEL_PILAH": svc_pilah.LABEL,
    })


@auth.butuh_masuk
async def detail(request):
    pengguna = request.state.pengguna
    objek = svc.ambil(int(request.path_params["id"]))
    if not objek:
        return PlainTextResponse("404 — Objek tidak ditemukan.", 404)
    if not svc.boleh_akses(pengguna, objek):
        return PlainTextResponse("403 — Objek ini di luar wilayah Anda.", 403)
    return web.render(request, "objek/detail.html", {
        "objek": objek,
        "berkas": svc_berkas.per_objek(objek["id"]),
        "dokumen": svc_dokumen.per_objek(objek["id"], pengguna),
        "kunjungan": svc_kunjungan.per_objek(objek["id"]),
        "riwayat": audit.riwayat("objek_wakaf", objek["id"]),
        "jenis_permohonan": svc_berkas.daftar_jenis(),
        "boleh_pilah": svc_pilah.boleh_memilah(pengguna),
        "LABEL_PILAH": svc_pilah.LABEL,
    })


@auth.butuh_peran("admin", "sekretariat", "korwil", "petugas")
async def baru(request):
    pengguna = request.state.pengguna
    if request.method == "POST":
        data = await _form_data(request)
        galat = svc.validasi(data)
        if not galat:
            objek_id = svc.buat(data, pengguna["id"])
            web.pesan(request, "Objek wakaf tersimpan.")
            return RedirectResponse(f"/objek/{objek_id}", status_code=303)
        return web.render(request, "objek/form.html", _konteks_form(
            pengguna, data, galat=galat), status=400)
    return web.render(request, "objek/form.html", _konteks_form(pengguna, {
        "status_sertipikat": "belum"}))


@auth.butuh_peran("admin", "sekretariat", "korwil", "petugas")
async def ubah(request):
    pengguna = request.state.pengguna
    objek = svc.ambil(int(request.path_params["id"]))
    if not objek:
        return PlainTextResponse("404 — Objek tidak ditemukan.", 404)
    if not svc.boleh_akses(pengguna, objek):
        return PlainTextResponse("403 — Objek ini di luar wilayah Anda.", 403)
    if request.method == "POST":
        data = await _form_data(request)
        galat = svc.validasi(data)
        if not galat:
            svc.ubah(objek["id"], data, pengguna["id"])
            web.pesan(request, "Perubahan tersimpan.")
            return RedirectResponse(f"/objek/{objek['id']}", status_code=303)
        return web.render(request, "objek/form.html", _konteks_form(
            pengguna, {**objek, **data}, galat=galat, objek=objek), status=400)
    return web.render(request, "objek/form.html", _konteks_form(pengguna, objek, objek=objek))


@auth.butuh_peran(*svc_pilah.PERAN_PEMILAH)
async def pilah(request):
    """Tandai satu atau banyak objek sekaligus: bisa / tidak bisa ditindaklanjuti.

    Dipakai dua tempat: bilah centang di daftar objek, dan panel di halaman
    detail. Keduanya kembali ke halaman asalnya lengkap dengan penyaringnya.
    """
    pengguna = request.state.pengguna
    form = await request.form()
    kembali = _kembali_sah(form.get("kembali"))
    try:
        hasil = svc_pilah.pilah(form.getlist("objek_id"),
                                web.teks_atau_none(form.get("status")) or "",
                                pengguna, form.get("alasan"))
    except svc_pilah.GalatPemilahan as galat:
        web.pesan(request, str(galat))
        return RedirectResponse(kembali, status_code=303)

    catatan = f"{hasil['diubah']} objek ditandai “{svc_pilah.LABEL[hasil['status']]}”."
    if hasil["tetap"]:
        catatan += f" {hasil['tetap']} sudah bertanda itu sebelumnya."
    if hasil["dilewati"]:
        catatan += f" {hasil['dilewati']} dilewati karena di luar wilayah Anda."
    web.pesan(request, catatan)
    return RedirectResponse(kembali, status_code=303)


def _kembali_sah(nilai) -> str:
    """Batasi tujuan redirect ke halaman objek saja — jangan percaya form."""
    tujuan = (nilai or "").strip()
    if tujuan.startswith("/objek/") and tujuan[7:].isdigit():
        return tujuan
    kueri = tujuan[len("/objek?"):] if tujuan.startswith("/objek?") else ""
    return f"/objek?{kueri}" if kueri else "/objek"


def _konteks_form(pengguna, nilai, galat=None, objek=None) -> dict:
    return {
        "nilai": nilai,
        "objek": objek,
        "galat": galat or [],
        "kecamatan": svc.daftar_kecamatan(pengguna),
        "desa": svc.daftar_desa(pengguna),
        "tipologi": svc.daftar_tipologi(),
    }


rute = [
    Route("/objek", daftar),
    Route("/objek/baru", baru, methods=["GET", "POST"]),
    Route("/objek/pilah", pilah, methods=["POST"]),
    Route("/objek/{id:int}", detail),
    Route("/objek/{id:int}/ubah", ubah, methods=["GET", "POST"]),
]
