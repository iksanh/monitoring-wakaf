"""Tes papan kendali korwil — terutama dua kolom turunan yang mudah salah:
Total Capaian (jumlah lima ember saling lepas) dan Selisih (alih media - tarikan)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.bantu import BasisTes  # noqa: E402


class TesKendali(BasisTes):
    def setUp(self):
        super().setUp()
        from services import berkas as svc_berkas, berkas_aksi as svc_aksi, kendali
        self.kendali = kendali
        self.svc_berkas = svc_berkas
        self.svc_aksi = svc_aksi
        self.pengguna_id = self.buat_pengguna()

        # Suwawa = Wilayah I, Kabila = Wilayah III.
        self.o = [self.buat_objek(f"Masjid {i}", "Suwawa") for i in range(6)]
        self.o3 = self.buat_objek("Masjid Kabila", "Kabila")

        # Objek ke-5 harus lewat isbat dulu — berkasnya jadi kolom Penetapan.
        self.db.jalankan("UPDATE objek_wakaf SET perlu_isbat = 1 WHERE id = ?",
                         (self.o[4],))

        # Wilayah I: 1 selesai, 1 proses, 2 akan didaftar, 1 tunggu penetapan,
        # 1 alih media.
        self.selesai = self.buat_berkas(self.o[0], "pertama_kali", "penyerahan")
        self.tandai_selesai(self.selesai, "2026-09-20")
        self.buat_berkas(self.o[1], "pertama_kali", "pengukuran")
        self.buat_berkas(self.o[2], "pertama_kali", "pra_daftar")
        self.buat_berkas(self.o[3], "tanah_terdaftar", "pra_daftar")
        self.isbat = self.buat_berkas(self.o[4], "pertama_kali", "pengukuran")
        self.am = self.buat_berkas(self.o[5], "alih_media", "penyerahan")
        self.tandai_selesai(self.am, "2026-09-21")

        # Wilayah III: satu berkas dalam proses saja.
        self.buat_berkas(self.o3, "pertama_kali", "yuridis")

    def tandai_selesai(self, berkas_id, tanggal):
        self.db.jalankan(
            "UPDATE berkas SET status = 'selesai', tanggal_selesai = ? WHERE id = ?",
            (tanggal, berkas_id))

    def tarik(self, berkas_id, tanggal="2026-09-15"):
        self.db.jalankan(
            "UPDATE berkas SET catatan_ditarik = 1, tanggal_ditarik = ? WHERE id = ?",
            (tanggal, berkas_id))

    # ---- periode ----
    def test_periode_sah_menolak_nilai_ngawur(self):
        self.assertEqual(self.kendali.periode_sah("2026-09"), "2026-09")
        self.assertEqual(self.kendali.periode_sah("2026-13"),
                         self.kendali.periode_sekarang())
        self.assertEqual(self.kendali.periode_sah(None),
                         self.kendali.periode_sekarang())
        self.assertEqual(self.kendali.periode_sah("2026-09 OR 1=1"),
                         self.kendali.periode_sekarang())

    def test_daftar_periode_mundur_dua_belas_bulan(self):
        daftar = self.kendali.daftar_periode()
        self.assertEqual(len(daftar), 12)
        self.assertEqual(daftar[0]["kode"], self.kendali.periode_sekarang())
        self.assertEqual(len({p["kode"] for p in daftar}), 12)

    def test_label_periode_bahasa_indonesia(self):
        self.assertEqual(self.kendali.label_periode("2026-09"), "September 2026")

    # ---- kolom ----
    def test_semua_wilayah_muncul_walau_kosong(self):
        papan = self.kendali.papan_kendali("2026-09")
        nama = [b["wilayah"] for b in papan["baris"]]
        self.assertEqual(nama, ["Wilayah I", "Wilayah II", "Wilayah III",
                                "Wilayah IV", "Rutin"])

    def test_lima_ember_saling_lepas(self):
        w1 = self.kendali.papan_kendali("2026-09")["baris"][0]
        self.assertEqual(w1["selesai"], 1)
        self.assertEqual(w1["proses"], 1)
        self.assertEqual(w1["akan_didaftar"], 2)
        self.assertEqual(w1["penetapan"], 1)
        self.assertEqual(w1["alih_media"], 1)

    # ---- siap diserahkan ----
    def siapkan_serah(self, kecamatan="Suwawa"):
        """Berkas aktif yang sudah sampai tahapan terakhir 'penyerahan'."""
        o = self.buat_objek("Masjid Siap Serah", kecamatan)
        return self.buat_berkas(o, "pertama_kali", "penyerahan")

    def test_berkas_di_penyerahan_masuk_kolom_siap_serah(self):
        self.siapkan_serah()
        w1 = self.kendali.papan_kendali("2026-09")["baris"][0]
        self.assertEqual(w1["siap_serah"], 1)

    def test_siap_serah_tidak_lagi_dihitung_dalam_proses(self):
        # Inti perubahan: dulu berkas di penyerahan tenggelam di 'proses'.
        sebelum = self.kendali.papan_kendali("2026-09")["baris"][0]["proses"]
        self.siapkan_serah()
        w1 = self.kendali.papan_kendali("2026-09")["baris"][0]
        self.assertEqual(w1["proses"], sebelum)
        self.assertEqual(w1["siap_serah"], 1)

    def test_siap_serah_menambah_total_capaian(self):
        sebelum = self.kendali.papan_kendali("2026-09")["baris"][0]["total_capaian"]
        self.siapkan_serah()
        w1 = self.kendali.papan_kendali("2026-09")["baris"][0]
        self.assertEqual(w1["total_capaian"], sebelum + 1)
        self.assertEqual(w1["total_capaian"],
                         sum(w1[k] for k in self.kendali.KOLOM_CAPAIAN))

    def test_siap_serah_stok_tidak_terpengaruh_periode(self):
        # Alasan kolom ini dipisah dari Berkas Selesai: ia tidak punya
        # tanggal_selesai, jadi tidak bisa disaring bulan.
        self.siapkan_serah()
        for periode in ("2026-09", "2026-08", "2025-01"):
            self.assertEqual(
                self.kendali.papan_kendali(periode)["baris"][0]["siap_serah"], 1)

    def test_penyerahan_selesai_pindah_ke_kolom_selesai(self):
        berkas_id = self.siapkan_serah()
        self.tandai_selesai(berkas_id, "2026-09-25")
        w1 = self.kendali.papan_kendali("2026-09")["baris"][0]
        self.assertEqual(w1["siap_serah"], 0)
        self.assertEqual(w1["selesai"], 2)

    def test_siap_serah_yang_masih_tunggu_penetapan_tetap_di_kolom_4(self):
        # Ember harus tetap saling lepas: kolom penetapan menang.
        o = self.buat_objek("Masjid Isbat Serah", "Suwawa", perlu_isbat=1)
        self.buat_berkas(o, "pertama_kali", "penyerahan")
        w1 = self.kendali.papan_kendali("2026-09")["baris"][0]
        self.assertEqual(w1["siap_serah"], 0)
        self.assertEqual(w1["penetapan"], 2)

    def test_enam_ember_tidak_pernah_dobel(self):
        self.siapkan_serah()
        w1 = self.kendali.papan_kendali("2026-09")["baris"][0]
        self.assertEqual(w1["total_capaian"],
                         sum(w1[k] for k in self.kendali.KOLOM_CAPAIAN))
        # Tujuh objek Wilayah I, tujuh berkas, semuanya terhitung tepat sekali.
        self.assertEqual(w1["total_capaian"], 7)

    # ---- potensi ----
    def test_potensi_menghitung_seluruh_objek_wilayah(self):
        # Wilayah I punya 6 objek, semuanya sudah berberkas.
        w1 = self.kendali.papan_kendali("2026-09")["baris"][0]
        self.assertEqual(w1["potensi"], 6)

    def test_potensi_menghitung_objek_yang_belum_punya_berkas(self):
        # Inti kolom ini: potensi adalah basis kerja, bukan berkas.
        self.buat_objek("Masjid Tanpa Berkas", "Suwawa")
        w1 = self.kendali.papan_kendali("2026-09")["baris"][0]
        self.assertEqual(w1["potensi"], 7)
        self.assertEqual(w1["total_capaian"], 6)

    def test_potensi_tidak_dobel_saat_objek_punya_berkas_batal(self):
        # Indeks unik migrasi 006 hanya mengikat berkas non-'batal', jadi satu
        # objek bisa punya beberapa baris berkas. Tanpa COUNT DISTINCT objek ini
        # akan terhitung dua kali.
        self.svc_aksi.batalkan(self.selesai, "salah objek", self.pengguna_id)
        self.buat_berkas(self.o[0], "pertama_kali", "pengukuran")
        w1 = self.kendali.papan_kendali("2026-09")["baris"][0]
        self.assertEqual(w1["potensi"], 6)

    def test_potensi_tidak_masuk_total_capaian(self):
        self.assertNotIn("potensi", self.kendali.KOLOM_CAPAIAN)
        w1 = self.kendali.papan_kendali("2026-09")["baris"][0]
        self.assertEqual(w1["total_capaian"],
                         sum(w1[k] for k in self.kendali.KOLOM_CAPAIAN))

    def test_potensi_tidak_terpengaruh_periode(self):
        # Potensi itu stok, bukan arus: bulan mana pun angkanya sama.
        for periode in ("2026-09", "2026-08", "2025-01"):
            self.assertEqual(
                self.kendali.papan_kendali(periode)["baris"][0]["potensi"], 6)

    def test_potensi_baris_total_menjumlah_semua_wilayah(self):
        papan = self.kendali.papan_kendali("2026-09")
        self.assertEqual(papan["total"]["potensi"],
                         sum(b["potensi"] for b in papan["baris"]))
        self.assertEqual(papan["total"]["potensi"], 7)

    def test_potensi_ikut_filter_wilayah_korwil(self):
        wil3 = self.db.ambil_satu("SELECT id FROM wilayah WHERE nama = 'Wilayah III'")
        korwil = {"peran": "korwil", "wilayah_id": wil3["id"]}
        papan = self.kendali.papan_kendali("2026-09", pengguna=korwil)
        self.assertEqual(len(papan["baris"]), 1)
        self.assertEqual(papan["baris"][0]["potensi"], 1)

    def test_total_capaian_jumlah_lima_kolom(self):
        w1 = self.kendali.papan_kendali("2026-09")["baris"][0]
        self.assertEqual(w1["total_capaian"], 1 + 1 + 2 + 1 + 1)

    def test_alih_media_tidak_dihitung_sebagai_berkas_selesai(self):
        # Berkas alih media juga berstatus 'selesai' di bulan yang sama; kalau
        # ember tidak saling lepas, kolom 'selesai' jadi 2 dan total dobel.
        w1 = self.kendali.papan_kendali("2026-09")["baris"][0]
        self.assertEqual(w1["selesai"], 1)

    def test_kolom_arus_disaring_periode(self):
        w1 = self.kendali.papan_kendali("2026-08")["baris"][0]
        self.assertEqual(w1["selesai"], 0)
        self.assertEqual(w1["alih_media"], 0)
        # Kolom stok tidak ikut disaring periode.
        self.assertEqual(w1["proses"], 1)
        self.assertEqual(w1["akan_didaftar"], 2)

    # ---- ember penetapan pengadilan ----
    def tetapkan(self, berkas_id, tanggal="2026-09-10"):
        self.db.jalankan(
            """UPDATE berkas SET no_penetapan = '1/Pdt.P/2026/PA.Gtlo',
                                 tanggal_penetapan = ? WHERE id = ?""",
            (tanggal, berkas_id))

    def test_menunggu_penetapan_masuk_kolom_4_bukan_proses(self):
        w1 = self.kendali.papan_kendali("2026-09")["baris"][0]
        self.assertEqual(w1["penetapan"], 1)
        self.assertEqual(w1["proses"], 1)   # hanya berkas yang tidak perlu isbat

    def test_penetapan_terbit_memindahkan_ke_kolom_proses(self):
        """Begitu penetapan diisi, berkas keluar dari kolom 4 dan masuk kolom 2."""
        self.tetapkan(self.isbat)
        w1 = self.kendali.papan_kendali("2026-09")["baris"][0]
        self.assertEqual(w1["penetapan"], 0)
        self.assertEqual(w1["proses"], 2)
        # total capaian tidak berubah — cuma berpindah ember
        self.assertEqual(w1["total_capaian"], 1 + 2 + 2 + 0 + 1)

    def test_perlu_isbat_di_pra_daftar_tetap_di_kolom_4(self):
        self.db.jalankan("UPDATE berkas SET tahapan_kode = 'pra_daftar' WHERE id = ?",
                         (self.isbat,))
        w1 = self.kendali.papan_kendali("2026-09")["baris"][0]
        self.assertEqual(w1["penetapan"], 1)
        self.assertEqual(w1["akan_didaftar"], 2)   # tidak ikut terhitung di sini

    def test_berkas_isbat_yang_selesai_masuk_kolom_selesai(self):
        """Capaiannya tidak boleh menguap setelah perkaranya rampung."""
        self.tetapkan(self.isbat)
        self.tandai_selesai(self.isbat, "2026-09-22")
        w1 = self.kendali.papan_kendali("2026-09")["baris"][0]
        self.assertEqual(w1["penetapan"], 0)
        self.assertEqual(w1["selesai"], 2)
        self.assertEqual(w1["total_capaian"], 2 + 1 + 2 + 0 + 1)

    def test_objek_tanpa_perlu_isbat_tidak_pernah_masuk_kolom_4(self):
        self.db.jalankan("UPDATE objek_wakaf SET perlu_isbat = 0 WHERE id = ?",
                         (self.o[4],))
        w1 = self.kendali.papan_kendali("2026-09")["baris"][0]
        self.assertEqual(w1["penetapan"], 0)
        self.assertEqual(w1["proses"], 2)

    # ---- selisih ----
    def test_selisih_alih_media_dikurangi_tarikan(self):
        self.tarik(self.selesai)
        self.tarik(self.am)
        self.tarik(self.buat_berkas(self.buat_objek("Masjid X", "Suwawa"),
                                    "alih_media", "pengukuran"))
        w1 = self.kendali.papan_kendali("2026-09")["baris"][0]
        self.assertEqual(w1["catatan_ditarik"], 3)
        self.assertEqual(w1["selisih"], 1 - 3)

    def test_selisih_nol_saat_tarikan_sama_dengan_alih_media(self):
        self.tarik(self.am)
        w1 = self.kendali.papan_kendali("2026-09")["baris"][0]
        self.assertEqual(w1["selisih"], 0)

    def test_tarikan_di_luar_periode_tidak_dihitung(self):
        self.tarik(self.am, "2026-07-01")
        w1 = self.kendali.papan_kendali("2026-09")["baris"][0]
        self.assertEqual(w1["catatan_ditarik"], 0)

    # ---- baris total ----
    def test_baris_total_menjumlah_semua_wilayah(self):
        papan = self.kendali.papan_kendali("2026-09")
        total = papan["total"]
        self.assertEqual(total["proses"], 2)          # Wilayah I + Wilayah III
        self.assertEqual(total["total_capaian"],
                         sum(b["total_capaian"] for b in papan["baris"]))
        self.assertEqual(total["selisih"],
                         total["alih_media"] - total["catatan_ditarik"])

    # ---- pengisian penetapan lewat service ----
    def test_simpan_penetapan_mengeluarkan_dari_kolom_4(self):
        self.svc_aksi.simpan_penetapan(self.isbat, "12/Pdt.P/2026/PA.Gtlo", "2026-09-11",
                             self.pengguna_id)
        b = self.svc_berkas.ambil(self.isbat)
        self.assertEqual(b["no_penetapan"], "12/Pdt.P/2026/PA.Gtlo")
        self.assertEqual(b["tanggal_penetapan"], "2026-09-11")
        self.assertEqual(
            self.kendali.papan_kendali("2026-09")["baris"][0]["penetapan"], 0)

    def test_penetapan_dikosongkan_lagi_kembali_ke_kolom_4(self):
        self.svc_aksi.simpan_penetapan(self.isbat, "12/Pdt.P/2026", "2026-09-11",
                             self.pengguna_id)
        self.svc_aksi.simpan_penetapan(self.isbat, "  ", "  ", self.pengguna_id)
        b = self.svc_berkas.ambil(self.isbat)
        self.assertIsNone(b["no_penetapan"])
        self.assertIsNone(b["tanggal_penetapan"])
        self.assertEqual(
            self.kendali.papan_kendali("2026-09")["baris"][0]["penetapan"], 1)

    def test_simpan_penetapan_tidak_menggeser_tahapan(self):
        sebelum = self.svc_berkas.ambil(self.isbat)["tahapan_kode"]
        self.svc_aksi.simpan_penetapan(self.isbat, "12/Pdt.P/2026", "2026-09-11",
                             self.pengguna_id)
        self.assertEqual(self.svc_berkas.ambil(self.isbat)["tahapan_kode"], sebelum)

    def test_simpan_penetapan_menulis_log_audit(self):
        self.svc_aksi.simpan_penetapan(self.isbat, "12/Pdt.P/2026", "2026-09-11",
                             self.pengguna_id)
        self.assertEqual(self.db.ambil_nilai(
            """SELECT COUNT(*) FROM log_audit
                WHERE aksi = 'penetapan_isbat' AND ref_id = ?""",
            (self.isbat,), 0), 1)

    def test_perlu_isbat_terbawa_ke_detail_berkas(self):
        """Template detail memakai berkas.perlu_isbat untuk memunculkan panelnya."""
        self.assertEqual(self.svc_berkas.ambil(self.isbat)["perlu_isbat"], 1)
        biasa = self.db.ambil_nilai(
            "SELECT id FROM berkas WHERE objek_wakaf_id = ?", (self.o[1],))
        self.assertEqual(self.svc_berkas.ambil(biasa)["perlu_isbat"], 0)

    # ---- filter wilayah ----
    def test_korwil_hanya_melihat_wilayahnya(self):
        wil3 = self.db.ambil_satu("SELECT id FROM wilayah WHERE nama = 'Wilayah III'")
        korwil = {"peran": "korwil", "wilayah_id": wil3["id"]}
        papan = self.kendali.papan_kendali("2026-09", pengguna=korwil)
        self.assertEqual([b["wilayah"] for b in papan["baris"]], ["Wilayah III"])
        self.assertEqual(papan["total"]["proses"], 1)

    def test_korwil_tidak_bisa_menembus_filter_lewat_query(self):
        wil3 = self.db.ambil_satu("SELECT id FROM wilayah WHERE nama = 'Wilayah III'")
        wil1 = self.db.ambil_satu("SELECT id FROM wilayah WHERE nama = 'Wilayah I'")
        korwil = {"peran": "korwil", "wilayah_id": wil3["id"]}
        papan = self.kendali.papan_kendali("2026-09", wilayah_id=wil1["id"],
                                           pengguna=korwil)
        self.assertEqual([b["wilayah"] for b in papan["baris"]], ["Wilayah III"])

    def test_penyaring_wilayah_untuk_peran_bebas(self):
        wil1 = self.db.ambil_satu("SELECT id FROM wilayah WHERE nama = 'Wilayah I'")
        papan = self.kendali.papan_kendali("2026-09", wilayah_id=wil1["id"])
        self.assertEqual([b["wilayah"] for b in papan["baris"]], ["Wilayah I"])

    # ---- integrasi dengan services/berkas ----
    def test_berkas_tanpa_tanggal_daftar_masuk_pra_daftar(self):
        objek = self.buat_objek("Masjid Y", "Suwawa")
        bid = self.svc_berkas.buat({"objek_wakaf_id": objek,
                        "jenis_permohonan_kode": "pertama_kali",
                        "tanggal_daftar": None}, self.pengguna_id)
        self.assertEqual(self.svc_berkas.ambil(bid)["tahapan_kode"], "pra_daftar")

    def test_berkas_dengan_tanggal_daftar_masuk_permohonan(self):
        objek = self.buat_objek("Masjid Z", "Suwawa")
        bid = self.svc_berkas.buat({"objek_wakaf_id": objek,
                        "jenis_permohonan_kode": "pertama_kali",
                        "tanggal_daftar": "2026-09-02"}, self.pengguna_id)
        self.assertEqual(self.svc_berkas.ambil(bid)["tahapan_kode"], "permohonan")

    def test_tandai_tarikan_terbaca_papan_kendali(self):
        self.svc_aksi.tandai_tarikan(self.am, True, "2026-09-15", self.pengguna_id)
        self.assertEqual(
            self.kendali.papan_kendali("2026-09")["baris"][0]["catatan_ditarik"], 1)
        self.svc_aksi.tandai_tarikan(self.am, False, None, self.pengguna_id)
        self.assertEqual(
            self.kendali.papan_kendali("2026-09")["baris"][0]["catatan_ditarik"], 0)

    def test_tandai_tarikan_tidak_menggeser_tahapan(self):
        sebelum = self.svc_berkas.ambil(self.am)["tahapan_kode"]
        self.svc_aksi.tandai_tarikan(self.am, True, "2026-09-15", self.pengguna_id)
        self.assertEqual(self.svc_berkas.ambil(self.am)["tahapan_kode"], sebelum)


if __name__ == "__main__":
    unittest.main()
