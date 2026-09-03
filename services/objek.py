"""Query dan aturan bisnis objek wakaf. Semua SQL modul objek ada di sini."""
import config
import db
from auth import PERAN_TERBATAS_WILAYAH
from services import audit

KOLOM_ISI = (
    "nama_objek", "desa_id", "kecamatan_id", "nama_wakif", "nama_nadzir", "no_aiw",
    "tanggal_aiw", "jenis_alas_hak", "tipe_hak", "nib", "luas_persil",
    "kecamatan_kkp", "desa_kkp", "rtrw", "tipologi_kode", "rekomendasi_isbat",
    "keterangan", "catatan_kua", "latitude", "longitude", "url_maps", "url_dokumen",
    "status_sertipikat", "is_potensi",
)

_PILIH = """
    SELECT o.*, k.nama AS kecamatan_nama, d.nama AS desa_nama,
           w.id AS wilayah_id, w.nama AS wilayah_nama,
           t.nama AS tipologi_nama, t.kompleksitas AS tipologi_kompleksitas
      FROM objek_wakaf o
      JOIN kecamatan k ON k.id = o.kecamatan_id
      LEFT JOIN desa d ON d.id = o.desa_id
      LEFT JOIN wilayah w ON w.id = k.wilayah_id
      LEFT JOIN tipologi t ON t.kode = o.tipologi_kode
"""


def batas_wilayah(pengguna) -> tuple[str, list]:
    """Klausa WHERE tambahan untuk peran yang dibatasi wilayahnya.

    Diterapkan di lapisan service, bukan sekadar menyembunyikan tombol.
    """
    if pengguna and pengguna["peran"] in PERAN_TERBATAS_WILAYAH:
        return (" AND k.wilayah_id = ? ", [pengguna["wilayah_id"] or -1])
    return ("", [])


def boleh_akses(pengguna, objek: dict) -> bool:
    if not pengguna:
        return False
    if pengguna["peran"] not in PERAN_TERBATAS_WILAYAH:
        return True
    return objek.get("wilayah_id") == pengguna["wilayah_id"]


