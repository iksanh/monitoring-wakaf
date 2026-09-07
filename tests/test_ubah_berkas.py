"""Perbaikan data administratif berkas — terutama nomor berkas yang salah ketik.

Yang dijaga di sini bukan cuma "kolomnya berubah", tapi kolom mana yang TIDAK
boleh ikut berubah: tahapan_kode, status, dan jenis_permohonan_kode masing-masing
punya jalurnya sendiri dan tidak boleh bisa ditembus lewat form ubah.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.bantu import BasisTes  # noqa: E402


class TesUbahBerkas(BasisTes):
    def setUp(self):
        super().setUp()
        import auth
        from services import berkas, ceklis

        self.auth = auth
        self.svc = berkas
        self.ceklis = ceklis
        self.pengguna_id = self.buat_pengguna()
        self.objek = self.buat_objek("Masjid Uji Ubah", "Suwawa")
        self.berkas = self.svc.buat(
            {"objek_wakaf_id": self.objek, "jenis_permohonan_kode": "pertama_kali",
             "no_berkas": "0001/2026", "tanggal_daftar": "2026-09-01"},
            self.pengguna_id)

    def isi(self, **ubah):
        dasar = {"no_berkas": "0001/2026", "tanggal_daftar": "2026-09-01",
                 "target_penyerahan": None, "petugas_id": None, "catatan": None}
        dasar.update(ubah)
        return dasar

    def ambil(self):
        return self.db.ambil_satu("SELECT * FROM berkas WHERE id = ?", (self.berkas,))

    # ---- yang memang boleh diubah ----
    def test_nomor_berkas_diperbarui(self):
        self.svc.ubah(self.berkas, self.isi(no_berkas="0042/2026"), self.pengguna_id)
        self.assertEqual(self.ambil()["no_berkas"], "0042/2026")

    def test_nomor_berkas_boleh_dikosongkan(self):
        self.svc.ubah(self.berkas, self.isi(no_berkas=None), self.pengguna_id)
        self.assertIsNone(self.ambil()["no_berkas"])

    def test_target_petugas_dan_catatan_diperbarui(self):
        petugas = self.buat_pengguna("ptg", "petugas")
        self.svc.ubah(self.berkas, self.isi(target_penyerahan="2026-10-01",
                                            petugas_id=petugas,
                                            catatan="Nomor diperbaiki dari loket"),
                      self.pengguna_id)
        baris = self.ambil()
        self.assertEqual(baris["target_penyerahan"], "2026-10-01")
        self.assertEqual(baris["petugas_id"], petugas)
        self.assertEqual(baris["catatan"], "Nomor diperbaiki dari loket")

    # ---- yang tidak boleh ikut berubah ----
    def test_tahapan_tidak_tersentuh(self):
        """Aturan domain #1: tahapan hanya lewat services/tahapan.pindah()."""
        from services import tahapan

        tahapan.pindah(self.berkas, "pengukuran", "masuk", "2026-09-05", None,
                       self.pengguna_id)
        self.svc.ubah(self.berkas,
                      self.isi(no_berkas="0042/2026", tahapan_kode="penyerahan"),
                      self.pengguna_id)
        self.assertEqual(self.ambil()["tahapan_kode"], "pengukuran")

    def test_status_tidak_bisa_dipasang_lewat_form(self):
        """'batal' hanya lewat berkas_aksi.batalkan() yang mewajibkan alasan."""
        self.svc.ubah(self.berkas, self.isi(status="batal"), self.pengguna_id)
        baris = self.ambil()
        self.assertEqual(baris["status"], "aktif")
        self.assertIsNone(baris["alasan_batal"])

    def test_jenis_permohonan_terkunci(self):
        """Ceklis disalin mengikuti jenis, jadi jenis tidak boleh berubah diam-diam."""
        sebelum = self.ceklis.progres(self.berkas)
        self.svc.ubah(self.berkas, self.isi(jenis_permohonan_kode="alih_media"),
                      self.pengguna_id)
        self.assertEqual(self.ambil()["jenis_permohonan_kode"], "pertama_kali")
        self.assertEqual(self.ceklis.progres(self.berkas), sebelum)

    def test_kolom_terlarang_tidak_ada_di_kolom_ubah(self):
        for kolom in ("tahapan_kode", "status", "jenis_permohonan_kode"):
            self.assertNotIn(kolom, self.svc.KOLOM_UBAH)

    # ---- jejak ----
    def test_menulis_log_audit_hanya_yang_berubah(self):
        self.svc.ubah(self.berkas, self.isi(no_berkas="0042/2026"), self.pengguna_id)
        baris = self.db.ambil_satu(
            """SELECT * FROM log_audit WHERE tabel = 'berkas' AND ref_id = ?
                 AND aksi = 'ubah' ORDER BY id DESC LIMIT 1""", (self.berkas,))
        self.assertIn("0001/2026", baris["data_lama"])
        self.assertIn("0042/2026", baris["data_baru"])
        # Kolom yang tidak disentuh tidak ikut membanjiri riwayat.
        self.assertNotIn("catatan", baris["data_baru"])

    def test_diubah_pada_terisi(self):
        self.assertIsNone(self.ambil()["diubah_pada"])
        self.svc.ubah(self.berkas, self.isi(no_berkas="0042/2026"), self.pengguna_id)
        self.assertIsNotNone(self.ambil()["diubah_pada"])

    def test_berkas_tidak_ada_ditolak(self):
        with self.assertRaises(ValueError):
            self.svc.ubah(999999, self.isi(), self.pengguna_id)

    # ---- peran ----
    def test_peran_yang_boleh_mengubah(self):
        self.assertEqual(set(self.auth.PERAN_UBAH_BERKAS),
                         {"admin", "sekretariat", "petugas_loket"})

    def test_korwil_dan_petugas_tidak_termasuk(self):
        for peran in ("korwil", "petugas", "pimpinan"):
            self.assertNotIn(peran, self.auth.PERAN_UBAH_BERKAS)


if __name__ == "__main__":
    unittest.main()
