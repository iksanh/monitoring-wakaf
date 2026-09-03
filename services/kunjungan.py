"""Kunjungan lapangan: catatan hasil + koordinat dari perangkat petugas."""
import db
from services import audit


def per_objek(objek_id: int) -> list[dict]:
    return db.ambil_semua(
        """SELECT k.*, p.nama AS nama_petugas
             FROM kunjungan k LEFT JOIN pengguna p ON p.id = k.oleh_pengguna_id
            WHERE k.objek_wakaf_id = ? ORDER BY k.tanggal DESC, k.id DESC""",
        (objek_id,),
    )


def catat(objek_id: int, data: dict, pengguna_id: int) -> int:
    kunjungan_id = db.jalankan(
        """INSERT INTO kunjungan (objek_wakaf_id, tanggal, oleh_pengguna_id, hasil,
                                  latitude, longitude, catatan)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (objek_id, data["tanggal"], pengguna_id, data.get("hasil"),
         data.get("latitude"), data.get("longitude"), data.get("catatan")),
    )
    audit.catat(None, pengguna_id, "kunjungan", "objek_wakaf", objek_id, None, dict(data))
    return kunjungan_id


def terbaru(batas: int = 10, wilayah_id=None) -> list[dict]:
    sql = """SELECT k.*, o.nama_objek, o.kode AS objek_kode, p.nama AS nama_petugas
               FROM kunjungan k
               JOIN objek_wakaf o ON o.id = k.objek_wakaf_id
               JOIN kecamatan kc ON kc.id = o.kecamatan_id
               LEFT JOIN pengguna p ON p.id = k.oleh_pengguna_id
              WHERE 1=1"""
    params: list = []
    if wilayah_id:
        sql += " AND kc.wilayah_id = ?"
        params.append(wilayah_id)
    return db.ambil_semua(sql + " ORDER BY k.tanggal DESC, k.id DESC LIMIT ?",
                          tuple(params + [batas]))
