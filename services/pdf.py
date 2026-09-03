"""Cetak PDF dengan reportlab platypus: rekap harian, daftar kendali, berita acara."""
import io

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (Paragraph, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

import config

_GAYA = getSampleStyleSheet()
_KOP1 = ParagraphStyle("kop1", parent=_GAYA["Title"], fontSize=13, leading=16,
                       alignment=TA_CENTER, spaceAfter=0)
_KOP2 = ParagraphStyle("kop2", parent=_GAYA["Normal"], fontSize=10.5, leading=14,
                       alignment=TA_CENTER, spaceAfter=10)
_ISI = ParagraphStyle("isi", parent=_GAYA["Normal"], fontSize=9, leading=12)
_SEL = ParagraphStyle("sel", parent=_GAYA["Normal"], fontSize=8, leading=10)

_GAYA_TABEL = TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0b6b3a")),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ("FONTSIZE", (0, 0), (-1, -1), 8),
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#bfcbd6")),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f4f7fa")]),
    ("LEFTPADDING", (0, 0), (-1, -1), 4),
    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
])


def _dokumen(judul: str):
    penampung = io.BytesIO()
    doc = SimpleDocTemplate(
        penampung, pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm, topMargin=2 * cm, bottomMargin=2 * cm,
        title=judul, author=config.NAMA_KANTOR,
    )
    return penampung, doc


def _kop(judul: str) -> list:
    return [
        Paragraph(judul, _KOP1),
        Paragraph(config.NAMA_KANTOR, _KOP2),
    ]


def _tabel(kolom: list[str], baris: list[list], lebar: list | None = None) -> Table:
    data = [[Paragraph(f"<b>{k}</b>", _SEL) for k in kolom]]
    for b in baris:
        data.append([Paragraph(str(v) if v not in (None, "") else "—", _SEL) for v in b])
    tabel = Table(data, colWidths=lebar, repeatRows=1)
    tabel.setStyle(_GAYA_TABEL)
    return tabel


def _tanda_tangan(jabatan: str = "Kepala Kantor") -> Table:
    tanggal = config.sekarang().strftime("%d %B %Y")
    isi = [[Paragraph(
        f"Bone Bolango, {tanggal}<br/>{jabatan}<br/><br/><br/><br/>"
        "(............................................)", _ISI)]]
    tabel = Table(isi, colWidths=[7 * cm], hAlign="RIGHT")
    tabel.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    return tabel


def rekap_harian(rekap: dict) -> bytes:
    penampung, doc = _dokumen("Rekap Harian Pergerakan Berkas")
    isi = _kop("REKAP HARIAN PERGERAKAN BERKAS WAKAF")
    isi.append(Paragraph(f"Tanggal: <b>{rekap['tanggal']}</b> — "
                         f"total pergerakan: <b>{rekap['total']}</b>", _ISI))
    isi.append(Spacer(1, 8))
    isi.append(_tabel(
        ["Tahapan", "Aksi", "Objek Wakaf", "Kecamatan", "Petugas", "Catatan"],
        [[b["tahapan_nama"], b["aksi"], b["nama_objek"], b["kecamatan_nama"],
          b["nama_pengguna"], b["catatan"]] for b in rekap["berkas"]],
        lebar=[2.6 * cm, 1.8 * cm, 4.4 * cm, 2.6 * cm, 2.6 * cm, 3.0 * cm],
    ))
    isi.append(Spacer(1, 18))
    isi.append(_tanda_tangan())
    doc.build(isi)
    return penampung.getvalue()


def rekap_potensi(baris: list[dict]) -> bytes:
    penampung, doc = _dokumen("Total Potensi Sertipikat Wakaf")
    isi = _kop("TOTAL POTENSI SERTIPIKAT WAKAF")
    data = [[b["kecamatan"], b["wilayah"], b["baru"], b["ada_hak"], b["isbat"], b["total"]]
            for b in baris]
    data.append(["TOTAL", "", sum(b["baru"] or 0 for b in baris),
                 sum(b["ada_hak"] or 0 for b in baris),
                 sum(b["isbat"] or 0 for b in baris),
                 sum(b["total"] or 0 for b in baris)])
    isi.append(_tabel(["Kecamatan", "Wilayah", "Baru", "Ada Hak", "Isbat", "Total"], data,
                      lebar=[4 * cm, 3 * cm, 2.2 * cm, 2.2 * cm, 2.2 * cm, 2.2 * cm]))
    isi.append(Spacer(1, 18))
    isi.append(_tanda_tangan())
    doc.build(isi)
    return penampung.getvalue()