def cari(pengguna, saring: dict, halaman: int = 1,
         per_halaman: int = config.BARIS_PER_HALAMAN) -> dict:
    syarat = ["o.is_aktif = 1"]
    params: list = []

    if saring.get("kecamatan_id"):
        syarat.append("o.kecamatan_id = ?")
        params.append(saring["kecamatan_id"])
    if saring.get("desa_id"):
        syarat.append("o.desa_id = ?")
        params.append(saring["desa_id"])
    if saring.get("tipologi_kode"):
        if saring["tipologi_kode"] == "kosong":
            syarat.append("o.tipologi_kode IS NULL")
        else:
            syarat.append("o.tipologi_kode = ?")
            params.append(saring["tipologi_kode"])
    if saring.get("status_sertipikat"):
        syarat.append("o.status_sertipikat = ?")
        params.append(saring["status_sertipikat"])
    if saring.get("aiw") == "ada":
        syarat.append("o.no_aiw IS NOT NULL AND trim(o.no_aiw) NOT IN ('', '-')")
    elif saring.get("aiw") == "belum":
        syarat.append("(o.no_aiw IS NULL OR trim(o.no_aiw) IN ('', '-'))")
    if saring.get("q"):
        syarat.append("(o.nama_objek LIKE ? OR o.nama_wakif LIKE ? OR o.kode LIKE ?)")
        pola = f"%{saring['q']}%"
        params += [pola, pola, pola]

    where = " WHERE " + " AND ".join(syarat)
    tambah, p_wilayah = batas_wilayah(pengguna)
    where += tambah
    params += p_wilayah

    total = db.ambil_nilai(
        f"""SELECT COUNT(*) FROM objek_wakaf o JOIN kecamatan k ON k.id = o.kecamatan_id
            {where}""",
        tuple(params), 0,
    )
    halaman = max(1, halaman)
    baris = db.ambil_semua(
        _PILIH + where + " ORDER BY k.nama, o.nama_objek LIMIT ? OFFSET ?",
        tuple(params) + (per_halaman, (halaman - 1) * per_halaman),
    )
    return {
        "baris": baris,
        "total": total,
        "halaman": halaman,
        "per_halaman": per_halaman,
        "jumlah_halaman": max(1, -(-total // per_halaman)),
    }


def ambil(objek_id: int) -> dict | None:
    return db.ambil_satu(_PILIH + " WHERE o.id = ?", (objek_id,))


def _kode_baru(kon, kecamatan_id: int) -> str:
    kec = kon.execute(
        "SELECT nama, kode_singkat FROM kecamatan WHERE id = ?", (kecamatan_id,)
    ).fetchone()
    singkat = (kec["kode_singkat"] or kec["nama"][:3]).upper()[:3]
    terakhir = kon.execute(
        "SELECT kode FROM objek_wakaf WHERE kode LIKE ? ORDER BY kode DESC LIMIT 1",
        (f"WKF-{singkat}-%",),
    ).fetchone()
    urut = int(terakhir["kode"].rsplit("-", 1)[1]) + 1 if terakhir else 1
    return f"WKF-{singkat}-{urut:03d}"


def validasi(data: dict) -> list[str]:
    """Validasi ketat hanya pada tiga field. Data tidak lengkap harus boleh disimpan."""
    galat = []
    if not (data.get("nama_objek") or "").strip():
        galat.append("Nama objek wajib diisi.")
    if not data.get("kecamatan_id"):
        galat.append("Kecamatan wajib dipilih.")
    if not data.get("desa_id"):
        galat.append("Desa wajib dipilih.")
    return galat


def buat(data: dict, pengguna_id: int) -> int:
    kon = db.koneksi()
    try:
        kon.execute("BEGIN")
        kode = _kode_baru(kon, data["kecamatan_id"])
        kolom = ", ".join(KOLOM_ISI)
        tanya = ", ".join("?" for _ in KOLOM_ISI)
        kur = kon.execute(
            f"""INSERT INTO objek_wakaf (kode, {kolom}, sumber_data, diubah_pada, diubah_oleh)
                VALUES (?, {tanya}, 'lapangan', ?, ?)""",
            (kode,) + tuple(data.get(k) for k in KOLOM_ISI)
            + (config.stempel_waktu(), pengguna_id),
        )
        audit.catat(kon, pengguna_id, "buat", "objek_wakaf", kur.lastrowid,
                    None, {k: data.get(k) for k in KOLOM_ISI})
        kon.commit()
        return kur.lastrowid
    except Exception:
        kon.rollback()
        raise
    finally:
        kon.close()


def ubah(objek_id: int, data: dict, pengguna_id: int) -> None:
    kon = db.koneksi()
    try:
        kon.execute("BEGIN")
        lama = kon.execute("SELECT * FROM objek_wakaf WHERE id = ?", (objek_id,)).fetchone()
        if not lama:
            raise ValueError("Objek tidak ditemukan.")
        set_sql = ", ".join(f"{k} = ?" for k in KOLOM_ISI)
        kon.execute(
            f"UPDATE objek_wakaf SET {set_sql}, diubah_pada = ?, diubah_oleh = ? WHERE id = ?",
            tuple(data.get(k) for k in KOLOM_ISI)
            + (config.stempel_waktu(), pengguna_id, objek_id),
        )
        berubah = {k: (lama[k], data.get(k)) for k in KOLOM_ISI if lama[k] != data.get(k)}
        audit.catat(kon, pengguna_id, "ubah", "objek_wakaf", objek_id,
                    {k: v[0] for k, v in berubah.items()},
                    {k: v[1] for k, v in berubah.items()})
        kon.commit()
    except Exception:
        kon.rollback()
        raise
    finally:
        kon.close()


def nonaktifkan(objek_id: int, pengguna_id: int) -> None:
    """Objek wakaf tidak pernah dihapus fisik."""
    kon = db.koneksi()
    try:
        kon.execute("BEGIN")
        kon.execute("UPDATE objek_wakaf SET is_aktif = 0, diubah_pada = ?, diubah_oleh = ? "
                    "WHERE id = ?", (config.stempel_waktu(), pengguna_id, objek_id))
        audit.catat(kon, pengguna_id, "nonaktif", "objek_wakaf", objek_id, None, None)
        kon.commit()
    finally:
        kon.close()


def daftar_kecamatan(pengguna=None) -> list[dict]:
    sql = ("SELECT k.id, k.nama, k.wilayah_id FROM kecamatan k WHERE 1=1")
    params: list = []
    if pengguna and pengguna["peran"] in PERAN_TERBATAS_WILAYAH:
        sql += " AND k.wilayah_id = ?"
        params.append(pengguna["wilayah_id"] or -1)
    return db.ambil_semua(sql + " ORDER BY k.nama", tuple(params))


def daftar_desa(pengguna=None) -> list[dict]:
    sql = """SELECT d.id, d.nama, d.kecamatan_id FROM desa d
             JOIN kecamatan k ON k.id = d.kecamatan_id WHERE 1=1"""
    params: list = []
    if pengguna and pengguna["peran"] in PERAN_TERBATAS_WILAYAH:
        sql += " AND k.wilayah_id = ?"
        params.append(pengguna["wilayah_id"] or -1)
    return db.ambil_semua(sql + " ORDER BY d.nama", tuple(params))


def daftar_tipologi() -> list[dict]:
    return db.ambil_semua("SELECT * FROM tipologi ORDER BY urutan")
