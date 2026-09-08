"""Koreksi jenis permohonan dan tahapan dari halaman Ubah Berkas.

Dua perubahan ini boleh dilakukan, tapi hanya lewat services/berkas_koreksi:
ganti jenis wajib menyusun ulang ceklis, koreksi tahapan wajib lewat
services/tahapan.pindah() supaya riwayat tetap utuh (aturan domain #1).
Keduanya wajib beralasan.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.bantu import BasisTes  # noqa: E402


class TesKoreksiBerkas(BasisTes):
    def setUp(self):
        super().setUp()
        import auth
        from services import berkas, berkas_koreksi, ceklis, tahapan

        self.auth = auth
        self.svc = berkas
        self.koreksi = berkas_koreksi
        self.ceklis = ceklis
        self.tahapan = tahapan
        self.pengguna_id = self.buat_pengguna()
        self.objek = self.buat_objek("Masjid Uji Koreksi", "Suwawa")
        self.berkas = self.svc.buat(
            {"objek_wakaf_id": self.objek, "jenis_permohonan_kode": "pertama_kali",
             "no_berkas": "0001/2026", "tanggal_daftar": "2026-09-01"},
            self.pengguna_id)

    def ambil(self):
        return self.db.ambil_satu("SELECT * FROM berkas WHERE id = ?", (self.berkas,))

    def nama_syarat(self):
        return [b["nama"] for b in self.ceklis.per_berkas(self.berkas)]

    # ---- ganti jenis permohonan ----
    def test_jenis_berubah_dan_ceklis_ikut_jenis_baru(self):
        self.koreksi.ganti_jenis(self.berkas, "tanah_terdaftar",
                                 "Ternyata sudah bersertipikat", self.pengguna_id)
        self.assertEqual(self.ambil()["jenis_permohonan_kode"], "tanah_terdaftar")
        seharusnya = [b["nama"] for b in self.db.ambil_semua(
            "SELECT nama FROM syarat WHERE jenis_permohonan_kode = ? ORDER BY urutan",
            ("tanah_terdaftar",))]
        self.assertEqual(self.nama_syarat(), seharusnya)

    def test_syarat_khas_jenis_lama_hilang(self):
        self.koreksi.ganti_jenis(self.berkas, "tanah_terdaftar",
                                 "salah pilih di loket", self.pengguna_id)
        self.assertNotIn("Surat Tanah", self.nama_syarat())
        self.assertIn("Sertipikat Asli", self.nama_syarat())

    def test_centang_syarat_bernama_sama_dibawa_pindah(self):
        aiw = self.db.ambil_satu(
            "SELECT id FROM syarat WHERE jenis_permohonan_kode = ? AND nama LIKE ?",
            ("pertama_kali", "AIW%"))
        self.ceklis.simpan(self.berkas, {aiw["id"]}, {aiw["id"]: "sudah discan"},
                           self.pengguna_id)
        ringkas = self.koreksi.ganti_jenis(self.berkas, "tanah_terdaftar",
                                           "salah pilih", self.pengguna_id)
        self.assertEqual(ringkas["centang_dibawa"], 1)
        baris = [b for b in self.ceklis.per_berkas(self.berkas)
                 if b["nama"].startswith("AIW")]
        self.assertEqual(len(baris), 1)
        self.assertEqual(baris[0]["terpenuhi"], 1)
        self.assertEqual(baris[0]["catatan"], "sudah discan")
        self.assertIsNotNone(baris[0]["tanggal_penuhi"])

    def test_centang_syarat_yang_tidak_ada_di_jenis_baru_tidak_terbawa(self):
        tanah = self.db.ambil_satu(
            "SELECT id FROM syarat WHERE jenis_permohonan_kode = ? AND nama = ?",
            ("pertama_kali", "Surat Tanah"))
        self.ceklis.simpan(self.berkas, {tanah["id"]}, {}, self.pengguna_id)
        ringkas = self.koreksi.ganti_jenis(self.berkas, "tanah_terdaftar",
                                           "salah pilih", self.pengguna_id)
        self.assertEqual(ringkas["centang_dibawa"], 0)
        self.assertIn("Surat Tanah", ringkas["syarat_hilang"])

    def test_jenis_tanpa_syarat_menyisakan_ceklis_kosong(self):
        self.koreksi.ganti_jenis(self.berkas, "alih_media", "berkasnya alih media",
                                 self.pengguna_id)
        self.assertEqual(self.nama_syarat(), [])

    def test_ganti_jenis_wajib_beralasan(self):
        with self.assertRaises(self.koreksi.KoreksiDitolak):
            self.koreksi.ganti_jenis(self.berkas, "tanah_terdaftar", "  ",
                                     self.pengguna_id)
        self.assertEqual(self.ambil()["jenis_permohonan_kode"], "pertama_kali")

    def test_jenis_tidak_dikenal_ditolak(self):
        with self.assertRaises(self.koreksi.KoreksiDitolak):
            self.koreksi.ganti_jenis(self.berkas, "ngawur", "alasan", self.pengguna_id)
        self.assertEqual(self.ambil()["jenis_permohonan_kode"], "pertama_kali")
        self.assertEqual(len(self.nama_syarat()), 6)

    def test_jenis_sama_ditolak(self):
        with self.assertRaises(self.koreksi.KoreksiDitolak):
            self.koreksi.ganti_jenis(self.berkas, "pertama_kali", "alasan",
                                     self.pengguna_id)

    def test_ganti_jenis_tercatat_di_audit(self):
        self.koreksi.ganti_jenis(self.berkas, "tanah_terdaftar",
                                 "salah pilih di loket", self.pengguna_id)
        baris = self.db.ambil_satu(
            """SELECT * FROM log_audit WHERE tabel = 'berkas' AND ref_id = ?
                 AND aksi = 'ganti_jenis' ORDER BY id DESC LIMIT 1""", (self.berkas,))
        self.assertIn("pertama_kali", baris["data_lama"])
        self.assertIn("Surat Tanah", baris["data_lama"])
        self.assertIn("salah pilih di loket", baris["data_baru"])

    # ---- koreksi tahapan ----
    def test_maju_menulis_riwayat_dan_memindahkan_berkas(self):
        self.koreksi.perbaiki_tahapan(self.berkas, "panitia_a",
                                      "sudah panitia A sejak Agustus", self.pengguna_id)
        self.assertEqual(self.ambil()["tahapan_kode"], "panitia_a")
        akhir = self.tahapan.riwayat(self.berkas)[-1]
        self.assertEqual(akhir["tahapan_kode"], "panitia_a")
        self.assertEqual(akhir["aksi"], "masuk")
        self.assertIn("sudah panitia A sejak Agustus", akhir["catatan"])

    def test_mundur_memakai_aksi_mundur(self):
        self.tahapan.pindah(self.berkas, "panitia_a", "masuk", "2026-09-05", None,
                            self.pengguna_id)
        self.koreksi.perbaiki_tahapan(self.berkas, "pengukuran", "salah klik kemarin",
                                      self.pengguna_id)
        self.assertEqual(self.ambil()["tahapan_kode"], "pengukuran")
        akhir = self.tahapan.riwayat(self.berkas)[-1]
        self.assertEqual(akhir["aksi"], "mundur")

    def test_koreksi_tahapan_wajib_beralasan(self):
        with self.assertRaises(self.koreksi.KoreksiDitolak):
            self.koreksi.perbaiki_tahapan(self.berkas, "panitia_a", None,
                                          self.pengguna_id)
        self.assertEqual(self.ambil()["tahapan_kode"], "permohonan")

    def test_tahapan_tidak_dikenal_ditolak(self):
        with self.assertRaises(self.koreksi.KoreksiDitolak):
            self.koreksi.perbaiki_tahapan(self.berkas, "ngawur", "alasan",
                                          self.pengguna_id)

    def test_tahapan_sama_ditolak(self):
        with self.assertRaises(self.koreksi.KoreksiDitolak):
            self.koreksi.perbaiki_tahapan(self.berkas, "permohonan", "alasan",
                                          self.pengguna_id)

    def test_berkas_selesai_dibuka_lagi_saat_ditarik_mundur(self):
        self.tahapan.pindah(self.berkas, "penyerahan", "masuk", "2026-09-05", None,
                            self.pengguna_id)
        self.tahapan.pindah(self.berkas, "penyerahan", "selesai", "2026-09-06", None,
                            self.pengguna_id)
        self.assertEqual(self.ambil()["status"], "selesai")
        self.koreksi.perbaiki_tahapan(self.berkas, "penerbitan",
                                      "sertipikat belum diserahkan", self.pengguna_id)
        baris = self.ambil()
        self.assertEqual(baris["status"], "aktif")
        self.assertIsNone(baris["tanggal_selesai"])
        self.assertEqual(baris["tahapan_kode"], "penerbitan")

    # ---- berkas batal ----
    def test_berkas_batal_tidak_bisa_dikoreksi(self):
        from services import berkas_aksi

        berkas_aksi.batalkan(self.berkas, "dobel", self.pengguna_id)
        with self.assertRaises(self.koreksi.KoreksiDitolak):
            self.koreksi.ganti_jenis(self.berkas, "tanah_terdaftar", "alasan",
                                     self.pengguna_id)
        with self.assertRaises(self.koreksi.KoreksiDitolak):
            self.koreksi.perbaiki_tahapan(self.berkas, "pengukuran", "alasan",
                                          self.pengguna_id)

    # ---- peran ----
    def test_peran_koreksi_lebih_sempit_dari_peran_ubah(self):
        self.assertEqual(set(self.auth.PERAN_KOREKSI_BERKAS), {"admin", "sekretariat"})
        for peran in self.auth.PERAN_KOREKSI_BERKAS:
            self.assertIn(peran, self.auth.PERAN_UBAH_BERKAS)
        self.assertNotIn("petugas_loket", self.auth.PERAN_KOREKSI_BERKAS)


if __name__ == "__main__":
    unittest.main()
