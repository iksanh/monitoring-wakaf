"""Tes pemilahan objek: bisa / tidak bisa ditindaklanjuti, dan efeknya ke rekap."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.bantu import BasisTes  # noqa: E402


class TesPemilahan(BasisTes):
    def setUp(self):
        super().setUp()
        from services import pemilahan

        self.svc = pemilahan
        self.wil1 = self.db.ambil_nilai("SELECT id FROM wilayah WHERE nama = 'Wilayah I'")
        self.admin = {"id": self.buat_pengguna("adm", "admin"),
                      "peran": "admin", "wilayah_id": None}
        self.korwil1 = {"id": self.buat_pengguna("kor1", "korwil", self.wil1),
                        "peran": "korwil", "wilayah_id": self.wil1}

        # Suwawa = Wilayah I, Kabila = Wilayah III.
        self.o1 = self.buat_objek("Masjid A", "Suwawa", tindak_lanjut="belum_dipilah")
        self.o2 = self.buat_objek("Masjid B", "Suwawa", tindak_lanjut="belum_dipilah")
        self.o3 = self.buat_objek("Masjid C", "Kabila", tindak_lanjut="belum_dipilah")

    def status(self, objek_id) -> str:
        return self.db.ambil_nilai(
            "SELECT status_tindak_lanjut FROM objek_wakaf WHERE id = ?", (objek_id,))

    # ---- bawaan ----
    def test_objek_baru_belum_dipilah(self):
        """Kolom bawaannya 'belum_dipilah' — bukan langsung dihitung potensi."""
        objek_id = self.db.jalankan(
            """INSERT INTO objek_wakaf (kode, nama_objek, kecamatan_id)
               VALUES ('WKF-BAW-001', 'Masjid Bawaan',
                       (SELECT id FROM kecamatan WHERE nama = 'Suwawa'))""")
        self.assertEqual(self.status(objek_id), "belum_dipilah")

    # ---- menandai ----
    def test_tandai_bisa_massal(self):
        hasil = self.svc.pilah([self.o1, self.o2], "bisa", self.admin)
        self.assertEqual(hasil["diubah"], 2)
        self.assertEqual(self.status(self.o1), "bisa")
        self.assertEqual(self.status(self.o2), "bisa")

    def test_tandai_tidak_bisa_menyimpan_alasan(self):
        self.svc.pilah([self.o1], "tidak_bisa", self.admin, "Tanah sengketa")
        baris = self.db.ambil_satu(
            "SELECT status_tindak_lanjut, alasan_tidak_bisa, dipilah_oleh, dipilah_pada "
            "FROM objek_wakaf WHERE id = ?", (self.o1,))
        self.assertEqual(baris["status_tindak_lanjut"], "tidak_bisa")
        self.assertEqual(baris["alasan_tidak_bisa"], "Tanah sengketa")
        self.assertEqual(baris["dipilah_oleh"], self.admin["id"])
        self.assertTrue(baris["dipilah_pada"])

    def test_tidak_bisa_wajib_beralasan(self):
        with self.assertRaises(self.svc.GalatPemilahan):
            self.svc.pilah([self.o1], "tidak_bisa", self.admin)
        with self.assertRaises(self.svc.GalatPemilahan):
            self.svc.pilah([self.o1], "tidak_bisa", self.admin, "   ")
        self.assertEqual(self.status(self.o1), "belum_dipilah")

    def test_kembali_ke_bisa_menghapus_alasan(self):
        self.svc.pilah([self.o1], "tidak_bisa", self.admin, "Tanah sengketa")
        self.svc.pilah([self.o1], "bisa", self.admin, "sisa ketikan")
        baris = self.db.ambil_satu(
            "SELECT status_tindak_lanjut, alasan_tidak_bisa FROM objek_wakaf WHERE id = ?",
            (self.o1,))
        self.assertEqual(baris["status_tindak_lanjut"], "bisa")
        self.assertIsNone(baris["alasan_tidak_bisa"])

    def test_id_kembar_hanya_dihitung_sekali(self):
        """Daftar objek mengirim id dua kali: kartu HP + baris tabel desktop."""
        hasil = self.svc.pilah([self.o1, self.o1], "bisa", self.admin)
        self.assertEqual(hasil["diubah"], 1)
        self.assertEqual(len(self.db.ambil_semua(
            "SELECT id FROM log_audit WHERE aksi = 'pilah' AND ref_id = ?",
            (self.o1,))), 1)

    def test_menandai_ulang_status_yang_sama_bukan_perubahan(self):
        self.svc.pilah([self.o1], "bisa", self.admin)
        hasil = self.svc.pilah([self.o1], "bisa", self.admin)
        self.assertEqual(hasil["diubah"], 0)
        self.assertEqual(hasil["tetap"], 1)

    def test_status_asing_ditolak(self):
        with self.assertRaises(self.svc.GalatPemilahan):
            self.svc.pilah([self.o1], "mungkin", self.admin)

    def test_tanpa_objek_ditolak(self):
        with self.assertRaises(self.svc.GalatPemilahan):
            self.svc.pilah([], "bisa", self.admin)

    def test_menulis_log_audit(self):
        self.svc.pilah([self.o1], "bisa", self.admin)
        baris = self.db.ambil_satu(
            "SELECT * FROM log_audit WHERE tabel = 'objek_wakaf' AND ref_id = ?",
            (self.o1,))
        self.assertEqual(baris["aksi"], "pilah")
        self.assertEqual(baris["pengguna_id"], self.admin["id"])
        self.assertIn("belum_dipilah", baris["data_lama"])
        self.assertIn("bisa", baris["data_baru"])

    # ---- peran & wilayah ----
    def test_petugas_tidak_boleh_memilah(self):
        petugas = {"id": self.buat_pengguna("ptg", "petugas", self.wil1),
                   "peran": "petugas", "wilayah_id": self.wil1}
        self.assertFalse(self.svc.boleh_memilah(petugas))
        with self.assertRaises(self.svc.GalatPemilahan):
            self.svc.pilah([self.o1], "bisa", petugas)
        self.assertEqual(self.status(self.o1), "belum_dipilah")

    def test_korwil_hanya_wilayahnya(self):
        """Batas wilayah ditegakkan di service, bukan sekadar disembunyikan di UI."""
        hasil = self.svc.pilah([self.o1, self.o3], "bisa", self.korwil1)
        self.assertEqual(hasil["diubah"], 1)
        self.assertEqual(hasil["dilewati"], 1)
        self.assertEqual(self.status(self.o1), "bisa")
        self.assertEqual(self.status(self.o3), "belum_dipilah")   # Wilayah III

    def test_objek_nonaktif_tidak_ikut_dipilah(self):
        self.db.jalankan("UPDATE objek_wakaf SET is_aktif = 0 WHERE id = ?", (self.o1,))
        hasil = self.svc.pilah([self.o1], "bisa", self.admin)
        self.assertEqual(hasil["diubah"], 0)

    # ---- ringkasan ----
    def test_ringkasan_per_status(self):
        self.svc.pilah([self.o1], "bisa", self.admin)
        self.svc.pilah([self.o2], "tidak_bisa", self.admin, "Sudah jadi jalan")
        ringkas = self.svc.ringkasan()
        self.assertEqual(ringkas["bisa"], 1)
        self.assertEqual(ringkas["tidak_bisa"], 1)
        self.assertEqual(ringkas["belum_dipilah"], 1)
        self.assertEqual(ringkas["total"], 3)

    def test_ringkasan_korwil_hanya_wilayahnya(self):
        self.assertEqual(self.svc.ringkasan(self.korwil1)["total"], 2)


class TesPemilahanKeRekap(BasisTes):
    """Angka potensi di rekap harus ikut hasil pemilahan, bukan seluruh objek."""

    def setUp(self):
        super().setUp()
        from services import pemilahan, rekap

        self.svc = pemilahan
        self.rekap = rekap
        self.admin = {"id": self.buat_pengguna("adm", "admin"),
                      "peran": "admin", "wilayah_id": None}
        self.o1 = self.buat_objek("Masjid A", "Suwawa", tindak_lanjut="belum_dipilah")
        self.o2 = self.buat_objek("Masjid B", "Suwawa", tindak_lanjut="belum_dipilah")
        self.o3 = self.buat_objek("Masjid C", "Suwawa", tindak_lanjut="belum_dipilah")

    def test_belum_dipilah_bukan_potensi(self):
        """Inti perbaikannya: tiga objek ada, tapi potensinya masih nol."""
        ringkas = self.rekap.ringkasan_dashboard()["objek"]
        self.assertEqual(ringkas["total"], 3)
        self.assertEqual(ringkas["potensi"], 0)
        self.assertEqual(ringkas["belum_dipilah"], 3)

    def test_dashboard_mengikuti_pemilahan(self):
        self.svc.pilah([self.o1, self.o2], "bisa", self.admin)
        self.svc.pilah([self.o3], "tidak_bisa", self.admin, "Beralih fungsi")
        ringkas = self.rekap.ringkasan_dashboard()["objek"]
        self.assertEqual(ringkas["potensi"], 2)
        self.assertEqual(ringkas["tidak_bisa"], 1)
        self.assertEqual(ringkas["belum_dipilah"], 0)
        self.assertEqual(ringkas["total"], 3)

    def test_rekap_kecamatan_memisahkan_ketiganya(self):
        self.svc.pilah([self.o1], "bisa", self.admin)
        self.svc.pilah([self.o2], "tidak_bisa", self.admin, "Sengketa")
        baris = {b["kecamatan"]: b
                 for b in self.rekap.rekap_potensi_kecamatan()}["Suwawa"]
        self.assertEqual(baris["total"], 1)            # kolom potensi
        self.assertEqual(baris["tidak_bisa"], 1)
        self.assertEqual(baris["belum_dipilah"], 1)
        self.assertEqual(baris["objek"], 3)            # tidak ada yang hilang
        self.assertEqual(baris["baru"] + baris["ada_hak"] + baris["isbat"],
                         baris["total"])

    def test_rekap_wilayah_mengikuti_pemilahan(self):
        self.svc.pilah([self.o1], "bisa", self.admin)
        baris = {b["wilayah"]: b for b in self.rekap.rekap_wilayah()}["Wilayah I"]
        self.assertEqual(baris["potensi"], 1)
        self.assertEqual(baris["belum_dipilah"], 2)
        self.assertEqual(baris["objek"], 3)

    def test_papan_kendali_memisahkan_potensi_dan_belum_dipilah(self):
        from services import kendali

        self.svc.pilah([self.o1], "bisa", self.admin)
        papan = kendali.papan_kendali("2026-08")
        baris = {b["wilayah"]: b for b in papan["baris"]}["Wilayah I"]
        self.assertEqual(baris["potensi"], 1)
        self.assertEqual(baris["belum_dipilah"], 2)
        # Potensi tetap di luar Total Capaian.
        self.assertEqual(baris["total_capaian"], 0)


if __name__ == "__main__":
    unittest.main()
