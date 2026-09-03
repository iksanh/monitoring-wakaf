"""Query master data, susunan tim, dan pengelolaan akun pengguna."""
import re
import secrets
import unicodedata

import auth
import db
from services import audit

# Jabatan di sheet 'Total Potensi Wilayah' -> peran aplikasi.
PERAN_DARI_JABATAN = {
    "korwil": "korwil",
    "anggota": "petugas",
    "petugas ukur": "petugas",
}


def wilayah() -> list[dict]:
    return db.ambil_semua("SELECT * FROM wilayah ORDER BY urutan")


def kecamatan() -> list[dict]:
    return db.ambil_semua(
        """SELECT k.id, k.nama, k.kode_singkat, COALESCE(w.nama, '-') AS wilayah,
                  (SELECT COUNT(*) FROM desa d WHERE d.kecamatan_id = k.id) AS jumlah_desa,
                  (SELECT COUNT(*) FROM objek_wakaf o
                    WHERE o.kecamatan_id = k.id AND o.is_aktif = 1) AS jumlah_objek
             FROM kecamatan k LEFT JOIN wilayah w ON w.id = k.wilayah_id
            ORDER BY w.urutan, k.nama"""
    )


def tipologi() -> list[dict]:
    return db.ambil_semua(
        """SELECT t.*, (SELECT COUNT(*) FROM objek_wakaf o
                         WHERE o.tipologi_kode = t.kode AND o.is_aktif = 1) AS jumlah
             FROM tipologi t ORDER BY t.urutan"""
    )


def syarat() -> list[dict]:
    return db.ambil_semua(
        """SELECT s.*, j.nama AS jenis_nama
             FROM syarat s JOIN jenis_permohonan j ON j.kode = s.jenis_permohonan_kode
            ORDER BY j.urutan, s.urutan"""
    )


def tim() -> list[dict]:
    """Susunan tim per wilayah, beserta akun yang sudah terhubung (kalau ada)."""
    return db.ambil_semua(
        """SELECT t.id, t.nama, t.jabatan, t.urutan, t.wilayah_id, t.pengguna_id,
                  w.nama AS wilayah, w.urutan AS wilayah_urutan,
                  k.nama AS kecamatan,
                  p.username, p.peran, p.aktif
             FROM tim t
             JOIN wilayah w ON w.id = t.wilayah_id
             LEFT JOIN kecamatan k ON k.id = t.kecamatan_id
             LEFT JOIN pengguna p ON p.id = t.pengguna_id
            ORDER BY w.urutan, t.urutan"""
    )


def peran_untuk(jabatan: str | None) -> str:
    return PERAN_DARI_JABATAN.get((jabatan or "").strip().lower(), "petugas")


def usulan_username(nama: str, terpakai: set | None = None) -> str:
    """Ubah nama lengkap jadi username: 'Sep Hamdan Rifanuddin, S.T.' -> 'sep.hamdan'.

    Gelar setelah koma dibuang. Kalau bentrok, ditambahi angka.
    """
    tanpa_gelar = nama.split(",")[0]
    bersih = unicodedata.normalize("NFKD", tanpa_gelar).encode("ascii", "ignore").decode()
    kata = [k for k in re.split(r"[^A-Za-z]+", bersih) if len(k) > 1]
    dasar = ".".join(kata[:2]).lower() or "pengguna"
    terpakai = terpakai if terpakai is not None else {
        b["username"] for b in db.ambil_semua("SELECT username FROM pengguna")
    }
    calon, urut = dasar, 1
    while calon in terpakai:
        urut += 1
        calon = f"{dasar}{urut}"
    terpakai.add(calon)
    return calon


