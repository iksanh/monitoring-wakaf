-- 014 — Penandaan prioritas jadi keputusan administrator.
--
-- Kolom is_prioritas sudah ada sejak migrasi 009, tapi siapa pun yang boleh
-- mengubah objek (admin, sekretariat, korwil, petugas) bisa mencentangnya lewat
-- form ubah objek. Akibatnya tidak ada keseragaman: satu korwil menandai lima
-- objek "prioritas", korwil lain tidak menandai sama sekali, dan lencana ★ di
-- daftar objek maupun daftar berkas tidak berarti apa-apa lagi.
--
-- Mulai sekarang penanda ini hanya boleh ditulis services/prioritas.tandai(),
-- dan hanya administrator yang boleh memanggilnya — sejalan dengan
-- services/pemilahan.pilah() yang memegang status_tindak_lanjut. Kolom di bawah
-- merekam siapa yang menandai dan kapan, supaya lencananya bisa dipertanggung-
-- jawabkan.
ALTER TABLE objek_wakaf ADD COLUMN prioritas_pada TEXT;
ALTER TABLE objek_wakaf ADD COLUMN prioritas_oleh INTEGER REFERENCES pengguna(id);
