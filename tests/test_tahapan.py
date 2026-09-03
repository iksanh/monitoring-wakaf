"""Tes services/tahapan.pindah() — dua tabel dalam satu transaksi."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.bantu import BasisTes  # noqa: E402


class TesPindah(BasisTes):
    def setUp(self):
        super().setUp()
        from services import tahapan
        self.tahapan = tahapan
        self.pengguna_id = self.buat_pengguna()
        self.objek_id = self.buat_objek()
        self.berkas_id = self.buat_berkas(self.objek_id)

    def _berkas(self):
        return self.db.ambil_satu("SELECT * FROM berkas WHERE id = ?", (self.berkas_id,))

    def _riwayat(self):
        return self.db.ambil_semua(
            "SELECT * FROM riwayat_tahapan WHERE berkas_id = ? ORDER BY id",
            (self.berkas_id,))

    def test_menulis_dua_tabel_sekaligus(self):
        sebelum = len(self._riwayat())
        self.tahapan.pindah(self.berkas_id, "pengukuran", "masuk", "2026-09-05",
                            "mulai ukur", self.pengguna_id)
        self.assertEqual(self._berkas()["tahapan_kode"], "pengukuran")
        riwayat = self._riwayat()
        self.assertEqual(len(riwayat), sebelum + 1)
        self.assertEqual(riwayat[-1]["tahapan_kode"], "pengukuran")
        self.assertEqual(riwayat[-1]["tanggal"], "2026-09-05")
        self.assertEqual(riwayat[-1]["aksi"], "masuk")

    def test_rollback_kalau_gagal(self):
        """Tahapan tidak dikenal: tidak boleh ada baris riwayat yang tertinggal."""
        sebelum_riwayat = len(self._riwayat())
        sebelum_tahapan = self._berkas()["tahapan_kode"]
        with self.assertRaises(self.tahapan.PindahDitolak):
            self.tahapan.pindah(self.berkas_id, "tahapan_hantu", "masuk",
                                "2026-09-05", None, self.pengguna_id)
        self.assertEqual(len(self._riwayat()), sebelum_riwayat)
        self.assertEqual(self._berkas()["tahapan_kode"], sebelum_tahapan)

    def test_tolak_mundur_tanpa_aksi_mundur(self):
        self.tahapan.pindah(self.berkas_id, "yuridis", "masuk", "2026-09-06",
                            None, self.pengguna_id)
        with self.assertRaises(self.tahapan.PindahDitolak):
            self.tahapan.pindah(self.berkas_id, "pengukuran", "masuk", "2026-09-07",
                                None, self.pengguna_id)
        self.assertEqual(self._berkas()["tahapan_kode"], "yuridis")

    def test_mundur_wajib_beralasan(self):
        self.tahapan.pindah(self.berkas_id, "yuridis", "masuk", "2026-09-06",
                            None, self.pengguna_id)
        with self.assertRaises(self.tahapan.PindahDitolak):
            self.tahapan.pindah(self.berkas_id, "pengukuran", "mundur", "2026-09-07",
                                "   ", self.pengguna_id)
        self.tahapan.pindah(self.berkas_id, "pengukuran", "mundur", "2026-09-07",
                            "berkas kurang lengkap", self.pengguna_id)
        self.assertEqual(self._berkas()["tahapan_kode"], "pengukuran")

    def test_kendala_tidak_menggeser_posisi(self):
        self.tahapan.pindah(self.berkas_id, "pengukuran", "masuk", "2026-09-05",
                            None, self.pengguna_id)
        self.tahapan.pindah(self.berkas_id, "pengukuran", "kendala", "2026-09-08",
                            "petugas ukur sakit", self.pengguna_id)
        self.assertEqual(self._berkas()["tahapan_kode"], "pengukuran")
        self.assertEqual(self._riwayat()[-1]["aksi"], "kendala")

    def test_selesai_di_tahapan_terakhir_menutup_berkas(self):
        for kode in ("pengukuran", "panitia_a", "yuridis", "penerbitan", "penyerahan"):
            self.tahapan.pindah(self.berkas_id, kode, "masuk", "2026-09-10",
                                None, self.pengguna_id)
        self.tahapan.pindah(self.berkas_id, "penyerahan", "selesai", "2026-09-24",
                            "diserahkan ke nadzir", self.pengguna_id)
        berkas = self._berkas()
        self.assertEqual(berkas["status"], "selesai")
        self.assertEqual(berkas["tanggal_selesai"], "2026-09-24")

    def test_tanggal_kejadian_boleh_mundur_dari_hari_input(self):
        self.tahapan.pindah(self.berkas_id, "pengukuran", "masuk", "2026-09-02",
                            None, self.pengguna_id)
        baris = self._riwayat()[-1]
        self.assertEqual(baris["tanggal"], "2026-09-02")
        self.assertIsNotNone(baris["dibuat_pada"])

    def test_aksi_tak_dikenal_ditolak(self):
        with self.assertRaises(self.tahapan.PindahDitolak):
            self.tahapan.pindah(self.berkas_id, "pengukuran", "loncat",
                                "2026-09-05", None, self.pengguna_id)

    def test_menulis_log_audit(self):
        self.tahapan.pindah(self.berkas_id, "pengukuran", "masuk", "2026-09-05",
                            None, self.pengguna_id)
        jumlah = self.db.ambil_nilai(
            "SELECT COUNT(*) FROM log_audit WHERE tabel = 'berkas' AND ref_id = ?",
            (self.berkas_id,), 0)
        self.assertGreaterEqual(jumlah, 1)


if __name__ == "__main__":
    unittest.main()
