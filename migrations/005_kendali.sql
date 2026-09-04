-- 005 — Dashboard kendali per korwil.
--
-- Menambah dua tahapan tunggu yang selama ini tidak punya tempat:
--   * pra_daftar           — berkas sudah disiapkan tim, belum masuk loket KKP.
--     Tahapan 'permohonan' (urutan 10) namanya "Sudah Daftar Loket", jadi tidak
--     ada posisi untuk berkas yang belum didaftarkan.
--   * penetapan_pengadilan — permohonan isbat yang menunggu penetapan pengadilan.
--     Dipasang di urutan 15 supaya berkas non-isbat cukup melompatinya.
--
-- Dan dua kolom untuk kolom "Catatan yang sudah ditarik" di papan kendali:
-- sertipikat/warkah yang sudah ditarik dari pemegang hak untuk dicatat wakafnya.
-- Selisih papan kendali = alih media selesai - catatan yang ditarik (tunggakan).

INSERT INTO tahapan (kode, urutan, nama, sla_hari) VALUES
    ('pra_daftar', 5, 'Akan Didaftar (Belum Loket)', NULL),
    ('penetapan_pengadilan', 15, 'Menunggu Penetapan Pengadilan', NULL);

ALTER TABLE berkas ADD COLUMN catatan_ditarik INTEGER NOT NULL DEFAULT 0;
ALTER TABLE berkas ADD COLUMN tanggal_ditarik TEXT;

CREATE INDEX idx_berkas_ditarik  ON berkas(tanggal_ditarik);
CREATE INDEX idx_berkas_tgl_selesai ON berkas(tanggal_selesai);
