"""Pergerakan tahapan berkas.

SATU-SATUNYA tempat yang boleh menulis berkas.tahapan_kode. Setiap pergerakan
menulis riwayat_tahapan DAN meng-update berkas dalam satu transaksi. Semua rekap
harian bersandar pada aturan ini.
"""
import config
import db
from services import audit

AKSI_SAH = ("masuk", "selesai", "kendala", "mundur")

# Tahapan tempat berkas lahir sebelum masuk loket. Tidak pernah jadi tujuan maju.
TAHAPAN_AWAL = "pra_daftar"


class PindahDitolak(Exception):
    """Pergerakan tidak memenuhi aturan domain."""


def daftar() -> list[dict]:
    return db.ambil_semua("SELECT * FROM tahapan ORDER BY urutan")


def peta_urutan() -> dict:
    return {t["kode"]: t["urutan"] for t in daftar()}


def nama_tahapan(kode: str) -> str:
    baris = db.ambil_satu("SELECT nama FROM tahapan WHERE kode = ?", (kode,))
    return baris["nama"] if baris else kode


def alur(berkas: dict) -> list[dict]:
    """Rangkaian tahapan yang berlaku untuk berkas ini, dengan penanda posisi.

    Dipakai stepper di halaman berkas. `posisi` bernilai 'lewat', 'kini',
    atau 'depan'.
    """
    urutan_kini = peta_urutan().get(berkas["tahapan_kode"], 0)
    hasil = []
    for t in daftar():
        if t["kode"] == TAHAPAN_AWAL and berkas["tahapan_kode"] != TAHAPAN_AWAL:
            continue
        t = dict(t)
        t["posisi"] = ("kini" if t["urutan"] == urutan_kini
                       else "lewat" if t["urutan"] < urutan_kini else "depan")
        hasil.append(t)
    return hasil


def berikutnya(kode: str) -> dict | None:
    """Tahapan sesudah `kode`. TAHAPAN_AWAL tidak pernah jadi tujuan maju."""
    urutan_kini = peta_urutan().get(kode)
    if urutan_kini is None:
        return None
    for t in daftar():
        if t["urutan"] > urutan_kini and t["kode"] != TAHAPAN_AWAL:
            return t
    return None


def sudah_dilewati(berkas: dict) -> list[dict]:
    """Tahapan yang boleh jadi tujuan aksi 'mundur' — hanya yang sudah lewat."""
    return [t for t in alur(berkas) if t["posisi"] == "lewat"]


def tujuan_akhir(berkas: dict, tahapan_kode: str, aksi: str) -> str:
    """Di tahapan mana berkas akan berada setelah pergerakan ini.

    Dipakai route untuk memeriksa ceklis terhadap tahapan tujuan yang benar,
    bukan terhadap tahapan yang sedang diselesaikan.
    """
    if aksi == "kendala":
        return berkas["tahapan_kode"]
    if aksi == "selesai":
        lanjut = berikutnya(tahapan_kode)
        return lanjut["kode"] if lanjut else tahapan_kode
    return tahapan_kode


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


def _catat(kon, berkas_id, tahapan_kode, aksi, tanggal, catatan, pengguna_id) -> None:
    """Tulis satu baris riwayat. Selalu dipanggil di dalam transaksi pindah()."""
    kon.execute(
        """INSERT INTO riwayat_tahapan
               (berkas_id, tahapan_kode, aksi, tanggal, catatan, oleh_pengguna_id)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (berkas_id, tahapan_kode, aksi, tanggal, catatan, pengguna_id),
    )


def pindah(berkas_id: int, tahapan_kode: str, aksi: str = "masuk",
           tanggal: str | None = None, catatan: str | None = None,
           pengguna_id: int | None = None, paksa: bool = False) -> dict:
    """Pindahkan berkas ke tahapan tertentu.

    Menolak lompatan mundur kecuali aksi='mundur' dengan catatan terisi.
    Aksi 'kendala' hanya mencatat, tidak menggeser posisi berkas.

    Aksi 'selesai' menutup `tahapan_kode` lalu langsung memasukkan berkas ke
    tahapan berikutnya — dua baris riwayat dalam satu transaksi, supaya lama
    pengerjaan tiap tahapan bisa dihitung. Kalau tidak ada tahapan berikutnya,
    berkas yang ditutup.
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

        _catat(kon, berkas_id, tahapan_kode, aksi, tanggal, catatan, pengguna_id)

        posisi = tahapan_kode
        if aksi != "kendala":
            status = berkas["status"]
            tanggal_selesai = berkas["tanggal_selesai"]
            if aksi == "selesai":
                lanjut = berikutnya(tahapan_kode)
                if lanjut:
                    # Tahapan ditutup, berkas langsung masuk tahapan berikutnya.
                    _catat(kon, berkas_id, lanjut["kode"], "masuk", tanggal,
                           None, pengguna_id)
                    posisi = lanjut["kode"]
                else:
                    status, tanggal_selesai = "selesai", tanggal
            kon.execute(
                """UPDATE berkas SET tahapan_kode = ?, status = ?, tanggal_selesai = ?,
                                     diubah_pada = ?
                    WHERE id = ?""",
                (posisi, status, tanggal_selesai, config.stempel_waktu(), berkas_id),
            )

        audit.catat(kon, pengguna_id, f"tahapan_{aksi}", "berkas", berkas_id,
                    {"tahapan_kode": berkas["tahapan_kode"]},
                    {"tahapan_kode": posisi, "diselesaikan": tahapan_kode,
                     "tanggal": tanggal, "catatan": catatan})
        kon.commit()
        return {"berkas_id": berkas_id, "tahapan_kode": posisi,
                "diselesaikan": tahapan_kode, "aksi": aksi, "tanggal": tanggal}
    except Exception:
        kon.rollback()
        raise
    finally:
        kon.close()