def buat_akun_tim(tim_ids: list[int], oleh: int) -> list[dict]:
    """Buatkan akun untuk anggota tim yang belum punya.

    Sandi awal dibuat acak dan HANYA dikembalikan di sini — setelah itu tidak
    bisa dilihat lagi karena yang disimpan cuma hash-nya.
    """
    if not tim_ids:
        return []
    tanya = ",".join("?" for _ in tim_ids)
    calon = db.ambil_semua(
        f"""SELECT t.id, t.nama, t.jabatan, t.wilayah_id, w.nama AS wilayah
              FROM tim t JOIN wilayah w ON w.id = t.wilayah_id
             WHERE t.id IN ({tanya}) AND t.pengguna_id IS NULL
             ORDER BY w.urutan, t.urutan""",
        tuple(tim_ids),
    )
    if not calon:
        return []

    terpakai = {b["username"] for b in db.ambil_semua("SELECT username FROM pengguna")}
    hasil = []
    kon = db.koneksi()
    try:
        kon.execute("BEGIN")
        for anggota in calon:
            username = usulan_username(anggota["nama"], terpakai)
            sandi = secrets.token_urlsafe(9)
            peran = peran_untuk(anggota["jabatan"])
            kur = kon.execute(
                """INSERT INTO pengguna (username, nama, password_hash, peran,
                                         wilayah_id, aktif)
                   VALUES (?, ?, ?, ?, ?, 1)""",
                (username, anggota["nama"], auth.buat_hash(sandi), peran,
                 anggota["wilayah_id"]),
            )
            kon.execute("UPDATE tim SET pengguna_id = ? WHERE id = ?",
                        (kur.lastrowid, anggota["id"]))
            audit.catat(kon, oleh, "buat_akun_tim", "pengguna", kur.lastrowid,
                        None, {"username": username, "peran": peran,
                               "tim_id": anggota["id"]})
            hasil.append({"nama": anggota["nama"], "username": username,
                          "sandi": sandi, "peran": peran,
                          "wilayah": anggota["wilayah"], "jabatan": anggota["jabatan"]})
        kon.commit()
        return hasil
    except Exception:
        kon.rollback()
        raise
    finally:
        kon.close()


def tim_tanpa_akun() -> list[int]:
    return [b["id"] for b in db.ambil_semua(
        "SELECT id FROM tim WHERE pengguna_id IS NULL")]


def pengguna() -> list[dict]:
    return db.ambil_semua(
        """SELECT p.id, p.username, p.nama, p.peran, p.aktif,
                  COALESCE(w.nama, '-') AS wilayah
             FROM pengguna p LEFT JOIN wilayah w ON w.id = p.wilayah_id
            ORDER BY p.aktif DESC, p.nama"""
    )


def tambah_pengguna(data: dict, oleh: int) -> str | None:
    """Kembalikan pesan galat, atau None kalau sukses."""
    if not data.get("username") or not data.get("nama"):
        return "Nama pengguna dan nama lengkap wajib diisi."
    if data.get("peran") not in auth.PERAN_TERSEDIA:
        return "Peran tidak dikenal."
    if len(data.get("sandi") or "") < 8:
        return "Sandi minimal 8 karakter."
    if data["peran"] in auth.PERAN_TERBATAS_WILAYAH and not data.get("wilayah_id"):
        return "Peran korwil dan petugas wajib punya wilayah."
    if db.ambil_satu("SELECT id FROM pengguna WHERE username = ?",
                     (data["username"].lower(),)):
        return "Nama pengguna sudah dipakai."
    pengguna_id = db.jalankan(
        """INSERT INTO pengguna (username, nama, password_hash, peran, wilayah_id, aktif)
           VALUES (?, ?, ?, ?, ?, 1)""",
        (data["username"].lower(), data["nama"], auth.buat_hash(data["sandi"]),
         data["peran"], data.get("wilayah_id")),
    )
    audit.catat(None, oleh, "buat", "pengguna", pengguna_id, None,
                {"username": data["username"], "peran": data["peran"]})
    return None


def set_aktif(pengguna_id: int, aktif: int, oleh: int) -> None:
    db.jalankan("UPDATE pengguna SET aktif = ? WHERE id = ?", (1 if aktif else 0, pengguna_id))
    audit.catat(None, oleh, "set_aktif", "pengguna", pengguna_id, None, {"aktif": aktif})


def reset_sandi(pengguna_id: int, oleh: int) -> str:
    sandi = secrets.token_urlsafe(9)
    auth.ganti_sandi(pengguna_id, sandi)
    audit.catat(None, oleh, "reset_sandi", "pengguna", pengguna_id, None, None)
    return sandi
