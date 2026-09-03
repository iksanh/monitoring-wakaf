"""Semua rekap. Tidak ada angka yang disimpan — semuanya hasil query."""
import config
import db
from auth import PERAN_TERBATAS_WILAYAH

# Klasifikasi potensi (pengganti kolom Baru / Ada Hak / Isbat di sheet POTENSI WAKAF).
# Diturunkan dari data, bukan diketik tangan.
_KELAS_POTENSI = """
    CASE
        WHEN o.rekomendasi_isbat IS NOT NULL
             AND trim(o.rekomendasi_isbat) NOT IN ('', '-') THEN 'isbat'
        WHEN o.tipe_hak IS NOT NULL
             AND trim(o.tipe_hak) NOT IN ('', '-') THEN 'ada_hak'
        ELSE 'baru'
    END
"""


def _batas(pengguna, wilayah_id=None) -> tuple[str, list]:
    """Filter wilayah: paksa untuk korwil/petugas, opsional untuk peran lain."""
    if pengguna and pengguna["peran"] in PERAN_TERBATAS_WILAYAH:
        return (" AND k.wilayah_id = ? ", [pengguna["wilayah_id"] or -1])
    if wilayah_id:
        return (" AND k.wilayah_id = ? ", [wilayah_id])
    return ("", [])


def rekap_harian(tanggal: str | None = None, wilayah_id=None, pengguna=None) -> dict:
    """Pergerakan pada satu tanggal, dikelompokkan per tahapan dan per wilayah."""
    tanggal = tanggal or config.hari_ini_iso()
    batas, p = _batas(pengguna, wilayah_id)

    per_tahapan = db.ambil_semua(
        f"""SELECT t.kode, t.nama, t.urutan, r.aksi, COUNT(*) AS jumlah
              FROM riwayat_tahapan r
              JOIN tahapan t ON t.kode = r.tahapan_kode
              JOIN berkas b ON b.id = r.berkas_id
              JOIN objek_wakaf o ON o.id = b.objek_wakaf_id
              JOIN kecamatan k ON k.id = o.kecamatan_id
             WHERE r.tanggal = ? {batas}
             GROUP BY t.kode, r.aksi
             ORDER BY t.urutan, r.aksi""",
        tuple([tanggal] + p),
    )
    per_wilayah = db.ambil_semua(
        f"""SELECT COALESCE(w.nama, '(tanpa wilayah)') AS wilayah, COUNT(*) AS jumlah
              FROM riwayat_tahapan r
              JOIN berkas b ON b.id = r.berkas_id
              JOIN objek_wakaf o ON o.id = b.objek_wakaf_id
              JOIN kecamatan k ON k.id = o.kecamatan_id
              LEFT JOIN wilayah w ON w.id = k.wilayah_id
             WHERE r.tanggal = ? {batas}
             GROUP BY w.id ORDER BY w.urutan""",
        tuple([tanggal] + p),
    )
    daftar = db.ambil_semua(
        f"""SELECT r.*, t.nama AS tahapan_nama, o.nama_objek, o.kode AS objek_kode,
                   b.no_berkas, k.nama AS kecamatan_nama, w.nama AS wilayah_nama,
                   pg.nama AS nama_pengguna
              FROM riwayat_tahapan r
              JOIN tahapan t ON t.kode = r.tahapan_kode
              JOIN berkas b ON b.id = r.berkas_id
              JOIN objek_wakaf o ON o.id = b.objek_wakaf_id
              JOIN kecamatan k ON k.id = o.kecamatan_id
              LEFT JOIN wilayah w ON w.id = k.wilayah_id
              LEFT JOIN pengguna pg ON pg.id = r.oleh_pengguna_id
             WHERE r.tanggal = ? {batas}
             ORDER BY t.urutan, o.nama_objek""",
        tuple([tanggal] + p),
    )
    return {"tanggal": tanggal, "per_tahapan": per_tahapan,
            "per_wilayah": per_wilayah, "berkas": daftar,
            "total": len(daftar)}


