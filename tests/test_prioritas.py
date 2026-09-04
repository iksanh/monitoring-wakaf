"""Tes penanda berkas prioritas: tersimpan, tersaring, terurut, dan terbawa
dari objek ke berkas."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.bantu import BasisTes  # noqa: E402


class TesPrioritas(BasisTes):
    def setUp(self):
        super().setUp()
        from services import berkas, objek
        self.svc_objek = objek
        self.svc_berkas = berkas
        self.pengguna_id = self.buat_pengguna()
        self.admin = {"peran": "admin", "wilayah_id": None}

        # Nama sengaja dibuat agar urutan abjadnya berlawanan dengan prioritas.
        self.biasa = self.buat_objek("Masjid Awal", "Suwawa")
        self.penting = self.buat_objek("Masjid Zulfikar", "Suwawa")
        self.db.jalankan("UPDATE objek_wakaf SET is_prioritas = 1 WHERE id = ?",
                         (self.penting,))
        self.b_biasa = self.buat_berkas(self.biasa)
        self.b_penting = self.buat_berkas(self.penting)

    def _isi_form(self, **ubah):
        """Isian form lengkap — kolom NOT NULL harus ikut, sama seperti route."""
        dasar = {
            "nama_objek": "Masjid Uji Form",
            "kecamatan_id": self.db.ambil_nilai(
                "SELECT id FROM kecamatan WHERE nama = 'Suwawa'"),
            "status_sertipikat": "belum",
            "is_potensi": 1,
            "perlu_isbat": 0,
            "is_prioritas": 0,
        }
        dasar.update(ubah)
        return dasar

    # ---- bawaan ----
    def test_bawaan_bukan_prioritas(self):
        objek = self.svc_objek.ambil(self.biasa)
        self.assertEqual(objek["is_prioritas"], 0)

    def test_kolom_ikut_disimpan_saat_buat(self):
        oid = self.svc_objek.buat(self._isi_form(is_prioritas=1), self.pengguna_id)
        self.assertEqual(self.svc_objek.ambil(oid)["is_prioritas"], 1)

    def test_kolom_ikut_disimpan_saat_ubah(self):
        self.svc_objek.ubah(self.biasa,
                            self._isi_form(nama_objek="Masjid Awal", is_prioritas=1),
                            self.pengguna_id)
        self.assertEqual(self.svc_objek.ambil(self.biasa)["is_prioritas"], 1)

    def test_prioritas_bisa_dicabut_lagi(self):
        self.svc_objek.ubah(self.penting,
                            self._isi_form(nama_objek="Masjid Zulfikar",
                                           is_prioritas=0),
                            self.pengguna_id)
        self.assertEqual(self.svc_objek.ambil(self.penting)["is_prioritas"], 0)

    # ---- filter di daftar objek ----
    def test_saring_objek_hanya_prioritas(self):
        hasil = self.svc_objek.cari(self.admin, {"prioritas": "ya"})
        self.assertEqual(hasil["total"], 1)
        self.assertEqual(hasil["baris"][0]["id"], self.penting)

    def test_saring_objek_bukan_prioritas(self):
        hasil = self.svc_objek.cari(self.admin, {"prioritas": "tidak"})
        self.assertEqual([b["id"] for b in hasil["baris"]], [self.biasa])

    def test_saring_objek_kosong_menampilkan_semua(self):
        self.assertEqual(self.svc_objek.cari(self.admin, {})["total"], 2)
        self.assertEqual(
            self.svc_objek.cari(self.admin, {"prioritas": None})["total"], 2)

    def test_nilai_saring_ngawur_tidak_menyaring(self):
        self.assertEqual(
            self.svc_objek.cari(self.admin, {"prioritas": "ngawur"})["total"], 2)

    def test_saring_prioritas_digabung_filter_lain(self):
        hasil = self.svc_objek.cari(self.admin, {"prioritas": "ya", "q": "Awal"})
        self.assertEqual(hasil["total"], 0)   # Masjid Awal bukan prioritas

    # ---- urutan ----
    def test_prioritas_naik_ke_atas_daftar_objek(self):
        baris = self.svc_objek.cari(self.admin, {})["baris"]
        self.assertEqual(baris[0]["id"], self.penting)   # walau abjadnya belakangan

    def test_prioritas_naik_ke_atas_daftar_berkas(self):
        baris = self.svc_berkas.cari(self.admin, {})["baris"]
        self.assertEqual(baris[0]["id"], self.b_penting)

    # ---- terbawa ke berkas ----
    def test_berkas_membawa_penanda_objeknya(self):
        self.assertEqual(self.svc_berkas.ambil(self.b_penting)["is_prioritas"], 1)
        self.assertEqual(self.svc_berkas.ambil(self.b_biasa)["is_prioritas"], 0)

    def test_saring_berkas_hanya_prioritas(self):
        hasil = self.svc_berkas.cari(self.admin, {"prioritas": "ya"})
        self.assertEqual(hasil["total"], 1)
        self.assertEqual(hasil["baris"][0]["id"], self.b_penting)

    def test_saring_berkas_bukan_prioritas(self):
        hasil = self.svc_berkas.cari(self.admin, {"prioritas": "tidak"})
        self.assertEqual([b["id"] for b in hasil["baris"]], [self.b_biasa])

    def test_penanda_berkas_ikut_berubah_saat_objek_diubah(self):
        """Penanda tinggal di objek, jadi berkas tidak perlu disentuh."""
        self.db.jalankan("UPDATE objek_wakaf SET is_prioritas = 1 WHERE id = ?",
                         (self.biasa,))
        self.assertEqual(self.svc_berkas.ambil(self.b_biasa)["is_prioritas"], 1)
        self.assertEqual(self.svc_berkas.cari(self.admin, {"prioritas": "ya"})["total"], 2)

    # ---- filter wilayah tetap berlaku ----
    def test_korwil_luar_wilayah_tidak_melihat_prioritas_orang_lain(self):
        wil3 = self.db.ambil_satu("SELECT id FROM wilayah WHERE nama = 'Wilayah III'")
        korwil = {"peran": "korwil", "wilayah_id": wil3["id"]}
        # Suwawa ada di Wilayah I, jadi korwil III tidak boleh melihatnya.
        self.assertEqual(
            self.svc_objek.cari(korwil, {"prioritas": "ya"})["total"], 0)
        self.assertEqual(
            self.svc_berkas.cari(korwil, {"prioritas": "ya"})["total"], 0)


if __name__ == "__main__":
    unittest.main()
