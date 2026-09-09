"""Kelola daerah administratif: kecamatan dan desa.

Dipisah dari services/master.py — di sana isinya query baca dan pengelolaan
akun; di sini semua tulisan ke tabel `kecamatan` dan `desa` lewat satu pintu.

Aturan yang ditegakkan di sini:

- Nama kecamatan unik sekabupaten, nama desa unik di dalam kecamatannya.
  Perbandingannya tidak peduli huruf besar-kecil supaya 'Suwawa' dan 'SUWAWA'
  tidak jadi dua baris.
- `kode_singkat` tiga huruf dan unik. Kolom itu dipakai
  `services/objek._kode_baru()` sebagai awalan kode objek (WKF-SWW-001), jadi
  dua kecamatan berkode sama akan membuat nomor urutnya saling makan.
- Kecamatan wajib punya wilayah. Filter wilayah untuk korwil dan petugas
  (aturan domain #3) menyaring lewat `kecamatan.wilayah_id` — kecamatan tanpa
  wilayah tidak akan pernah muncul di layar mereka, dan datanya hilang diam-diam.
- Desa tidak bisa dipindah ke kecamatan lain, hanya diganti namanya.
  `objek_wakaf` menyimpan `desa_id` DAN `kecamatan_id` secara terpisah;
  memindah desa membuat kedua kolom itu bertentangan pada baris yang sudah ada.
- Baris master hanya boleh dihapus selama belum dipakai. Tabel ini tidak punya
  kolom `is_aktif`, jadi tidak ada penghapusan lunak: yang sudah dipakai objek
  wakaf dipertahankan apa adanya, bukan disembunyikan.
"""
import re

import db
from services import audit, normalisasi

# Master daerah berlaku sekabupaten dan menyentuh kode objek, jadi bukan urusan
# korwil. Halaman daftarnya tetap bisa dibaca semua peran; yang dibatasi hanya
# tombol dan aksinya.
PERAN_PENGELOLA = ("admin",)

_KODE_SINGKAT = re.compile(r"^[A-Za-z]{3}$")


class GalatDaerah(Exception):
    """Permintaan yang tidak sah — ditampilkan apa adanya ke pengguna."""


def boleh_mengelola(pengguna) -> bool:
    return bool(pengguna) and pengguna["peran"] in PERAN_PENGELOLA


def _pastikan_boleh(pengguna) -> None:
    if not boleh_mengelola(pengguna):
        raise GalatDaerah("Hanya administrator yang boleh mengubah daftar "
                          "kecamatan dan desa.")


# ---- baca ----

def daftar_kecamatan() -> list[dict]:
    return db.ambil_semua(
        """SELECT k.id, k.nama, k.kode_singkat, k.wilayah_id,
                  COALESCE(w.nama, '-') AS wilayah,
                  (SELECT COUNT(*) FROM desa d WHERE d.kecamatan_id = k.id) AS jumlah_desa,
                  (SELECT COUNT(*) FROM objek_wakaf o
                    WHERE o.kecamatan_id = k.id AND o.is_aktif = 1) AS jumlah_objek,
                  -- jumlah_pakai ikut menghitung objek nonaktif dan baris tim:
                  -- barisnya tidak muncul di daftar, tapi tetap menunjuk ke sini
                  -- dan tetap menghalangi penghapusan.
                  (SELECT COUNT(*) FROM objek_wakaf o WHERE o.kecamatan_id = k.id)
                  + (SELECT COUNT(*) FROM tim t WHERE t.kecamatan_id = k.id) AS jumlah_pakai
             FROM kecamatan k LEFT JOIN wilayah w ON w.id = k.wilayah_id
            ORDER BY w.urutan, k.nama"""
    )


def ambil_kecamatan(kecamatan_id: int) -> dict | None:
    return db.ambil_satu(
        """SELECT k.id, k.nama, k.kode_singkat, k.wilayah_id,
                  COALESCE(w.nama, '-') AS wilayah,
                  (SELECT COUNT(*) FROM desa d WHERE d.kecamatan_id = k.id) AS jumlah_desa,
                  (SELECT COUNT(*) FROM objek_wakaf o
                    WHERE o.kecamatan_id = k.id AND o.is_aktif = 1) AS jumlah_objek,
                  -- jumlah_pakai ikut menghitung objek nonaktif dan baris tim:
                  -- barisnya tidak muncul di daftar, tapi tetap menunjuk ke sini
                  -- dan tetap menghalangi penghapusan.
                  (SELECT COUNT(*) FROM objek_wakaf o WHERE o.kecamatan_id = k.id)
                  + (SELECT COUNT(*) FROM tim t WHERE t.kecamatan_id = k.id) AS jumlah_pakai
             FROM kecamatan k LEFT JOIN wilayah w ON w.id = k.wilayah_id
            WHERE k.id = ?""",
        (kecamatan_id,),
    )