def rekap_tahapan(wilayah_id=None, pengguna=None) -> dict:
    """Posisi berkas aktif sekarang per tahapan (corong)."""
    batas, p = _batas(pengguna, wilayah_id)
    # Filter wilayah ditaruh di klausa JOIN supaya tahapan yang kosong tetap muncul.
    join_batas = " AND k.wilayah_id = ? " if batas else ""
    corong = db.ambil_semua(
        f"""SELECT t.kode, t.nama, t.urutan, t.sla_hari,
                   SUM(CASE WHEN b.status = 'aktif' THEN 1 ELSE 0 END) AS aktif,
                   COUNT(b.id) AS semua
              FROM tahapan t
              LEFT JOIN berkas b ON b.tahapan_kode = t.kode
              LEFT JOIN objek_wakaf o ON o.id = b.objek_wakaf_id
              LEFT JOIN kecamatan k ON k.id = o.kecamatan_id {join_batas}
             GROUP BY t.kode ORDER BY t.urutan""",
        tuple(p),
    )
    per_wilayah = db.ambil_semua(
        f"""SELECT COALESCE(w.nama, '(tanpa wilayah)') AS wilayah, b.tahapan_kode,
                   COUNT(*) AS jumlah
              FROM berkas b
              JOIN objek_wakaf o ON o.id = b.objek_wakaf_id
              JOIN kecamatan k ON k.id = o.kecamatan_id
              LEFT JOIN wilayah w ON w.id = k.wilayah_id
             WHERE b.status = 'aktif' {batas}
             GROUP BY w.id, b.tahapan_kode ORDER BY w.urutan""",
        tuple(p),
    )
    return {"corong": corong, "per_wilayah": per_wilayah,
            "total_aktif": sum(b["aktif"] for b in corong)}


def rekap_potensi_kecamatan(pengguna=None, wilayah_id=None) -> list[dict]:
    """Pengganti sheet POTENSI WAKAF: per kecamatan, dipecah Baru / Ada Hak / Isbat."""
    batas, p = _batas(pengguna, wilayah_id)
    return db.ambil_semua(
        f"""SELECT k.id, k.nama AS kecamatan, COALESCE(w.nama, '-') AS wilayah,
                   SUM(CASE WHEN {_KELAS_POTENSI} = 'baru' THEN 1 ELSE 0 END) AS baru,
                   SUM(CASE WHEN {_KELAS_POTENSI} = 'ada_hak' THEN 1 ELSE 0 END) AS ada_hak,
                   SUM(CASE WHEN {_KELAS_POTENSI} = 'isbat' THEN 1 ELSE 0 END) AS isbat,
                   COUNT(o.id) AS total
              FROM kecamatan k
              LEFT JOIN wilayah w ON w.id = k.wilayah_id
              LEFT JOIN objek_wakaf o
                     ON o.kecamatan_id = k.id AND o.is_potensi = 1 AND o.is_aktif = 1
             WHERE 1=1 {batas}
             GROUP BY k.id ORDER BY w.urutan, k.nama""",
        tuple(p),
    )


def rekap_wilayah(pengguna=None) -> list[dict]:
    """Pengganti sheet Total Potensi Wilayah."""
    batas, p = _batas(pengguna)
    syarat = " AND w.id = ? " if batas else ""
    return db.ambil_semua(
        f"""SELECT w.id, w.nama AS wilayah,
                   COUNT(DISTINCT k.id) AS jumlah_kecamatan,
                   COUNT(o.id) AS potensi,
                   SUM(CASE WHEN o.status_sertipikat = 'sudah' THEN 1 ELSE 0 END) AS sudah,
                   SUM(CASE WHEN o.status_sertipikat = 'proses' THEN 1 ELSE 0 END) AS proses
              FROM wilayah w
              LEFT JOIN kecamatan k ON k.wilayah_id = w.id
              LEFT JOIN objek_wakaf o
                     ON o.kecamatan_id = k.id AND o.is_potensi = 1 AND o.is_aktif = 1
             WHERE 1=1 {syarat}
             GROUP BY w.id ORDER BY w.urutan""",
        tuple(p),
    )


def rekap_tipologi(kecamatan_id=None, pengguna=None) -> list[dict]:
    batas, p = _batas(pengguna)
    syarat, params = "", list(p)
    if kecamatan_id:
        syarat = " AND o.kecamatan_id = ? "
        params.append(kecamatan_id)
    return db.ambil_semua(
        f"""SELECT t.kode, t.nama, t.kategori, t.kompleksitas, t.urutan,
                   COUNT(o.id) AS jumlah
              FROM tipologi t
              LEFT JOIN objek_wakaf o ON o.tipologi_kode = t.kode AND o.is_aktif = 1
              LEFT JOIN kecamatan k ON k.id = o.kecamatan_id
             WHERE 1=1 {batas} {syarat}
             GROUP BY t.kode ORDER BY t.urutan""",
        tuple(params),
    )


def tipologi_kosong(kecamatan_id=None, pengguna=None) -> int:
    batas, p = _batas(pengguna)
    syarat, params = "", list(p)
    if kecamatan_id:
        syarat = " AND o.kecamatan_id = ? "
        params.append(kecamatan_id)
    return db.ambil_nilai(
        f"""SELECT COUNT(*) FROM objek_wakaf o
              JOIN kecamatan k ON k.id = o.kecamatan_id
             WHERE o.tipologi_kode IS NULL AND o.is_aktif = 1 {batas} {syarat}""",
        tuple(params), 0,
    )


