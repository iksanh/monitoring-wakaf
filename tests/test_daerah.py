"""Tes pengelolaan master daerah: kecamatan dan desa."""
import unittest

from tests.bantu import BasisTes


class TesDaerah(BasisTes):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Batas id kecamatan bawaan seed 002. Baris di atas ini dibuat tes dan
        # dibersihkan tiap kali supaya tes tidak saling mewarisi master.
        cls._kec_seed = cls.db.ambil_nilai("SELECT MAX(id) FROM kecamatan", (), 0)

    def setUp(self):
        super().setUp()
        with self.db.buka() as kon:
            kon.execute("DELETE FROM desa")
            kon.execute("DELETE FROM kecamatan WHERE id > ?", (self._kec_seed,))
        from services import daerah
        self.svc = daerah
        self.admin = {"id": self.buat_pengguna("adm", "admin"), "peran": "admin"}

    def _kecamatan_baru(self, nama="Uji Baru", kode="UJI", wilayah_id=1) -> int:
        return self.svc.tambah_kecamatan(
            {"nama": nama, "kode_singkat": kode, "wilayah_id": wilayah_id}, self.admin)

    def _objek_di(self, kecamatan_id, desa_id=None, is_aktif=1) -> int:
        urut = self.db.ambil_nilai("SELECT COUNT(*) FROM objek_wakaf", (), 0) + 1
        return self.db.jalankan(
            """INSERT INTO objek_wakaf (kode, nama_objek, kecamatan_id, desa_id,
                                        sumber_data, is_aktif)
               VALUES (?, 'Masjid Uji', ?, ?, 'uji', ?)""",
            (f"WKF-UJI-{urut:03d}", kecamatan_id, desa_id, is_aktif),
        )

    # ---- kecamatan ----

    def test_tambah_kecamatan_muncul_di_daftar(self):
        kec_id = self._kecamatan_baru("Pinogu", "PNG", 2)
        kec = self.svc.ambil_kecamatan(kec_id)
        self.assertEqual(kec["nama"], "Pinogu")
        self.assertEqual(kec["kode_singkat"], "PNG")
        self.assertEqual(kec["wilayah"], "Wilayah II")
        self.assertIn("Pinogu", [b["nama"] for b in self.svc.daftar_kecamatan()])

    def test_nama_kecamatan_wajib_dan_unik(self):
        self._kecamatan_baru("Pinogu", "PNG")
        with self.assertRaises(self.svc.GalatDaerah):
            self._kecamatan_baru("   ", "ABC")
        # Perbandingannya tidak peduli huruf besar-kecil.
        with self.assertRaises(self.svc.GalatDaerah):
            self._kecamatan_baru("pinogu", "ABC")

    def test_kode_singkat_harus_tiga_huruf_dan_unik(self):
        self._kecamatan_baru("Pinogu", "PNG")
        for kode in ("", "PN", "PNGG", "PN1"):
            with self.assertRaises(self.svc.GalatDaerah):
                self._kecamatan_baru(f"Uji {kode}X", kode)
        with self.assertRaises(self.svc.GalatDaerah):
            self._kecamatan_baru("Uji Lain", "png")   # bentrok, beda kapital saja

    def test_wilayah_wajib_dan_harus_dikenal(self):
        with self.assertRaises(self.svc.GalatDaerah):
            self._kecamatan_baru("Pinogu", "PNG", wilayah_id=None)
        with self.assertRaises(self.svc.GalatDaerah):
            self._kecamatan_baru("Pinogu", "PNG", wilayah_id=999)

    def test_kode_singkat_baru_dipakai_kode_objek(self):
        """Kode kecamatan itu awalan kode objek — pastikan sambungannya nyata."""
        from services import objek
        kec_id = self._kecamatan_baru("Pinogu", "PNG")
        objek_id = objek.buat({"nama_objek": "Masjid Pinogu", "kecamatan_id": kec_id,
                               "status_sertipikat": "belum", "perlu_isbat": 0,
                               "is_prioritas": 0}, self.admin["id"])
        kode = self.db.ambil_nilai("SELECT kode FROM objek_wakaf WHERE id = ?",
                                   (objek_id,))
        self.assertTrue(kode.startswith("WKF-PNG-"), kode)

    def test_ubah_kecamatan_mencatat_yang_berubah_saja(self):
        kec_id = self._kecamatan_baru("Pinogu", "PNG", 2)
        self.svc.ubah_kecamatan(kec_id, {"nama": "Pinogu Raya", "kode_singkat": "PNG",
                                         "wilayah_id": 3}, self.admin)
        kec = self.svc.ambil_kecamatan(kec_id)
        self.assertEqual(kec["nama"], "Pinogu Raya")
        self.assertEqual(kec["wilayah_id"], 3)
        catatan = self.db.ambil_satu(
            """SELECT data_lama, data_baru FROM log_audit
                WHERE tabel = 'kecamatan' AND aksi = 'ubah' AND ref_id = ?""",
            (kec_id,))
        self.assertIn("Pinogu Raya", catatan["data_baru"])
        self.assertNotIn("kode_singkat", catatan["data_baru"])

    def test_hapus_kecamatan_hanya_kalau_belum_dipakai(self):
        kec_id = self._kecamatan_baru("Pinogu", "PNG")
        self.svc.tambah_desa(kec_id, "Dulamayo", self.admin)
        with self.assertRaises(self.svc.GalatDaerah):
            self.svc.hapus_kecamatan(kec_id, self.admin)   # masih punya desa

        desa_id = self.svc.daftar_desa(kec_id)[0]["id"]
        self.svc.hapus_desa(desa_id, self.admin)
        self.svc.hapus_kecamatan(kec_id, self.admin)
        self.assertIsNone(self.svc.ambil_kecamatan(kec_id))

    def test_kecamatan_dengan_objek_nonaktif_tetap_tidak_bisa_dihapus(self):
        """Objek nonaktif tidak muncul di daftar, tapi barisnya masih menunjuk ke sini."""
        kec_id = self._kecamatan_baru("Pinogu", "PNG")
        self._objek_di(kec_id, is_aktif=0)
        self.assertEqual(self.svc.ambil_kecamatan(kec_id)["jumlah_objek"], 0)
        with self.assertRaises(self.svc.GalatDaerah):
            self.svc.hapus_kecamatan(kec_id, self.admin)

    # ---- desa ----

    def test_nama_desa_unik_per_kecamatan(self):
        satu = self._kecamatan_baru("Pinogu", "PNG")
        dua = self._kecamatan_baru("Pinogu Timur", "PGT")
        self.svc.tambah_desa(satu, "Dulamayo", self.admin)
        # Nama yang sama di kecamatan lain tetap boleh.
        self.svc.tambah_desa(dua, "Dulamayo", self.admin)
        with self.assertRaises(self.svc.GalatDaerah):
            self.svc.tambah_desa(satu, "dulamayo", self.admin)
        with self.assertRaises(self.svc.GalatDaerah):
            self.svc.tambah_desa(satu, "  ", self.admin)

    def test_nama_desa_dirapikan(self):
        kec_id = self._kecamatan_baru()
        desa_id = self.svc.tambah_desa(kec_id, "  dulamayo   utara ", self.admin)
        self.assertEqual(self.svc.ambil_desa(desa_id)["nama"], "Dulamayo Utara")

    def test_ubah_desa_hanya_ganti_nama(self):
        kec_id = self._kecamatan_baru()
        desa_id = self.svc.tambah_desa(kec_id, "Dulamayo", self.admin)
        self.svc.ubah_desa(desa_id, "Dulamayo Selatan", self.admin)
        desa = self.svc.ambil_desa(desa_id)
        self.assertEqual(desa["nama"], "Dulamayo Selatan")
        self.assertEqual(desa["kecamatan_id"], kec_id)

    def test_hapus_desa_yang_dipakai_objek_ditolak(self):
        kec_id = self._kecamatan_baru()
        desa_id = self.svc.tambah_desa(kec_id, "Dulamayo", self.admin)
        self._objek_di(kec_id, desa_id)
        with self.assertRaises(self.svc.GalatDaerah):
            self.svc.hapus_desa(desa_id, self.admin)
        self.assertIsNotNone(self.svc.ambil_desa(desa_id))

    def test_hapus_desa_kosong_berhasil_dan_tercatat(self):
        kec_id = self._kecamatan_baru()
        desa_id = self.svc.tambah_desa(kec_id, "Dulamayo", self.admin)
        self.assertEqual(self.svc.hapus_desa(desa_id, self.admin), "Dulamayo")
        self.assertIsNone(self.svc.ambil_desa(desa_id))
        self.assertEqual(self.db.ambil_nilai(
            """SELECT COUNT(*) FROM log_audit
                WHERE tabel = 'desa' AND ref_id = ? AND aksi = 'hapus'""",
            (desa_id,), 0), 1)

    # ---- hak akses ----

    def test_hanya_admin_yang_boleh_mengubah(self):
        kec_id = self._kecamatan_baru()
        desa_id = self.svc.tambah_desa(kec_id, "Dulamayo", self.admin)
        for peran in ("korwil", "sekretariat", "petugas", "petugas_loket"):
            orang = {"id": self.buat_pengguna(f"u_{peran}", peran, 1), "peran": peran}
            self.assertFalse(self.svc.boleh_mengelola(orang))
            with self.assertRaises(self.svc.GalatDaerah):
                self.svc.tambah_kecamatan(
                    {"nama": "Curi", "kode_singkat": "CRI", "wilayah_id": 1}, orang)
            with self.assertRaises(self.svc.GalatDaerah):
                self.svc.ubah_kecamatan(kec_id, {"nama": "Curi", "kode_singkat": "CRI",
                                                 "wilayah_id": 1}, orang)
            with self.assertRaises(self.svc.GalatDaerah):
                self.svc.hapus_kecamatan(kec_id, orang)
            with self.assertRaises(self.svc.GalatDaerah):
                self.svc.tambah_desa(kec_id, "Curi", orang)
            with self.assertRaises(self.svc.GalatDaerah):
                self.svc.ubah_desa(desa_id, "Curi", orang)
            with self.assertRaises(self.svc.GalatDaerah):
                self.svc.hapus_desa(desa_id, orang)
        self.assertEqual(self.svc.ambil_desa(desa_id)["nama"], "Dulamayo")


if __name__ == "__main__":
    unittest.main()
