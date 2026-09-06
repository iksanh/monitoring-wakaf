"""Unggah, pratinjau, penggantian, dan penghapusan dokumen (foto/PDF/tautan)."""
import re
import secrets
import unicodedata
from pathlib import Path

import config
import db
from services import audit, penyimpanan

_TAK_AMAN = re.compile(r"[^a-z0-9]+")

# Ekstensi yang bisa ditampilkan langsung di halaman, beserta tipe MIME-nya.
TIPE_MIME = {
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
    ".pdf": "application/pdf",
}
_PRATINJAU = {".jpg": "gambar", ".jpeg": "gambar", ".png": "gambar", ".pdf": "pdf"}

_KOLOM = """d.id, d.objek_wakaf_id, d.berkas_id, d.jenis, d.nama_file, d.path,
            d.url_eksternal, d.ukuran_byte, d.diunggah_pada, d.oleh,
            d.is_aktif, d.dihapus_pada"""


def slug(nama: str) -> str:
    teks = unicodedata.normalize("NFKD", nama).encode("ascii", "ignore").decode()
    return _TAK_AMAN.sub("-", teks.lower()).strip("-") or "berkas"


def _ekstensi(dokumen: dict) -> str:
    return Path(dokumen.get("nama_file") or dokumen.get("path") or "").suffix.lower()


def tipe_pratinjau(dokumen: dict) -> str | None:
    """'gambar', 'pdf', atau None kalau hanya bisa diunduh / dibuka di tab lain."""
    if not dokumen.get("path"):
        return None
    return _PRATINJAU.get(_ekstensi(dokumen))


def tipe_mime(dokumen: dict) -> str:
    return TIPE_MIME.get(_ekstensi(dokumen), "application/octet-stream")


def _lengkapi(baris: list[dict], pengguna: dict | None) -> list[dict]:
    """Tambah penanda tampilan: jenis pratinjau dan boleh-tidaknya dikelola."""
    for d in baris:
        d["pratinjau"] = tipe_pratinjau(d)
        d["boleh_kelola"] = bool(pengguna) and boleh_kelola(pengguna, d)
    return baris


def per_objek(objek_id: int, pengguna: dict | None = None) -> list[dict]:
    return _lengkapi(db.ambil_semua(
        f"""SELECT {_KOLOM}, p.nama AS nama_pengunggah
              FROM dokumen d LEFT JOIN pengguna p ON p.id = d.oleh
             WHERE d.objek_wakaf_id = ? AND d.is_aktif = 1
             ORDER BY d.id DESC""",
        (objek_id,),
    ), pengguna)


def per_berkas(berkas_id: int, pengguna: dict | None = None) -> list[dict]:
    return _lengkapi(db.ambil_semua(
        f"""SELECT {_KOLOM}, p.nama AS nama_pengunggah
              FROM dokumen d LEFT JOIN pengguna p ON p.id = d.oleh
             WHERE d.berkas_id = ? AND d.is_aktif = 1
             ORDER BY d.id DESC""",
        (berkas_id,),
    ), pengguna)


def periksa_unggahan(nama_file: str, ukuran: int) -> str | None:
    ext = Path(nama_file).suffix.lower()
    if ext not in config.EKSTENSI_DIIZINKAN:
        return f"Jenis file {ext or '(tanpa ekstensi)'} tidak diizinkan. Hanya jpg, png, pdf."
    if ukuran > config.MAKS_UNGGAH_BYTE:
        return f"Ukuran file melebihi {config.MAKS_UNGGAH_BYTE // (1024 * 1024)} MB."
    if ukuran == 0:
        return "File kosong."
    return None


def _tulis_file(objek_id: int, nama_file: str, isi: bytes) -> tuple[str, str]:
    """Simpan berkas, kembalikan (kunci, nama_tampilan).

    Kunci diberi imbuhan acak, bukan nomor urut seperti dulu: di S3 pengecekan
    "sudah terpakai atau belum" berarti satu permintaan HEAD tiap putaran, dan
    dua unggahan bersamaan masih bisa memilih nama yang sama.
    """
    tahun = config.sekarang().strftime("%Y")
    ext = Path(nama_file).suffix.lower()
    dasar = slug(Path(nama_file).stem)[:60]
    kunci = f"{tahun}/{objek_id}/{dasar}-{secrets.token_hex(4)}{ext}"
    penyimpanan.simpan(kunci, isi, TIPE_MIME.get(ext, "application/octet-stream"))
    return kunci, f"{dasar}{ext}"


