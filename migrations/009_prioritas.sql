-- 009 — Penanda berkas prioritas.
--
-- Ditaruh di objek_wakaf, sejalan dengan perlu_isbat (migrasi 008): satu objek =
-- satu berkas, dan penandanya sudah ada sejak objek dibuat — jauh sebelum
-- berkasnya lahir. Berkas ikut membacanya lewat JOIN, jadi filter prioritas
-- tersedia di halaman objek maupun halaman berkas tanpa data ganda.
ALTER TABLE objek_wakaf ADD COLUMN is_prioritas INTEGER NOT NULL DEFAULT 0;

CREATE INDEX idx_objek_prioritas ON objek_wakaf(is_prioritas);
