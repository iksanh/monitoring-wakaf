"""Pengaturan aplikasi yang berlaku sekantor — satu tabel kunci-nilai.

Bukan config.py: yang di sana dibaca dari environment variable dan hanya berubah
saat deploy. Yang di sini diubah administrator dari halaman /pengaturan sambil
aplikasi jalan, dan berlaku untuk semua pengguna sekaligus.

Menambah pengaturan baru = menambah satu entri di TERSEDIA. Tidak perlu migrasi
skema lagi; barisnya lahir sendiri saat pertama kali disimpan, dan sebelum itu
`ambil()` memakai nilai bawaan dari TERSEDIA.
"""
import config
import db
from services import audit

# kunci -> (bawaan, label, keterangan)
TERSEDIA = {
    "tag_prioritas": (
        True,
        "Tampilkan tag prioritas",
        "Lencana ★ Prioritas di daftar objek wakaf, daftar berkas, dan halaman "
        "detail. Kalau dimatikan, lencananya saja yang hilang — penanda "
        "prioritas tetap tersimpan, urutan daftar tetap mendahulukannya, dan "
        "penyaring “Hanya prioritas” tetap bisa dipakai.",
    ),
}

# Hanya administrator. Pengaturan ini berlaku untuk semua orang sekaligus, jadi
# bukan preferensi tampilan per pengguna.
PERAN_PENGATUR = ("admin",)


class GalatPengaturan(Exception):
    """Permintaan pengaturan yang tidak sah — ditampilkan apa adanya ke pengguna."""


def boleh_mengatur(pengguna) -> bool:
    return bool(pengguna) and pengguna["peran"] in PERAN_PENGATUR


def _bawaan(kunci: str) -> bool:
    return TERSEDIA[kunci][0]


def ambil(kunci: str) -> bool:
    """Nilai satu pengaturan. Baris yang belum pernah disimpan pakai bawaannya."""
    if kunci not in TERSEDIA:
        raise GalatPengaturan(f"Pengaturan “{kunci}” tidak dikenal.")
    nilai = db.ambil_nilai("SELECT nilai FROM pengaturan WHERE kunci = ?", (kunci,))
    if nilai is None:
        return _bawaan(kunci)
    return nilai == "1"


def semua() -> dict:
    """Semua pengaturan yang dikenal, lengkap dengan yang belum pernah disimpan."""
    tersimpan = {b["kunci"]: b["nilai"] == "1"
                 for b in db.ambil_semua("SELECT kunci, nilai FROM pengaturan")}
    return {kunci: tersimpan.get(kunci, bawaan)
            for kunci, (bawaan, _, _) in TERSEDIA.items()}


def daftar_untuk_halaman() -> list[dict]:
    """Bahan render halaman pengaturan: kunci, label, keterangan, nilai kini."""
    nilai = semua()
    return [{"kunci": kunci, "label": label, "keterangan": keterangan,
             "nilai": nilai[kunci]}
            for kunci, (_, label, keterangan) in TERSEDIA.items()]


def simpan(kunci: str, nyala, pengguna) -> bool:
    """Simpan satu pengaturan. Kembalikan True kalau nilainya benar-benar berubah."""
    if not boleh_mengatur(pengguna):
        raise GalatPengaturan("Hanya administrator yang boleh mengubah pengaturan.")
    if kunci not in TERSEDIA:
        raise GalatPengaturan(f"Pengaturan “{kunci}” tidak dikenal.")

    baru = "1" if nyala else "0"
    kon = db.koneksi()
    try:
        kon.execute("BEGIN")
        lama = kon.execute("SELECT nilai FROM pengaturan WHERE kunci = ?",
                           (kunci,)).fetchone()
        nilai_lama = lama["nilai"] if lama else ("1" if _bawaan(kunci) else "0")
        if lama and nilai_lama == baru:
            kon.commit()
            return False
        # ON CONFLICT: kunci yang belum pernah disimpan lahir di sini.
        kon.execute(
            """INSERT INTO pengaturan (kunci, nilai, diubah_pada, diubah_oleh)
                    VALUES (?, ?, ?, ?)
               ON CONFLICT(kunci) DO UPDATE
                    SET nilai = excluded.nilai,
                        diubah_pada = excluded.diubah_pada,
                        diubah_oleh = excluded.diubah_oleh""",
            (kunci, baru, config.stempel_waktu(), pengguna["id"]),
        )
        audit.catat(kon, pengguna["id"], "atur", "pengaturan", None,
                    {kunci: nilai_lama}, {kunci: baru})
        kon.commit()
        return True
    except Exception:
        kon.rollback()
        raise
    finally:
        kon.close()
