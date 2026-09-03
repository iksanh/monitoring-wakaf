"""Penulis log_audit — dipakai semua service yang mengubah data."""
import json

import db


def _ringkas(data) -> str | None:
    if data is None:
        return None
    if isinstance(data, str):
        return data
    return json.dumps(data, ensure_ascii=False, default=str)


def catat(kon, pengguna_id, aksi: str, tabel: str, ref_id, data_lama=None, data_baru=None) -> None:
    """Catat perubahan. `kon` boleh None kalau tidak sedang dalam transaksi."""
    sql = """INSERT INTO log_audit (pengguna_id, aksi, tabel, ref_id, data_lama, data_baru)
             VALUES (?, ?, ?, ?, ?, ?)"""
    params = (pengguna_id, aksi, tabel, ref_id, _ringkas(data_lama), _ringkas(data_baru))
    if kon is None:
        db.jalankan(sql, params)
    else:
        kon.execute(sql, params)


def riwayat(tabel: str, ref_id: int, batas: int = 20) -> list[dict]:
    return db.ambil_semua(
        """SELECT a.*, p.nama AS nama_pengguna
             FROM log_audit a LEFT JOIN pengguna p ON p.id = a.pengguna_id
            WHERE a.tabel = ? AND a.ref_id = ?
            ORDER BY a.id DESC LIMIT ?""",
        (tabel, ref_id, batas),
    )
