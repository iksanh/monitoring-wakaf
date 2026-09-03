-- 003 — Seed jadwal sosialisasi dari sheet 'Jadwal Sosialisasi'
-- (Sekretariat Wakaf Bonbol 2026.xlsx, 11-22 September 2026).

INSERT INTO sosialisasi (id, tanggal, jam_mulai, jam_selesai, lokasi, pembina, status, catatan) VALUES
    (1, '2026-09-11', '08.30', '11.00', 'Kecamatan Suwawa Timur & Suwawa Tengah', NULL, 'rencana', 'Sasaran: Suwawa Timur & Suwawa Tengah');
INSERT INTO sosialisasi_kecamatan (sosialisasi_id, kecamatan_id)
    SELECT 1, id FROM kecamatan WHERE lower(nama) = lower('Suwawa Timur');
INSERT INTO sosialisasi_kecamatan (sosialisasi_id, kecamatan_id)
    SELECT 1, id FROM kecamatan WHERE lower(nama) = lower('Suwawa Tengah');

INSERT INTO sosialisasi (id, tanggal, jam_mulai, jam_selesai, lokasi, pembina, status, catatan) VALUES
    (2, '2026-09-14', '09.00', '12.00', 'Kecamatan Bulango Ulu, Bulango Utara & Bulango Selatan', NULL, 'rencana', 'Sasaran: Bulango Ulu, Bulango Utara & Bulango Selatan');
INSERT INTO sosialisasi_kecamatan (sosialisasi_id, kecamatan_id)
    SELECT 2, id FROM kecamatan WHERE lower(nama) = lower('Bulango Ulu');
INSERT INTO sosialisasi_kecamatan (sosialisasi_id, kecamatan_id)
    SELECT 2, id FROM kecamatan WHERE lower(nama) = lower('Bulango Utara');
INSERT INTO sosialisasi_kecamatan (sosialisasi_id, kecamatan_id)
    SELECT 2, id FROM kecamatan WHERE lower(nama) = lower('Bulango Selatan');

INSERT INTO sosialisasi (id, tanggal, jam_mulai, jam_selesai, lokasi, pembina, status, catatan) VALUES
    (3, '2026-09-15', '09.00', '12.00', 'Kecamatan Bone Pantai & Kabila Bone', NULL, 'rencana', 'Sasaran: Bone Pantai & Kabila Bone');
INSERT INTO sosialisasi_kecamatan (sosialisasi_id, kecamatan_id)
    SELECT 3, id FROM kecamatan WHERE lower(nama) = lower('Bone Pantai');
INSERT INTO sosialisasi_kecamatan (sosialisasi_id, kecamatan_id)
    SELECT 3, id FROM kecamatan WHERE lower(nama) = lower('Kabila Bone');

INSERT INTO sosialisasi (id, tanggal, jam_mulai, jam_selesai, lokasi, pembina, status, catatan) VALUES
    (4, '2026-09-16', '09.00', '12.00', 'Kecamatan Bulawa & Bone Raya', NULL, 'rencana', 'Sasaran: Bulawa & Bone Raya');
INSERT INTO sosialisasi_kecamatan (sosialisasi_id, kecamatan_id)
    SELECT 4, id FROM kecamatan WHERE lower(nama) = lower('Bulawa');
INSERT INTO sosialisasi_kecamatan (sosialisasi_id, kecamatan_id)
    SELECT 4, id FROM kecamatan WHERE lower(nama) = lower('Bone Raya');

INSERT INTO sosialisasi (id, tanggal, jam_mulai, jam_selesai, lokasi, pembina, status, catatan) VALUES
    (5, '2026-09-17', '09.00', '12.00', 'Kecamatan Tapa & Bulango Timur', NULL, 'rencana', 'Sasaran: Tapa & Bulango Timur');
INSERT INTO sosialisasi_kecamatan (sosialisasi_id, kecamatan_id)
    SELECT 5, id FROM kecamatan WHERE lower(nama) = lower('Tapa');
INSERT INTO sosialisasi_kecamatan (sosialisasi_id, kecamatan_id)
    SELECT 5, id FROM kecamatan WHERE lower(nama) = lower('Bulango Timur');

INSERT INTO sosialisasi (id, tanggal, jam_mulai, jam_selesai, lokasi, pembina, status, catatan) VALUES
    (6, '2026-09-18', '08.30', '11.00', 'Kecamatan Botupingge & Kabila', NULL, 'rencana', 'Sasaran: Botupingge & Kabila');
INSERT INTO sosialisasi_kecamatan (sosialisasi_id, kecamatan_id)
    SELECT 6, id FROM kecamatan WHERE lower(nama) = lower('Botupingge');
INSERT INTO sosialisasi_kecamatan (sosialisasi_id, kecamatan_id)
    SELECT 6, id FROM kecamatan WHERE lower(nama) = lower('Kabila');

INSERT INTO sosialisasi (id, tanggal, jam_mulai, jam_selesai, lokasi, pembina, status, catatan) VALUES
    (7, '2026-09-21', '09.00', '12.00', 'Kecamatan Tilongkabila, Suwawa & Suwawa Selatan', NULL, 'rencana', 'Sasaran: Tilongkabila, Suwawa & Suwawa Selatan');
INSERT INTO sosialisasi_kecamatan (sosialisasi_id, kecamatan_id)
    SELECT 7, id FROM kecamatan WHERE lower(nama) = lower('Tilongkabila');
INSERT INTO sosialisasi_kecamatan (sosialisasi_id, kecamatan_id)
    SELECT 7, id FROM kecamatan WHERE lower(nama) = lower('Suwawa');
INSERT INTO sosialisasi_kecamatan (sosialisasi_id, kecamatan_id)
    SELECT 7, id FROM kecamatan WHERE lower(nama) = lower('Suwawa Selatan');

INSERT INTO sosialisasi (id, tanggal, jam_mulai, jam_selesai, lokasi, pembina, status, catatan) VALUES
    (8, '2026-09-22', '09.00', '12.00', 'Kecamatan Bone', NULL, 'rencana', 'Sasaran: Bone');
INSERT INTO sosialisasi_kecamatan (sosialisasi_id, kecamatan_id)
    SELECT 8, id FROM kecamatan WHERE lower(nama) = lower('Bone');
