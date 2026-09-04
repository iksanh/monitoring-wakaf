"""Ubah data pengguna di /master/pengguna, termasuk penjaga admin terakhir."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.bantu import BasisTes  # noqa: E402


class TesUbahPengguna(BasisTes):
    def setUp(self):
        super().setUp()
        from services import master
        self.svc = master
        self.wil1 = self.db.ambil_nilai("SELECT id FROM wilayah WHERE nama = 'Wilayah I'")
        self.wil2 = self.db.ambil_nilai("SELECT id FROM wilayah WHERE nama = 'Wilayah II'")
        self.admin = self.buat_pengguna("bosadmin", "admin")
        self.orang = self.buat_pengguna("petugasa", "petugas", self.wil1)

    def isi(self, **ubah):
        lama = self.svc.ambil_pengguna(self.orang)
        dasar = {"username": lama["username"], "nama": lama["nama"],
                 "peran": lama["peran"], "wilayah_id": lama["wilayah_id"]}
        dasar.update(ubah)
        return dasar

    def ubah(self, **kk):
        return self.svc.ubah_pengguna(self.orang, self.isi(**kk), self.admin)

    # ---- perubahan yang sah ----
    def test_ubah_nama_dan_username(self):
        self.assertIsNone(self.ubah(username="petugasb", nama="Petugas Baru"))
        p = self.svc.ambil_pengguna(self.orang)
        self.assertEqual(p["username"], "petugasb")
        self.assertEqual(p["nama"], "Petugas Baru")

    def test_username_dijadikan_huruf_kecil(self):
        self.ubah(username="  PetugasBesar  ")
        self.assertEqual(self.svc.ambil_pengguna(self.orang)["username"],
                         "petugasbesar")

    def test_ubah_peran_dan_wilayah(self):
        self.assertIsNone(self.ubah(peran="korwil", wilayah_id=self.wil2))
        p = self.svc.ambil_pengguna(self.orang)
        self.assertEqual(p["peran"], "korwil")
        self.assertEqual(p["wilayah_id"], self.wil2)

    def test_wilayah_dikosongkan_untuk_peran_tanpa_batas(self):
        """Hanya korwil & petugas yang datanya dibatasi wilayah."""
        self.assertIsNone(self.ubah(peran="sekretariat", wilayah_id=self.wil1))
        self.assertIsNone(self.svc.ambil_pengguna(self.orang)["wilayah_id"])

    def test_sandi_tidak_ikut_berubah(self):
        sebelum = self.db.ambil_nilai(
            "SELECT password_hash FROM pengguna WHERE id = ?", (self.orang,))
        self.ubah(nama="Nama Lain")
        self.assertEqual(self.db.ambil_nilai(
            "SELECT password_hash FROM pengguna WHERE id = ?", (self.orang,)), sebelum)

    def test_status_aktif_tidak_ikut_berubah(self):
        self.svc.set_aktif(self.orang, 0, self.admin)
        self.ubah(nama="Nama Lain")
        self.assertEqual(self.svc.ambil_pengguna(self.orang)["aktif"], 0)

    def test_menulis_log_audit(self):
        self.ubah(nama="Nama Lain")
        self.assertEqual(self.db.ambil_nilai(
            """SELECT COUNT(*) FROM log_audit
                WHERE aksi = 'ubah' AND tabel = 'pengguna' AND ref_id = ?""",
            (self.orang,), 0), 1)

    # ---- validasi ----
    def test_nama_dan_username_wajib(self):
        for kosong in ("", "   "):
            self.assertIsNotNone(self.ubah(username=kosong))
            self.assertIsNotNone(self.ubah(nama=kosong))

    def test_peran_tak_dikenal_ditolak(self):
        self.assertIsNotNone(self.ubah(peran="raja"))

    def test_korwil_wajib_punya_wilayah(self):
        galat = self.ubah(peran="korwil", wilayah_id=None)
        self.assertIn("wajib punya wilayah", galat)

    def test_username_bentrok_ditolak(self):
        galat = self.ubah(username="bosadmin")
        self.assertIn("sudah dipakai", galat)

    def test_username_sendiri_tidak_dianggap_bentrok(self):
        self.assertIsNone(self.ubah(nama="Ganti Nama Saja"))

    def test_pengguna_tak_ada_ditolak(self):
        self.assertIsNotNone(
            self.svc.ubah_pengguna(9999, self.isi(), self.admin))

    def test_penolakan_tidak_menyimpan_apa_pun(self):
        sebelum = self.svc.ambil_pengguna(self.orang)
        self.ubah(username="bosadmin", nama="Harusnya Batal")
        self.assertEqual(self.svc.ambil_pengguna(self.orang), sebelum)

    # ---- penjaga admin terakhir ----
    def test_admin_terakhir_tidak_boleh_diturunkan(self):
        galat = self.svc.ubah_pengguna(
            self.admin, {"username": "bosadmin", "nama": "Bos", "peran": "petugas",
                         "wilayah_id": self.wil1}, self.admin)
        self.assertIn("satu-satunya admin", galat)
        self.assertEqual(self.svc.ambil_pengguna(self.admin)["peran"], "admin")

    def test_admin_boleh_diturunkan_kalau_ada_admin_lain(self):
        self.buat_pengguna("admincadangan", "admin")
        self.assertIsNone(self.svc.ubah_pengguna(
            self.admin, {"username": "bosadmin", "nama": "Bos", "peran": "petugas",
                         "wilayah_id": self.wil1}, self.admin))

    def test_admin_lain_yang_nonaktif_tidak_dihitung(self):
        cadangan = self.buat_pengguna("admincadangan", "admin")
        self.svc.set_aktif(cadangan, 0, self.admin)
        self.assertIsNotNone(self.svc.ubah_pengguna(
            self.admin, {"username": "bosadmin", "nama": "Bos", "peran": "petugas",
                         "wilayah_id": self.wil1}, self.admin))

    def test_admin_terakhir_tidak_boleh_dinonaktifkan(self):
        galat = self.svc.set_aktif(self.admin, 0, self.admin)
        self.assertIn("satu-satunya admin", galat)
        self.assertEqual(self.svc.ambil_pengguna(self.admin)["aktif"], 1)

    def test_nonaktifkan_pengguna_biasa_tetap_boleh(self):
        self.assertIsNone(self.svc.set_aktif(self.orang, 0, self.admin))
        self.assertEqual(self.svc.ambil_pengguna(self.orang)["aktif"], 0)

    def test_mengaktifkan_kembali_tidak_dijaga(self):
        self.svc.set_aktif(self.orang, 0, self.admin)
        self.assertIsNone(self.svc.set_aktif(self.orang, 1, self.admin))
        self.assertEqual(self.svc.ambil_pengguna(self.orang)["aktif"], 1)

    # ---- ambil_pengguna ----
    def test_ambil_pengguna_membawa_nama_wilayah(self):
        p = self.svc.ambil_pengguna(self.orang)
        self.assertEqual(p["wilayah"], "Wilayah I")
        self.assertNotIn("password_hash", p)

    def test_ambil_pengguna_tak_ada(self):
        self.assertIsNone(self.svc.ambil_pengguna(9999))


if __name__ == "__main__":
    unittest.main()
