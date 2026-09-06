"""Tes lapisan penyimpanan: backend lokal, backend S3, dan penjaga kunci.

Backend S3 diuji dengan klien tiruan di memori — tes tidak pernah menyentuh
jaringan maupun butuh kredensial AWS.
"""
import config
from services import dokumen as svc_dokumen, penyimpanan
from tests.bantu import BasisTes


class KlienS3Palsu:
    """Meniru bagian boto3 yang dipakai: put/get/head_object + exceptions.NoSuchKey."""

    class NoSuchKey(Exception):
        pass

    def __init__(self):
        self.isi = {}
        self.tipe = {}
        self.enkripsi = {}
        # boto3 menaruh kelas galatnya di klien, bukan di modul.
        self.exceptions = type("Galat", (), {"NoSuchKey": KlienS3Palsu.NoSuchKey})

    def put_object(self, Bucket, Key, Body, ContentType, ServerSideEncryption):  # noqa: N803
        self.isi[(Bucket, Key)] = Body
        self.tipe[(Bucket, Key)] = ContentType
        self.enkripsi[(Bucket, Key)] = ServerSideEncryption

    def get_object(self, Bucket, Key):  # noqa: N803
        if (Bucket, Key) not in self.isi:
            raise KlienS3Palsu.NoSuchKey(Key)
        return {"Body": _Aliran(self.isi[(Bucket, Key)])}

    def head_object(self, Bucket, Key):  # noqa: N803
        if (Bucket, Key) not in self.isi:
            raise KlienS3Palsu.NoSuchKey(Key)
        return {"ContentLength": len(self.isi[(Bucket, Key)])}


class _Aliran:
    def __init__(self, data):
        self._data = data

    def read(self):
        return self._data


class TesKunci(BasisTes):
    def test_kunci_wajar_diterima(self):
        self.assertEqual(penyimpanan.periksa_kunci("2026/17/aiw-a1b2.pdf"),
                         "2026/17/aiw-a1b2.pdf")

    def test_backslash_windows_dinormalkan(self):
        self.assertEqual(penyimpanan.periksa_kunci("2026\\17\\foto.jpg"),
                         "2026/17/foto.jpg")

    def test_kunci_berbahaya_ditolak(self):
        for jahat in ("../rahasia.txt", "2026/../../etc/passwd", "/etc/passwd",
                      "", "   ", "2026//foto.jpg", "..", "C:/Windows/win.ini"):
            with self.subTest(kunci=jahat):
                with self.assertRaises(penyimpanan.KunciTidakSah):
                    penyimpanan.periksa_kunci(jahat)

    def test_kunci_berbahaya_tidak_bisa_dibaca(self):
        # Penjaga yang sama harus berlaku lewat jalur publik, bukan cuma periksa_kunci.
        self.assertFalse(penyimpanan.ada("../rahasia.txt"))
        self.assertIsNone(penyimpanan.path_lokal("../rahasia.txt"))
        with self.assertRaises(penyimpanan.KunciTidakSah):
            penyimpanan.baca("../rahasia.txt")


class TesBackendLokal(BasisTes):
    def setUp(self):
        super().setUp()
        config.PENYIMPANAN = "lokal"

    def test_simpan_lalu_baca(self):
        penyimpanan.simpan("2026/9/uji.pdf", b"halo", "application/pdf")
        self.assertEqual(penyimpanan.baca("2026/9/uji.pdf"), b"halo")
        self.assertTrue(penyimpanan.ada("2026/9/uji.pdf"))
        self.assertEqual(penyimpanan.ukuran("2026/9/uji.pdf"), 4)
        self.assertIsNotNone(penyimpanan.path_lokal("2026/9/uji.pdf"))

    def test_berkas_hilang_bukan_gagal_biasa(self):
        with self.assertRaises(penyimpanan.BerkasHilang):
            penyimpanan.baca("2026/9/tidak-ada.pdf")
        self.assertFalse(penyimpanan.ada("2026/9/tidak-ada.pdf"))
        self.assertIsNone(penyimpanan.ukuran("2026/9/tidak-ada.pdf"))


