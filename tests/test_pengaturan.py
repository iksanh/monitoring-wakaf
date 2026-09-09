"""Tes pengaturan aplikasi — saklar tampilan tag prioritas."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.bantu import BasisTes  # noqa: E402


class TesPengaturan(BasisTes):
    def setUp(self):
        super().setUp()
        from services import pengaturan

        self.svc = pengaturan
        self.admin = {"id": self.buat_pengguna("adm", "admin"),
                      "peran": "admin", "wilayah_id": None}
        # setUp induk tidak mengosongkan tabel pengaturan (bukan tabel
        # transaksional), jadi kembalikan ke keadaan seed migrasi 015 sendiri.
        self.db.jalankan("DELETE FROM pengaturan")
        self.db.jalankan("INSERT INTO pengaturan (kunci, nilai) VALUES ('tag_prioritas', '1')")

    def nilai(self, kunci="tag_prioritas"):
        return self.db.ambil_nilai("SELECT nilai FROM pengaturan WHERE kunci = ?", (kunci,))

    # ---- bawaan ----
    def test_tag_prioritas_bawaannya_menyala(self):
        self.assertTrue(self.svc.ambil("tag_prioritas"))

    def test_baris_yang_belum_pernah_disimpan_pakai_bawaan(self):
        """Pengaturan baru boleh ditambah di TERSEDIA tanpa migrasi."""
        self.db.jalankan("DELETE FROM pengaturan WHERE kunci = 'tag_prioritas'")
        self.assertTrue(self.svc.ambil("tag_prioritas"))
        self.assertEqual(self.svc.semua()["tag_prioritas"], True)

    def test_semua_memuat_setiap_kunci_yang_dikenal(self):
        self.assertEqual(set(self.svc.semua()), set(self.svc.TERSEDIA))

    # ---- menyimpan ----
    def test_matikan_tag_prioritas(self):
        self.assertTrue(self.svc.simpan("tag_prioritas", False, self.admin))
        self.assertFalse(self.svc.ambil("tag_prioritas"))
        self.assertEqual(self.nilai(), "0")

    def test_nyalakan_lagi(self):
        self.svc.simpan("tag_prioritas", False, self.admin)
        self.assertTrue(self.svc.simpan("tag_prioritas", True, self.admin))
        self.assertTrue(self.svc.ambil("tag_prioritas"))

    def test_menyimpan_nilai_yang_sama_tidak_dihitung_berubah(self):
        self.assertFalse(self.svc.simpan("tag_prioritas", True, self.admin))

    def test_merekam_siapa_dan_kapan(self):
        self.svc.simpan("tag_prioritas", False, self.admin)
        baris = self.db.ambil_satu(
            "SELECT diubah_oleh, diubah_pada FROM pengaturan WHERE kunci = 'tag_prioritas'")
        self.assertEqual(baris["diubah_oleh"], self.admin["id"])
        self.assertTrue(baris["diubah_pada"])

    def test_perubahan_menulis_log_audit(self):
        self.svc.simpan("tag_prioritas", False, self.admin)
        baris = self.db.ambil_satu(
            "SELECT data_lama, data_baru FROM log_audit WHERE aksi = 'atur'")
        self.assertIn('"tag_prioritas": "1"', baris["data_lama"])
        self.assertIn('"tag_prioritas": "0"', baris["data_baru"])

    def test_yang_tidak_berubah_tidak_menulis_audit(self):
        self.svc.simpan("tag_prioritas", True, self.admin)
        self.assertEqual(self.db.ambil_nilai(
            "SELECT COUNT(*) FROM log_audit WHERE aksi = 'atur'", (), 0), 0)

    # ---- siapa yang boleh ----
    def test_hanya_admin_yang_boleh_mengatur(self):
        for peran in ("sekretariat", "korwil", "petugas", "petugas_loket", "pimpinan"):
            pengguna = {"id": self.buat_pengguna(f"u_{peran}", peran),
                        "peran": peran, "wilayah_id": None}
            self.assertFalse(self.svc.boleh_mengatur(pengguna), peran)
            with self.assertRaises(self.svc.GalatPengaturan, msg=peran):
                self.svc.simpan("tag_prioritas", False, pengguna)
        self.assertTrue(self.svc.ambil("tag_prioritas"))

    def test_tanpa_pengguna_ditolak(self):
        self.assertFalse(self.svc.boleh_mengatur(None))
        with self.assertRaises(self.svc.GalatPengaturan):
            self.svc.simpan("tag_prioritas", False, None)

    # ---- kunci ngawur ----
    def test_kunci_tak_dikenal_ditolak_saat_dibaca(self):
        with self.assertRaises(self.svc.GalatPengaturan):
            self.svc.ambil("ngawur")

    def test_kunci_tak_dikenal_ditolak_saat_disimpan(self):
        with self.assertRaises(self.svc.GalatPengaturan):
            self.svc.simpan("ngawur", True, self.admin)
        self.assertIsNone(self.nilai("ngawur"))

    # ---- saklar tidak menyentuh datanya ----
    def test_mematikan_tag_tidak_mengubah_penanda_objek(self):
        """Yang disembunyikan cuma lencananya — data dan penyaring tetap jalan."""
        from services import objek as svc_objek

        oid = self.buat_objek("Masjid Prioritas", "Suwawa")
        self.db.jalankan("UPDATE objek_wakaf SET is_prioritas = 1 WHERE id = ?", (oid,))
        self.svc.simpan("tag_prioritas", False, self.admin)

        self.assertEqual(svc_objek.ambil(oid)["is_prioritas"], 1)
        hasil = svc_objek.cari(self.admin, {"prioritas": "ya"})
        self.assertEqual([b["id"] for b in hasil["baris"]], [oid])

    def test_mematikan_tag_tidak_mengubah_urutan_daftar(self):
        from services import objek as svc_objek

        biasa = self.buat_objek("Masjid Awal", "Suwawa")
        penting = self.buat_objek("Masjid Zulfikar", "Suwawa")
        self.db.jalankan("UPDATE objek_wakaf SET is_prioritas = 1 WHERE id = ?", (penting,))
        self.svc.simpan("tag_prioritas", False, self.admin)

        baris = svc_objek.cari(self.admin, {})["baris"]
        self.assertEqual([b["id"] for b in baris], [penting, biasa])


if __name__ == "__main__":
    unittest.main()