def rekap_penyerahan(tanggal_target: str, pengguna=None) -> dict:
    """Pengganti sheet 'Penyerahan 24 Sept': per wilayah, dipivot per jenis permohonan."""
    batas, p = _batas(pengguna)
    baris = db.ambil_semua(
        f"""SELECT COALESCE(w.nama, '(tanpa wilayah)') AS wilayah,
                   b.jenis_permohonan_kode AS jenis, COUNT(*) AS jumlah
              FROM berkas b
              JOIN objek_wakaf o ON o.id = b.objek_wakaf_id
              JOIN kecamatan k ON k.id = o.kecamatan_id
              LEFT JOIN wilayah w ON w.id = k.wilayah_id
             WHERE b.tahapan_kode = 'penyerahan'
               AND (b.target_penyerahan = ? OR b.tanggal_selesai = ?) {batas}
             GROUP BY w.id, b.jenis_permohonan_kode ORDER BY w.urutan""",
        tuple([tanggal_target, tanggal_target] + p),
    )
    jenis = db.ambil_semua("SELECT kode, nama FROM jenis_permohonan ORDER BY urutan")
    pivot: dict = {}
    for b in baris:
        baris_wilayah = pivot.setdefault(b["wilayah"], {j["kode"]: 0 for j in jenis})
        baris_wilayah[b["jenis"]] = b["jumlah"]
    for nama, isi in pivot.items():
        isi["total"] = sum(v for k, v in isi.items() if k != "total")
    return {"tanggal": tanggal_target, "jenis": jenis, "pivot": pivot,
            "total": sum(i["total"] for i in pivot.values())}


def berkas_macet(hari: int = 14, pengguna=None, wilayah_id=None) -> list[dict]:
    """Berkas aktif yang tidak bergerak melebihi N hari (atau melebihi sla_hari)."""
    batas, p = _batas(pengguna, wilayah_id)
    return db.ambil_semua(
        f"""SELECT b.id, b.no_berkas, o.nama_objek, o.kode AS objek_kode,
                   k.nama AS kecamatan_nama, w.nama AS wilayah_nama,
                   t.nama AS tahapan_nama, t.sla_hari,
                   gerak.tanggal_terakhir,
                   CAST(julianday('now','+8 hours')
                        - julianday(gerak.tanggal_terakhir) AS INTEGER) AS umur_hari
              FROM berkas b
              JOIN objek_wakaf o ON o.id = b.objek_wakaf_id
              JOIN kecamatan k ON k.id = o.kecamatan_id
              LEFT JOIN wilayah w ON w.id = k.wilayah_id
              JOIN tahapan t ON t.kode = b.tahapan_kode
              JOIN (SELECT berkas_id, MAX(tanggal) AS tanggal_terakhir
                      FROM riwayat_tahapan GROUP BY berkas_id) gerak
                ON gerak.berkas_id = b.id
             WHERE b.status = 'aktif' {batas}
               AND julianday('now','+8 hours') - julianday(gerak.tanggal_terakhir)
                   > COALESCE(t.sla_hari, ?)
             ORDER BY umur_hari DESC""",
        tuple(p + [hari]),
    )


def ringkasan_dashboard(pengguna=None) -> dict:
    batas, p = _batas(pengguna)
    objek = db.ambil_satu(
        f"""SELECT COUNT(*) AS total,
                   SUM(CASE WHEN o.is_potensi = 1 THEN 1 ELSE 0 END) AS potensi,
                   SUM(CASE WHEN o.status_sertipikat = 'sudah' THEN 1 ELSE 0 END) AS sudah,
                   SUM(CASE WHEN o.no_aiw IS NULL OR trim(o.no_aiw) IN ('','-')
                            THEN 1 ELSE 0 END) AS tanpa_aiw
              FROM objek_wakaf o JOIN kecamatan k ON k.id = o.kecamatan_id
             WHERE o.is_aktif = 1 {batas}""",
        tuple(p),
    ) or {}
    berkas_aktif = db.ambil_nilai(
        f"""SELECT COUNT(*) FROM berkas b
              JOIN objek_wakaf o ON o.id = b.objek_wakaf_id
              JOIN kecamatan k ON k.id = o.kecamatan_id
             WHERE b.status = 'aktif' {batas}""",
        tuple(p), 0,
    )
    return {"objek": objek, "berkas_aktif": berkas_aktif}
