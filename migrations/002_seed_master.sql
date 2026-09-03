-- 002 — Seed master: wilayah, kecamatan, tipologi, tahapan,
-- jenis permohonan, dan syarat. Teks tipologi & syarat diambil apa adanya
-- dari file Excel sumber (sheet TIPOLOGI dan sheet Kontrol).

INSERT INTO wilayah (id, nama, urutan) VALUES
    (1, 'Wilayah I', 1),
    (2, 'Wilayah II', 2),
    (3, 'Wilayah III', 3),
    (4, 'Wilayah IV', 4),
    (5, 'Rutin', 5);

INSERT INTO kecamatan (nama, kode_singkat, wilayah_id) VALUES
    ('Suwawa', 'SWW', 1),
    ('Suwawa Selatan', 'SWS', 1),
    ('Bulango Ulu', 'BLU', 1),
    ('Bone Pantai', 'BNP', 1),
    ('Bulawa', 'BLW', 2),
    ('Bone Raya', 'BNR', 2),
    ('Tapa', 'TPA', 2),
    ('Botupingge', 'BTP', 2),
    ('Kabila', 'KBL', 3),
    ('Kabila Bone', 'KBB', 3),
    ('Suwawa Tengah', 'SWT', 3),
    ('Suwawa Timur', 'SWM', 3),
    ('Tilongkabila', 'TLK', 3),
    ('Bone', 'BON', 4),
    ('Bulango Selatan', 'BLS', 4),
    ('Bulango Timur', 'BLT', 4),
    ('Bulango Utara', 'BLA', 4);

INSERT INTO tipologi (kode, urutan, kategori, nama, deskripsi, kompleksitas) VALUES
    ('T1', 1, 'SERTIFIKASI REGULER', 'Ada AIW (Asli)', 'Dokumen Akta Ikrar Wakaf (AIW) asli tersedia, lengkap, dan valid.', 'Rendah (Proses Reguler)'),
    ('T2', 2, 'PERHATIAN / PENYELAMATAN DOKUMEN', 'Nomor AIW Ada, Dokumen Hilang/Salinan', '• Nomor AIW tercatat secara resmi.
 • Dokumen AIW fisik hilang atau hanya berupa salinan/fotokopi.', 'Sedang (Penyelamatan Dokumen)'),
    ('T3', 3, 'PERHATIAN / PENYELAMATAN DOKUMEN', 'Tidak Ada AIW, Wakif & Nadzir Ada', '• AIW tidak tersedia/belum terbit.
 • Data keberadaan Wakif dan Nadzir teridentifikasi jelas.', 'Sedang (Penyelamatan Dokumen)'),
    ('T4', 4, 'KRITIS / KOMPLEKSITAS LEGAL', 'Kehilangan AIW, Wakif Tidak Ada', '• Dokumen AIW tidak ada / hilang.
 • Wakif sudah tidak ada / tidak diketahui keberadaannya.', 'Tinggi (Kompleksitas Legal)'),
    ('T5', 5, 'KRITIS / KOMPLEKSITAS LEGAL', 'Kehilangan AIW, Nadzir Tidak Ada', '• Dokumen AIW tidak ada / hilang.
 • Nadzir sudah tidak ada / tidak aktif / tidak teridentifikasi.', 'Tinggi (Kompleksitas Legal)'),
    ('T6', 6, 'KRITIS / KOMPLEKSITAS LEGAL', 'Kehilangan AIW, Wakif & Nadzir Tidak Ada', '• Dokumen AIW tidak ada / hilang.
 • Baik Wakif maupun Nadzir dua-duanya tidak ada / tidak teridentifikasi.', 'Sangat Tinggi (Kritis)'),
    ('T7', 7, 'KRITIS / KOMPLEKSITAS LEGAL', 'Sengketa / Klaim Pihak Ketiga', '• Terdapat sengketa, keberatan, atau klaim kepemilikan dari pihak ketiga/ahli waris atas tanah wakaf.', 'Sangat Tinggi (Sengketa Legal)');

INSERT INTO tahapan (kode, urutan, nama, sla_hari) VALUES
    ('permohonan', 10, 'Permohonan (Sudah Daftar Loket)', NULL),
    ('pengukuran', 20, 'Pengukuran', NULL),
    ('panitia_a', 30, 'Pemeriksaan Tanah (Panitia A)', NULL),
    ('yuridis', 40, 'Pemeriksaan Yuridis', NULL),
    ('penerbitan', 50, 'Penerbitan', NULL),
    ('penyerahan', 60, 'Penyerahan', NULL);

INSERT INTO jenis_permohonan (kode, nama, urutan) VALUES
    ('pertama_kali', 'Pendaftaran Pertama Kali', 1),
    ('tanah_terdaftar', 'Wakaf dari Tanah Terdaftar (Bersertipikat)', 2),
    ('alih_media', 'Alih Media', 3),
    ('pemisahan', 'Pemisahan Bidang', 4),
    ('isbat', 'Isbat Wakaf', 5);

INSERT INTO syarat (jenis_permohonan_kode, urutan, nama, wajib) VALUES
    ('pertama_kali', 1, 'Formulir, Lampiran:
 1. Surat Pernyataan Nadzhir
 2. Surat Pemasangan Tanda Batas & Tetangga Berbatasan (beserta sketsa & foto geotag)', 1),
    ('pertama_kali', 2, 'AIW/APAIW (jika melalui Isbat, plus Salinan Penetapan Isbat)', 1),
    ('pertama_kali', 3, 'Surat Tanah', 1),
    ('pertama_kali', 4, 'Surat Pengesahan Nazir', 1),
    ('pertama_kali', 5, 'Surat Kuasa apabila di kuasakan', 0),
    ('pertama_kali', 6, 'Ktp Pemberi dan penerima kuasa', 0),
    ('tanah_terdaftar', 1, 'Formulir, Lampiran:
 1. Surat Pernyataan Nadzhir', 1),
    ('tanah_terdaftar', 2, 'AIW/APAIW (jika melalui Isbat, plus Salinan Penetapan Isbat)', 1),
    ('tanah_terdaftar', 3, 'Sertipikat Asli', 1),
    ('tanah_terdaftar', 4, 'Surat Pengesahan Nazir', 1),
    ('tanah_terdaftar', 5, 'Surat Kuasa apabila di kuasakan', 0),
    ('tanah_terdaftar', 6, 'Ktp Pemberi dan penerima kuasa', 0);