def daftar_desa(kecamatan_id: int) -> list[dict]:
    """Desa satu kecamatan, beserta berapa objek wakaf aktif yang memakainya."""
    return db.ambil_semua(
        """SELECT d.id, d.nama, d.kecamatan_id,
                  (SELECT COUNT(*) FROM objek_wakaf o
                    WHERE o.desa_id = d.id AND o.is_aktif = 1) AS jumlah_objek,
                  (SELECT COUNT(*) FROM objek_wakaf o
                    WHERE o.desa_id = d.id) AS jumlah_pakai
             FROM desa d WHERE d.kecamatan_id = ? ORDER BY d.nama""",
        (kecamatan_id,),
    )


def ambil_desa(desa_id: int) -> dict | None:
    return db.ambil_satu(
        "SELECT id, nama, kecamatan_id FROM desa WHERE id = ?", (desa_id,))


# ---- validasi ----

def _nama_kecamatan(nilai, kecuali_id: int | None = None) -> str:
    nama = normalisasi.kecamatan(nilai)
    if not nama:
        raise GalatDaerah("Nama kecamatan wajib diisi.")
    bentrok = db.ambil_satu(
        "SELECT id FROM kecamatan WHERE lower(nama) = ? AND id <> ?",
        (nama.lower(), kecuali_id or -1),
    )
    if bentrok:
        raise GalatDaerah(f"Kecamatan {nama} sudah ada.")
    return nama


def _kode_singkat(nilai, kecuali_id: int | None = None) -> str:
    kode = (normalisasi.rapikan(nilai) or "").upper()
    if not _KODE_SINGKAT.match(kode):
        raise GalatDaerah("Kode singkat harus tepat tiga huruf, misalnya SWW.")
    bentrok = db.ambil_satu(
        "SELECT nama FROM kecamatan WHERE upper(kode_singkat) = ? AND id <> ?",
        (kode, kecuali_id or -1),
    )
    if bentrok:
        raise GalatDaerah(
            f"Kode {kode} sudah dipakai kecamatan {bentrok['nama']}. Kode ini "
            "jadi awalan nomor objek wakaf, jadi tidak boleh kembar.")
    return kode


def _wilayah_id(nilai) -> int:
    if not nilai:
        raise GalatDaerah("Wilayah wajib dipilih — kecamatan tanpa wilayah "
                          "tidak akan terlihat oleh korwil dan petugas.")
    if not db.ambil_satu("SELECT id FROM wilayah WHERE id = ?", (nilai,)):
        raise GalatDaerah("Wilayah tidak dikenal.")
    return int(nilai)


def _nama_desa(nilai, kecamatan_id: int, kecuali_id: int | None = None) -> str:
    nama = normalisasi.desa(nilai)
    if not nama:
        raise GalatDaerah("Nama desa wajib diisi.")
    bentrok = db.ambil_satu(
        """SELECT id FROM desa
            WHERE kecamatan_id = ? AND lower(nama) = ? AND id <> ?""",
        (kecamatan_id, nama.lower(), kecuali_id or -1),
    )
    if bentrok:
        raise GalatDaerah(f"Desa {nama} sudah ada di kecamatan ini.")
    return nama


# ---- tulis ----

def tambah_kecamatan(data: dict, pengguna) -> int:
    _pastikan_boleh(pengguna)
    nilai = {
        "nama": _nama_kecamatan(data.get("nama")),
        "kode_singkat": _kode_singkat(data.get("kode_singkat")),
        "wilayah_id": _wilayah_id(data.get("wilayah_id")),
    }
    with db.buka() as kon:
        kur = kon.execute(
            "INSERT INTO kecamatan (nama, kode_singkat, wilayah_id) VALUES (?, ?, ?)",
            (nilai["nama"], nilai["kode_singkat"], nilai["wilayah_id"]),
        )
        audit.catat(kon, pengguna["id"], "buat", "kecamatan", kur.lastrowid,
                    None, nilai)
        return kur.lastrowid


def ubah_kecamatan(kecamatan_id: int, data: dict, pengguna) -> None:
    """Ganti nama, kode singkat, atau wilayah satu kecamatan.

    Mengubah kode singkat tidak menyentuh kode objek yang sudah terbit — yang
    ikut berubah hanya awalan objek yang didaftarkan setelah ini.
    """
    _pastikan_boleh(pengguna)
    lama = ambil_kecamatan(kecamatan_id)
    if not lama:
        raise GalatDaerah("Kecamatan tidak ditemukan.")
    nilai = {
        "nama": _nama_kecamatan(data.get("nama"), kecamatan_id),
        "kode_singkat": _kode_singkat(data.get("kode_singkat"), kecamatan_id),
        "wilayah_id": _wilayah_id(data.get("wilayah_id")),
    }
    berubah = {k: v for k, v in nilai.items() if lama[k] != v}
    if not berubah:
        return
    with db.buka() as kon:
        kon.execute(
            "UPDATE kecamatan SET nama = ?, kode_singkat = ?, wilayah_id = ? "
            "WHERE id = ?",
            (nilai["nama"], nilai["kode_singkat"], nilai["wilayah_id"], kecamatan_id),
        )
        audit.catat(kon, pengguna["id"], "ubah", "kecamatan", kecamatan_id,
                    {k: lama[k] for k in berubah}, berubah)


