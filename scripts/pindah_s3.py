"""Pindahkan berkas dokumen dari disk ke bucket S3.

Kunci di S3 dibuat sama persis dengan kolom `dokumen.path` yang sudah ada, jadi
skrip ini tidak menyentuh database sama sekali — tidak ada migrasi skema, dan
kalau ternyata bermasalah tinggal kembalikan PENYIMPANAN ke `lokal`.

    python -m scripts.pindah_s3 --dry-run     # lihat apa yang akan diunggah
    python -m scripts.pindah_s3               # unggah yang belum ada di bucket
    python -m scripts.pindah_s3 --periksa     # cocokkan ukuran disk vs bucket

Sumbernya selalu dibaca dari disk lewat config.UPLOAD_DIR, tujuannya selalu S3,
berapa pun nilai PENYIMPANAN saat skrip dijalankan. Setelah --periksa bersih,
baru PENYIMPANAN dibalik ke `s3` lalu layanan di-restart. File di disk sengaja
tidak dihapus.
"""
import argparse
import sys

import config
import db
from services import dokumen as svc_dokumen, penyimpanan


def _baris_dokumen() -> list[dict]:
    """Semua dokumen berupa file, termasuk yang sudah ditandai terhapus.

    Yang terhapus ikut dipindah supaya penghapusan tetap bisa dibatalkan setelah
    disk lama dibersihkan.
    """
    return db.ambil_semua(
        "SELECT id, path, nama_file, ukuran_byte, is_aktif FROM dokumen "
        "WHERE path IS NOT NULL AND path <> '' ORDER BY id"
    )


def jalankan(dry_run: bool, hanya_periksa: bool) -> int:
    if not config.S3_BUCKET:
        print("S3_BUCKET belum diisi.", file=sys.stderr)
        return 2

    sumber_dir = config.UPLOAD_DIR
    # Tujuan selalu S3; pembacaan dari disk dilakukan langsung, bukan lewat backend.
    config.PENYIMPANAN = "s3"
    penyimpanan.lupakan_klien()

    baris = _baris_dokumen()
    print(f"{len(baris)} dokumen berupa file di database.")
    print(f"Sumber : {sumber_dir}")
    print(f"Tujuan : s3://{config.S3_BUCKET}/{(config.S3_PREFIX or '').strip('/')}\n")

    naik = lewat = hilang = beda = gagal = 0
    for d in baris:
        kunci = d["path"]
        try:
            sumber = sumber_dir / penyimpanan.periksa_kunci(kunci)
        except penyimpanan.KunciTidakSah:
            print(f"  ! dokumen {d['id']}: kunci tidak sah {kunci!r}")
            gagal += 1
            continue

        try:
            di_bucket = penyimpanan.ukuran(kunci)
        except penyimpanan.GagalPenyimpanan as galat:
            print(f"  ! dokumen {d['id']}: bucket tidak bisa dihubungi — {galat}")
            return 2

        if not sumber.is_file():
            # Baris menggantung: filenya sudah tidak ada di disk sejak sebelum ini.
            tanda = "sudah di bucket" if di_bucket is not None else "TIDAK ADA di bucket"
            print(f"  ? dokumen {d['id']}: {kunci} hilang dari disk — {tanda}")
            hilang += 1
            continue

        besar = sumber.stat().st_size
        if di_bucket is not None:
            if di_bucket != besar:
                print(f"  ! dokumen {d['id']}: ukuran beda — disk {besar} B, "
                      f"bucket {di_bucket} B")
                beda += 1
            else:
                lewat += 1
            continue

        if hanya_periksa:
            print(f"  - dokumen {d['id']}: {kunci} belum ada di bucket")
            beda += 1
            continue
        if dry_run:
            print(f"  + akan unggah {kunci} ({besar} B)")
            naik += 1
            continue

        try:
            penyimpanan.simpan(kunci, sumber.read_bytes(),
                               svc_dokumen.TIPE_MIME.get(sumber.suffix.lower(),
                                                         "application/octet-stream"))
            naik += 1
        except Exception as galat:
            print(f"  ! dokumen {d['id']}: gagal unggah — {galat}")
            gagal += 1

    print(f"\nDiunggah {naik} · sudah ada {lewat} · hilang dari disk {hilang} · "
          f"belum cocok {beda} · gagal {gagal}")
    if gagal or beda:
        print("Belum aman dibalik ke PENYIMPANAN=s3.")
        return 1
    if dry_run:
        print("Pratinjau saja — belum ada yang diunggah.")
        return 0
    print("Semua berkas di disk sudah ada di bucket dengan ukuran sama.")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Pindahkan berkas dokumen ke S3.")
    p.add_argument("--dry-run", action="store_true", help="tampilkan saja, jangan unggah")
    p.add_argument("--periksa", action="store_true",
                   help="cuma cocokkan disk dengan bucket, jangan unggah")
    a = p.parse_args()
    return jalankan(a.dry_run, a.periksa)


if __name__ == "__main__":
    raise SystemExit(main())
