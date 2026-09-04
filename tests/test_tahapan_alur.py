"""Tes alur tahapan: percabangan isbat, aksi 'selesai' yang otomatis maju,
dan pilihan mundur yang dibatasi ke tahapan yang sudah dilewati."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.bantu import BasisTes  # noqa: E402


class TesAlurTahapan(BasisTes):
    def setUp(self):
        super().setUp()
        from services import tahapan
        self.tahapan = tahapan
        self.pengguna_id = self.buat_pengguna()
        self.objek_id = self.buat_objek()
        self.berkas_id = self.buat_berkas(self.objek_id)

    def _berkas(self, berkas_id=None):
        return self.db.ambil_satu("SELECT * FROM berkas WHERE id = ?",
                                  (berkas_id or self.berkas_id,))

    def _riwayat(self, berkas_id=None):
        return self.db.ambil_semua(
            "SELECT * FROM riwayat_tahapan WHERE berkas_id = ? ORDER BY id",
            (berkas_id or self.berkas_id,))

    def _berkas_jenis_lain(self):
        objek = self.buat_objek("Masjid Lain", "Kabila")
        return self.buat_berkas(objek, jenis="alih_media")

    # ---- bentuk alur ----
    def test_alur_lurus_sama_untuk_semua_jenis(self):
        biasa = [t["kode"] for t in self.tahapan.alur(self._berkas())]
        lain = [t["kode"]
                for t in self.tahapan.alur(self._berkas(self._berkas_jenis_lain()))]
        self.assertEqual(biasa, lain)
        self.assertEqual(biasa, ["permohonan", "pengukuran", "panitia_a",
                                 "yuridis", "penerbitan", "penyerahan"])

    def test_pra_daftar_tidak_pernah_jadi_tujuan_maju(self):
        self.assertNotEqual(
            self.tahapan.berikutnya("pra_daftar")["kode"], "pra_daftar")
        alur = self.tahapan.alur(self._berkas())
        self.assertNotIn("pra_daftar", [t["kode"] for t in alur])

    def test_pra_daftar_muncul_kalau_berkas_memang_di_sana(self):
        self.db.jalankan("UPDATE berkas SET tahapan_kode = 'pra_daftar' WHERE id = ?",
                         (self.berkas_id,))
        alur = self.tahapan.alur(self._berkas())
        self.assertEqual(alur[0]["kode"], "pra_daftar")
        self.assertEqual(alur[0]["posisi"], "kini")

    def test_penanda_posisi_di_alur(self):
        self.tahapan.pindah(self.berkas_id, "yuridis", "masuk", "2026-09-05",
                            None, self.pengguna_id)
        posisi = {t["kode"]: t["posisi"] for t in self.tahapan.alur(self._berkas())}
        self.assertEqual(posisi["pengukuran"], "lewat")
        self.assertEqual(posisi["yuridis"], "kini")
        self.assertEqual(posisi["penerbitan"], "depan")

    # ---- aksi 'selesai' otomatis maju ----
    def test_selesai_menulis_dua_baris_dan_memajukan(self):
        self.tahapan.pindah(self.berkas_id, "pengukuran", "masuk", "2026-09-02",
                            None, self.pengguna_id)
        sebelum = len(self._riwayat())
        self.tahapan.pindah(self.berkas_id, "pengukuran", "selesai", "2026-09-05",
                            "ukur beres", self.pengguna_id)

        riwayat = self._riwayat()
        self.assertEqual(len(riwayat), sebelum + 2)
        self.assertEqual((riwayat[-2]["tahapan_kode"], riwayat[-2]["aksi"]),
                         ("pengukuran", "selesai"))
        self.assertEqual((riwayat[-1]["tahapan_kode"], riwayat[-1]["aksi"]),
                         ("panitia_a", "masuk"))
        self.assertEqual(riwayat[-1]["tanggal"], "2026-09-05")
        self.assertEqual(self._berkas()["tahapan_kode"], "panitia_a")

    def test_catatan_menempel_di_baris_selesai_bukan_baris_masuk(self):
        self.tahapan.pindah(self.berkas_id, "pengukuran", "selesai", "2026-09-05",
                            "ukur beres", self.pengguna_id)
        riwayat = self._riwayat()
        self.assertEqual(riwayat[-2]["catatan"], "ukur beres")
        self.assertIsNone(riwayat[-1]["catatan"])

    def test_selesai_dari_permohonan_jenis_lain_juga_masuk_pengukuran(self):
        berkas_id = self._berkas_jenis_lain()
        self.tahapan.pindah(berkas_id, "permohonan", "selesai", "2026-09-05",
                            None, self.pengguna_id)
        self.assertEqual(self._berkas(berkas_id)["tahapan_kode"], "pengukuran")

    def test_selesai_dari_permohonan_biasa_masuk_pengukuran(self):
        self.tahapan.pindah(self.berkas_id, "permohonan", "selesai", "2026-09-05",
                            None, self.pengguna_id)
        self.assertEqual(self._berkas()["tahapan_kode"], "pengukuran")

    def test_selesai_di_tahapan_terakhir_menutup_berkas(self):
        self.tahapan.pindah(self.berkas_id, "penyerahan", "masuk", "2026-09-20",
                            None, self.pengguna_id)
        sebelum = len(self._riwayat())
        self.tahapan.pindah(self.berkas_id, "penyerahan", "selesai", "2026-09-24",
                            "diserahkan", self.pengguna_id)
        berkas = self._berkas()
        self.assertEqual(berkas["status"], "selesai")
        self.assertEqual(berkas["tanggal_selesai"], "2026-09-24")
        self.assertEqual(berkas["tahapan_kode"], "penyerahan")
        # tidak ada baris 'masuk' tambahan karena tidak ada tahapan sesudahnya
        self.assertEqual(len(self._riwayat()), sebelum + 1)

    def test_selesai_gagal_tidak_meninggalkan_baris_separuh(self):
        sebelum = len(self._riwayat())
        with self.assertRaises(self.tahapan.PindahDitolak):
            self.tahapan.pindah(self.berkas_id, "tahapan_hantu", "selesai",
                                "2026-09-05", None, self.pengguna_id)
        self.assertEqual(len(self._riwayat()), sebelum)

    def test_lama_tiap_tahapan_bisa_dihitung_dari_riwayat(self):
        """Alasan utama memilih dua baris riwayat."""
        self.tahapan.pindah(self.berkas_id, "pengukuran", "masuk", "2026-09-02",
                            None, self.pengguna_id)
        self.tahapan.pindah(self.berkas_id, "pengukuran", "selesai", "2026-09-05",
                            None, self.pengguna_id)
        baris = [r for r in self._riwayat() if r["tahapan_kode"] == "pengukuran"]
        mulai = next(r["tanggal"] for r in baris if r["aksi"] == "masuk")
        usai = next(r["tanggal"] for r in baris if r["aksi"] == "selesai")
        self.assertEqual((mulai, usai), ("2026-09-02", "2026-09-05"))

    # ---- pilihan mundur ----
    def test_mundur_hanya_menawarkan_tahapan_yang_sudah_lewat(self):
        self.tahapan.pindah(self.berkas_id, "yuridis", "masuk", "2026-09-05",
                            None, self.pengguna_id)
        kode = [t["kode"] for t in self.tahapan.sudah_dilewati(self._berkas())]
        self.assertEqual(kode, ["permohonan", "pengukuran", "panitia_a"])
        self.assertNotIn("yuridis", kode)
        self.assertNotIn("penerbitan", kode)

    def test_mundur_kosong_di_tahapan_pertama(self):
        self.assertEqual(self.tahapan.sudah_dilewati(self._berkas()), [])

    # ---- tujuan_akhir, dipakai route untuk memeriksa ceklis ----
    def test_tujuan_akhir_selesai_adalah_tahapan_berikutnya(self):
        berkas = self._berkas()
        self.assertEqual(
            self.tahapan.tujuan_akhir(berkas, "permohonan", "selesai"), "pengukuran")

    def test_tujuan_akhir_kendala_tetap_di_tempat(self):
        berkas = self._berkas()
        self.assertEqual(
            self.tahapan.tujuan_akhir(berkas, "permohonan", "kendala"), "permohonan")

    def test_tujuan_akhir_masuk_sama_dengan_yang_diminta(self):
        berkas = self._berkas()
        self.assertEqual(
            self.tahapan.tujuan_akhir(berkas, "yuridis", "masuk"), "yuridis")

    def test_ceklis_diperiksa_terhadap_tahapan_tujuan(self):
        """Menyelesaikan 'permohonan' berarti masuk 'pengukuran' — gerbang ceklis
        harus ikut menyala di situ, bukan diam karena yang dikirim 'permohonan'."""
        from services import berkas as svc_berkas, ceklis
        # Lewat service supaya ceklis syaratnya ikut tersalin dan masih kosong.
        objek = self.buat_objek("Masjid Ceklis", "Kabila")
        berkas_id = svc_berkas.buat(
            {"objek_wakaf_id": objek, "jenis_permohonan_kode": "pertama_kali",
             "tanggal_daftar": "2026-09-01"}, self.pengguna_id)
        berkas = self._berkas(berkas_id)

        tujuan = self.tahapan.tujuan_akhir(berkas, "permohonan", "selesai")
        self.assertEqual(tujuan, ceklis.TAHAPAN_BUTUH_SYARAT)
        self.assertIsNotNone(ceklis.halangan_pindah(berkas_id, tujuan))
        # Sedangkan tahapan yang dikirim form ('permohonan') tidak berpagar —
        # inilah yang dulu membuat gerbang ceklis terlewat.
        self.assertIsNone(ceklis.halangan_pindah(berkas_id, "permohonan"))


if __name__ == "__main__":
    unittest.main()
