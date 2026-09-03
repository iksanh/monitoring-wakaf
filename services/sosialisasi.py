"""Jadwal sosialisasi/penyuluhan wakaf."""
import db
from services import audit


def daftar(status: str | None = None) -> list[dict]:
    sql = """SELECT s.*,
                    (SELECT group_concat(k.nama, ', ')
                       FROM sosialisasi_kecamatan sk JOIN kecamatan k ON k.id = sk.kecamatan_id
                      WHERE sk.sosialisasi_id = s.id) AS kecamatan_sasaran
               FROM sosialisasi s WHERE 1=1"""
    params: list = []
    if status:
        sql += " AND s.status = ?"
        params.append(status)
    return db.ambil_semua(sql + " ORDER BY s.tanggal, s.jam_mulai", tuple(params))


def ambil(sosialisasi_id: int) -> dict | None:
    baris = db.ambil_satu("SELECT * FROM sosialisasi WHERE id = ?", (sosialisasi_id,))
    if baris:
        baris["kecamatan_ids"] = [
            b["kecamatan_id"] for b in db.ambil_semua(
                "SELECT kecamatan_id FROM sosialisasi_kecamatan WHERE sosialisasi_id = ?",
                (sosialisasi_id,))
        ]
    return baris


KOLOM = ("tanggal", "jam_mulai", "jam_selesai", "lokasi", "pembina", "status",
         "jumlah_peserta", "catatan")


def simpan(sosialisasi_id, data: dict, kecamatan_ids: list, pengguna_id: int) -> int:
    kon = db.koneksi()
    try:
        kon.execute("BEGIN")
        if sosialisasi_id:
            set_sql = ", ".join(f"{k} = ?" for k in KOLOM)
            kon.execute(f"UPDATE sosialisasi SET {set_sql} WHERE id = ?",
                        tuple(data.get(k) for k in KOLOM) + (sosialisasi_id,))
            aksi = "ubah"
        else:
            kur = kon.execute(
                f"""INSERT INTO sosialisasi ({", ".join(KOLOM)})
                    VALUES ({", ".join("?" for _ in KOLOM)})""",
                tuple(data.get(k) for k in KOLOM))
            sosialisasi_id = kur.lastrowid
            aksi = "buat"
        kon.execute("DELETE FROM sosialisasi_kecamatan WHERE sosialisasi_id = ?",
                    (sosialisasi_id,))
        for kid in kecamatan_ids:
            kon.execute(
                "INSERT OR IGNORE INTO sosialisasi_kecamatan (sosialisasi_id, kecamatan_id) "
                "VALUES (?, ?)", (sosialisasi_id, kid))
        audit.catat(kon, pengguna_id, aksi, "sosialisasi", sosialisasi_id, None, dict(data))
        kon.commit()
        return sosialisasi_id
    except Exception:
        kon.rollback()
        raise
    finally:
        kon.close()
