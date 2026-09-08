"""Cetak panduan PDF "Mengubah Data Berkas" untuk pegawai.

Isinya statis — bukan laporan dari database — jadi tinggal di scripts/, bukan
di services/pdf.py yang khusus cetakan berdata. Jalankan ulang setiap kali
halaman /berkas/{id}/ubah berubah supaya panduannya tidak basi.

    python -m scripts.manual_ubah_berkas                 # -> Panduan-Ubah-Berkas.pdf
    python -m scripts.manual_ubah_berkas /path/lain.pdf
"""
import sys

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (ListFlowable, ListItem, Paragraph,
                                SimpleDocTemplate, Spacer, Table, TableStyle)

import config

HIJAU = colors.HexColor("#0b6b3a")
KUNING_MUDA = colors.HexColor("#fdf4e0")
KUNING_GARIS = colors.HexColor("#ecd08a")
ABU_MUDA = colors.HexColor("#f4f7fa")
GARIS = colors.HexColor("#bfcbd6")

_G = getSampleStyleSheet()
JUDUL = ParagraphStyle("judul", parent=_G["Title"], fontSize=16, leading=20,
                       textColor=HIJAU, alignment=TA_CENTER, spaceAfter=2)
SUBJUDUL = ParagraphStyle("subjudul", parent=_G["Normal"], fontSize=10.5, leading=14,
                          alignment=TA_CENTER, spaceAfter=16)
BAGIAN = ParagraphStyle("bagian", parent=_G["Heading2"], fontSize=12, leading=15,
                        textColor=HIJAU, spaceBefore=14, spaceAfter=6,
                        keepWithNext=1)
ISI = ParagraphStyle("isi", parent=_G["Normal"], fontSize=9.5, leading=13.5,
                     spaceAfter=6)
SEL = ParagraphStyle("sel", parent=_G["Normal"], fontSize=8.5, leading=11.5)
CATATAN = ParagraphStyle("catatan", parent=ISI, fontSize=9, leading=12.5, spaceAfter=0)
KAKI = ParagraphStyle("kaki", parent=_G["Normal"], fontSize=7.5, leading=10,
                      textColor=colors.HexColor("#6b7885"))

GAYA_TABEL = TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), HIJAU),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("GRID", (0, 0), (-1, -1), 0.4, GARIS),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, ABU_MUDA]),
    ("LEFTPADDING", (0, 0), (-1, -1), 5),
    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ("TOPPADDING", (0, 0), (-1, -1), 4),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
])


def tabel(kolom, baris, lebar):
    data = [[Paragraph(f"<b>{k}</b>", SEL) for k in kolom]]
    data += [[Paragraph(str(v), SEL) for v in b] for b in baris]
    t = Table(data, colWidths=lebar, repeatRows=1)
    t.setStyle(GAYA_TABEL)
    return t


def kotak(judul, teks, warna=KUNING_MUDA, garis=KUNING_GARIS):
    """Kotak peringatan/catatan supaya hal penting tidak terlewat saat dibaca cepat."""
    isi = Paragraph(f"<b>{judul}</b><br/>{teks}", CATATAN)
    t = Table([[isi]], colWidths=[16.4 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), warna),
        ("BOX", (0, 0), (-1, -1), 0.6, garis),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    return [Spacer(1, 2), t, Spacer(1, 8)]


def langkah(butir):
    return ListFlowable([ListItem(Paragraph(b, ISI), leftIndent=16) for b in butir],
                        bulletType="1", leftIndent=14, bulletFontSize=9.5)


def poin(butir):
    return ListFlowable([ListItem(Paragraph(b, ISI), leftIndent=16) for b in butir],
                        bulletType="bullet", start="•", leftIndent=14, bulletFontSize=9.5)


def bagian(nomor, judul):
    return Paragraph(f"{nomor}. {judul}", BAGIAN)


def _kaki_halaman(kanvas, doc):
    kanvas.saveState()
    kanvas.setFont("Helvetica", 7.5)
    kanvas.setFillColor(colors.HexColor("#6b7885"))
    kanvas.drawString(2 * cm, 1.2 * cm,
                      f"Panduan Mengubah Data Berkas — {config.NAMA_KANTOR}")
    kanvas.drawRightString(19 * cm, 1.2 * cm, f"Halaman {doc.page}")
    kanvas.restoreState()


