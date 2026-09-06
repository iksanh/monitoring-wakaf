"""Route dokumen objek/berkas: unggah, pratinjau, ganti, hapus."""
from starlette.responses import (FileResponse, PlainTextResponse, RedirectResponse,
                                 Response)
from starlette.routing import Route

import auth
import web
from services import dokumen as svc_dokumen, objek as svc_objek, penyimpanan


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
            try:
                svc_dokumen.simpan_unggahan(objek["id"], berkas_id, jenis,
                                            unggahan.filename, isi, pengguna["id"])
                web.pesan(request, "Dokumen terunggah.")
            except penyimpanan.GagalPenyimpanan as kendala:
                web.pesan(request, f"Gagal unggah: {kendala}")
    else:
        web.pesan(request, "Tidak ada file atau tautan yang dikirim.")
    return RedirectResponse(f"/objek/{objek['id']}#dokumen", status_code=303)


def _dokumen_terjangkau(request):
    """Ambil dokumen sekaligus pastikan objeknya masih dalam wilayah pengguna.

    Kembalikan (dokumen, None) kalau boleh, atau (None, respons galat).
    """
    dokumen = svc_dokumen.ambil(int(request.path_params["id"]))
    if not dokumen or not dokumen["is_aktif"]:
        return None, PlainTextResponse("404 — Dokumen tidak ditemukan.", 404)
    objek = svc_objek.ambil(dokumen["objek_wakaf_id"]) if dokumen["objek_wakaf_id"] else None
    if objek and not svc_objek.boleh_akses(request.state.pengguna, objek):
        return None, PlainTextResponse("403 — Dokumen ini di luar wilayah Anda.", 403)
    return dokumen, None


def _sebutan(nama: str) -> str:
    """Nama file ikut ke header mentah, jadi buang karakter yang bisa merusaknya."""
    return "".join(c for c in nama if c.isascii() and c.isprintable()
                   and c != chr(34)) or "dokumen"


def _sajikan(dokumen, sebaris: bool):
    """Kirim berkas: dari disk lewat FileResponse, dari S3 lewat isi di memori.

    Sengaja tidak memakai presigned URL. Dengan diambilkan aplikasi, pemeriksaan
    wilayah di _dokumen_terjangkau() tetap berlaku untuk setiap permintaan dan
    tidak ada alamat bucket yang bisa disalin keluar. Ukuran unggahan dibatasi
    10 MB, jadi menaruhnya di memori sebentar masih wajar.
    """
    nama = dokumen["nama_file"] or "dokumen"
    tanda = ("inline" if sebaris else "attachment") + f'; filename="{_sebutan(nama)}"'

    berkas = svc_dokumen.path_absolut(dokumen)
    if berkas is not None:
        if not sebaris:
            return FileResponse(berkas, filename=nama)
        return FileResponse(berkas, media_type=svc_dokumen.tipe_mime(dokumen),
                            headers={"Content-Disposition": tanda})

    try:
        muatan = svc_dokumen.isi(dokumen)
    except (penyimpanan.KunciTidakSah, penyimpanan.BerkasHilang):
        return PlainTextResponse("404 — File tidak ada di penyimpanan.", 404)
    except penyimpanan.GagalPenyimpanan:
        return PlainTextResponse(
            "503 — Penyimpanan berkas sedang tidak bisa dihubungi. Coba lagi sebentar lagi.",
            503)
    return Response(muatan, media_type=svc_dokumen.tipe_mime(dokumen),
                    headers={"Content-Disposition": tanda})


@auth.butuh_masuk
async def unduh_dokumen(request):
    dokumen, galat = _dokumen_terjangkau(request)
    if galat:
        return galat
    if dokumen["url_eksternal"]:
        return RedirectResponse(dokumen["url_eksternal"], status_code=303)
    return _sajikan(dokumen, sebaris=False)


@auth.butuh_masuk
async def pratinjau_dokumen(request):
    """Sajikan file apa adanya supaya bisa ditampilkan di <img> / <iframe>."""
    dokumen, galat = _dokumen_terjangkau(request)
    if galat:
        return galat
    if dokumen["url_eksternal"]:
        return RedirectResponse(dokumen["url_eksternal"], status_code=303)
    if not dokumen["pratinjau"]:
        return PlainTextResponse("415 — Jenis file ini tidak bisa dipratinjau.", 415)
    return _sajikan(dokumen, sebaris=True)


@auth.butuh_masuk
async def ubah_dokumen(request):
    pengguna = request.state.pengguna
    dokumen, galat = _dokumen_terjangkau(request)
    if galat:
        return galat
    if not svc_dokumen.boleh_kelola(pengguna, dokumen):
        return PlainTextResponse("403 — Hanya pengunggah atau sekretariat yang boleh mengubah.", 403)
    form = await request.form()
    jenis = web.teks_atau_none(form.get("jenis")) or "lainnya"
    tautan = web.teks_atau_none(form.get("url_eksternal"))
    unggahan = form.get("berkas_file")
    nama_file, isi = None, None
    if unggahan is not None and getattr(unggahan, "filename", ""):
        isi = await unggahan.read()
        pesan_galat = svc_dokumen.periksa_unggahan(unggahan.filename, len(isi))
        if pesan_galat:
            web.pesan(request, "Gagal ganti file: " + pesan_galat)
            return _kembali(dokumen)
        nama_file = unggahan.filename
    try:
        svc_dokumen.ganti(dokumen["id"], jenis, nama_file, isi, tautan, pengguna["id"])
        web.pesan(request, "Dokumen diperbarui.")
    except penyimpanan.GagalPenyimpanan as kendala:
        web.pesan(request, f"Gagal menyimpan file pengganti: {kendala}")
    return _kembali(dokumen)


@auth.butuh_masuk
async def hapus_dokumen(request):
    pengguna = request.state.pengguna
    dokumen, galat = _dokumen_terjangkau(request)
    if galat:
        return galat
    if not svc_dokumen.boleh_kelola(pengguna, dokumen):
        return PlainTextResponse("403 — Hanya pengunggah atau sekretariat yang boleh menghapus.", 403)
    svc_dokumen.hapus(dokumen["id"], pengguna["id"])
    web.pesan(request, "Dokumen dihapus dari daftar. Filenya masih tersimpan.")
    return _kembali(dokumen)


def _kembali(dokumen):
    tujuan = (f"/objek/{dokumen['objek_wakaf_id']}#dokumen" if dokumen["objek_wakaf_id"]
              else f"/berkas/{dokumen['berkas_id']}")
    return RedirectResponse(tujuan, status_code=303)


rute = [
    Route("/objek/{id:int}/dokumen", unggah_dokumen, methods=["POST"]),
    Route("/dokumen/{id:int}", unduh_dokumen),
    Route("/dokumen/{id:int}/pratinjau", pratinjau_dokumen),
    Route("/dokumen/{id:int}/ubah", ubah_dokumen, methods=["POST"]),
    Route("/dokumen/{id:int}/hapus", hapus_dokumen, methods=["POST"]),
]
