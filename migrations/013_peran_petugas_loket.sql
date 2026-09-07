-- 013 — Peran baru: petugas_loket.
--
-- Loket adalah pintu masuk permohonan di kantor. Perannya sengaja sempit: boleh
-- melihat objek & berkas dan mendaftarkan objek jadi berkas, tapi tidak memindah
-- tahapan, tidak mengubah data objek, dan tidak memilah. Ia juga TIDAK dibatasi
-- wilayah (bukan anggota PERAN_TERBATAS_WILAYAH) — satu loket melayani seluruh
-- kabupaten, bukan satu wilayah tim.
--
-- Kolom pengguna.peran punya CHECK berisi daftar peran, dan SQLite tidak bisa
-- mengubah CHECK lewat ALTER TABLE. Jadi tabelnya dibangun ulang dengan cara
-- resmi: tabel baru, salin isi, buang yang lama, ganti nama.
--
-- Tujuh tabel menunjuk pengguna(id) — tim, objek_wakaf, berkas, riwayat_tahapan,
-- dokumen, kunjungan, log_audit — jadi DROP TABLE pengguna akan ditolak selama
-- penegakan foreign key menyala. db._jalankan_migrasi() yang mengurusnya: ia
-- mematikan foreign_keys selama migrasi jalan lalu memeriksa baris yatim dengan
-- PRAGMA foreign_key_check sebelum COMMIT. Karena id disalin apa adanya, semua
-- penunjuk itu tetap sah.

CREATE TABLE pengguna_baru (
    id            INTEGER PRIMARY KEY,
    username      TEXT NOT NULL UNIQUE,
    nama          TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    peran         TEXT NOT NULL CHECK (peran IN ('admin', 'sekretariat', 'korwil',
                                                 'petugas', 'petugas_loket', 'pimpinan')),
    wilayah_id    INTEGER REFERENCES wilayah(id),
    aktif         INTEGER NOT NULL DEFAULT 1,
    dibuat_pada   TEXT NOT NULL DEFAULT (datetime('now','+8 hours'))
);

INSERT INTO pengguna_baru (id, username, nama, password_hash, peran, wilayah_id,
                           aktif, dibuat_pada)
     SELECT id, username, nama, password_hash, peran, wilayah_id, aktif, dibuat_pada
       FROM pengguna;

DROP TABLE pengguna;

ALTER TABLE pengguna_baru RENAME TO pengguna;