class TesBackendS3(BasisTes):
    def setUp(self):
        super().setUp()
        self.klien = KlienS3Palsu()
        config.PENYIMPANAN = "s3"
        config.S3_BUCKET = "bucket-uji"
        config.S3_PREFIX = "dokumen"
        penyimpanan._klien_s3 = self.klien

    def tearDown(self):
        config.PENYIMPANAN = "lokal"
        penyimpanan.lupakan_klien()
        super().tearDown()

    def test_kunci_diberi_prefix_dan_dienkripsi(self):
        penyimpanan.simpan("2026/9/uji.pdf", b"halo", "application/pdf")
        self.assertIn(("bucket-uji", "dokumen/2026/9/uji.pdf"), self.klien.isi)
        self.assertEqual(self.klien.tipe[("bucket-uji", "dokumen/2026/9/uji.pdf")],
                         "application/pdf")
        self.assertEqual(self.klien.enkripsi[("bucket-uji", "dokumen/2026/9/uji.pdf")],
                         "AES256")

    def test_prefix_kosong_tidak_bikin_garis_miring_ganda(self):
        config.S3_PREFIX = ""
        penyimpanan.simpan("2026/9/uji.pdf", b"halo", "application/pdf")
        self.assertIn(("bucket-uji", "2026/9/uji.pdf"), self.klien.isi)

    def test_simpan_lalu_baca(self):
        penyimpanan.simpan("2026/9/uji.pdf", b"isi berkas", "application/pdf")
        self.assertEqual(penyimpanan.baca("2026/9/uji.pdf"), b"isi berkas")
        self.assertTrue(penyimpanan.ada("2026/9/uji.pdf"))
        self.assertEqual(penyimpanan.ukuran("2026/9/uji.pdf"), 10)

    def test_tidak_ada_di_bucket(self):
        with self.assertRaises(penyimpanan.BerkasHilang):
            penyimpanan.baca("2026/9/tidak-ada.pdf")
        self.assertFalse(penyimpanan.ada("2026/9/tidak-ada.pdf"))
        self.assertIsNone(penyimpanan.ukuran("2026/9/tidak-ada.pdf"))

    def test_path_lokal_kosong_supaya_route_ambil_isi(self):
        penyimpanan.simpan("2026/9/uji.pdf", b"halo", "application/pdf")
        self.assertIsNone(penyimpanan.path_lokal("2026/9/uji.pdf"))

    def test_bucket_bermasalah_jadi_gagal_penyimpanan(self):
        def meledak(**_):
            raise RuntimeError("koneksi putus")

        self.klien.put_object = meledak
        with self.assertRaises(penyimpanan.GagalPenyimpanan):
            penyimpanan.simpan("2026/9/uji.pdf", b"halo", "application/pdf")

    def test_dokumen_service_ikut_ke_s3(self):
        # Jalur nyata: unggah lewat service, lalu baca balik tanpa menyentuh disk.
        pengguna_id = self.buat_pengguna()
        objek_id = self.buat_objek()
        dokumen_id = svc_dokumen.simpan_unggahan(
            objek_id, None, "AIW", "AIW Desa Uji.pdf", b"%PDF-1.4", pengguna_id)
        dokumen = svc_dokumen.ambil(dokumen_id)

        self.assertEqual(svc_dokumen.isi(dokumen), b"%PDF-1.4")
        self.assertIsNone(svc_dokumen.path_absolut(dokumen))
        self.assertTrue(svc_dokumen.tersedia(dokumen))
        # Nama tampilan tetap rapi walau kunci diberi imbuhan acak.
        self.assertEqual(dokumen["nama_file"], "aiw-desa-uji.pdf")
        self.assertRegex(dokumen["path"], r"^\d{4}/\d+/aiw-desa-uji-[0-9a-f]{8}\.pdf$")
        self.assertFalse((config.UPLOAD_DIR / dokumen["path"]).exists())


class TesKunciUnik(BasisTes):
    def setUp(self):
        super().setUp()
        config.PENYIMPANAN = "lokal"

    def test_nama_sama_tidak_saling_menimpa(self):
        pengguna_id = self.buat_pengguna()
        objek_id = self.buat_objek()
        satu = svc_dokumen.ambil(svc_dokumen.simpan_unggahan(
            objek_id, None, "AIW", "sama.pdf", b"pertama", pengguna_id))
        dua = svc_dokumen.ambil(svc_dokumen.simpan_unggahan(
            objek_id, None, "AIW", "sama.pdf", b"kedua", pengguna_id))

        self.assertNotEqual(satu["path"], dua["path"])
        self.assertEqual(satu["nama_file"], dua["nama_file"])
        self.assertEqual(svc_dokumen.isi(satu), b"pertama")
        self.assertEqual(svc_dokumen.isi(dua), b"kedua")
