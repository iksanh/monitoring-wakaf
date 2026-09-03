"""Unggah dan pencatatan dokumen (foto/PDF) serta tautan Google Drive."""
import re
import unicodedata
from pathlib import Path

import config
import db
from services import audit

_TAK_AMAN = re.compile(r"[^a-z0-9]+")


def slug(nama: str) -> str:
    teks = unicodedata.normalize("NFKD", nama).encode("ascii", "ignore").decode()
    return _TAK_AMAN.sub("-", teks.lower()).strip("-") or "berkas"


def per_objek(objek_id: int) -> list[dict]:
    return db.ambil_semua(
        """SELECT d.*, p.nama AS nama_pengunggah
             FROM dokumen d LEFT JOIN pengguna p ON p.id = d.oleh
            WHERE d.objek_wakaf_id = ? ORDER BY d.id DESC""",
        (objek_id,),
    )


def per_berkas(berkas_id: int) -> list[dict]:
    return db.ambil_semua(
        """SELECT d.*, p.nama AS nama_pengunggah
             FROM dokumen d LEFT JOIN pengguna p ON p.id = d.oleh
            WHERE d.berkas_id = ? ORDER BY d.id DESC""",
        (berkas_id,),
    )


def periksa_unggahan(nama_file: str, ukuran: int) -> str | None:
    ext = Path(nama_file).suffix.lower()
    if ext not in config.EKSTENSI_DIIZINKAN:
        return f"Jenis file {ext or '(tanpa ekstensi)'} tidak diizinkan. Hanya jpg, png, pdf."
    if ukuran > config.MAKS_UNGGAH_BYTE:
        return f"Ukuran file melebihi {config.MAKS_UNGGAH_BYTE // (1024 * 1024)} MB."
    if ukuran == 0:
        return "File kosong."
    return None


def simpan_unggahan(objek_id: int, berkas_id, jenis: str, nama_file: str,
                    isi: bytes, pengguna_id: int) -> int:
    """Tulis file ke UPLOAD_DIR/<tahun>/<objek_id>/ lalu catat metadatanya."""
    tahun = config.sekarang().strftime("%Y")
    folder = config.UPLOAD_DIR / tahun / str(objek_id)
    folder.mkdir(parents=True, exist_ok=True)
    ext = Path(nama_file).suffix.lower()
    dasar = slug(Path(nama_file).stem)[:60]
    tujuan = folder / f"{dasar}{ext}"
    urut = 1
    while tujuan.exists():
        urut += 1
        tujuan = folder / f"{dasar}-{urut}{ext}"
    tujuan.write_bytes(isi)
    relatif = str(tujuan.relative_to(config.UPLOAD_DIR)).replace("\\", "/")

    dokumen_id = db.jalankan(
        """INSERT INTO dokumen (objek_wakaf_id, berkas_id, jenis, nama_file, path,
                                ukuran_byte, oleh)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (objek_id, berkas_id, jenis, tujuan.name, relatif, len(isi), pengguna_id),
    )
    audit.catat(None, pengguna_id, "unggah_dokumen", "dokumen", dokumen_id,
                None, {"objek_wakaf_id": objek_id, "path": relatif})
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
    return db.ambil_satu("SELECT * FROM dokumen WHERE id = ?", (dokumen_id,))


def path_absolut(dokumen: dict) -> Path | None:
    if not dokumen.get("path"):
        return None
    calon = (config.UPLOAD_DIR / dokumen["path"]).resolve()
    akar = config.UPLOAD_DIR.resolve()
    if akar not in calon.parents:
        return None
    return calon if calon.exists() else None
