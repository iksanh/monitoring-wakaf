#!/usr/bin/env bash
# Cadangkan database wakaf: salin aman -> cek integritas -> kompres -> unggah S3.
set -euo pipefail

DB_PATH="${DB_PATH:-/data/wakaf.db}"
TUJUAN_S3="${TUJUAN_S3:-s3://cadangan-bpn-bonbol/app-wakaf}"
SIMPAN_HARI="${SIMPAN_HARI:-30}"
STEMPEL="$(TZ=Asia/Makassar date +%Y%m%d-%H%M)"
KERJA="$(mktemp -d)"
trap 'rm -rf "$KERJA"' EXIT

SALINAN="$KERJA/wakaf-$STEMPEL.db"

# .backup aman dijalankan saat aplikasi sedang menulis (mode WAL).
sqlite3 "$DB_PATH" ".backup '$SALINAN'"

HASIL="$(sqlite3 "$SALINAN" 'PRAGMA integrity_check;')"
if [ "$HASIL" != "ok" ]; then
    echo "GAGAL: integrity_check -> $HASIL" >&2
    exit 1
fi

gzip -9 "$SALINAN"
ARSIP="$SALINAN.gz"

if command -v aws >/dev/null 2>&1; then
    aws s3 cp "$ARSIP" "$TUJUAN_S3/$(basename "$ARSIP")"
else
    echo "aws CLI tidak ada — salinan ditinggal di /data/cadangan" >&2
    mkdir -p /data/cadangan
    cp "$ARSIP" /data/cadangan/
fi

# Cadangan lokal lama dibersihkan.
find /data/cadangan -name 'wakaf-*.db.gz' -mtime "+$SIMPAN_HARI" -delete 2>/dev/null || true

echo "Cadangan selesai: $(basename "$ARSIP")"
