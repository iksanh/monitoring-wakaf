-- 008 — Penanda isbat yang sebenarnya.
--
-- Sebelum ini isbat ditandai tiga cara setengah jadi: teks bebas
-- objek_wakaf.rekomendasi_isbat (yang dipakai rekap potensi seolah-olah flag),
-- jenis_permohonan 'isbat' (0 syarat, 0 berkas), dan tahapan yang sudah dihapus
-- migrasi 007. Isbat terjadi SEBELUM berkas didaftarkan di loket, jadi ia bukan
-- jenis permohonan loket — permohonannya tetap 'Pendaftaran Pertama Kali' dengan
-- salinan penetapan sebagai lampiran.
--
-- Dua lapis penanda, masing-masing mencatat yang memang diketahuinya:
--   objek_wakaf.perlu_isbat  — rencana; dipakai Rekap Potensi untuk objek yang
--                              belum punya berkas sama sekali.
--   berkas.no_penetapan      — realisasi; selama tanggal_penetapan masih kosong,
--   berkas.tanggal_penetapan   perkaranya dianggap masih di pengadilan.

ALTER TABLE objek_wakaf ADD COLUMN perlu_isbat INTEGER NOT NULL DEFAULT 0;
ALTER TABLE berkas ADD COLUMN no_penetapan TEXT;
ALTER TABLE berkas ADD COLUMN tanggal_penetapan TEXT;

CREATE INDEX idx_objek_perlu_isbat ON objek_wakaf(perlu_isbat);

-- Masjid Kapal Munzalan: putusan isbatnya memang sudah ada.
UPDATE objek_wakaf SET perlu_isbat = 1 WHERE kode = 'WKF-BLS-008';

-- Masjid Al-Multazam: 'LP2B' itu catatan tata ruang (Lahan Pertanian Pangan
-- Berkelanjutan), bukan isbat. Teksnya dipindah ke keterangan supaya tidak
-- hilang, lalu kolom rekomendasi_isbat dikosongkan.
UPDATE objek_wakaf
   SET keterangan = COALESCE(keterangan || ' | ', '') || 'LP2B',
       rekomendasi_isbat = NULL,
       perlu_isbat = 0
 WHERE kode = 'WKF-KBL-016';

-- Isbat bukan jenis permohonan loket. Aman dihapus: belum ada berkas maupun
-- syarat yang menunjuknya, dan foreign_keys=ON akan membatalkan migrasi kalau ada.
DELETE FROM jenis_permohonan WHERE kode = 'isbat';
