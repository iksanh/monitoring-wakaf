-- 015 — Tabel pengaturan aplikasi.
--
-- Sebelum ini tidak ada tempat menyimpan pilihan yang berlaku sekantor. Yang
-- pertama butuh: menyalakan/mematikan tampilan tag prioritas. Lencana ★ tidak
-- dipakai semua orang, dan waktu tidak dipakai ia cuma bikin kolom nama objek
-- ramai. Datanya sendiri tidak ke mana-mana — `objek_wakaf.is_prioritas` tetap
-- tersimpan dan penyaring "Hanya prioritas" tetap jalan; yang disembunyikan
-- hanya lencananya.
--
-- Bentuknya sengaja kunci-nilai, bukan satu kolom per pilihan: menambah
-- pengaturan berikutnya cukup INSERT satu baris, tidak perlu migrasi skema
-- lagi. Nilai disimpan sebagai teks — pembacanya di services/pengaturan.py
-- yang menerjemahkan '1'/'0' jadi boolean.
CREATE TABLE pengaturan (
    kunci        TEXT PRIMARY KEY,
    nilai        TEXT NOT NULL,
    diubah_pada  TEXT,
    diubah_oleh  INTEGER REFERENCES pengguna(id)
);

-- Bawaannya menyala supaya tidak ada yang kehilangan tanda yang sudah dipasang
-- begitu versi ini naik.
INSERT INTO pengaturan (kunci, nilai) VALUES ('tag_prioritas', '1');
