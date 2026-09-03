"""Tes ketujuh fungsi rekap dengan fixture kecil: 5 berkas, beberapa pergerakan."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.bantu import BasisTes  # noqa: E402


class TesRekap(BasisTes):
    def setUp(self):
        super().setUp()
        from services import rekap, tahapan
        self.rekap = rekap
        self.tahapan = tahapan
        self.pengguna_id = self.buat_pengguna()

        # Suwawa & Bulango Ulu = Wilayah I, Kabila = Wilayah III.
        self.o1 = self.buat_objek("Masjid A", "Suwawa", tipologi="T1")
        self.o2 = self.buat_objek("Masjid B", "Suwawa", tipologi="T6",
                                  tipe_hak="Hak Milik")
        self.o3 = self.buat_objek("Masjid C", "Bulango Ulu", tipologi="T6",
                                  rekomendasi_isbat="Isbat")
        self.o4 = self.buat_objek("Masjid D", "Kabila", tipologi=None)
        self.o5 = self.buat_objek("Masjid E", "Kabila", tipologi="T2", status="sudah")

        self.b1 = self.buat_berkas(self.o1, "pertama_kali")
        self.b2 = self.buat_berkas(self.o2, "pertama_kali")
        self.b3 = self.buat_berkas(self.o3, "alih_media")
        self.b4 = self.buat_berkas(self.o4, "tanah_terdaftar")
        self.b5 = self.buat_berkas(self.o5, "alih_media")

        # Tiga pergerakan pada 2026-08-10.
        self.tahapan.pindah(self.b1, "pengukuran", "masuk", "2026-08-10", None,
                            self.pengguna_id)
        self.tahapan.pindah(self.b2, "pengukuran", "masuk", "2026-08-10", None,
                            self.pengguna_id)
        self.tahapan.pindah(self.b3, "panitia_a", "masuk", "2026-08-10", None,
                            self.pengguna_id)
        # Satu pergerakan di tanggal lain.
        self.tahapan.pindah(self.b4, "pengukuran", "masuk", "2026-08-11", None,
                            self.pengguna_id)

    # 1
    def test_rekap_harian_hanya_menghitung_tanggal_yang_diminta(self):
        hasil = self.rekap.rekap_harian("2026-08-10")
        self.assertEqual(hasil["total"], 3)
        jumlah = {(b["kode"], b["aksi"]): b["jumlah"] for b in hasil["per_tahapan"]}
        self.assertEqual(jumlah[("pengukuran", "masuk")], 2)
        self.assertEqual(jumlah[("panitia_a", "masuk")], 1)

    def test_rekap_harian_per_wilayah(self):
        hasil = self.rekap.rekap_harian("2026-08-10")
        per = {b["wilayah"]: b["jumlah"] for b in hasil["per_wilayah"]}
        self.assertEqual(per["Wilayah I"], 3)

    def test_rekap_harian_tanggal_kosong(self):
        self.assertEqual(self.rekap.rekap_harian("2020-01-01")["total"], 0)

    # 2
    def test_rekap_tahapan_menghitung_posisi_sekarang(self):
        hasil = self.rekap.rekap_tahapan()
        aktif = {b["kode"]: b["aktif"] for b in hasil["corong"]}
        self.assertEqual(aktif["permohonan"], 1)   # b5 belum bergerak
        self.assertEqual(aktif["pengukuran"], 3)   # b1, b2, b4
        self.assertEqual(aktif["panitia_a"], 1)    # b3
        self.assertEqual(hasil["total_aktif"], 5)

    def test_rekap_tahapan_menampilkan_tahapan_kosong(self):
        kode = [b["kode"] for b in self.rekap.rekap_tahapan()["corong"]]
        self.assertIn("penyerahan", kode)

    # 3
    def test_rekap_potensi_kecamatan(self):
        baris = {b["kecamatan"]: b for b in self.rekap.rekap_potensi_kecamatan()}
        self.assertEqual(baris["Suwawa"]["total"], 2)
        self.assertEqual(baris["Suwawa"]["baru"], 1)      # o1: tanpa hak & isbat
        self.assertEqual(baris["Suwawa"]["ada_hak"], 1)   # o2: punya tipe_hak
        self.assertEqual(baris["Bulango Ulu"]["isbat"], 1)
        self.assertEqual(baris["Bulawa"]["total"], 0)     # kecamatan tanpa objek tetap muncul

    # 4
    def test_rekap_wilayah(self):
        baris = {b["wilayah"]: b for b in self.rekap.rekap_wilayah()}
        self.assertEqual(baris["Wilayah I"]["potensi"], 3)
        self.assertEqual(baris["Wilayah III"]["potensi"], 2)
        self.assertEqual(baris["Wilayah III"]["sudah"], 1)
        self.assertEqual(baris["Wilayah II"]["potensi"], 0)

    # 5
    def test_rekap_tipologi(self):
        baris = {b["kode"]: b["jumlah"] for b in self.rekap.rekap_tipologi()}
        self.assertEqual(baris["T1"], 1)
        self.assertEqual(baris["T6"], 2)
        self.assertEqual(baris["T7"], 0)
        self.assertEqual(self.rekap.tipologi_kosong(), 1)

    def test_rekap_tipologi_disaring_kecamatan(self):
        kec = self.db.ambil_satu("SELECT id FROM kecamatan WHERE nama = 'Suwawa'")
        baris = {b["kode"]: b["jumlah"] for b in self.rekap.rekap_tipologi(kec["id"])}
        self.assertEqual(baris["T1"], 1)
        self.assertEqual(baris["T6"], 1)

    # 6
    def test_rekap_penyerahan_dipivot_per_jenis(self):
        for kode in ("panitia_a", "yuridis", "penerbitan", "penyerahan"):
            self.tahapan.pindah(self.b1, kode, "masuk", "2026-08-20", None,
                                self.pengguna_id)
        self.db.jalankan("UPDATE berkas SET target_penyerahan = ? WHERE id = ?",
                         ("2026-08-24", self.b1))
        hasil = self.rekap.rekap_penyerahan("2026-08-24")
        self.assertEqual(hasil["total"], 1)
        self.assertEqual(hasil["pivot"]["Wilayah I"]["pertama_kali"], 1)
        self.assertEqual(hasil["pivot"]["Wilayah I"]["alih_media"], 0)

    def test_rekap_penyerahan_tanggal_tanpa_berkas(self):
        self.assertEqual(self.rekap.rekap_penyerahan("2027-12-31")["total"], 0)

    # 7
    def test_berkas_macet(self):
        # Semua fixture bergerak terakhir pada 2026-08-10/11, jauh di masa lalu
        # relatif terhadap 'now', jadi semuanya melewati batas 14 hari.
        macet = self.rekap.berkas_macet(14)
        self.assertEqual(len(macet), 5)
        self.assertGreaterEqual(macet[0]["umur_hari"], macet[-1]["umur_hari"])

    def test_berkas_macet_hormati_sla_tahapan(self):
        self.db.jalankan("UPDATE tahapan SET sla_hari = 100000 WHERE kode = 'pengukuran'")
        kode = {b["tahapan_nama"] for b in self.rekap.berkas_macet(14)}
        self.assertNotIn("Pengukuran", kode)

    def test_berkas_selesai_tidak_dihitung_macet(self):
        self.db.jalankan("UPDATE berkas SET status = 'selesai' WHERE id = ?", (self.b1,))
        self.assertEqual(len(self.rekap.berkas_macet(14)), 4)

    # filter wilayah untuk peran terbatas
    def test_korwil_hanya_melihat_wilayahnya(self):
        wil1 = self.db.ambil_satu("SELECT id FROM wilayah WHERE nama = 'Wilayah I'")
        korwil = {"peran": "korwil", "wilayah_id": wil1["id"]}
        hasil = self.rekap.rekap_harian("2026-08-10", pengguna=korwil)
        self.assertEqual(hasil["total"], 3)

        wil3 = self.db.ambil_satu("SELECT id FROM wilayah WHERE nama = 'Wilayah III'")
        korwil3 = {"peran": "korwil", "wilayah_id": wil3["id"]}
        self.assertEqual(self.rekap.rekap_harian("2026-08-10", pengguna=korwil3)["total"], 0)

    def test_ringkasan_dashboard(self):
        ringkasan = self.rekap.ringkasan_dashboard()
        self.assertEqual(ringkasan["objek"]["total"], 5)
        self.assertEqual(ringkasan["berkas_aktif"], 5)


if __name__ == "__main__":
    unittest.main()
