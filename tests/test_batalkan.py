"""Batalkan pendaftaran: berkas keluar dari daftar, objeknya bebas lagi."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.bantu import BasisTes  # noqa: E402


class TesBatalkan(BasisTes):
    def setUp(self):
        super().setUp()
        from services import berkas as svc_berkas, berkas_aksi as svc_aksi
        self.svc = svc_berkas
        self.aksi = svc_aksi
        self.pengguna_id = self.buat_pengguna()
        self.admin = {"peran": "admin", "wilayah_id": None}

        self.objek = self.buat_objek("Masjid Uji Batal", "Suwawa")
        self.berkas = self.buat_berkas(self.objek, no_berkas="99/2026")
        self.lain = self.buat_berkas(self.buat_objek("Masjid Lain", "Suwawa"))

    def batalkan(self, alasan="Salah input, objeknya bukan yang ini."):
        self.aksi.batalkan(self.berkas, alasan, self.pengguna_id, "2026-09-03")

    # ---- aturan pembatalan ----
    def test_status_jadi_batal(self):
        self.batalkan()
        b = self.svc.ambil(self.berkas)
        self.assertEqual(b["status"], "batal")
        self.assertEqual(b["tanggal_batal"], "2026-09-03")
        self.assertIn("Salah input", b["alasan_batal"])

    def test_alasan_wajib_diisi(self):
        for kosong in (None, "", "   "):
            with self.assertRaises(self.aksi.BatalDitolak):
                self.aksi.batalkan(self.berkas, kosong, self.pengguna_id)
        self.assertEqual(self.svc.ambil(self.berkas)["status"], "aktif")

    def test_tidak_bisa_dibatalkan_dua_kali(self):
        self.batalkan()
        with self.assertRaises(self.aksi.BatalDitolak):
            self.batalkan()

    def test_berkas_tak_dikenal_ditolak(self):
        with self.assertRaises(self.aksi.BatalDitolak):
            self.aksi.batalkan(9999, "apa saja", self.pengguna_id)

    def test_tanggal_bawaan_hari_ini(self):
        import config
        self.aksi.batalkan(self.berkas, "tanpa tanggal", self.pengguna_id)
        self.assertEqual(self.svc.ambil(self.berkas)["tanggal_batal"],
                         config.hari_ini_iso())

    def test_menulis_log_audit(self):
        self.batalkan()
        self.assertEqual(self.db.ambil_nilai(
            "SELECT COUNT(*) FROM log_audit WHERE aksi = 'batalkan' AND ref_id = ?",
            (self.berkas,), 0), 1)

    def test_tidak_menyentuh_tahapan(self):
        sebelum = self.svc.ambil(self.berkas)["tahapan_kode"]
        self.batalkan()
        self.assertEqual(self.svc.ambil(self.berkas)["tahapan_kode"], sebelum)

    def test_riwayat_dan_ceklis_tidak_dihapus(self):
        riwayat = self.db.ambil_nilai(
            "SELECT COUNT(*) FROM riwayat_tahapan WHERE berkas_id = ?",
            (self.berkas,), 0)
        self.batalkan()
        self.assertEqual(self.db.ambil_nilai(
            "SELECT COUNT(*) FROM riwayat_tahapan WHERE berkas_id = ?",
            (self.berkas,), 0), riwayat)

    # ---- daftar /berkas ----
    def test_hilang_dari_daftar_berkas(self):
        self.assertEqual(self.svc.cari(self.admin, {})["total"], 2)
        self.batalkan()
        hasil = self.svc.cari(self.admin, {})
        self.assertEqual(hasil["total"], 1)
        self.assertEqual([b["id"] for b in hasil["baris"]], [self.lain])

    def test_masih_bisa_dilihat_lewat_filter_status_batal(self):
        self.batalkan()
        hasil = self.svc.cari(self.admin, {"status": "batal"})
        self.assertEqual([b["id"] for b in hasil["baris"]], [self.berkas])

    def test_filter_status_lain_tidak_terpengaruh(self):
        self.batalkan()
        self.assertEqual(self.svc.cari(self.admin, {"status": "aktif"})["total"], 1)

    def test_masih_bisa_dibuka_langsung(self):
        """Halaman detailnya tetap ada, cuma tidak muncul di daftar."""
        self.batalkan()
        self.assertIsNotNone(self.svc.ambil(self.berkas))

    # ---- objek kembali bebas ----
    def test_objek_bisa_dibuatkan_berkas_baru(self):
        with self.assertRaises(self.svc.BerkasGanda):
            self.svc.buat({"objek_wakaf_id": self.objek,
                           "jenis_permohonan_kode": "pertama_kali"}, self.pengguna_id)
        self.batalkan()
        baru = self.svc.buat({"objek_wakaf_id": self.objek,
                              "jenis_permohonan_kode": "pertama_kali"},
                             self.pengguna_id)
        self.assertNotEqual(baru, self.berkas)

    def test_penghalang_hilang_setelah_dibatalkan(self):
        self.assertIsNotNone(self.svc.berkas_penghalang(self.objek))
        self.batalkan()
        self.assertIsNone(self.svc.berkas_penghalang(self.objek))

    def test_berkas_baru_tidak_menabrak_indeks_unik(self):
        self.batalkan()
        self.svc.buat({"objek_wakaf_id": self.objek,
                       "jenis_permohonan_kode": "pertama_kali"}, self.pengguna_id)
        self.assertEqual(self.db.ambil_nilai(
            "SELECT COUNT(*) FROM berkas WHERE objek_wakaf_id = ?", (self.objek,), 0), 2)

    # ---- rekap ----
    def test_tidak_lagi_dihitung_rekap(self):
        from services import kendali, rekap
        self.assertEqual(rekap.ringkasan_dashboard()["berkas_aktif"], 2)
        self.batalkan()
        self.assertEqual(rekap.ringkasan_dashboard()["berkas_aktif"], 1)
        self.assertEqual(rekap.rekap_tahapan()["total_aktif"], 1)
        self.assertEqual(len(rekap.berkas_macet(14)), 1)
        papan = kendali.papan_kendali("2026-08")
        self.assertEqual(papan["total"]["total_capaian"], 1)


if __name__ == "__main__":
    unittest.main()
