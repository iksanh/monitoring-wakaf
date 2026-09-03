"""Tes pembuatan akun dari susunan tim."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.bantu import BasisTes  # noqa: E402


class TesUsernameTim(BasisTes):
    def setUp(self):
        super().setUp()
        from services import master
        self.master = master

    def test_gelar_dibuang_dan_dua_kata_pertama_dipakai(self):
        self.assertEqual(
            self.master.usulan_username("Sep Hamdan Rifanuddin, S.T.", set()),
            "sep.hamdan")
        self.assertEqual(
            self.master.usulan_username("Moh. Ikhsan A.H, S.Kom", set()),
            "moh.ikhsan")
        self.assertEqual(
            self.master.usulan_username("Marten Bento", set()), "marten.bento")

    def test_username_bentrok_diberi_angka(self):
        terpakai = {"marten.bento"}
        self.assertEqual(
            self.master.usulan_username("Marten Bento", terpakai), "marten.bento2")
        self.assertEqual(
            self.master.usulan_username("Marten Bento", terpakai), "marten.bento3")

    def test_jabatan_dipetakan_ke_peran(self):
        self.assertEqual(self.master.peran_untuk("Korwil"), "korwil")
        self.assertEqual(self.master.peran_untuk("Anggota"), "petugas")
        self.assertEqual(self.master.peran_untuk("Petugas Ukur"), "petugas")
        self.assertEqual(self.master.peran_untuk(None), "petugas")


class TesBuatAkunTim(BasisTes):
    def setUp(self):
        super().setUp()
        from services import master
        self.master = master
        self.admin_id = self.buat_pengguna("admin_uji", "admin")
        # Kosongkan tautan akun supaya tiap tes mulai dari nol.
        self.db.jalankan("UPDATE tim SET pengguna_id = NULL")

    def test_seed_tim_terisi_23_orang(self):
        self.assertEqual(len(self.master.tim()), 23)

    def test_akun_mewarisi_wilayah_dan_peran_dari_tim(self):
        korwil = self.db.ambil_satu(
            "SELECT id, wilayah_id FROM tim WHERE jabatan = 'Korwil' ORDER BY id LIMIT 1")
        dibuat = self.master.buat_akun_tim([korwil["id"]], self.admin_id)
        self.assertEqual(len(dibuat), 1)
        self.assertEqual(dibuat[0]["peran"], "korwil")

        akun = self.db.ambil_satu(
            "SELECT * FROM pengguna WHERE username = ?", (dibuat[0]["username"],))
        self.assertEqual(akun["peran"], "korwil")
        self.assertEqual(akun["wilayah_id"], korwil["wilayah_id"])
        self.assertEqual(akun["aktif"], 1)

    def test_sandi_awal_bisa_dipakai_login(self):
        import auth
        satu = self.db.ambil_satu("SELECT id FROM tim ORDER BY id LIMIT 1")
        dibuat = self.master.buat_akun_tim([satu["id"]], self.admin_id)[0]
        akun = self.db.ambil_satu(
            "SELECT password_hash FROM pengguna WHERE username = ?", (dibuat["username"],))
        self.assertTrue(auth.periksa_hash(dibuat["sandi"], akun["password_hash"]))
        self.assertNotIn(dibuat["sandi"], akun["password_hash"])

    def test_anggota_tertaut_ke_akunnya(self):
        satu = self.db.ambil_satu("SELECT id FROM tim ORDER BY id LIMIT 1")
        self.master.buat_akun_tim([satu["id"]], self.admin_id)
        baris = self.db.ambil_satu("SELECT pengguna_id FROM tim WHERE id = ?", (satu["id"],))
        self.assertIsNotNone(baris["pengguna_id"])

    def test_tidak_membuat_akun_ganda(self):
        satu = self.db.ambil_satu("SELECT id FROM tim ORDER BY id LIMIT 1")
        self.assertEqual(len(self.master.buat_akun_tim([satu["id"]], self.admin_id)), 1)
        self.assertEqual(self.master.buat_akun_tim([satu["id"]], self.admin_id), [])

    def test_buat_massal_menghasilkan_username_unik(self):
        semua = self.master.tim_tanpa_akun()
        self.assertEqual(len(semua), 23)
        dibuat = self.master.buat_akun_tim(semua, self.admin_id)
        self.assertEqual(len(dibuat), 23)
        username = [d["username"] for d in dibuat]
        self.assertEqual(len(set(username)), 23)
        self.assertEqual(self.master.tim_tanpa_akun(), [])

    def test_korwil_hasil_seed_hanya_melihat_wilayahnya(self):
        """Akun yang dibuat harus benar-benar terbatas di lapisan service."""
        from services import objek as svc_objek
        semua = self.master.tim_tanpa_akun()
        self.master.buat_akun_tim(semua, self.admin_id)
        korwil = self.db.ambil_satu(
            "SELECT * FROM pengguna WHERE peran = 'korwil' ORDER BY id LIMIT 1")

        self.buat_objek("Masjid Wilayah I", "Suwawa")        # Wilayah I
        self.buat_objek("Masjid Wilayah III", "Kabila")      # Wilayah III

        hasil = svc_objek.cari(dict(korwil), {})
        wilayah = {b["wilayah_id"] for b in hasil["baris"]}
        self.assertTrue(wilayah <= {korwil["wilayah_id"]})

    def test_daftar_kosong_tidak_membuat_apa_apa(self):
        sebelum = self.db.ambil_nilai("SELECT COUNT(*) FROM pengguna", (), 0)
        self.assertEqual(self.master.buat_akun_tim([], self.admin_id), [])
        self.assertEqual(self.db.ambil_nilai("SELECT COUNT(*) FROM pengguna", (), 0), sebelum)


if __name__ == "__main__":
    unittest.main()
