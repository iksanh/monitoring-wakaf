"""CLI impor Excel.

    python -m scripts.impor "data_master/Rekapan Wakaf Bone bolango.xlsx" --dry-run
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import db  # noqa: E402
from services import impor_simpan  # noqa: E402


def utama(argv=None) -> int:
    p = argparse.ArgumentParser(description="Impor Rekapan Wakaf dari Excel.")
    p.add_argument("berkas", help="path file .xlsx")
    p.add_argument("--dry-run", action="store_true",
                   help="hanya pratinjau, semua perubahan di-rollback")
    arg = p.parse_args(argv)

    if not Path(arg.berkas).exists():
        print(f"File tidak ditemukan: {arg.berkas}")
        return 2

    db.siapkan()
    laporan = impor_simpan.impor(arg.berkas, dry_run=arg.dry_run)
    print(impor_simpan.teks_laporan(laporan))
    if arg.dry_run:
        print("\n(dry-run — tidak ada yang ditulis ke database)")
    return 0


if __name__ == "__main__":
    raise SystemExit(utama())
