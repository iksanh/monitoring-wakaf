-- 006 — Satu objek wakaf hanya boleh punya satu berkas permohonan.
--
-- Sebelum ini tidak ada penjagaan apa pun: form berkas yang dikirim ulang selalu
-- membuat baris baru. Akibatnya Masjid Al-Fajar sempat punya empat berkas kembar
-- (sudah dibersihkan, lihat log_audit aksi 'hapus_duplikat').
--
-- Berkas berstatus 'batal' sengaja dikecualikan supaya objek yang permohonannya
-- dibatalkan masih bisa didaftarkan ulang.
CREATE UNIQUE INDEX idx_berkas_satu_per_objek
    ON berkas(objek_wakaf_id) WHERE status <> 'batal';