def hapus_kecamatan(kecamatan_id: int, pengguna) -> str:
    """Hapus kecamatan yang belum dipakai. Kembalikan namanya."""
    _pastikan_boleh(pengguna)
    lama = ambil_kecamatan(kecamatan_id)
    if not lama:
        raise GalatDaerah("Kecamatan tidak ditemukan.")
    # jumlah_objek hanya menghitung yang aktif; objek nonaktif barisnya masih
    # menunjuk ke sini, jadi dihitung ulang tanpa saringan is_aktif.
    dipakai = db.ambil_nilai(
        "SELECT COUNT(*) FROM objek_wakaf WHERE kecamatan_id = ?", (kecamatan_id,), 0)
    if dipakai:
        raise GalatDaerah(
            f"{lama['nama']} masih dipakai {dipakai} objek wakaf. Pindahkan "
            "objeknya dulu sebelum kecamatan ini dihapus.")
    if lama["jumlah_desa"]:
        raise GalatDaerah(
            f"{lama['nama']} masih punya {lama['jumlah_desa']} desa. "
            "Hapus desanya dulu.")
    if db.ambil_nilai("SELECT COUNT(*) FROM tim WHERE kecamatan_id = ?",
                      (kecamatan_id,), 0):
        raise GalatDaerah(f"{lama['nama']} masih tercantum di susunan tim.")
    with db.buka() as kon:
        kon.execute("DELETE FROM kecamatan WHERE id = ?", (kecamatan_id,))
        audit.catat(kon, pengguna["id"], "hapus", "kecamatan", kecamatan_id,
                    {k: lama[k] for k in ("nama", "kode_singkat", "wilayah_id")},
                    None)
    return lama["nama"]


def tambah_desa(kecamatan_id: int, nama, pengguna) -> int:
    _pastikan_boleh(pengguna)
    if not ambil_kecamatan(kecamatan_id):
        raise GalatDaerah("Kecamatan tidak ditemukan.")
    nama = _nama_desa(nama, kecamatan_id)
    with db.buka() as kon:
        kur = kon.execute("INSERT INTO desa (kecamatan_id, nama) VALUES (?, ?)",
                          (kecamatan_id, nama))
        audit.catat(kon, pengguna["id"], "buat", "desa", kur.lastrowid, None,
                    {"nama": nama, "kecamatan_id": kecamatan_id})
        return kur.lastrowid


def ubah_desa(desa_id: int, nama, pengguna) -> None:
    """Ganti nama desa. Kecamatannya sengaja tidak ikut bisa dipindah."""
    _pastikan_boleh(pengguna)
    lama = ambil_desa(desa_id)
    if not lama:
        raise GalatDaerah("Desa tidak ditemukan.")
    nama = _nama_desa(nama, lama["kecamatan_id"], desa_id)
    if nama == lama["nama"]:
        return
    with db.buka() as kon:
        kon.execute("UPDATE desa SET nama = ? WHERE id = ?", (nama, desa_id))
        audit.catat(kon, pengguna["id"], "ubah", "desa", desa_id,
                    {"nama": lama["nama"]}, {"nama": nama})


def hapus_desa(desa_id: int, pengguna) -> str:
    """Hapus desa yang belum dipakai objek wakaf. Kembalikan namanya."""
    _pastikan_boleh(pengguna)
    lama = ambil_desa(desa_id)
    if not lama:
        raise GalatDaerah("Desa tidak ditemukan.")
    dipakai = db.ambil_nilai(
        "SELECT COUNT(*) FROM objek_wakaf WHERE desa_id = ?", (desa_id,), 0)
    if dipakai:
        raise GalatDaerah(
            f"Desa {lama['nama']} masih dipakai {dipakai} objek wakaf. "
            "Pindahkan objeknya dulu sebelum desa ini dihapus.")
    with db.buka() as kon:
        kon.execute("DELETE FROM desa WHERE id = ?", (desa_id,))
        audit.catat(kon, pengguna["id"], "hapus", "desa", desa_id,
                    {"nama": lama["nama"], "kecamatan_id": lama["kecamatan_id"]},
                    None)
    return lama["nama"]
