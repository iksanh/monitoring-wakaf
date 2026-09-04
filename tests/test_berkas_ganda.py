"""Satu objek wakaf hanya boleh punya satu berkas permohonan.

Diuji di dua lapis: aturan di services/berkas.buat() dan indeks unik parsial
idx_berkas_satu_per_objek (migrasi 006) yang menjaga kalau ada jalur lain.
"""
import sqlite3
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.bantu import BasisTes  # noqa: E402


class TesBerkasGanda(BasisTes):
    def setUp(self):
        super().setUp()
        from services import berkas
        self.svc = berkas
        self.pengguna_id = self.buat_pengguna()
        self.objek = self.buat_objek("Masjid Al-Fajar", "Suwawa Tengah")

    def buat_lewat_service(self, objek_id=None, jenis="pertama_kali",
                           tanggal="2026-09-01"):
        return self.svc.buat({"objek_wakaf_id": objek_id or self.objek,
                              "jenis_permohonan_kode": jenis,
                              "no_berkas": "12345/2026",
                              "tanggal_daftar": tanggal}, self.pengguna_id)

    # ---- lapis service ----
    def test_berkas_pertama_tetap_boleh(self):
        berkas_id = self.buat_lewat_service()
        self.assertEqual(self.svc.ambil(berkas_id)["objek_wakaf_id"], self.objek)

    def test_berkas_kedua_ditolak(self):
        self.buat_lewat_service()
        with self.assertRaises(self.svc.BerkasGanda):
            self.buat_lewat_service()

    def test_berkas_kedua_ditolak_walau_jenis_berbeda(self):
        self.buat_lewat_service(jenis="pertama_kali")
        with self.assertRaises(self.svc.BerkasGanda):
            self.buat_lewat_service(jenis="alih_media")

    def test_penolakan_tidak_meninggalkan_sisa(self):
        self.buat_lewat_service()
        with self.assertRaises(self.svc.BerkasGanda):
            self.buat_lewat_service()
        self.assertEqual(
            self.db.ambil_nilai("SELECT COUNT(*) FROM berkas WHERE objek_wakaf_id = ?",
                                (self.objek,)), 1)
        self.assertEqual(
            self.db.ambil_nilai("SELECT COUNT(*) FROM riwayat_tahapan"), 1)
        self.assertEqual(
            self.db.ambil_nilai("SELECT COUNT(*) FROM ceklis_berkas"), 6)

    def test_pesan_galat_menyebut_berkas_yang_sudah_ada(self):
        self.buat_lewat_service()
        with self.assertRaises(self.svc.BerkasGanda) as ditangkap:
            self.buat_lewat_service()
        pesan = str(ditangkap.exception)
        self.assertIn("12345/2026", pesan)
        self.assertIn("sudah punya berkas", pesan)

    def test_objek_lain_tidak_terhalang(self):
        self.buat_lewat_service()
        lain = self.buat_objek("Masjid Lain", "Suwawa Tengah")
        self.assertTrue(self.buat_lewat_service(objek_id=lain))

    # ---- berkas batal ----
    def test_berkas_batal_tidak_menghalangi(self):
        pertama = self.buat_lewat_service()
        self.db.jalankan("UPDATE berkas SET status = 'batal' WHERE id = ?", (pertama,))
        kedua = self.buat_lewat_service()
        self.assertNotEqual(pertama, kedua)

    def test_berkas_selesai_tetap_menghalangi(self):
        pertama = self.buat_lewat_service()
        self.db.jalankan(
            "UPDATE berkas SET status = 'selesai', tanggal_selesai = ? WHERE id = ?",
            ("2026-09-20", pertama))
        with self.assertRaises(self.svc.BerkasGanda):
            self.buat_lewat_service()

    # ---- pemeriksa yang dipakai route & template ----
    def test_berkas_penghalang_kosong_saat_belum_ada_berkas(self):
        self.assertIsNone(self.svc.berkas_penghalang(self.objek))

    def test_berkas_penghalang_menunjuk_berkas_yang_ada(self):
        berkas_id = self.buat_lewat_service()
        ada = self.svc.berkas_penghalang(self.objek)
        self.assertEqual(ada["id"], berkas_id)
        self.assertEqual(ada["jenis_nama"], "Pendaftaran Pertama Kali")
        self.assertEqual(ada["tahapan_nama"], "Permohonan (Sudah Daftar Loket)")

    def test_berkas_penghalang_abaikan_yang_batal(self):
        pertama = self.buat_lewat_service()
        self.db.jalankan("UPDATE berkas SET status = 'batal' WHERE id = ?", (pertama,))
        self.assertIsNone(self.svc.berkas_penghalang(self.objek))

    # ---- lapis database ----
    def test_indeks_unik_menolak_insert_langsung(self):
        self.buat_lewat_service()
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.jalankan(
                """INSERT INTO berkas (objek_wakaf_id, jenis_permohonan_kode,
                                       tahapan_kode, status)
                   VALUES (?, 'pertama_kali', 'permohonan', 'aktif')""",
                (self.objek,))

    def test_indeks_unik_mengizinkan_beberapa_berkas_batal(self):
        pertama = self.buat_lewat_service()
        self.db.jalankan("UPDATE berkas SET status = 'batal' WHERE id = ?", (pertama,))
        self.db.jalankan(
            """INSERT INTO berkas (objek_wakaf_id, jenis_permohonan_kode,
                                   tahapan_kode, status)
               VALUES (?, 'pertama_kali', 'permohonan', 'batal')""",
            (self.objek,))
        self.assertEqual(
            self.db.ambil_nilai("SELECT COUNT(*) FROM berkas WHERE objek_wakaf_id = ?",
                                (self.objek,)), 2)


if __name__ == "__main__":
    unittest.main()
