"""Query dan aturan berkas permohonan."""
import config
import db
from auth import PERAN_TERBATAS_WILAYAH
from services import audit, ceklis, tahapan as svc_tahapan

_PILIH = """
    SELECT b.*, o.nama_objek, o.kode AS objek_kode, o.kecamatan_id,
           k.nama AS kecamatan_nama, w.id AS wilayah_id, w.nama AS wilayah_nama,
           t.nama AS tahapan_nama, t.urutan AS tahapan_urutan, t.sla_hari,
           j.nama AS jenis_nama, p.nama AS petugas_nama,
           (SELECT max(r.tanggal) FROM riwayat_tahapan r WHERE r.berkas_id = b.id)
               AS tanggal_gerak_terakhir
      FROM berkas b
      JOIN objek_wakaf o ON o.id = b.objek_wakaf_id
      JOIN kecamatan k ON k.id = o.kecamatan_id
      LEFT JOIN wilayah w ON w.id = k.wilayah_id
      JOIN tahapan t ON t.kode = b.tahapan_kode
      JOIN jenis_permohonan j ON j.kode = b.jenis_permohonan_kode
      LEFT JOIN pengguna p ON p.id = b.petugas_id
"""


def batas_wilayah(pengguna) -> tuple[str, list]:
    if pengguna and pengguna["peran"] in PERAN_TERBATAS_WILAYAH:
        return (" AND k.wilayah_id = ? ", [pengguna["wilayah_id"] or -1])
    return ("", [])


def boleh_akses(pengguna, berkas: dict) -> bool:
    if not pengguna:
        return False
    if pengguna["peran"] not in PERAN_TERBATAS_WILAYAH:
        return True
    return berkas.get("wilayah_id") == pengguna["wilayah_id"]


def daftar_jenis() -> list[dict]:
    return db.ambil_semua("SELECT * FROM jenis_permohonan ORDER BY urutan")


def cari(pengguna, saring: dict, halaman: int = 1,
         per_halaman: int = config.BARIS_PER_HALAMAN) -> dict:
    syarat, params = ["1=1"], []
    if saring.get("tahapan_kode"):
        syarat.append("b.tahapan_kode = ?")
        params.append(saring["tahapan_kode"])
    if saring.get("wilayah_id"):
        syarat.append("k.wilayah_id = ?")
        params.append(saring["wilayah_id"])
    if saring.get("jenis_permohonan_kode"):
        syarat.append("b.jenis_permohonan_kode = ?")
        params.append(saring["jenis_permohonan_kode"])
    if saring.get("status"):
        syarat.append("b.status = ?")
        params.append(saring["status"])
    if saring.get("q"):
        syarat.append("(o.nama_objek LIKE ? OR b.no_berkas LIKE ?)")
        params += [f"%{saring['q']}%"] * 2

    where = " WHERE " + " AND ".join(syarat)
    tambah, p = batas_wilayah(pengguna)
    where += tambah
    params += p

    total = db.ambil_nilai(
        f"""SELECT COUNT(*) FROM berkas b
              JOIN objek_wakaf o ON o.id = b.objek_wakaf_id
              JOIN kecamatan k ON k.id = o.kecamatan_id {where}""",
        tuple(params), 0,
    )
    baris = db.ambil_semua(
        _PILIH + where + " ORDER BY t.urutan, b.tanggal_daftar DESC, b.id DESC LIMIT ? OFFSET ?",
        tuple(params) + (per_halaman, (max(1, halaman) - 1) * per_halaman),
    )
    return {"baris": baris, "total": total, "halaman": max(1, halaman),
            "jumlah_halaman": max(1, -(-total // per_halaman))}


def ambil(berkas_id: int) -> dict | None:
    return db.ambil_satu(_PILIH + " WHERE b.id = ?", (berkas_id,))


def per_objek(objek_id: int) -> list[dict]:
    return db.ambil_semua(_PILIH + " WHERE b.objek_wakaf_id = ? ORDER BY b.id DESC",
                          (objek_id,))


def buat(data: dict, pengguna_id: int) -> int:
    """Buat berkas baru, salin ceklis syarat, dan catat tahapan pertama."""
    tahapan_awal = db.ambil_satu("SELECT kode FROM tahapan ORDER BY urutan LIMIT 1")
    kon = db.koneksi()
    try:
        kon.execute("BEGIN")
        kur = kon.execute(
            """INSERT INTO berkas (no_berkas, objek_wakaf_id, jenis_permohonan_kode,
                                   tahapan_kode, status, tanggal_daftar,
                                   target_penyerahan, petugas_id, catatan)
               VALUES (?, ?, ?, ?, 'aktif', ?, ?, ?, ?)""",
            (data.get("no_berkas"), data["objek_wakaf_id"], data["jenis_permohonan_kode"],
             tahapan_awal["kode"], data.get("tanggal_daftar") or config.hari_ini_iso(),
             data.get("target_penyerahan"), data.get("petugas_id"), data.get("catatan")),
        )
        berkas_id = kur.lastrowid
        ceklis.salin_syarat(kon, berkas_id, data["jenis_permohonan_kode"])
        kon.execute(
            """INSERT INTO riwayat_tahapan
                   (berkas_id, tahapan_kode, aksi, tanggal, catatan, oleh_pengguna_id)
               VALUES (?, ?, 'masuk', ?, 'Berkas dibuat.', ?)""",
            (berkas_id, tahapan_awal["kode"],
             data.get("tanggal_daftar") or config.hari_ini_iso(), pengguna_id),
        )
        audit.catat(kon, pengguna_id, "buat", "berkas", berkas_id, None, dict(data))
        kon.commit()
        return berkas_id
    except Exception:
        kon.rollback()
        raise
    finally:
        kon.close()


KOLOM_UBAH = ("no_berkas", "jenis_permohonan_kode", "status", "tanggal_daftar",
              "target_penyerahan", "petugas_id", "catatan")


def ubah(berkas_id: int, data: dict, pengguna_id: int) -> None:
    """Ubah data administratif berkas. tahapan_kode TIDAK pernah disentuh di sini."""
    kon = db.koneksi()
    try:
        kon.execute("BEGIN")
        lama = kon.execute("SELECT * FROM berkas WHERE id = ?", (berkas_id,)).fetchone()
        if not lama:
            raise ValueError("Berkas tidak ditemukan.")
        set_sql = ", ".join(f"{k} = ?" for k in KOLOM_UBAH)
        kon.execute(
            f"UPDATE berkas SET {set_sql}, diubah_pada = ? WHERE id = ?",
            tuple(data.get(k) for k in KOLOM_UBAH) + (config.stempel_waktu(), berkas_id),
        )
        audit.catat(kon, pengguna_id, "ubah", "berkas", berkas_id,
                    {k: lama[k] for k in KOLOM_UBAH}, {k: data.get(k) for k in KOLOM_UBAH})
        kon.commit()
    except Exception:
        kon.rollback()
        raise
    finally:
        kon.close()


def daftar_wilayah() -> list[dict]:
    return db.ambil_semua("SELECT id, nama FROM wilayah ORDER BY urutan")


def daftar_petugas() -> list[dict]:
    return db.ambil_semua(
        "SELECT id, nama, peran FROM pengguna WHERE aktif = 1 ORDER BY nama")


def tahapan_berikutnya(berkas: dict) -> dict | None:
    return svc_tahapan.berikutnya(berkas["tahapan_kode"])