def daftar_kendali(berkas: dict, linimasa: list[dict], ceklis: list[dict]) -> bytes:
    """Lembar kendali per berkas, untuk arsip fisik."""
    penampung, doc = _dokumen("Daftar Kendali Berkas")
    isi = _kop("DAFTAR KENDALI BERKAS WAKAF")
    isi.append(_tabel(["Uraian", "Isi"], [
        ["Nomor Berkas", berkas.get("no_berkas")],
        ["Objek Wakaf", f"{berkas['nama_objek']} ({berkas['objek_kode']})"],
        ["Kecamatan / Wilayah", f"{berkas['kecamatan_nama']} / {berkas.get('wilayah_nama')}"],
        ["Jenis Permohonan", berkas["jenis_nama"]],
        ["Tahapan Sekarang", berkas["tahapan_nama"]],
        ["Tanggal Daftar", berkas.get("tanggal_daftar")],
        ["Target Penyerahan", berkas.get("target_penyerahan")],
        ["Petugas", berkas.get("petugas_nama")],
    ], lebar=[5 * cm, 11.9 * cm]))
    isi.append(Spacer(1, 12))

    isi.append(Paragraph("<b>Ceklis Persyaratan</b>", _ISI))
    isi.append(Spacer(1, 4))
    isi.append(_tabel(["No", "Persyaratan", "Wajib", "Terpenuhi", "Catatan"],
                      [[i, c["nama"], "Ya" if c["wajib"] else "Tidak",
                        "✓" if c["terpenuhi"] else "", c["catatan"]]
                       for i, c in enumerate(ceklis, 1)],
                      lebar=[1 * cm, 8 * cm, 1.6 * cm, 2 * cm, 4.3 * cm]))
    isi.append(Spacer(1, 12))

    isi.append(Paragraph("<b>Riwayat Tahapan</b>", _ISI))
    isi.append(Spacer(1, 4))
    isi.append(_tabel(["Tanggal", "Tahapan", "Aksi", "Petugas", "Catatan"],
                      [[r["tanggal"], r["tahapan_nama"], r["aksi"],
                        r["nama_pengguna"], r["catatan"]] for r in linimasa],
                      lebar=[2.4 * cm, 4 * cm, 2 * cm, 3.5 * cm, 5 * cm]))
    isi.append(Spacer(1, 18))
    isi.append(_tanda_tangan("Petugas"))
    doc.build(isi)
    return penampung.getvalue()


def berita_acara(berkas: dict, penerima: str = "", tanggal: str | None = None) -> bytes:
    penampung, doc = _dokumen("Berita Acara Penyerahan Sertipikat")
    tanggal = tanggal or config.hari_ini_iso()
    isi = _kop("BERITA ACARA PENYERAHAN SERTIPIKAT TANAH WAKAF")
    isi.append(Paragraph(
        f"Pada hari ini, tanggal {tanggal}, bertempat di {config.NAMA_KANTOR}, "
        "telah dilakukan penyerahan sertipikat tanah wakaf dengan rincian sebagai berikut:",
        _ISI))
    isi.append(Spacer(1, 10))
    isi.append(_tabel(["Uraian", "Isi"], [
        ["Objek Wakaf", berkas["nama_objek"]],
        ["Kode Objek", berkas["objek_kode"]],
        ["Nomor Berkas", berkas.get("no_berkas")],
        ["Kecamatan", berkas["kecamatan_nama"]],
        ["Jenis Permohonan", berkas["jenis_nama"]],
        ["Diterima oleh (Nadzir)", penerima],
    ], lebar=[5 * cm, 11.9 * cm]))
    isi.append(Spacer(1, 10))
    isi.append(Paragraph(
        "Demikian berita acara ini dibuat dengan sebenarnya untuk dipergunakan "
        "sebagaimana mestinya.", _ISI))
    isi.append(Spacer(1, 24))
    isi.append(Table([[Paragraph("Yang Menyerahkan,<br/><br/><br/><br/>"
                                 "(..................................)", _ISI),
                       Paragraph("Yang Menerima,<br/><br/><br/><br/>"
                                 "(..................................)", _ISI)]],
                     colWidths=[8.4 * cm, 8.4 * cm]))
    doc.build(isi)
    return penampung.getvalue()
