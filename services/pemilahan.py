"""Pemilahan objek wakaf: bisa / tidak bisa ditindaklanjuti.

Satu-satunya tempat yang menulis `objek_wakaf.status_tindak_lanjut`. Tidak ada
`UPDATE objek_wakaf SET status_tindak_lanjut` di tempat lain — sama seperti
`tahapan.pindah()` menjaga `berkas.tahapan_kode`. Semua angka potensi di rekap
bersandar pada aturan ini.

Fungsi ini yang mencatat siapa memilah, kapan, dan alasannya kalau objeknya
dinyatakan tidak bisa ditindaklanjuti, sekalian menulis log_audit per objek.
"""
import config
import db
from auth import PERAN_TERBATAS_WILAYAH
from services import audit

BELUM = "belum_dipilah"
BISA = "bisa"
TIDAK_BISA = "tidak_bisa"
STATUS = (BELUM, BISA, TIDAK_BISA)

LABEL = {
    BELUM: "Belum dipilah",
    BISA: "Bisa ditindaklanjuti",
    TIDAK_BISA: "Tidak bisa ditindaklanjuti",
}
# Peran yang boleh memutuskan. Petugas lapangan tetap boleh mengubah data objek,
# tapi keputusan "ini potensi atau bukan" dipegang admin dan korwil — korwil
# hanya untuk objek di wilayahnya sendiri.
PERAN_PEMILAH = ("admin", "korwil")


class GalatPemilahan(Exception):
    """Permintaan pemilahan yang tidak sah — ditampilkan apa adanya ke pengguna."""


def boleh_memilah(pengguna) -> bool:
    return bool(pengguna) and pengguna["peran"] in PERAN_PEMILAH


def pilah(objek_ids, status: str, pengguna, alasan: str | None = None) -> dict:
    """Tandai satu atau banyak objek sekaligus. Kembalikan jumlah yang berubah.

    Objek di luar wilayah korwil diam-diam tidak ikut terubah — bukan galat,
    tapi ikut dilaporkan lewat kunci `dilewati` supaya bisa diberitahukan.
    """
    if not boleh_memilah(pengguna):
        raise GalatPemilahan("Hanya administrator dan koordinator wilayah yang "
                             "boleh memilah objek.")
    if status not in STATUS:
        raise GalatPemilahan("Status pemilahan tidak dikenal.")

    alasan = (alasan or "").strip() or None
    if status == TIDAK_BISA and not alasan:
        raise GalatPemilahan("Objek yang tidak bisa ditindaklanjuti wajib "
                             "disertai alasan.")
    if status != TIDAK_BISA:
        alasan = None

    # Halaman daftar merender tiap objek dua kali (kartu HP + baris tabel desktop),
    # jadi id kembar wajar terkirim. dict.fromkeys membuangnya tanpa mengacak urutan.
    ids = list(dict.fromkeys(int(i) for i in objek_ids if str(i).strip()))
    if not ids:
        raise GalatPemilahan("Tidak ada objek yang dicentang.")

    tanya = ", ".join("?" for _ in ids)
    waktu = config.stempel_waktu() if status != BELUM else None
    oleh = pengguna["id"] if status != BELUM else None

    kon = db.koneksi()
    try:
        kon.execute("BEGIN")
        sql = f"""SELECT o.id, o.status_tindak_lanjut, o.alasan_tidak_bisa
                    FROM objek_wakaf o
                    JOIN kecamatan k ON k.id = o.kecamatan_id
                   WHERE o.id IN ({tanya}) AND o.is_aktif = 1"""
        params = list(ids)
        if pengguna["peran"] in PERAN_TERBATAS_WILAYAH:
            sql += " AND k.wilayah_id = ?"
            params.append(pengguna["wilayah_id"] or -1)
        sasaran = kon.execute(sql, tuple(params)).fetchall()

        diubah = 0
        for baris in sasaran:
            if baris["status_tindak_lanjut"] == status and baris["alasan_tidak_bisa"] == alasan:
                continue
            kon.execute(
                """UPDATE objek_wakaf
                      SET status_tindak_lanjut = ?, alasan_tidak_bisa = ?,
                          dipilah_pada = ?, dipilah_oleh = ?,
                          diubah_pada = ?, diubah_oleh = ?
                    WHERE id = ?""",
                (status, alasan, waktu, oleh, config.stempel_waktu(),
                 pengguna["id"], baris["id"]),
            )
            audit.catat(
                kon, pengguna["id"], "pilah", "objek_wakaf", baris["id"],
                {"status_tindak_lanjut": baris["status_tindak_lanjut"],
                 "alasan_tidak_bisa": baris["alasan_tidak_bisa"]},
                {"status_tindak_lanjut": status, "alasan_tidak_bisa": alasan},
            )
            diubah += 1
        kon.commit()
    except Exception:
        kon.rollback()
        raise
    finally:
        kon.close()

    return {"diubah": diubah, "dilewati": len(ids) - len(sasaran),
            "tetap": len(sasaran) - diubah, "status": status}


def ringkasan(pengguna=None) -> dict:
    """Hitungan objek aktif per status pemilahan. Selalu berisi ketiga kunci."""
    syarat, params = "", []
    if pengguna and pengguna["peran"] in PERAN_TERBATAS_WILAYAH:
        syarat = " AND k.wilayah_id = ? "
        params.append(pengguna["wilayah_id"] or -1)
    baris = db.ambil_semua(
        f"""SELECT o.status_tindak_lanjut AS status, COUNT(*) AS jumlah
              FROM objek_wakaf o JOIN kecamatan k ON k.id = o.kecamatan_id
             WHERE o.is_aktif = 1 {syarat}
             GROUP BY o.status_tindak_lanjut""",
        tuple(params),
    )
    hasil = {s: 0 for s in STATUS}
    for b in baris:
        hasil[b["status"]] = b["jumlah"]
    hasil["total"] = sum(hasil[s] for s in STATUS)
    return hasil