def susun() -> list:
    tanggal = config.sekarang().strftime("%d %B %Y")
    isi = [
        Paragraph("PANDUAN MENGUBAH DATA BERKAS", JUDUL),
        Paragraph(f"Aplikasi Sertipikasi Tanah Wakaf<br/>{config.NAMA_KANTOR}<br/>"
                  f"Disusun {tanggal}", SUBJUDUL),
    ]

    isi.append(bagian(1, "Kapan panduan ini dipakai"))
    isi.append(Paragraph(
        "Halaman <b>Ubah Berkas</b> dipakai untuk <b>memperbaiki data yang salah "
        "tercatat</b> — salah ketik nomor berkas, salah pilih jenis permohonan di "
        "loket, atau tahapan yang tidak sesuai keadaan sebenarnya di lapangan.", ISI))
    isi.append(Paragraph(
        "Halaman ini <b>bukan</b> untuk menjalankan berkas. Menggerakkan berkas dari "
        "satu tahapan ke tahapan berikutnya tetap lewat tombol tahapan di halaman "
        "berkas seperti biasa.", ISI))

    isi.append(bagian(2, "Siapa boleh mengubah apa"))
    isi.append(tabel(
        ["Yang diubah", "Admin", "Sekretariat", "Petugas Loket", "Korwil / Petugas"],
        [["Nomor berkas, tanggal daftar, target, petugas, catatan",
          "Ya", "Ya", "Ya", "Tidak"],
         ["Jenis permohonan", "Ya", "Ya", "Tidak", "Tidak"],
         ["Tahapan (koreksi)", "Ya", "Ya", "Tidak", "Tidak"],
         ["Status berkas (batal)", "Ya", "Ya", "Tidak", "Tidak"]],
        lebar=[6.4 * cm, 2 * cm, 2.6 * cm, 2.8 * cm, 2.6 * cm]))
    isi.append(Spacer(1, 4))
    isi.append(Paragraph(
        "Korwil dan petugas lapangan tidak melihat tombol <i>Ubah Berkas</i>. Mereka "
        "tetap bisa menggerakkan tahapan dan mengisi ceklis seperti biasa.", ISI))

    isi.append(bagian(3, "Membuka halaman Ubah Berkas"))
    isi.append(langkah([
        "Buka menu <b>Berkas</b>.",
        "Cari berkasnya — pakai kotak pencarian (nama objek atau nomor berkas) atau "
        "filter kecamatan/tahapan.",
        "Klik berkasnya untuk membuka halaman detail.",
        "Klik tombol <b>Ubah Berkas</b> di bagian atas halaman.",
    ]))
    isi.extend(kotak(
        "Tombol Ubah Berkas tidak muncul?",
        "Dua kemungkinan: (a) peran akun Anda tidak berhak — lihat tabel di bagian 2; "
        "atau (b) berkas itu sudah <b>dibatalkan</b>. Berkas batal memang tidak bisa "
        "diubah lagi; objeknya sudah kembali jadi objek wakaf biasa dan tinggal "
        "didaftarkan ulang dari halaman objek."))

    isi.append(bagian(4, "Bagian A — Data administratif"))
    isi.append(Paragraph(
        "Bagian ini terbuka untuk semua peran yang berhak dan tidak perlu alasan.", ISI))
    isi.append(tabel(
        ["Isian", "Keterangan"],
        [["Nomor Berkas",
          "Nomor dari loket KKP. <b>Boleh dikosongkan</b> — banyak berkas lama memang "
          "belum punya nomor. Isi kalau nomornya sudah keluar, atau perbaiki kalau "
          "salah ketik."],
         ["Tanggal Daftar Loket",
          "Tanggal berkas diterima di loket. Mengisi tanggal di sini <b>tidak</b> "
          "memindahkan tahapan (lihat kotak di bawah)."],
         ["Target Penyerahan", "Target sertipikat diserahkan ke nadzir. Boleh kosong."],
         ["Petugas", "Petugas yang memegang berkas. Boleh dikosongkan."],
         ["Catatan", "Catatan bebas — mis. alasan nomor berkas diperbaiki."]],
        lebar=[4.2 * cm, 12.2 * cm]))
    isi.extend(kotak(
        "Mengisi tanggal daftar tidak memindahkan tahapan",
        "Berkas yang masih di tahapan <i>Akan Didaftar</i> tetap di situ walaupun "
        "tanggal daftarnya diisi. Untuk memindahkannya, pakai tombol tahapan di "
        "halaman berkas — atau, kalau memang salah catat sejak awal, pakai koreksi "
        "tahapan di bagian 6."))
    isi.append(Paragraph(
        "Setelah selesai, tekan <b>Simpan Perubahan</b>.", ISI))

    isi.append(bagian(5, "Bagian B — Koreksi jenis permohonan"))
    isi.append(Paragraph(
        "Hanya untuk <b>Admin</b> dan <b>Sekretariat</b>. Dipakai kalau jenis "
        "permohonannya salah dipilih waktu berkas didaftarkan di loket — misalnya "
        "dicatat <i>Pendaftaran Pertama Kali</i> padahal tanahnya sudah bersertipikat.",
        ISI))
    isi.append(langkah([
        "Di halaman Ubah Berkas, klik bagian kuning "
        "<b>Koreksi jenis permohonan / tahapan</b> untuk membukanya.",
        "Pada <b>Jenis Permohonan</b>, pilih jenis yang benar. Isian ini sudah "
        "terisi jenis berkas sekarang — biarkan apa adanya kalau tidak mau diubah.",
        "Isi <b>Alasan Koreksi</b>. Wajib — perubahan ditolak kalau alasannya kosong.",
        "Tekan <b>Simpan Perubahan</b>.",
    ]))
    isi.append(Paragraph("<b>Yang terjadi setelah disimpan:</b>", ISI))
    isi.append(poin([
        "Ceklis persyaratan <b>disusun ulang</b> mengikuti jenis yang baru.",
        "Syarat yang namanya sama persis di kedua jenis (mis. AIW/APAIW, Surat "
        "Pengesahan Nazir, surat kuasa) <b>tetap tercentang</b> beserta catatannya — "
        "tidak perlu diperiksa ulang.",
        "Syarat khas jenis lama hilang dari ceklis. Contoh: <i>Surat Tanah</i> pada "
        "Pendaftaran Pertama Kali diganti <i>Sertipikat Asli</i> pada Wakaf dari "
        "Tanah Terdaftar.",
        "Keadaan ceklis sebelum diubah tersimpan lengkap di log audit, jadi masih "
        "bisa ditelusuri kalau ada pertanyaan.",
    ]))
    isi.extend(kotak(
        "Periksa ceklisnya setelah ganti jenis",
        "Buka halaman berkas dan lihat bagian Ceklis. Syarat baru yang belum pernah "
        "diperiksa akan tampil belum tercentang — itu normal, memang perlu diperiksa."))

    isi.append(bagian(6, "Bagian C — Koreksi tahapan"))
    isi.append(Paragraph(
        "Hanya untuk <b>Admin</b> dan <b>Sekretariat</b>. Dipakai kalau posisi berkas "
        "di aplikasi tidak sesuai keadaan sebenarnya — misalnya berkas sudah di "
        "Panitia A sejak bulan lalu tapi di aplikasi masih tercatat Permohonan, atau "
        "sebaliknya ada yang salah klik sehingga terlanjur maju.", ISI))
    isi.append(langkah([
        "Buka bagian kuning <b>Koreksi jenis permohonan / tahapan</b>.",
        "Pada <b>Tahapan</b>, pilih tahapan yang benar. Isian ini sudah terisi "
        "tahapan berkas sekarang.",
        "Isi <b>Alasan Koreksi</b>. Wajib.",
        "Tekan <b>Simpan Perubahan</b>.",
    ]))
    isi.append(Paragraph("<b>Yang terjadi setelah disimpan:</b>", ISI))
    isi.append(poin([
        "Koreksi <b>tercatat di riwayat tahapan</b> berkas, lengkap dengan alasan dan "
        "nama yang mengubah. Jejak lama tidak dihapus.",
        "Kalau tahapannya <b>maju</b>, tercatat sebagai <i>masuk</i>. Kalau "
        "<b>mundur</b>, tercatat sebagai <i>mundur</i>.",
        "Berkas yang terlanjur berstatus <b>selesai</b> akan <b>dibuka lagi jadi "
        "aktif</b> kalau tahapannya ditarik mundur, supaya rekap tidak salah hitung.",
        "Rekap harian dan papan kendali langsung ikut menyesuaikan — semua angka "
        "dihitung dari riwayat ini.",
    ]))
    isi.extend(kotak(
        "Koreksi, bukan jalan pintas",
        "Untuk berkas yang berjalan normal, gerakkan lewat tombol tahapan di halaman "
        "berkas — di situ ada pemeriksaan ceklis syarat sebelum masuk Pengukuran. "
        "Koreksi di halaman ini melewati pemeriksaan itu karena dipakai untuk "
        "membetulkan catatan atas kejadian yang sudah lewat.",
        warna=colors.HexColor("#fdecec"), garis=colors.HexColor("#e8b4b4")))

    isi.append(bagian(7, "Yang tidak bisa diubah di halaman ini"))
    isi.append(tabel(
        ["Mau mengubah", "Jalurnya"],
        [["Status berkas jadi <b>Batal</b>",
          "Halaman berkas → <b>Batalkan pendaftaran</b> (admin/sekretariat, wajib "
          "beralasan). Objeknya kembali jadi objek wakaf biasa dan bisa didaftarkan "
          "ulang."],
         ["Objek wakaf dari sebuah berkas",
          "Tidak bisa dipindah. Batalkan berkasnya, lalu daftarkan berkas baru dari "
          "objek yang benar."],
         ["Data objek wakaf (nama, luas, tipologi, dll)",
          "Halaman <b>Objek Wakaf</b> → buka objeknya → Ubah."],
         ["Status bisa/tidak bisa ditindaklanjuti",
          "Halaman <b>Objek Wakaf</b> → pemilahan (admin/korwil)."],
         ["Berkas yang sudah dibatalkan",
          "Tidak bisa dikoreksi lagi. Daftarkan ulang objeknya."]],
        lebar=[5.4 * cm, 11 * cm]))

    isi.append(bagian(8, "Kalau muncul pesan galat"))
    isi.append(tabel(
        ["Pesan", "Artinya"],
        [["Perubahan jenis permohonan atau tahapan wajib disertai alasan.",
          "Anda mengubah jenis atau tahapan tapi kolom Alasan Koreksi kosong. Isi "
          "alasannya, lalu simpan lagi. Data administratif belum ikut tersimpan — "
          "isian Anda masih utuh di layar."],
         ["Koreksi gagal: Berkas ini sudah dibatalkan.",
          "Berkas batal tidak bisa dikoreksi. Daftarkan ulang objeknya."],
         ["Koreksi gagal: Berkas sudah ada di tahapan itu.",
          "Tahapan yang dipilih sama dengan tahapan sekarang — tidak ada yang perlu "
          "diubah."],
         ["Berkas ini di luar wilayah Anda.",
          "Akun korwil/petugas hanya bisa membuka berkas di wilayahnya sendiri."]],
        lebar=[6.6 * cm, 9.8 * cm]))

    isi.append(bagian(9, "Semua perubahan tercatat"))
    isi.append(Paragraph(
        "Setiap perubahan di halaman ini menulis <b>log audit</b>: siapa yang "
        "mengubah, kapan, isi sebelum dan sesudahnya. Koreksi tahapan juga muncul di "
        "riwayat tahapan berkas. Jadi tidak ada perubahan yang hilang jejak — kalau "
        "ada yang keliru, masih bisa ditelusuri dan dibetulkan.", ISI))
    isi.append(Spacer(1, 10))
    isi.append(Paragraph(
        "Kalau ragu, <b>jangan tebak-tebak</b> — tanya admin aplikasi dulu. "
        "Memperbaiki data yang salah lebih repot daripada menanyakannya.", ISI))
    return isi


def buat(tujuan: str) -> str:
    doc = SimpleDocTemplate(
        tujuan, pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm, topMargin=2 * cm, bottomMargin=2 * cm,
        title="Panduan Mengubah Data Berkas", author=config.NAMA_KANTOR,
    )
    doc.build(susun(), onFirstPage=_kaki_halaman, onLaterPages=_kaki_halaman)
    return tujuan


if __name__ == "__main__":
    tujuan = sys.argv[1] if len(sys.argv) > 1 else "Panduan-Ubah-Berkas.pdf"
    print("Tersimpan:", buat(tujuan))
