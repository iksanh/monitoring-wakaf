"""Pergerakan tahapan berkas.

SATU-SATUNYA tempat yang boleh menulis berkas.tahapan_kode. Setiap pergerakan
menulis riwayat_tahapan DAN meng-update berkas dalam satu transaksi. Semua rekap
harian bersandar pada aturan ini.
"""
import config
import db
from services import audit

AKSI_SAH = ("masuk", "selesai", "kendala", "mundur")


class PindahDitolak(Exception):
    """Pergerakan tidak memenuhi aturan domain."""


def daftar() -> list[dict]:
    return db.ambil_semua("SELECT * FROM tahapan ORDER BY urutan")


def peta_urutan() -> dict:
    return {t["kode"]: t["urutan"] for t in daftar()}


def berikutnya(kode: str) -> dict | None:
    return db.ambil_satu(
        """SELECT * FROM tahapan
            WHERE urutan > (SELECT urutan FROM tahapan WHERE kode = ?)
            ORDER BY urutan LIMIT 1""",
        (kode,),
    )


def riwayat(berkas_id: int) -> list[dict]:
    return db.ambil_semua(
        """SELECT r.*, t.nama AS tahapan_nama, t.urutan AS tahapan_urutan,
                  p.nama AS nama_pengguna
             FROM riwayat_tahapan r
             JOIN tahapan t ON t.kode = r.tahapan_kode
             LEFT JOIN pengguna p ON p.id = r.oleh_pengguna_id
            WHERE r.berkas_id = ?
            ORDER BY r.tanggal, r.id""",
        (berkas_id,),
    )


def pindah(berkas_id: int, tahapan_kode: str, aksi: str = "masuk",
           tanggal: str | None = None, catatan: str | None = None,
           pengguna_id: int | None = None, paksa: bool = False) -> dict:
    """Pindahkan berkas ke tahapan tertentu.

    Menolak lompatan mundur kecuali aksi='mundur' dengan catatan terisi.
    Aksi 'kendala' hanya mencatat, tidak menggeser posisi berkas.
    """
    if aksi not in AKSI_SAH:
        raise PindahDitolak(f"Aksi '{aksi}' tidak dikenal.")
    tanggal = tanggal or config.hari_ini_iso()

    kon = db.koneksi()
    try:
        kon.execute("BEGIN")
        berkas = kon.execute("SELECT * FROM berkas WHERE id = ?", (berkas_id,)).fetchone()
        if not berkas:
            raise PindahDitolak("Berkas tidak ditemukan.")

        tujuan = kon.execute("SELECT * FROM tahapan WHERE kode = ?", (tahapan_kode,)).fetchone()
        if not tujuan:
            raise PindahDitolak(f"Tahapan '{tahapan_kode}' tidak ada.")
        kini = kon.execute("SELECT * FROM tahapan WHERE kode = ?",
                           (berkas["tahapan_kode"],)).fetchone()

        mundur = tujuan["urutan"] < kini["urutan"]
        if mundur and aksi != "mundur":
            raise PindahDitolak(
                "Tidak boleh mundur ke tahapan sebelumnya. Pakai aksi 'mundur' "
                "dan isi alasannya."
            )
        if aksi == "mundur" and not (catatan or "").strip():
            raise PindahDitolak("Aksi mundur wajib disertai catatan alasan.")

        kon.execute(
            """INSERT INTO riwayat_tahapan
                   (berkas_id, tahapan_kode, aksi, tanggal, catatan, oleh_pengguna_id)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (berkas_id, tahapan_kode, aksi, tanggal, catatan, pengguna_id),
        )

        if aksi != "kendala":
            status = berkas["status"]
            tanggal_selesai = berkas["tanggal_selesai"]
            terakhir = kon.execute(
                "SELECT kode FROM tahapan ORDER BY urutan DESC LIMIT 1").fetchone()
            if aksi == "selesai" and tahapan_kode == terakhir["kode"]:
                status, tanggal_selesai = "selesai", tanggal
            kon.execute(
                """UPDATE berkas SET tahapan_kode = ?, status = ?, tanggal_selesai = ?,
                                     diubah_pada = ?
                    WHERE id = ?""",
                (tahapan_kode, status, tanggal_selesai, config.stempel_waktu(), berkas_id),
            )

        audit.catat(kon, pengguna_id, f"tahapan_{aksi}", "berkas", berkas_id,
                    {"tahapan_kode": berkas["tahapan_kode"]},
                    {"tahapan_kode": tahapan_kode, "tanggal": tanggal, "catatan": catatan})
        kon.commit()
        return {"berkas_id": berkas_id, "tahapan_kode": tahapan_kode,
                "aksi": aksi, "tanggal": tanggal}
    except Exception:
        kon.rollback()
        raise
    finally:
        kon.close()
