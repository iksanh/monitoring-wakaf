"""Aksi administratif pada berkas yang bukan pergerakan tahapan.

Dipisah dari services/berkas.py supaya kedua modul tetap pendek. Tidak satu pun
fungsi di sini menyentuh berkas.tahapan_kode — itu hanya boleh lewat
services/tahapan.pindah().
"""
import config
import db
from services import audit


def tandai_tarikan(berkas_id: int, ditarik: bool, tanggal: str | None,
                   pengguna_id: int) -> None:
    """Catat bahwa sertipikat/warkah berkas ini sudah (atau belum) ditarik.

    Dipakai kolom "Catatan yang sudah ditarik" di papan kendali korwil.
    Tidak menyentuh tahapan_kode — ini catatan administratif, bukan pergerakan.
    """
    tanggal = ((tanggal or "").strip() or config.hari_ini_iso()) if ditarik else None
    kon = db.koneksi()
    try:
        kon.execute("BEGIN")
        lama = kon.execute(
            "SELECT catatan_ditarik, tanggal_ditarik FROM berkas WHERE id = ?",
            (berkas_id,)).fetchone()
        if not lama:
            raise ValueError("Berkas tidak ditemukan.")
        kon.execute(
            """UPDATE berkas SET catatan_ditarik = ?, tanggal_ditarik = ?,
                                 diubah_pada = ?
                WHERE id = ?""",
            (1 if ditarik else 0, tanggal, config.stempel_waktu(), berkas_id),
        )
        audit.catat(kon, pengguna_id, "tarikan", "berkas", berkas_id, dict(lama),
                    {"catatan_ditarik": 1 if ditarik else 0, "tanggal_ditarik": tanggal})
        kon.commit()
    except Exception:
        kon.rollback()
        raise
    finally:
        kon.close()


class BatalDitolak(Exception):
    """Pembatalan tidak memenuhi syarat."""


def batalkan(berkas_id: int, alasan: str | None, pengguna_id: int,
             tanggal: str | None = None) -> None:
    """Batalkan pendaftaran berkas: status jadi 'batal'.

    Berkas lalu hilang dari daftar /berkas dan objeknya kembali bebas dibuatkan
    berkas baru — idx_berkas_satu_per_objek mengecualikan status 'batal'.
    Riwayat tahapan dan ceklis tidak dihapus, hanya tidak lagi ditampilkan.
    """
    alasan = (alasan or "").strip()
    if not alasan:
        raise BatalDitolak("Pembatalan wajib disertai alasan tertulis.")
    tanggal = (tanggal or "").strip() or config.hari_ini_iso()

    kon = db.koneksi()
    try:
        kon.execute("BEGIN")
        lama = kon.execute("SELECT status FROM berkas WHERE id = ?",
                           (berkas_id,)).fetchone()
        if not lama:
            raise BatalDitolak("Berkas tidak ditemukan.")
        if lama["status"] == "batal":
            raise BatalDitolak("Berkas ini sudah dibatalkan.")
        kon.execute(
            """UPDATE berkas SET status = 'batal', alasan_batal = ?,
                                 tanggal_batal = ?, diubah_pada = ?
                WHERE id = ?""",
            (alasan, tanggal, config.stempel_waktu(), berkas_id),
        )
        audit.catat(kon, pengguna_id, "batalkan", "berkas", berkas_id,
                    {"status": lama["status"]},
                    {"status": "batal", "alasan_batal": alasan,
                     "tanggal_batal": tanggal})
        kon.commit()
    except Exception:
        kon.rollback()
        raise
    finally:
        kon.close()


def simpan_penetapan(berkas_id: int, no_penetapan: str | None,
                     tanggal_penetapan: str | None, pengguna_id: int) -> None:
    """Catat penetapan isbat dari Pengadilan Agama.

    Selama tanggal_penetapan masih kosong, perkaranya dianggap masih di
    pengadilan — itu yang dihitung kolom "Penetapan Pengadilan" di papan kendali.
    Tidak menyentuh tahapan_kode; ini catatan administratif, bukan pergerakan.
    """
    no_penetapan = (no_penetapan or "").strip() or None
    tanggal_penetapan = (tanggal_penetapan or "").strip() or None
    kon = db.koneksi()
    try:
        kon.execute("BEGIN")
        lama = kon.execute(
            "SELECT no_penetapan, tanggal_penetapan FROM berkas WHERE id = ?",
            (berkas_id,)).fetchone()
        if not lama:
            raise ValueError("Berkas tidak ditemukan.")
        kon.execute(
            """UPDATE berkas SET no_penetapan = ?, tanggal_penetapan = ?,
                                 diubah_pada = ?
                WHERE id = ?""",
            (no_penetapan, tanggal_penetapan, config.stempel_waktu(), berkas_id),
        )
        audit.catat(kon, pengguna_id, "penetapan_isbat", "berkas", berkas_id,
                    dict(lama), {"no_penetapan": no_penetapan,
                                 "tanggal_penetapan": tanggal_penetapan})
        kon.commit()
    except Exception:
        kon.rollback()
        raise
    finally:
        kon.close()
