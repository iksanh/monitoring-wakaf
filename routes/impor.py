"""Route impor Excel: unggah, pratinjau (dry-run), lalu konfirmasi."""
import tempfile
from pathlib import Path

from starlette.routing import Route

import auth
import web
from services import impor_simpan


@auth.butuh_peran("admin")
async def halaman(request):
    if request.method != "POST":
        return web.render(request, "impor.html", {})

    form = await request.form()
    unggahan = form.get("berkas_excel")
    if not unggahan or not getattr(unggahan, "filename", ""):
        return web.render(request, "impor.html",
                          {"galat": "Pilih file .xlsx dulu."}, status=400)
    if not unggahan.filename.lower().endswith(".xlsx"):
        return web.render(request, "impor.html",
                          {"galat": "Hanya file .xlsx yang diterima."}, status=400)

    dry_run = form.get("aksi") != "simpan"
    isi = await unggahan.read()
    sementara = Path(tempfile.gettempdir()) / f"impor_wakaf_{unggahan.filename}"
    sementara.write_bytes(isi)
    try:
        laporan = impor_simpan.impor(sementara, pengguna_id=request.state.pengguna["id"],
                                     dry_run=dry_run)
    except Exception as galat:  # laporkan ke pengguna, jangan diam-diam gagal
        return web.render(request, "impor.html",
                          {"galat": f"Impor gagal: {galat}"}, status=500)
    finally:
        sementara.unlink(missing_ok=True)

    return web.render(request, "impor.html", {
        "laporan": laporan,
        "teks_laporan": impor_simpan.teks_laporan(laporan),
        "dry_run": dry_run,
        "nama_berkas": unggahan.filename,
    })


rute = [Route("/impor", halaman, methods=["GET", "POST"])]
