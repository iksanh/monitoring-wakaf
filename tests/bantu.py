"""Perkakas tes: database sementara berisi master + fixture kecil."""
import os
import tempfile
import unittest
from pathlib import Path

AKAR = Path(__file__).resolve().parent.parent


class BasisTes(unittest.TestCase):
    """Setiap tes dapat database SQLite baru yang sudah dimigrasi."""

    @classmethod
    def setUpClass(cls):
        cls._dir = tempfile.TemporaryDirectory()
        os.environ["DB_PATH"] = str(Path(cls._dir.name) / "uji.db")
        os.environ["UPLOAD_DIR"] = str(Path(cls._dir.name) / "unggah")
        import config
        import db
        config.DB_PATH = os.environ["DB_PATH"]
        config.UPLOAD_DIR = Path(os.environ["UPLOAD_DIR"])
        cls.db = db
        db.siapkan()

    @classmethod
    def tearDownClass(cls):
        cls._dir.cleanup()

    def setUp(self):
        # Kosongkan tabel transaksional supaya tes tidak saling mempengaruhi.
        with self.db.buka() as kon:
            # tim.pengguna_id menunjuk ke pengguna — lepas dulu sebelum dihapus.
            kon.execute("UPDATE tim SET pengguna_id = NULL")
            for tabel in ("riwayat_tahapan", "ceklis_berkas", "dokumen", "kunjungan",
                          "log_audit", "berkas", "objek_wakaf", "pengguna"):
                kon.execute(f"DELETE FROM {tabel}")
            # Kembalikan master ke keadaan seed — ada tes yang mengubah SLA.
            kon.execute("UPDATE tahapan SET sla_hari = NULL")

    # ---- fixture ----
    def buat_pengguna(self, username="uji", peran="sekretariat", wilayah_id=None) -> int:
        import auth
        return self.db.jalankan(
            """INSERT INTO pengguna (username, nama, password_hash, peran, wilayah_id)
               VALUES (?, ?, ?, ?, ?)""",
            (username, username.title(), auth.buat_hash("rahasia123"), peran, wilayah_id),
        )

    def buat_objek(self, nama="Masjid Uji", kecamatan="Suwawa", tipologi=None,
                   tipe_hak=None, rekomendasi_isbat=None, status="belum",
                   perlu_isbat=0) -> int:
        kec = self.db.ambil_satu("SELECT id FROM kecamatan WHERE nama = ?", (kecamatan,))
        urut = self.db.ambil_nilai("SELECT COUNT(*) FROM objek_wakaf", (), 0) + 1
        return self.db.jalankan(
            """INSERT INTO objek_wakaf (kode, nama_objek, kecamatan_id, tipologi_kode,
                                        tipe_hak, rekomendasi_isbat, status_sertipikat,
                                        is_potensi, sumber_data, perlu_isbat)
               VALUES (?, ?, ?, ?, ?, ?, ?, 1, 'uji', ?)""",
            (f"WKF-UJI-{urut:03d}", nama, kec["id"], tipologi, tipe_hak,
             rekomendasi_isbat, status, perlu_isbat),
        )

    def buat_berkas(self, objek_id, jenis="pertama_kali", tahapan="permohonan",
                    tanggal="2026-08-01", no_berkas=None) -> int:
        berkas_id = self.db.jalankan(
            """INSERT INTO berkas (no_berkas, objek_wakaf_id, jenis_permohonan_kode,
                                   tahapan_kode, status, tanggal_daftar)
               VALUES (?, ?, ?, ?, 'aktif', ?)""",
            (no_berkas, objek_id, jenis, tahapan, tanggal),
        )
        self.db.jalankan(
            """INSERT INTO riwayat_tahapan (berkas_id, tahapan_kode, aksi, tanggal)
               VALUES (?, ?, 'masuk', ?)""",
            (berkas_id, tahapan, tanggal),
        )
        return berkas_id
