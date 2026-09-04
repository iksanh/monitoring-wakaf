-- 007 — Hapus tahapan 'penetapan_pengadilan' yang ditambahkan migrasi 005.
--
-- Alur tahapan kembali lurus tanpa percabangan: setiap jenis permohonan melewati
-- rangkaian yang sama. Permohonan isbat tetap dibedakan lewat
-- berkas.jenis_permohonan_kode = 'isbat', bukan lewat tahapan tersendiri.
--
-- foreign_keys=ON aktif saat migrasi jalan, jadi kalau ternyata masih ada baris
-- berkas atau riwayat_tahapan yang menunjuk tahapan ini, DELETE di bawah akan
-- gagal dan migrasi dibatalkan — bukan diam-diam merusak data.
DELETE FROM tahapan WHERE kode = 'penetapan_pengadilan';
