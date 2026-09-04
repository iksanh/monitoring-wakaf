"""Penyaring prioritas di dashboard dan seluruh halaman rekap.

Termasuk satu tes regresi untuk corong tahapan, yang dulu mengabaikan filter
karena penyaringnya ditaruh di klausa JOIN sebuah LEFT JOIN.
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.bantu import BasisTes  # noqa: E402


class TesRekapPrioritas(BasisTes):
    def setUp(self):
        super().setUp()
        from services import kendali, rekap, tahapan
        self.rekap = rekap
        self.kendali = kendali
        self.tahapan = tahapan
        self.pengguna_id = self.buat_pengguna()

        # Suwawa = Wilayah I, Kabila = Wilayah III.
        self.penting = self.buat_objek("Masjid Prioritas", "Suwawa", tipologi="T1")
        self.biasa = self.buat_objek("Masjid Biasa", "Suwawa", tipologi="T6")
        self.jauh = self.buat_objek("Masjid Kabila", "Kabila", tipologi="T6")
        self.db.jalankan("UPDATE objek_wakaf SET is_prioritas = 1 WHERE id = ?",
                         (self.penting,))

        self.b_penting = self.buat_berkas(self.penting)
        self.b_biasa = self.buat_berkas(self.biasa)
        self.b_jauh = self.buat_berkas(self.jauh)
        for bid in (self.b_penting, self.b_biasa, self.b_jauh):
            # Tanggal di masa lalu supaya ketiganya terhitung macet.
            self.tahapan.pindah(bid, "pengukuran", "masuk", "2026-08-10", None,
                                self.pengguna_id)

    # ---- ringkasan dashboard ----
    def test_ringkasan_dashboard_disaring(self):
        self.assertEqual(
            self.rekap.ringkasan_dashboard(prioritas="ya")["objek"]["total"], 1)
        self.assertEqual(
            self.rekap.ringkasan_dashboard(prioritas="tidak")["objek"]["total"], 2)
        self.assertEqual(self.rekap.ringkasan_dashboard()["objek"]["total"], 3)

    def test_berkas_aktif_dashboard_disaring(self):
        self.assertEqual(
            self.rekap.ringkasan_dashboard(prioritas="ya")["berkas_aktif"], 1)
        self.assertEqual(self.rekap.ringkasan_dashboard()["berkas_aktif"], 3)

    # ---- corong tahapan (regresi) ----
    def test_corong_menghormati_penyaring_prioritas(self):
        self.assertEqual(self.rekap.rekap_tahapan(prioritas="ya")["total_aktif"], 1)
        self.assertEqual(self.rekap.rekap_tahapan(prioritas="tidak")["total_aktif"], 2)
        self.assertEqual(self.rekap.rekap_tahapan()["total_aktif"], 3)

    def test_corong_menghormati_penyaring_wilayah(self):
        """Regresi: dulu corong mengabaikan filter wilayah sepenuhnya."""
        wil1 = self.db.ambil_nilai("SELECT id FROM wilayah WHERE nama = 'Wilayah I'")
        wil2 = self.db.ambil_nilai("SELECT id FROM wilayah WHERE nama = 'Wilayah II'")
        self.assertEqual(self.rekap.rekap_tahapan(wilayah_id=wil1)["total_aktif"], 2)
        self.assertEqual(self.rekap.rekap_tahapan(wilayah_id=wil2)["total_aktif"], 0)

    def test_corong_tetap_menampilkan_tahapan_kosong_saat_disaring(self):
        corong = self.rekap.rekap_tahapan(prioritas="ya")["corong"]
        self.assertIn("penyerahan", [t["kode"] for t in corong])
        self.assertEqual(len(corong),
                         self.db.ambil_nilai("SELECT COUNT(*) FROM tahapan"))

    def test_corong_korwil_tetap_dibatasi_wilayahnya(self):
        wil3 = self.db.ambil_nilai("SELECT id FROM wilayah WHERE nama = 'Wilayah III'")
        korwil = {"peran": "korwil", "wilayah_id": wil3}
        self.assertEqual(self.rekap.rekap_tahapan(pengguna=korwil)["total_aktif"], 1)

    # ---- rekap harian ----
    def test_rekap_harian_disaring(self):
        self.assertEqual(
            self.rekap.rekap_harian("2026-08-10", prioritas="ya")["total"], 1)
        self.assertEqual(
            self.rekap.rekap_harian("2026-08-10", prioritas="tidak")["total"], 2)
        self.assertEqual(self.rekap.rekap_harian("2026-08-10")["total"], 3)

    # ---- potensi & wilayah ----
    def test_potensi_kecamatan_disaring(self):
        baris = {b["kecamatan"]: b
                 for b in self.rekap.rekap_potensi_kecamatan(prioritas="ya")}
        self.assertEqual(baris["Suwawa"]["total"], 1)
        self.assertEqual(baris["Kabila"]["total"], 0)

    def test_potensi_tetap_menampilkan_kecamatan_kosong(self):
        baris = self.rekap.rekap_potensi_kecamatan(prioritas="ya")
        self.assertEqual(len(baris),
                         self.db.ambil_nilai("SELECT COUNT(*) FROM kecamatan"))

    def test_rekap_wilayah_disaring(self):
        baris = {b["wilayah"]: b for b in self.rekap.rekap_wilayah(prioritas="ya")}
        self.assertEqual(baris["Wilayah I"]["potensi"], 1)
        self.assertEqual(baris["Wilayah III"]["potensi"], 0)
        # semua wilayah tetap muncul
        self.assertEqual(len(baris),
                         self.db.ambil_nilai("SELECT COUNT(*) FROM wilayah"))

    # ---- tipologi ----
    def test_rekap_tipologi_disaring(self):
        baris = {b["kode"]: b["jumlah"]
                 for b in self.rekap.rekap_tipologi(prioritas="ya")}
        self.assertEqual(baris["T1"], 1)
        self.assertEqual(baris["T6"], 0)
        self.assertEqual(len(baris),
                         self.db.ambil_nilai("SELECT COUNT(*) FROM tipologi"))

    def test_tipologi_kosong_disaring(self):
        tanpa = self.buat_objek("Masjid Tanpa Tipologi", "Suwawa")
        self.assertEqual(self.rekap.tipologi_kosong(prioritas="ya"), 0)
        self.db.jalankan("UPDATE objek_wakaf SET is_prioritas = 1 WHERE id = ?",
                         (tanpa,))
        self.assertEqual(self.rekap.tipologi_kosong(prioritas="ya"), 1)
        self.assertEqual(self.rekap.tipologi_kosong(), 1)

    # ---- penyerahan & macet ----
    def test_rekap_penyerahan_disaring(self):
        for bid in (self.b_penting, self.b_biasa):
            for kode in ("panitia_a", "yuridis", "penerbitan", "penyerahan"):
                self.tahapan.pindah(bid, kode, "masuk", "2026-09-20", None,
                                    self.pengguna_id)
            self.db.jalankan("UPDATE berkas SET target_penyerahan = ? WHERE id = ?",
                             ("2026-09-24", bid))
        self.assertEqual(
            self.rekap.rekap_penyerahan("2026-09-24", prioritas="ya")["total"], 1)
        self.assertEqual(self.rekap.rekap_penyerahan("2026-09-24")["total"], 2)

    def test_berkas_macet_disaring(self):
        self.assertEqual(len(self.rekap.berkas_macet(14, prioritas="ya")), 1)
        self.assertEqual(len(self.rekap.berkas_macet(14, prioritas="tidak")), 2)
        self.assertEqual(len(self.rekap.berkas_macet(14)), 3)

    # ---- papan kendali ----
    def test_papan_kendali_disaring(self):
        for nilai, harap in (("ya", 1), ("tidak", 2), (None, 3)):
            papan = self.kendali.papan_kendali("2026-09", prioritas=nilai)
            self.assertEqual(papan["total"]["total_capaian"], harap, nilai)
            self.assertEqual(len(papan["baris"]),
                             self.db.ambil_nilai("SELECT COUNT(*) FROM wilayah"))

    # ---- nilai penyaring yang tidak dikenal ----
    def test_nilai_ngawur_tidak_menyaring_apa_pun(self):
        for nilai in ("ngawur", "", "1", "YA"):
            self.assertEqual(
                self.rekap.ringkasan_dashboard(prioritas=nilai)["objek"]["total"], 3,
                nilai)
            self.assertEqual(self.rekap.rekap_tahapan(prioritas=nilai)["total_aktif"],
                             3, nilai)

    # ---- filter wilayah tetap di atas filter prioritas ----
    def test_korwil_tidak_bisa_menembus_wilayah_lewat_prioritas(self):
        wil3 = self.db.ambil_nilai("SELECT id FROM wilayah WHERE nama = 'Wilayah III'")
        korwil = {"peran": "korwil", "wilayah_id": wil3}
        # objek prioritas ada di Wilayah I, korwil III tidak boleh melihatnya
        self.assertEqual(
            self.rekap.ringkasan_dashboard(korwil, "ya")["objek"]["total"], 0)
        self.assertEqual(
            self.rekap.rekap_harian("2026-08-10", pengguna=korwil,
                                    prioritas="ya")["total"], 0)
        self.assertEqual(
            self.kendali.papan_kendali("2026-09", pengguna=korwil,
                                       prioritas="ya")["total"]["total_capaian"], 0)


if __name__ == "__main__":
    unittest.main()
