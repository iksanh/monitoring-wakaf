-- 004 — Susunan tim per wilayah, diambil dari sheet 'Total Potensi Wilayah'.
-- Kolom kecamatan_id ditambahkan karena sheet sumber mencantumkan kecamatan
-- binaan tiap anggota; kalau tidak disimpan, informasi itu hilang.

ALTER TABLE tim ADD COLUMN kecamatan_id INTEGER REFERENCES kecamatan(id);
ALTER TABLE tim ADD COLUMN urutan INTEGER NOT NULL DEFAULT 0;

INSERT INTO tim (wilayah_id, nama, jabatan, urutan, kecamatan_id)
    SELECT w.id, 'Sep Hamdan Rifanuddin, S.T.', 'Korwil', 1,
           (SELECT id FROM kecamatan WHERE lower(nama) = lower('Suwawa'))
      FROM wilayah w WHERE w.nama = 'Wilayah I';
INSERT INTO tim (wilayah_id, nama, jabatan, urutan, kecamatan_id)
    SELECT w.id, 'Nabila Tahira Ali, S.T.', 'Anggota', 2,
           (SELECT id FROM kecamatan WHERE lower(nama) = lower('Suwawa Selatan'))
      FROM wilayah w WHERE w.nama = 'Wilayah I';
INSERT INTO tim (wilayah_id, nama, jabatan, urutan, kecamatan_id)
    SELECT w.id, 'Moh. Ikhsan A.H, S.Kom', 'Anggota', 3,
           (SELECT id FROM kecamatan WHERE lower(nama) = lower('Bulango Ulu'))
      FROM wilayah w WHERE w.nama = 'Wilayah I';
INSERT INTO tim (wilayah_id, nama, jabatan, urutan, kecamatan_id)
    SELECT w.id, 'Wulandari Paramata, S.E.', 'Anggota', 4,
           (SELECT id FROM kecamatan WHERE lower(nama) = lower('Bone Pantai'))
      FROM wilayah w WHERE w.nama = 'Wilayah I';
INSERT INTO tim (wilayah_id, nama, jabatan, urutan, kecamatan_id)
    SELECT w.id, 'Abdul Sabrin Husa', 'Petugas Ukur', 5, NULL
      FROM wilayah w WHERE w.nama = 'Wilayah I';
INSERT INTO tim (wilayah_id, nama, jabatan, urutan, kecamatan_id)
    SELECT w.id, 'Asda Ichsanto Utomo, S.T', 'Korwil', 1,
           (SELECT id FROM kecamatan WHERE lower(nama) = lower('Tilongkabila'))
      FROM wilayah w WHERE w.nama = 'Wilayah III';
INSERT INTO tim (wilayah_id, nama, jabatan, urutan, kecamatan_id)
    SELECT w.id, 'Mohammad Fadly Ilahude, A.Md', 'Anggota', 2,
           (SELECT id FROM kecamatan WHERE lower(nama) = lower('Kabila'))
      FROM wilayah w WHERE w.nama = 'Wilayah III';
INSERT INTO tim (wilayah_id, nama, jabatan, urutan, kecamatan_id)
    SELECT w.id, 'Dina Azrina Nasution, S.H', 'Anggota', 3,
           (SELECT id FROM kecamatan WHERE lower(nama) = lower('Kabila Bone'))
      FROM wilayah w WHERE w.nama = 'Wilayah III';
INSERT INTO tim (wilayah_id, nama, jabatan, urutan, kecamatan_id)
    SELECT w.id, 'Pratno Kurniawan, S.H', 'Anggota', 4,
           (SELECT id FROM kecamatan WHERE lower(nama) = lower('Suwawa Tengah'))
      FROM wilayah w WHERE w.nama = 'Wilayah III';
INSERT INTO tim (wilayah_id, nama, jabatan, urutan, kecamatan_id)
    SELECT w.id, 'Mohammad Zainal Muttaqin, S.T.', 'Petugas Ukur', 5,
           (SELECT id FROM kecamatan WHERE lower(nama) = lower('Suwawa Timur'))
      FROM wilayah w WHERE w.nama = 'Wilayah III';
