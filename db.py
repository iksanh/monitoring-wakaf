"""Koneksi SQLite dan runner migrasi. Tidak ada ORM — SQL ditulis eksplisit."""
import sqlite3
from pathlib import Path

import config

_MIGRASI_DIR = config.AKAR / "migrations"


def koneksi() -> sqlite3.Connection:
    """Koneksi baru. Pemanggil bertanggung jawab menutup (pakai `with tutup(...)`)."""
    kon = sqlite3.connect(config.DB_PATH, timeout=15)
    kon.row_factory = sqlite3.Row
    kon.execute("PRAGMA foreign_keys=ON")
    return kon


class buka:
    """Context manager koneksi: commit kalau sukses, rollback kalau gagal."""

    def __enter__(self) -> sqlite3.Connection:
        self.kon = koneksi()
        return self.kon

    def __exit__(self, tipe, nilai, jejak):
        try:
            if tipe is None:
                self.kon.commit()
            else:
                self.kon.rollback()
        finally:
            self.kon.close()
        return False


def ambil_semua(sql: str, params=()) -> list[dict]:
    with buka() as kon:
        return [dict(b) for b in kon.execute(sql, params).fetchall()]


def ambil_satu(sql: str, params=()) -> dict | None:
    with buka() as kon:
        baris = kon.execute(sql, params).fetchone()
        return dict(baris) if baris else None


def ambil_nilai(sql: str, params=(), bawaan=None):
    baris = ambil_satu(sql, params)
    if not baris:
        return bawaan
    return next(iter(baris.values()))


def jalankan(sql: str, params=()) -> int:
    """Jalankan satu perintah tulis, kembalikan lastrowid."""
    with buka() as kon:
        kur = kon.execute(sql, params)
        return kur.lastrowid


def _jalankan_migrasi(kon, nama: str, isi: str) -> None:
    """Jalankan satu berkas migrasi dalam satu transaksi.

    foreign_keys dimatikan selama migrasi jalan. Membangun ulang tabel — satu-
    satunya cara SQLite mengubah CHECK constraint — berarti DROP TABLE induk yang
    masih ditunjuk tabel anak, dan itu selalu ditolak selama penegakan FK menyala.
    PRAGMA-nya tidak bisa diubah dari dalam transaksi, jadi harus di luar BEGIN.
    (PRAGMA defer_foreign_keys tidak menolong: penghitung pelanggarannya sudah
    naik saat DROP dan tidak turun lagi meski tabel penggantinya dibuat.)

    Gantinya, PRAGMA foreign_key_check dijalankan sebelum COMMIT. Kalau migrasi
    meninggalkan baris yatim, transaksinya dibatalkan — jadi mematikan penegakan
    FK di sini tidak berarti kehilangan jaring pengamannya.
    """
    kon.execute("PRAGMA foreign_keys=OFF")
    try:
        # executescript menutup transaksi yang menggantung sebelum jalan, jadi
        # BEGIN di bawah ini yang berlaku. COMMIT sengaja tidak ikut di skrip —
        # foreign_key_check harus sempat jalan sebelum perubahannya dikunci.
        kon.executescript("BEGIN;\n" + isi)
        yatim = kon.execute("PRAGMA foreign_key_check").fetchall()
        if yatim:
            raise RuntimeError(
                f"meninggalkan baris yatim di tabel: "
                + ", ".join(sorted({b[0] for b in yatim}))
            )
        kon.execute("COMMIT")
    except Exception as galat:
        kon.rollback()
        raise RuntimeError(f"Migrasi gagal: {nama} — {galat}") from galat
    finally:
        kon.execute("PRAGMA foreign_keys=ON")


def siapkan() -> list[str]:
    """Jalankan migrasi yang belum pernah dijalankan. Kembalikan daftar versi baru."""
    Path(config.DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    kon = koneksi()
    try:
        kon.execute("PRAGMA journal_mode=WAL")
        kon.execute(
            """CREATE TABLE IF NOT EXISTS skema_versi (
                   versi TEXT PRIMARY KEY,
                   dijalankan_pada TEXT NOT NULL DEFAULT (datetime('now','+8 hours'))
               )"""
        )
        kon.commit()
        sudah = {b["versi"] for b in kon.execute("SELECT versi FROM skema_versi")}
        baru = []
        for berkas in sorted(_MIGRASI_DIR.glob("*.sql")):
            if berkas.name in sudah:
                continue
            isi = berkas.read_text(encoding="utf-8")
            _jalankan_migrasi(kon, berkas.name, isi)
            kon.execute("INSERT INTO skema_versi (versi) VALUES (?)", (berkas.name,))
            kon.commit()
            baru.append(berkas.name)
        return baru
    finally:
        kon.close()
