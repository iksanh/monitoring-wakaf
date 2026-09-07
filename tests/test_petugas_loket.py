"""Peran petugas_loket, dan aturan bahwa hanya objek 'bisa' yang boleh didaftarkan.

Aturan pendaftarannya diuji di lapis service (services/berkas.buat()), bukan di
template — tombolnya disembunyikan cuma supaya tidak membingungkan.
"""
import sqlite3
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.bantu import BasisTes  # noqa: E402


class TesPeranLoket(BasisTes):
    """Peran barunya terdaftar di aplikasi maupun di CHECK constraint database."""

    def setUp(self):
        super().setUp()
        import auth
        from services import master, pemilahan

        self.auth = auth
        self.master = master
        self.pemilahan = pemilahan

    def test_peran_tersedia(self):
        self.assertIn("petugas_loket", self.auth.PERAN_TERSEDIA)
        self.assertEqual(self.auth.LABEL_PERAN["petugas_loket"], "Petugas Loket")

    def test_loket_tidak_dibatasi_wilayah(self):
        """Satu loket melayani seluruh kabupaten, bukan satu wilayah tim."""
        self.assertNotIn("petugas_loket", self.auth.PERAN_TERBATAS_WILAYAH)

    def test_loket_boleh_mendaftarkan(self):
        self.assertIn("petugas_loket", self.auth.PERAN_PENDAFTAR)

    def test_loket_tidak_boleh_memilah(self):
        loket = {"id": 1, "peran": "petugas_loket", "wilayah_id": None}
        self.assertFalse(self.pemilahan.boleh_memilah(loket))

    def test_database_menerima_peran_loket(self):
        pengguna_id = self.buat_pengguna("loket1", "petugas_loket")
        self.assertEqual(
            self.db.ambil_nilai("SELECT peran FROM pengguna WHERE id = ?", (pengguna_id,)),
            "petugas_loket")

    def test_database_menolak_peran_asing(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.jalankan(
                """INSERT INTO pengguna (username, nama, password_hash, peran)
                   VALUES ('ngawur', 'Ngawur', 'x', 'tukang_parkir')""")

    def test_tambah_pengguna_loket_tanpa_wilayah(self):
        """Wilayah hanya wajib untuk korwil & petugas, bukan loket."""
        galat = self.master.tambah_pengguna(
            {"username": "loket2", "nama": "Loket Dua", "peran": "petugas_loket",
             "sandi": "rahasia123", "wilayah_id": None},
            self.buat_pengguna("adm", "admin"))
        self.assertIsNone(galat)
        orang = self.db.ambil_satu("SELECT * FROM pengguna WHERE username = 'loket2'")
        self.assertEqual(orang["peran"], "petugas_loket")
        self.assertIsNone(orang["wilayah_id"])


class TesHanyaObjekBisaYangDidaftarkan(BasisTes):
    def setUp(self):
        super().setUp()
        from services import berkas, pemilahan

        self.svc = berkas
        self.pemilahan = pemilahan
        self.pengguna_id = self.buat_pengguna()
        self.admin = {"id": self.buat_pengguna("adm", "admin"),
                      "peran": "admin", "wilayah_id": None}

    def daftarkan(self, objek_id):
        return self.svc.buat({"objek_wakaf_id": objek_id,
                              "jenis_permohonan_kode": "pertama_kali",
                              "no_berkas": "12345/2026",
                              "tanggal_daftar": "2026-09-01"}, self.pengguna_id)

    def test_objek_bisa_boleh_didaftarkan(self):
        objek = self.buat_objek("Masjid Bisa", "Suwawa", tindak_lanjut="bisa")
        berkas_id = self.daftarkan(objek)
        self.assertEqual(self.svc.ambil(berkas_id)["objek_wakaf_id"], objek)

    def test_objek_belum_dipilah_ditolak(self):
        objek = self.buat_objek("Masjid Belum", "Suwawa", tindak_lanjut="belum_dipilah")
        with self.assertRaises(self.svc.ObjekBelumBisaDidaftarkan) as galat:
            self.daftarkan(objek)
        self.assertIn("belum dipilah", str(galat.exception))
        self.assertEqual(
            self.db.ambil_nilai("SELECT COUNT(*) FROM berkas WHERE objek_wakaf_id = ?",
                                (objek,)), 0)

    def test_objek_tidak_bisa_ditolak_dengan_alasannya(self):
        objek = self.buat_objek("Masjid Sengketa", "Suwawa",
                                tindak_lanjut="belum_dipilah")
        self.pemilahan.pilah([objek], "tidak_bisa", self.admin, "Tanah sengketa")
        with self.assertRaises(self.svc.ObjekBelumBisaDidaftarkan) as galat:
            self.daftarkan(objek)
        self.assertIn("Tanah sengketa", str(galat.exception))

    def test_ceklis_tidak_ikut_terbuat_saat_ditolak(self):
        """Penolakan terjadi sebelum apa pun ditulis — transaksinya utuh."""
        objek = self.buat_objek("Masjid Belum", "Suwawa", tindak_lanjut="belum_dipilah")
        with self.assertRaises(self.svc.ObjekBelumBisaDidaftarkan):
            self.daftarkan(objek)
        self.assertEqual(self.db.ambil_nilai("SELECT COUNT(*) FROM ceklis_berkas"), 0)
        self.assertEqual(self.db.ambil_nilai("SELECT COUNT(*) FROM riwayat_tahapan"), 0)

    def test_objek_dipilah_ulang_jadi_boleh(self):
        objek = self.buat_objek("Masjid Berubah", "Suwawa",
                                tindak_lanjut="belum_dipilah")
        with self.assertRaises(self.svc.ObjekBelumBisaDidaftarkan):
            self.daftarkan(objek)
        self.pemilahan.pilah([objek], "bisa", self.admin)
        self.assertTrue(self.daftarkan(objek))

    # ---- helper pesan yang dipakai route & template ----
    def test_alasan_belum_bisa_kosong_kalau_boleh(self):
        objek = self.buat_objek("Masjid Bisa", "Suwawa", tindak_lanjut="bisa")
        baris = self.db.ambil_satu("SELECT * FROM objek_wakaf WHERE id = ?", (objek,))
        self.assertIsNone(self.svc.alasan_belum_bisa(baris))

    def test_alasan_belum_bisa_menjelaskan_keadaannya(self):
        objek = self.buat_objek("Masjid Belum", "Suwawa", tindak_lanjut="belum_dipilah")
        baris = self.db.ambil_satu("SELECT * FROM objek_wakaf WHERE id = ?", (objek,))
        self.assertIn("belum dipilah", self.svc.alasan_belum_bisa(baris))


if __name__ == "__main__":
    unittest.main()