INSERT INTO tim (wilayah_id, nama, jabatan, urutan, kecamatan_id)
    SELECT w.id, 'Bahmid Kasim M. Hulopi, S.E.', 'Korwil', 1,
           (SELECT id FROM kecamatan WHERE lower(nama) = lower('Bulawa'))
      FROM wilayah w WHERE w.nama = 'Wilayah II';
INSERT INTO tim (wilayah_id, nama, jabatan, urutan, kecamatan_id)
    SELECT w.id, 'Iswan B. Padu, S.H.', 'Anggota', 2,
           (SELECT id FROM kecamatan WHERE lower(nama) = lower('Bone Raya'))
      FROM wilayah w WHERE w.nama = 'Wilayah II';
INSERT INTO tim (wilayah_id, nama, jabatan, urutan, kecamatan_id)
    SELECT w.id, 'Asifa Zunda, A.P.', 'Anggota', 3,
           (SELECT id FROM kecamatan WHERE lower(nama) = lower('Tapa'))
      FROM wilayah w WHERE w.nama = 'Wilayah II';
INSERT INTO tim (wilayah_id, nama, jabatan, urutan, kecamatan_id)
    SELECT w.id, 'Syamsul Rizal Paneo', 'Petugas Ukur', 4,
           (SELECT id FROM kecamatan WHERE lower(nama) = lower('Botupingge'))
      FROM wilayah w WHERE w.nama = 'Wilayah II';
INSERT INTO tim (wilayah_id, nama, jabatan, urutan, kecamatan_id)
    SELECT w.id, 'Ismail Polamolo', 'Anggota', 5, NULL
      FROM wilayah w WHERE w.nama = 'Wilayah II';
INSERT INTO tim (wilayah_id, nama, jabatan, urutan, kecamatan_id)
    SELECT w.id, 'Rian Makuta', 'Anggota', 6, NULL
      FROM wilayah w WHERE w.nama = 'Wilayah II';
INSERT INTO tim (wilayah_id, nama, jabatan, urutan, kecamatan_id)
    SELECT w.id, 'Rini Rahman', 'Anggota', 7, NULL
      FROM wilayah w WHERE w.nama = 'Wilayah II';
INSERT INTO tim (wilayah_id, nama, jabatan, urutan, kecamatan_id)
    SELECT w.id, 'Dian Pratama Eka Putra, S.T.', 'Korwil', 1,
           (SELECT id FROM kecamatan WHERE lower(nama) = lower('Bone'))
      FROM wilayah w WHERE w.nama = 'Wilayah IV';
INSERT INTO tim (wilayah_id, nama, jabatan, urutan, kecamatan_id)
    SELECT w.id, 'Jimmy Febryanto Silitonga, S.H.', 'Anggota', 2,
           (SELECT id FROM kecamatan WHERE lower(nama) = lower('Bulango Utara'))
      FROM wilayah w WHERE w.nama = 'Wilayah IV';
INSERT INTO tim (wilayah_id, nama, jabatan, urutan, kecamatan_id)
    SELECT w.id, 'Indriana R. Igirisa, S.P.W.K.', 'Anggota', 3,
           (SELECT id FROM kecamatan WHERE lower(nama) = lower('Bulango Timur'))
      FROM wilayah w WHERE w.nama = 'Wilayah IV';
INSERT INTO tim (wilayah_id, nama, jabatan, urutan, kecamatan_id)
    SELECT w.id, 'Marten Bento', 'Anggota', 4, NULL
      FROM wilayah w WHERE w.nama = 'Wilayah IV';
INSERT INTO tim (wilayah_id, nama, jabatan, urutan, kecamatan_id)
    SELECT w.id, 'Gunawan Wahab', 'Petugas Ukur', 5, NULL
      FROM wilayah w WHERE w.nama = 'Wilayah IV';
INSERT INTO tim (wilayah_id, nama, jabatan, urutan, kecamatan_id)
    SELECT w.id, 'Sarini Karim', 'Anggota', 6, NULL
      FROM wilayah w WHERE w.nama = 'Wilayah IV';