def simpan_unggahan(objek_id: int, berkas_id, jenis: str, nama_file: str,
                    isi: bytes, pengguna_id: int) -> int:
    kunci, tampilan = _tulis_file(objek_id, nama_file, isi)
    dokumen_id = db.jalankan(
        """INSERT INTO dokumen (objek_wakaf_id, berkas_id, jenis, nama_file, path,
                                ukuran_byte, oleh)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (objek_id, berkas_id, jenis, tampilan, kunci, len(isi), pengguna_id),
    )
    audit.catat(None, pengguna_id, "unggah_dokumen", "dokumen", dokumen_id,
                None, {"objek_wakaf_id": objek_id, "path": kunci})
    return dokumen_id


def simpan_tautan(objek_id: int, berkas_id, jenis: str, url: str, pengguna_id: int) -> int:
    dokumen_id = db.jalankan(
        """INSERT INTO dokumen (objek_wakaf_id, berkas_id, jenis, url_eksternal, oleh)
           VALUES (?, ?, ?, ?, ?)""",
        (objek_id, berkas_id, jenis, url, pengguna_id),
    )
    audit.catat(None, pengguna_id, "tautan_dokumen", "dokumen", dokumen_id,
                None, {"url": url})
    return dokumen_id


def ambil(dokumen_id: int) -> dict | None:
    dokumen = db.ambil_satu(
        f"""SELECT {_KOLOM}, p.nama AS nama_pengunggah
              FROM dokumen d LEFT JOIN pengguna p ON p.id = d.oleh
             WHERE d.id = ?""",
        (dokumen_id,),
    )
    if dokumen:
        dokumen["pratinjau"] = tipe_pratinjau(dokumen)
    return dokumen


def boleh_kelola(pengguna: dict, dokumen: dict) -> bool:
    """Pengunggahnya sendiri boleh; selain itu hanya admin/sekretariat/korwil.

    Pemeriksaan wilayah objeknya dilakukan terpisah oleh pemanggil lewat
    services/objek.boleh_akses(), sama seperti saat mengunggah.
    """
    if pengguna["peran"] == "pimpinan":
        return False
    if dokumen["oleh"] == pengguna["id"]:
        return True
    return pengguna["peran"] in ("admin", "sekretariat", "korwil")


def ganti(dokumen_id: int, jenis: str | None, nama_file: str | None,
          isi: bytes | None, url: str | None, pengguna_id: int) -> None:
    """Perbarui jenis, dan bila diberikan, ganti file atau tautannya.

    File pengganti ditulis dengan nama baru; file lama tidak ditimpa maupun
    dihapus supaya versi sebelumnya masih bisa diambil dari server.
    """
    lama = ambil(dokumen_id)
    if not lama:
        return
    baru = {"jenis": jenis, "path": lama["path"], "nama_file": lama["nama_file"],
            "ukuran_byte": lama["ukuran_byte"], "url_eksternal": lama["url_eksternal"]}
    if isi is not None and nama_file:
        kunci, tampilan = _tulis_file(lama["objek_wakaf_id"], nama_file, isi)
        baru.update(path=kunci, nama_file=tampilan,
                    ukuran_byte=len(isi), url_eksternal=None)
    elif url:
        baru.update(path=None, nama_file=None, ukuran_byte=None, url_eksternal=url)

    db.jalankan(
        """UPDATE dokumen SET jenis = ?, path = ?, nama_file = ?, ukuran_byte = ?,
                              url_eksternal = ?
            WHERE id = ?""",
        (baru["jenis"], baru["path"], baru["nama_file"], baru["ukuran_byte"],
         baru["url_eksternal"], dokumen_id),
    )
    audit.catat(None, pengguna_id, "ubah_dokumen", "dokumen", dokumen_id,
                {k: lama[k] for k in baru}, baru)


def hapus(dokumen_id: int, pengguna_id: int) -> None:
    """Penghapusan logis: baris ditandai, file di server dibiarkan utuh."""
    lama = ambil(dokumen_id)
    if not lama or not lama["is_aktif"]:
        return
    db.jalankan(
        "UPDATE dokumen SET is_aktif = 0, dihapus_pada = ?, dihapus_oleh = ? WHERE id = ?",
        (config.stempel_waktu(), pengguna_id, dokumen_id),
    )
    audit.catat(None, pengguna_id, "hapus_dokumen", "dokumen", dokumen_id,
                {"nama_file": lama["nama_file"], "path": lama["path"],
                 "url_eksternal": lama["url_eksternal"]}, None)


def path_absolut(dokumen: dict) -> Path | None:
    """Path di disk, atau None kalau berkasnya di S3 / tidak ada.

    Route memakainya untuk memilih FileResponse (murah, mendukung Range) sebelum
    jatuh ke isi().
    """
    if not dokumen.get("path"):
        return None
    return penyimpanan.path_lokal(dokumen["path"])


def isi(dokumen: dict) -> bytes:
    """Isi berkas apa pun backend-nya. Melempar GagalPenyimpanan kalau tidak bisa."""
    return penyimpanan.baca(dokumen["path"])


def tersedia(dokumen: dict) -> bool:
    return bool(dokumen.get("path")) and penyimpanan.ada(dokumen["path"])
