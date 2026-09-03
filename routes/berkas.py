"""Route berkas permohonan, ceklis syarat, dokumen, dan kunjungan lapangan."""
from starlette.responses import FileResponse, PlainTextResponse, RedirectResponse
from starlette.routing import Route

import auth
import config
import web
from services import audit, berkas as svc, ceklis as svc_ceklis
from services import dokumen as svc_dokumen, kunjungan as svc_kunjungan
from services import objek as svc_objek, tahapan as svc_tahapan


@auth.butuh_masuk
async def daftar(request):
    pengguna = request.state.pengguna
    p = request.query_params
    saring = {
        "tahapan_kode": web.teks_atau_none(p.get("tahapan_kode")),
        "wilayah_id": web.int_atau(p.get("wilayah_id")),
        "jenis_permohonan_kode": web.teks_atau_none(p.get("jenis_permohonan_kode")),
        "status": web.teks_atau_none(p.get("status")),
        "q": web.teks_atau_none(p.get("q")),
    }
    hasil = svc.cari(pengguna, saring, web.int_atau(p.get("hlm"), 1) or 1)
    return web.render(request, "berkas/daftar.html", {
        "hasil": hasil, "saring": saring,
        "tahapan": svc_tahapan.daftar(),
        "jenis": svc.daftar_jenis(),
        "wilayah": svc.daftar_wilayah(),
        "kueri": request.url.query,
    })



@auth.butuh_masuk
async def detail(request):
    pengguna = request.state.pengguna
    berkas = svc.ambil(int(request.path_params["id"]))
    if not berkas:
        return PlainTextResponse("404 — Berkas tidak ditemukan.", 404)
    if not svc.boleh_akses(pengguna, berkas):
        return PlainTextResponse("403 — Berkas ini di luar wilayah Anda.", 403)
    return web.render(request, "berkas/detail.html", {
        "berkas": berkas,
        "linimasa": svc_tahapan.riwayat(berkas["id"]),
        "tahapan": svc_tahapan.daftar(),
        "berikutnya": svc.tahapan_berikutnya(berkas),
        "ceklis": svc_ceklis.per_berkas(berkas["id"]),
        "progres": svc_ceklis.progres(berkas["id"]),
        "dokumen": svc_dokumen.per_berkas(berkas["id"]),
        "hari_ini": config.hari_ini_iso(),
    })


@auth.butuh_peran("admin", "sekretariat", "korwil")
async def baru(request):
    pengguna = request.state.pengguna
    objek = svc_objek.ambil(int(request.path_params["id"]))
    if not objek:
        return PlainTextResponse("404 — Objek tidak ditemukan.", 404)
    if not svc_objek.boleh_akses(pengguna, objek):
        return PlainTextResponse("403 — Objek ini di luar wilayah Anda.", 403)
    if request.method == "POST":
        form = await request.form()
        data = {
            "objek_wakaf_id": objek["id"],
            "no_berkas": web.teks_atau_none(form.get("no_berkas")),
            "jenis_permohonan_kode": form.get("jenis_permohonan_kode"),
            "tanggal_daftar": web.teks_atau_none(form.get("tanggal_daftar")),
            "target_penyerahan": web.teks_atau_none(form.get("target_penyerahan")),
            "petugas_id": web.int_atau(form.get("petugas_id")),
            "catatan": web.teks_atau_none(form.get("catatan")),
        }
        if not data["jenis_permohonan_kode"]:
            return web.render(request, "berkas/form.html", {
                "objek": objek, "jenis": svc.daftar_jenis(),
                "petugas": svc.daftar_petugas(), "nilai": data,
                "galat": ["Jenis permohonan wajib dipilih."],
                "hari_ini": config.hari_ini_iso()}, status=400)
        berkas_id = svc.buat(data, pengguna["id"])
        web.pesan(request, "Berkas dibuat. Ceklis syarat sudah disiapkan.")
        return RedirectResponse(f"/berkas/{berkas_id}", status_code=303)
    return web.render(request, "berkas/form.html", {
        "objek": objek, "jenis": svc.daftar_jenis(), "petugas": svc.daftar_petugas(),
        "nilai": {"tanggal_daftar": config.hari_ini_iso()},
        "hari_ini": config.hari_ini_iso()})


