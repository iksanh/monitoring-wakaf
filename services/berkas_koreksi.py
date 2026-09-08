"""Koreksi berkas yang jenis permohonan atau tahapannya salah tercatat.

Dipisah dari services/berkas.py karena dua perubahan ini bukan sekadar UPDATE
kolom seperti berkas.ubah():

  * ganti jenis   — ceklis syarat harus disusun ulang mengikuti jenis baru,
                    kalau tidak berkasnya membawa ceklis jenis lama selamanya.
  * ganti tahapan — wajib lewat services/tahapan.pindah() (aturan domain #1),
                    supaya riwayat_tahapan tetap jadi satu-satunya sumber
                    kebenaran pergerakan yang dipakai semua rekap.

Keduanya wajib beralasan dan tercatat di log_audit, sama seperti pembatalan.
Yang boleh memakainya: auth.PERAN_KOREKSI_BERKAS.
"""
import config
import db
from services import audit, ceklis, tahapan as svc_tahapan


class KoreksiDitolak(Exception):
    """Koreksi tidak memenuhi syarat."""


def _berkas_bisa_dikoreksi(kon, berkas_id: int):
    baris = kon.execute("SELECT * FROM berkas WHERE id = ?", (berkas_id,)).fetchone()
    if not baris:
        raise KoreksiDitolak("Berkas tidak ditemukan.")
    if baris["status"] == "batal":
        raise KoreksiDitolak(
            "Berkas ini sudah dibatalkan. Daftarkan ulang objeknya kalau "
            "permohonannya mau dijalankan lagi.")
    return baris


def ganti_jenis(berkas_id: int, jenis_kode: str, alasan: str | None,
                pengguna_id: int) -> dict:
    """Ganti jenis permohonan berkas dan susun ulang ceklis syaratnya.

    Centang dan catatan syarat yang teksnya sama persis dibawa pindah — lihat
    services/ceklis.selaraskan_syarat(). Syarat khas jenis lama hilang dari
    ceklis; keadaan lamanya disimpan utuh di log_audit.
    """
    alasan = (alasan or "").strip()
    if not alasan:
        raise KoreksiDitolak("Penggantian jenis permohonan wajib disertai alasan.")

    kon = db.koneksi()
    try:
        kon.execute("BEGIN")
        berkas = _berkas_bisa_dikoreksi(kon, berkas_id)
        jenis = kon.execute("SELECT * FROM jenis_permohonan WHERE kode = ?",
                            (jenis_kode,)).fetchone()
        if not jenis:
            raise KoreksiDitolak(f"Jenis permohonan '{jenis_kode}' tidak ada.")
        if jenis_kode == berkas["jenis_permohonan_kode"]:
            raise KoreksiDitolak("Jenis permohonannya sudah itu — tidak ada yang diubah.")

        ceklis_lama = ceklis.rekam_keadaan(kon, berkas_id)
        kon.execute(
            "UPDATE berkas SET jenis_permohonan_kode = ?, diubah_pada = ? WHERE id = ?",
            (jenis_kode, config.stempel_waktu(), berkas_id),
        )
        ringkas = ceklis.selaraskan_syarat(kon, berkas_id, jenis_kode)
        audit.catat(kon, pengguna_id, "ganti_jenis", "berkas", berkas_id,
                    {"jenis_permohonan_kode": berkas["jenis_permohonan_kode"],
                     "ceklis": ceklis_lama},
                    {"jenis_permohonan_kode": jenis_kode, "alasan": alasan,
                     "ceklis": ringkas})
        kon.commit()
        return ringkas
    except Exception:
        kon.rollback()
        raise
    finally:
        kon.close()


def perbaiki_tahapan(berkas_id: int, tahapan_kode: str, alasan: str | None,
                     pengguna_id: int, tanggal: str | None = None) -> dict:
    """Pindahkan berkas ke tahapan yang seharusnya, sebagai koreksi pencatatan.

    Penulisannya tetap lewat services/tahapan.pindah(): aksi 'masuk' kalau maju,
    'mundur' kalau mundur. Jadi koreksi ini juga meninggalkan jejak di
    riwayat_tahapan, bukan diam-diam mengubah kolom.
    """
    alasan = (alasan or "").strip()
    if not alasan:
        raise KoreksiDitolak("Koreksi tahapan wajib disertai alasan.")

    with db.buka() as kon:
        berkas = _berkas_bisa_dikoreksi(kon, berkas_id)
        tujuan = kon.execute("SELECT * FROM tahapan WHERE kode = ?",
                             (tahapan_kode,)).fetchone()
        if not tujuan:
            raise KoreksiDitolak(f"Tahapan '{tahapan_kode}' tidak ada.")
        kini = kon.execute("SELECT * FROM tahapan WHERE kode = ?",
                           (berkas["tahapan_kode"],)).fetchone()
        if tahapan_kode == berkas["tahapan_kode"]:
            raise KoreksiDitolak("Berkas sudah ada di tahapan itu — tidak ada yang diubah.")
        mundur = tujuan["urutan"] < kini["urutan"]
        status_lama, selesai_lama = berkas["status"], berkas["tanggal_selesai"]

    hasil = svc_tahapan.pindah(
        berkas_id, tahapan_kode, aksi="mundur" if mundur else "masuk",
        tanggal=tanggal or config.hari_ini_iso(),
        catatan=f"Koreksi tahapan: {alasan}", pengguna_id=pengguna_id)

    # Berkas yang terlanjur ditutup harus terbuka lagi kalau tahapannya ditarik
    # mundur — kalau tidak, rekap menghitungnya selesai padahal masih berjalan.
    # Ini menyentuh status, bukan tahapan_kode, jadi tidak melanggar aturan #1.
    if mundur and status_lama == "selesai":
        with db.buka() as kon:
            kon.execute(
                """UPDATE berkas SET status = 'aktif', tanggal_selesai = NULL,
                                     diubah_pada = ? WHERE id = ?""",
                (config.stempel_waktu(), berkas_id))
            audit.catat(kon, pengguna_id, "koreksi_tahapan_buka", "berkas", berkas_id,
                        {"status": status_lama, "tanggal_selesai": selesai_lama},
                        {"status": "aktif", "tanggal_selesai": None})
        hasil["status"] = "aktif"
    return hasil
