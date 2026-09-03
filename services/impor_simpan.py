"""Menyimpan hasil parser Excel ke database. Idempoten: dua kali jalan, hasil sama."""
import config
import db
from services import audit, impor_excel


def _peta_kecamatan(kon) -> dict:
    return {b["nama"].lower(): dict(b) for b in kon.execute(
        "SELECT id, nama, kode_singkat FROM kecamatan")}


def _kode_objek(kode_singkat: str | None, nama_kecamatan: str, urut: int) -> str:
    singkat = (kode_singkat or nama_kecamatan[:3]).upper()[:3]
    return f"WKF-{singkat}-{urut:03d}"


def _desa_id(kon, cache: dict, kecamatan_id: int, nama_desa: str | None, laporan):
    if not nama_desa:
        return None
    kunci = (kecamatan_id, nama_desa.lower())
    if kunci in cache:
        return cache[kunci]
    baris = kon.execute(
        "SELECT id FROM desa WHERE kecamatan_id = ? AND lower(nama) = ?",
        (kecamatan_id, nama_desa.lower()),
    ).fetchone()
    if baris:
        cache[kunci] = baris["id"]
        return baris["id"]
    kur = kon.execute(
        "INSERT INTO desa (kecamatan_id, nama) VALUES (?, ?)", (kecamatan_id, nama_desa)
    )
    laporan.desa_baru += 1
    cache[kunci] = kur.lastrowid
    return kur.lastrowid


KOLOM_OBJEK = (
    "nama_objek", "desa_id", "kecamatan_id", "nama_wakif", "nama_nadzir", "no_aiw",
    "tipe_hak", "nib", "luas_persil", "kecamatan_kkp", "desa_kkp", "rtrw",
    "tipologi_kode", "rekomendasi_isbat", "keterangan", "catatan_kua",
    "latitude", "longitude", "url_maps", "url_dokumen",
)


def simpan(objek: list[dict], kemenag: list[dict], laporan, pengguna_id=None,
           dry_run: bool = False) -> "impor_excel.Laporan":
    """Tulis hasil parser. Kalau dry_run, semua perubahan di-rollback di akhir."""
    kon = db.koneksi()
    try:
        kon.execute("BEGIN")
        peta_kec = _peta_kecamatan(kon)
        cache_desa: dict = {}
        urut_per_kecamatan: dict = {}

        for baris in objek:
            nama_kec = baris.get("kecamatan")
            kec = peta_kec.get((nama_kec or "").lower())
            if not kec:
                laporan.dilewati.append(
                    f"{baris['sheet']} baris {baris['baris']} ({baris['nama_objek']}): "
                    f"kecamatan '{nama_kec}' tidak ada di master."
                )
                continue

            urut_per_kecamatan[kec["id"]] = urut_per_kecamatan.get(kec["id"], 0) + 1
            kode = _kode_objek(kec["kode_singkat"], kec["nama"], urut_per_kecamatan[kec["id"]])
            desa_id = _desa_id(kon, cache_desa, kec["id"], baris.get("desa"), laporan)

            nilai = {k: baris.get(k) for k in KOLOM_OBJEK}
            nilai["desa_id"] = desa_id
            nilai["kecamatan_id"] = kec["id"]

            lama = kon.execute("SELECT * FROM objek_wakaf WHERE kode = ?", (kode,)).fetchone()
            if lama:
                set_sql = ", ".join(f"{k} = ?" for k in KOLOM_OBJEK)
                kon.execute(
                    f"""UPDATE objek_wakaf SET {set_sql},
                            diubah_pada = ?, diubah_oleh = ?
                        WHERE kode = ?""",
                    tuple(nilai[k] for k in KOLOM_OBJEK)
                    + (config.stempel_waktu(), pengguna_id, kode),
                )
                audit.catat(kon, pengguna_id, "impor_perbarui", "objek_wakaf",
                            lama["id"], None, {"kode": kode})
            else:
                kolom_sql = ", ".join(KOLOM_OBJEK)
                tanya = ", ".join("?" for _ in KOLOM_OBJEK)
                kur = kon.execute(
                    f"""INSERT INTO objek_wakaf (kode, {kolom_sql}, is_potensi, sumber_data)
                        VALUES (?, {tanya}, 1, 'excel_migrasi')""",
                    (kode,) + tuple(nilai[k] for k in KOLOM_OBJEK),
                )
                audit.catat(kon, pengguna_id, "impor_baru", "objek_wakaf",
                            kur.lastrowid, None, {"kode": kode})
            laporan.tersimpan[baris["sheet"]] = laporan.tersimpan.get(baris["sheet"], 0) + 1

        for baris in kemenag:
            kolom = [k for k in baris if k != "id_kemenag"]
            set_sql = ", ".join(f"{k} = ?" for k in kolom)
            kur = kon.execute(
                f"""UPDATE referensi_kemenag SET {set_sql} WHERE id_kemenag = ?""",
                tuple(baris[k] for k in kolom) + (baris["id_kemenag"],),
            )
            if kur.rowcount == 0:
                semua = ["id_kemenag"] + kolom
                kon.execute(
                    f"""INSERT INTO referensi_kemenag ({", ".join(semua)})
                        VALUES ({", ".join("?" for _ in semua)})""",
                    tuple(baris[k] for k in semua),
                )
            laporan.kemenag_tersimpan += 1

        if dry_run:
            kon.rollback()
        else:
            kon.commit()
        return laporan
    except Exception:
        kon.rollback()
        raise
    finally:
        kon.close()


