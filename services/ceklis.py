"""Ceklis persyaratan per berkas (sumber: sheet Kontrol)."""
import config
import db
from services import audit

# Tahapan yang baru boleh dimasuki setelah syarat wajib lengkap.
TAHAPAN_BUTUH_SYARAT = "pengukuran"


def salin_syarat(kon, berkas_id: int, jenis_kode: str) -> int:
    """Salin daftar syarat sesuai jenis permohonan ke ceklis_berkas."""
    baris = kon.execute(
        "SELECT id FROM syarat WHERE jenis_permohonan_kode = ? ORDER BY urutan",
        (jenis_kode,),
    ).fetchall()
    for s in baris:
        kon.execute(
            "INSERT OR IGNORE INTO ceklis_berkas (berkas_id, syarat_id) VALUES (?, ?)",
            (berkas_id, s["id"]),
        )
    return len(baris)


def rekam_keadaan(kon, berkas_id: int) -> list[dict]:
    """Potret ceklis berkas apa adanya — dipakai log_audit sebelum disusun ulang."""
    return [
        {"syarat": b["nama"], "terpenuhi": b["terpenuhi"],
         "tanggal_penuhi": b["tanggal_penuhi"], "catatan": b["catatan"]}
        for b in kon.execute(
            """SELECT s.nama, c.terpenuhi, c.tanggal_penuhi, c.catatan
                 FROM ceklis_berkas c JOIN syarat s ON s.id = c.syarat_id
                WHERE c.berkas_id = ? ORDER BY s.urutan""", (berkas_id,)).fetchall()
    ]


def selaraskan_syarat(kon, berkas_id: int, jenis_kode: str) -> dict:
    """Susun ulang ceklis berkas mengikuti jenis permohonan yang baru.

    Dipanggil services/berkas_koreksi.ganti_jenis() di dalam transaksinya.
    Baris ceklis lama diganti daftar syarat jenis baru; centang, tanggal, dan
    catatan dibawa pindah untuk syarat yang teksnya sama persis — banyak syarat
    dipakai lebih dari satu jenis (AIW/APAIW, Surat Pengesahan Nazir, surat
    kuasa), jadi pemeriksaan yang sudah dilakukan tidak perlu diulang.
    """
    lama = {b["syarat"]: b for b in rekam_keadaan(kon, berkas_id)}
    kon.execute("DELETE FROM ceklis_berkas WHERE berkas_id = ?", (berkas_id,))
    baru = kon.execute(
        "SELECT id, nama FROM syarat WHERE jenis_permohonan_kode = ? ORDER BY urutan",
        (jenis_kode,),
    ).fetchall()
    dibawa = 0
    for s in baru:
        sebelumnya = lama.get(s["nama"])
        if sebelumnya and sebelumnya["terpenuhi"]:
            dibawa += 1
        kon.execute(
            """INSERT INTO ceklis_berkas (berkas_id, syarat_id, terpenuhi,
                                          tanggal_penuhi, catatan)
               VALUES (?, ?, ?, ?, ?)""",
            (berkas_id, s["id"],
             sebelumnya["terpenuhi"] if sebelumnya else 0,
             sebelumnya["tanggal_penuhi"] if sebelumnya else None,
             sebelumnya["catatan"] if sebelumnya else None),
        )
    nama_baru = {s["nama"] for s in baru}
    return {"syarat_lama": len(lama), "syarat_baru": len(baru), "centang_dibawa": dibawa,
            "syarat_hilang": sorted(n for n in lama if n not in nama_baru)}


def per_berkas(berkas_id: int) -> list[dict]:
    return db.ambil_semua(
        """SELECT c.*, s.nama, s.urutan, s.wajib
             FROM ceklis_berkas c JOIN syarat s ON s.id = c.syarat_id
            WHERE c.berkas_id = ? ORDER BY s.urutan""",
        (berkas_id,),
    )


def progres(berkas_id: int) -> dict:
    baris = per_berkas(berkas_id)
    terpenuhi = sum(1 for b in baris if b["terpenuhi"])
    wajib = [b for b in baris if b["wajib"]]
    return {
        "total": len(baris),
        "terpenuhi": terpenuhi,
        "wajib_total": len(wajib),
        "wajib_terpenuhi": sum(1 for b in wajib if b["terpenuhi"]),
        "wajib_lengkap": all(b["terpenuhi"] for b in wajib) if wajib else True,
        "persen": round(terpenuhi * 100 / len(baris)) if baris else 0,
    }


def simpan(berkas_id: int, terpenuhi_ids: set, catatan: dict, pengguna_id: int) -> None:
    kon = db.koneksi()
    try:
        kon.execute("BEGIN")
        for baris in kon.execute(
            "SELECT id, syarat_id, terpenuhi FROM ceklis_berkas WHERE berkas_id = ?",
            (berkas_id,),
        ).fetchall():
            baru = 1 if baris["syarat_id"] in terpenuhi_ids else 0
            kon.execute(
                """UPDATE ceklis_berkas
                      SET terpenuhi = ?, catatan = ?,
                          tanggal_penuhi = CASE WHEN ? = 1 AND tanggal_penuhi IS NULL
                                                THEN ? ELSE
                                                CASE WHEN ? = 0 THEN NULL
                                                     ELSE tanggal_penuhi END END
                    WHERE id = ?""",
                (baru, catatan.get(baris["syarat_id"]), baru, config.hari_ini_iso(),
                 baru, baris["id"]),
            )
        audit.catat(kon, pengguna_id, "ubah_ceklis", "berkas", berkas_id, None,
                    {"terpenuhi": sorted(terpenuhi_ids)})
        kon.commit()
    except Exception:
        kon.rollback()
        raise
    finally:
        kon.close()


def halangan_pindah(berkas_id: int, tahapan_kode: str) -> str | None:
    """Kembalikan pesan peringatan kalau syarat wajib belum lengkap, selain itu None."""
    if tahapan_kode != TAHAPAN_BUTUH_SYARAT:
        return None
    p = progres(berkas_id)
    if p["wajib_lengkap"]:
        return None
    kurang = p["wajib_total"] - p["wajib_terpenuhi"]
    return (f"{kurang} syarat wajib belum terpenuhi "
            f"({p['wajib_terpenuhi']}/{p['wajib_total']}).")
