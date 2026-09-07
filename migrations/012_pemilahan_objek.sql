-- 012 — Pemilahan objek: bisa / tidak bisa ditindaklanjuti.
--
-- Sebelum ini "potensi" cuma kolom is_potensi INTEGER DEFAULT 1, dan importer
-- Excel mengisinya 1 untuk semua baris. Akibatnya dashboard memperlihatkan
-- "Objek wakaf 225 / Potensi sertipikasi 225" — angka yang tidak pernah
-- diputuskan siapa pun, jadi tidak berarti apa-apa.
--
-- Kenyataannya objek wakaf harus dipilah dulu: mana yang bisa ditindaklanjuti
-- (itu yang jadi potensi sertipikasi) dan mana yang tidak bisa — tanahnya
-- sengketa, nadzirnya tidak ketemu, sudah beralih fungsi, dan seterusnya.
-- Boolean tidak cukup karena "belum diperiksa" bukan "sudah diputuskan tidak
-- bisa". Karena itu tiga keadaan, bukan dua:
--
--   belum_dipilah  — bawaan; belum ada yang memutuskan. BUKAN potensi.
--   bisa           — sudah diperiksa, bisa ditindaklanjuti = potensi.
--   tidak_bisa     — sudah diperiksa, tidak bisa. Wajib beralasan.
--
-- Yang menulis kolom ini hanya services/pemilahan.pilah(); ia sekalian mencatat
-- log_audit dan siapa/kapan memilah. Kolom is_potensi dibuang supaya tidak ada
-- dua sumber kebenaran — semua rekap sekarang membaca status_tindak_lanjut.
ALTER TABLE objek_wakaf ADD COLUMN status_tindak_lanjut TEXT NOT NULL
    DEFAULT 'belum_dipilah'
    CHECK (status_tindak_lanjut IN ('belum_dipilah', 'bisa', 'tidak_bisa'));
ALTER TABLE objek_wakaf ADD COLUMN alasan_tidak_bisa TEXT;
ALTER TABLE objek_wakaf ADD COLUMN dipilah_pada TEXT;
ALTER TABLE objek_wakaf ADD COLUMN dipilah_oleh INTEGER REFERENCES pengguna(id);

CREATE INDEX idx_objek_tindak_lanjut ON objek_wakaf(status_tindak_lanjut);

-- Objek yang berkasnya sudah didaftarkan jelas bisa ditindaklanjuti — buktinya
-- berkasnya jalan. Sisanya dibiarkan 'belum_dipilah' supaya pemilahannya benar
-- benar diputuskan orang, bukan diwarisi dari default importer.
UPDATE objek_wakaf SET status_tindak_lanjut = 'bisa'
 WHERE id IN (SELECT objek_wakaf_id FROM berkas WHERE status <> 'batal');

ALTER TABLE objek_wakaf DROP COLUMN is_potensi;