def impor(path, pengguna_id=None, dry_run: bool = False):
    objek, kemenag, laporan = impor_excel.baca_berkas(path)
    return simpan(objek, kemenag, laporan, pengguna_id=pengguna_id, dry_run=dry_run)


def teks_laporan(laporan) -> str:
    baris = ["== LAPORAN IMPOR ==", ""]
    baris.append(f"{'Sheet':<20} {'Terbaca':>8} {'Tersimpan':>10}")
    for sheet in laporan.terbaca:
        baris.append(f"{sheet:<20} {laporan.terbaca[sheet]:>8} "
                     f"{laporan.tersimpan.get(sheet, 0):>10}")
    baris.append(f"{'TOTAL':<20} {laporan.total_terbaca:>8} {laporan.total_tersimpan:>10}")
    baris.append("")
    baris.append(f"Desa baru dibuat        : {laporan.desa_baru}")
    baris.append(f"Referensi Kemenag       : {sum(laporan.kemenag_terbaca.values())} terbaca, "
                 f"{laporan.kemenag_tersimpan} tersimpan")
    for sheet, n in laporan.kemenag_terbaca.items():
        baris.append(f"    - {sheet}: {n}")
    baris.append("")
    baris.append("Sebaran tipologi:")
    for kode in sorted(laporan.tipologi, key=lambda k: (k == "(kosong)", k)):
        baris.append(f"    {kode:<10} {laporan.tipologi[kode]:>4}")
    terisi = sum(n for k, n in laporan.tipologi.items() if k != "(kosong)")
    baris.append(f"    {'terisi':<10} {terisi:>4}")
    baris.append("")
    baris.append(f"Baris tanpa nomor urut (legenda/rekap, bukan data): {len(laporan.bukan_data)}")
    baris.extend("    " + t for t in laporan.bukan_data)
    baris.append("")
    baris.append(f"Dilewati ({len(laporan.dilewati)}):")
    baris.extend("    " + t for t in laporan.dilewati or ["(tidak ada)"])
    baris.append("")
    baris.append(f"Peringatan ({len(laporan.peringatan)}):")
    baris.extend("    " + t for t in laporan.peringatan or ["(tidak ada)"])
    return "\n".join(baris)