@auth.butuh_peran("admin", "sekretariat", "korwil")
async def simpan_ceklis(request):
    pengguna = request.state.pengguna
    berkas = svc.ambil(int(request.path_params["id"]))
    if not berkas or not svc.boleh_akses(pengguna, berkas):
        return PlainTextResponse("403 — Tidak berhak.", 403)
    form = await request.form()
    terpenuhi = {int(v) for v in form.getlist("terpenuhi")}
    catatan = {}
    for kunci in form:
        if kunci.startswith("catatan_"):
            catatan[int(kunci.removeprefix("catatan_"))] = web.teks_atau_none(form.get(kunci))
    svc_ceklis.simpan(berkas["id"], terpenuhi, catatan, pengguna["id"])
    web.pesan(request, "Ceklis diperbarui.")
    return RedirectResponse(f"/berkas/{berkas['id']}#ceklis", status_code=303)


@auth.butuh_masuk
async def unggah_dokumen(request):
    pengguna = request.state.pengguna
    objek = svc_objek.ambil(int(request.path_params["id"]))
    if not objek or not svc_objek.boleh_akses(pengguna, objek):
        return PlainTextResponse("403 — Tidak berhak.", 403)
    form = await request.form()
    jenis = web.teks_atau_none(form.get("jenis")) or "lainnya"
    berkas_id = web.int_atau(form.get("berkas_id"))
    tautan = web.teks_atau_none(form.get("url_eksternal"))
    unggahan = form.get("berkas_file")

    if tautan:
        svc_dokumen.simpan_tautan(objek["id"], berkas_id, jenis, tautan, pengguna["id"])
        web.pesan(request, "Tautan dokumen tersimpan.")
    elif unggahan is not None and getattr(unggahan, "filename", ""):
        isi = await unggahan.read()
        galat = svc_dokumen.periksa_unggahan(unggahan.filename, len(isi))
        if galat:
            web.pesan(request, "Gagal unggah: " + galat)
        else:
            svc_dokumen.simpan_unggahan(objek["id"], berkas_id, jenis,
                                        unggahan.filename, isi, pengguna["id"])
            web.pesan(request, "Dokumen terunggah.")
    else:
        web.pesan(request, "Tidak ada file atau tautan yang dikirim.")
    return RedirectResponse(f"/objek/{objek['id']}#dokumen", status_code=303)


@auth.butuh_masuk
async def unduh_dokumen(request):
    dokumen = svc_dokumen.ambil(int(request.path_params["id"]))
    if not dokumen:
        return PlainTextResponse("404 — Dokumen tidak ditemukan.", 404)
    if dokumen["url_eksternal"]:
        return RedirectResponse(dokumen["url_eksternal"], status_code=303)
    path = svc_dokumen.path_absolut(dokumen)
    if not path:
        return PlainTextResponse("404 — File tidak ada di server.", 404)
    return FileResponse(path, filename=dokumen["nama_file"])


@auth.butuh_masuk
async def catat_kunjungan(request):
    pengguna = request.state.pengguna
    objek = svc_objek.ambil(int(request.path_params["id"]))
    if not objek or not svc_objek.boleh_akses(pengguna, objek):
        return PlainTextResponse("403 — Tidak berhak.", 403)
    form = await request.form()
    svc_kunjungan.catat(objek["id"], {
        "tanggal": web.teks_atau_none(form.get("tanggal")) or config.hari_ini_iso(),
        "hasil": web.teks_atau_none(form.get("hasil")),
        "latitude": web.float_atau(form.get("latitude")),
        "longitude": web.float_atau(form.get("longitude")),
        "catatan": web.teks_atau_none(form.get("catatan")),
    }, pengguna["id"])
    web.pesan(request, "Kunjungan tercatat.")
    return RedirectResponse(f"/objek/{objek['id']}#kunjungan", status_code=303)


rute = [
    Route("/berkas", daftar),
    Route("/berkas/{id:int}", detail),
    Route("/berkas/{id:int}/ceklis", simpan_ceklis, methods=["POST"]),
    Route("/objek/{id:int}/berkas/baru", baru, methods=["GET", "POST"]),
    Route("/objek/{id:int}/dokumen", unggah_dokumen, methods=["POST"]),
    Route("/objek/{id:int}/kunjungan", catat_kunjungan, methods=["POST"]),
    Route("/dokumen/{id:int}", unduh_dokumen),
]
