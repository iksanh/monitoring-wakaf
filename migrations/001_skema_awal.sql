-- 001 — Skema awal aplikasi sertipikasi tanah wakaf.

-- ============ MASTER / REFERENSI ============
CREATE TABLE wilayah (
    id      INTEGER PRIMARY KEY,
    nama    TEXT NOT NULL UNIQUE,
    urutan  INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE kecamatan (
    id           INTEGER PRIMARY KEY,
    nama         TEXT NOT NULL UNIQUE,
    kode_singkat TEXT,
    wilayah_id   INTEGER REFERENCES wilayah(id)
);

CREATE TABLE desa (
    id           INTEGER PRIMARY KEY,
    kecamatan_id INTEGER NOT NULL REFERENCES kecamatan(id),
    nama         TEXT NOT NULL,
    UNIQUE (kecamatan_id, nama)
);

CREATE TABLE tipologi (
    kode         TEXT PRIMARY KEY,
    urutan       INTEGER NOT NULL,
    kategori     TEXT,
    nama         TEXT NOT NULL,
    deskripsi    TEXT,
    kompleksitas TEXT
);

CREATE TABLE tahapan (
    kode     TEXT PRIMARY KEY,
    urutan   INTEGER NOT NULL UNIQUE,
    nama     TEXT NOT NULL,
    sla_hari INTEGER
);

CREATE TABLE jenis_permohonan (
    kode   TEXT PRIMARY KEY,
    nama   TEXT NOT NULL,
    urutan INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE syarat (
    id                    INTEGER PRIMARY KEY,
    jenis_permohonan_kode TEXT NOT NULL REFERENCES jenis_permohonan(kode),
    urutan                INTEGER NOT NULL,
    nama                  TEXT NOT NULL,
    wajib                 INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX idx_syarat_jenis ON syarat(jenis_permohonan_kode);

CREATE TABLE pengguna (
    id            INTEGER PRIMARY KEY,
    username      TEXT NOT NULL UNIQUE,
    nama          TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    peran         TEXT NOT NULL CHECK (peran IN ('admin','sekretariat','korwil','petugas','pimpinan')),
    wilayah_id    INTEGER REFERENCES wilayah(id),
    aktif         INTEGER NOT NULL DEFAULT 1,
    dibuat_pada   TEXT NOT NULL DEFAULT (datetime('now','+8 hours'))
);

CREATE TABLE tim (
    id          INTEGER PRIMARY KEY,
    wilayah_id  INTEGER NOT NULL REFERENCES wilayah(id),
    pengguna_id INTEGER REFERENCES pengguna(id),
    nama        TEXT NOT NULL,
    jabatan     TEXT
);

-- ============ ENTITAS INTI ============
CREATE TABLE objek_wakaf (
    id                INTEGER PRIMARY KEY,
    kode              TEXT NOT NULL UNIQUE,
    nama_objek        TEXT NOT NULL,
    desa_id           INTEGER REFERENCES desa(id),
    kecamatan_id      INTEGER NOT NULL REFERENCES kecamatan(id),
    nama_wakif        TEXT,
    nama_nadzir       TEXT,
    no_aiw            TEXT,
    tanggal_aiw       TEXT,
    jenis_alas_hak    TEXT,
    tipe_hak          TEXT,
    nib               TEXT,
    luas_persil       REAL,
    kecamatan_kkp     TEXT,
    desa_kkp          TEXT,
    rtrw              TEXT,
    tipologi_kode     TEXT REFERENCES tipologi(kode),
    rekomendasi_isbat TEXT,
    keterangan        TEXT,
    catatan_kua       TEXT,
    latitude          REAL,
    longitude         REAL,
    url_maps          TEXT,
    url_dokumen       TEXT,
    status_sertipikat TEXT NOT NULL DEFAULT 'belum'
                      CHECK (status_sertipikat IN ('belum','proses','sudah')),
    is_potensi        INTEGER NOT NULL DEFAULT 1,
    is_aktif          INTEGER NOT NULL DEFAULT 1,
    sumber_data       TEXT NOT NULL DEFAULT 'lapangan',
    dibuat_pada       TEXT NOT NULL DEFAULT (datetime('now','+8 hours')),
    diubah_pada       TEXT,
    diubah_oleh       INTEGER REFERENCES pengguna(id)
);
CREATE INDEX idx_objek_kecamatan ON objek_wakaf(kecamatan_id);
CREATE INDEX idx_objek_desa      ON objek_wakaf(desa_id);
CREATE INDEX idx_objek_tipologi  ON objek_wakaf(tipologi_kode);
CREATE INDEX idx_objek_status    ON objek_wakaf(status_sertipikat);
CREATE INDEX idx_objek_nama      ON objek_wakaf(nama_objek);

CREATE TABLE berkas (
    id                    INTEGER PRIMARY KEY,
    no_berkas             TEXT,
    objek_wakaf_id        INTEGER NOT NULL REFERENCES objek_wakaf(id),
    jenis_permohonan_kode TEXT NOT NULL REFERENCES jenis_permohonan(kode),
    tahapan_kode          TEXT NOT NULL REFERENCES tahapan(kode),
    status                TEXT NOT NULL DEFAULT 'aktif'
                          CHECK (status IN ('aktif','selesai','tertunda','batal')),
    tanggal_daftar        TEXT,
    target_penyerahan     TEXT,
    tanggal_selesai       TEXT,
    petugas_id            INTEGER REFERENCES pengguna(id),
    catatan               TEXT,
    dibuat_pada           TEXT NOT NULL DEFAULT (datetime('now','+8 hours')),
    diubah_pada           TEXT
);
CREATE INDEX idx_berkas_tahapan ON berkas(tahapan_kode);
CREATE INDEX idx_berkas_objek   ON berkas(objek_wakaf_id);
CREATE INDEX idx_berkas_status  ON berkas(status);

CREATE TABLE riwayat_tahapan (
    id               INTEGER PRIMARY KEY,
    berkas_id        INTEGER NOT NULL REFERENCES berkas(id),
    tahapan_kode     TEXT NOT NULL REFERENCES tahapan(kode),
    aksi             TEXT NOT NULL CHECK (aksi IN ('masuk','selesai','kendala','mundur')),
    tanggal          TEXT NOT NULL,
    catatan          TEXT,
    oleh_pengguna_id INTEGER REFERENCES pengguna(id),
    dibuat_pada      TEXT NOT NULL DEFAULT (datetime('now','+8 hours'))
);
CREATE INDEX idx_riwayat_tanggal ON riwayat_tahapan(tanggal);
CREATE INDEX idx_riwayat_berkas  ON riwayat_tahapan(berkas_id);

CREATE TABLE ceklis_berkas (
    id             INTEGER PRIMARY KEY,
    berkas_id      INTEGER NOT NULL REFERENCES berkas(id),
    syarat_id      INTEGER NOT NULL REFERENCES syarat(id),
    terpenuhi      INTEGER NOT NULL DEFAULT 0,
    tanggal_penuhi TEXT,
    catatan        TEXT,
    UNIQUE (berkas_id, syarat_id)
);

CREATE TABLE dokumen (
    id             INTEGER PRIMARY KEY,
    objek_wakaf_id INTEGER REFERENCES objek_wakaf(id),
    berkas_id      INTEGER REFERENCES berkas(id),
    jenis          TEXT,
    nama_file      TEXT,
    path           TEXT,
    url_eksternal  TEXT,
    ukuran_byte    INTEGER,
    diunggah_pada  TEXT NOT NULL DEFAULT (datetime('now','+8 hours')),
    oleh           INTEGER REFERENCES pengguna(id)
);
CREATE INDEX idx_dokumen_objek ON dokumen(objek_wakaf_id);

CREATE TABLE kunjungan (
    id               INTEGER PRIMARY KEY,
    objek_wakaf_id   INTEGER NOT NULL REFERENCES objek_wakaf(id),
    tanggal          TEXT NOT NULL,
    oleh_pengguna_id INTEGER REFERENCES pengguna(id),
    hasil            TEXT,
    latitude         REAL,
    longitude        REAL,
    catatan          TEXT,
    dibuat_pada      TEXT NOT NULL DEFAULT (datetime('now','+8 hours'))
);
CREATE INDEX idx_kunjungan_objek ON kunjungan(objek_wakaf_id);

CREATE TABLE sosialisasi (
    id             INTEGER PRIMARY KEY,
    tanggal        TEXT NOT NULL,
    jam_mulai      TEXT,
    jam_selesai    TEXT,
    lokasi         TEXT,
    pembina        TEXT,
    status         TEXT NOT NULL DEFAULT 'rencana'
                   CHECK (status IN ('rencana','terlaksana','batal')),
    jumlah_peserta INTEGER,
    catatan        TEXT
);

CREATE TABLE sosialisasi_kecamatan (
    sosialisasi_id INTEGER NOT NULL REFERENCES sosialisasi(id) ON DELETE CASCADE,
    kecamatan_id   INTEGER NOT NULL REFERENCES kecamatan(id),
    PRIMARY KEY (sosialisasi_id, kecamatan_id)
);

CREATE TABLE referensi_kemenag (
    id                INTEGER PRIMARY KEY,
    nama              TEXT,
    kabupaten         TEXT,
    kecamatan         TEXT,
    desa              TEXT,
    kategori          TEXT,
    tahun_berdiri     INTEGER,
    id_kemenag        TEXT UNIQUE,
    sumber            TEXT,
    keterangan        TEXT,
    tipe_hak          TEXT,
    status_sertipikat TEXT,
    tahun             INTEGER,
    nib               TEXT,
    luas              REAL,
    latitude          REAL,
    longitude         REAL,
    objek_wakaf_id    INTEGER REFERENCES objek_wakaf(id)
);
CREATE INDEX idx_kemenag_kecamatan ON referensi_kemenag(kecamatan);

CREATE TABLE log_audit (
    id          INTEGER PRIMARY KEY,
    pengguna_id INTEGER REFERENCES pengguna(id),
    aksi        TEXT NOT NULL,
    tabel       TEXT NOT NULL,
    ref_id      INTEGER,
    data_lama   TEXT,
    data_baru   TEXT,
    waktu       TEXT NOT NULL DEFAULT (datetime('now','+8 hours'))
);
CREATE INDEX idx_audit_tabel ON log_audit(tabel, ref_id);
CREATE INDEX idx_audit_waktu ON log_audit(waktu);
