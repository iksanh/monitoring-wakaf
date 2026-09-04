-- 010 — Alasan pembatalan berkas.
--
-- "Batalkan pendaftaran" mengubah berkas.status jadi 'batal'. Berkasnya lalu
-- disembunyikan dari daftar /berkas dan objeknya kembali bebas dibuatkan berkas
-- baru — indeks unik idx_berkas_satu_per_objek (migrasi 006) memang sudah
-- mengecualikan status 'batal'.
--
-- Riwayat tahapan sengaja tidak disentuh: aksi di riwayat_tahapan dibatasi CHECK
-- ('masuk','selesai','kendala','mundur') dan pembatalan bukan pergerakan tahapan.
-- Alasannya disimpan di kolom sendiri supaya bisa ditampilkan, bukan ditumpangkan
-- ke kolom catatan yang dipakai petugas.
ALTER TABLE berkas ADD COLUMN alasan_batal TEXT;
ALTER TABLE berkas ADD COLUMN tanggal_batal TEXT;
