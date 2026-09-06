-- 011 — Dokumen bisa diganti dan dihapus dari halaman objek.
--
-- Penghapusan sengaja tidak fisik. File di UPLOAD_DIR dibiarkan utuh dan barisnya
-- hanya ditandai is_aktif = 0, mengikuti kebiasaan aplikasi ini (objek wakaf pun
-- tidak pernah dihapus fisik): dokumen wakaf sering satu-satunya salinan digital
-- AIW yang dipegang kantor, jadi salah klik tidak boleh berarti hilang permanen.
-- Baris yang ditandai hilang dari daftar; jejak siapa dan kapan tetap ada di sini
-- dan di log_audit.
--
-- Penggantian file tidak menimpa file lama: simpan_unggahan() selalu memilih nama
-- baru yang belum terpakai, dan path lama tercatat di log_audit sebagai data_lama.
ALTER TABLE dokumen ADD COLUMN is_aktif INTEGER NOT NULL DEFAULT 1;
ALTER TABLE dokumen ADD COLUMN dihapus_pada TEXT;
ALTER TABLE dokumen ADD COLUMN dihapus_oleh INTEGER REFERENCES pengguna(id);
