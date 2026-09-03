@echo off
rem ============================================================
rem  siapkan-lingkungan.bat - dipanggil lewat CALL oleh
rem  jalankan.bat / tes.bat / impor.bat.
rem  Sengaja TANPA setlocal supaya variabel (VPY dan isi .env)
rem  ikut terbawa ke berkas pemanggil.
rem ============================================================

set "AKAR=%~dp0"
set "VPY=%AKAR%venv\Scripts\python.exe"

if exist "%VPY%" goto cek_paket

rem ---------- 1. Cari Python dan buat virtual environment ----------
echo   [1] Membuat virtual environment di venv\ ...
set "PY="
py -3 --version >nul 2>&1 && set "PY=py -3"
if defined PY goto py_ketemu
python --version >nul 2>&1 && set "PY=python"
:py_ketemu
if not defined PY goto tanpa_python

%PY% -m venv "%AKAR%venv"
if errorlevel 1 goto gagal_venv
if not exist "%VPY%" goto gagal_venv

rem ---------- 2. Pasang dependensi ----------
:cek_paket
if "%PASANG_ULANG%"=="1" del /q "%AKAR%venv\.paket-terpasang" >nul 2>&1
if exist "%AKAR%venv\.paket-terpasang" goto cek_env

echo   [2] Memasang dependensi dari requirements.txt ...
echo       (hanya sekali, bisa makan beberapa menit)
"%VPY%" -m pip install --disable-pip-version-check --quiet --upgrade pip
"%VPY%" -m pip install --disable-pip-version-check -r "%AKAR%requirements.txt"
if errorlevel 1 goto gagal_pip
> "%AKAR%venv\.paket-terpasang" echo %DATE% %TIME%

rem ---------- 3. Buat .env kalau belum ada ----------
:cek_env
if exist "%AKAR%.env" goto muat_env

echo   [3] Membuat berkas .env dengan SECRET_KEY acak ...
set "KUNCI="
"%VPY%" -c "import secrets;print(secrets.token_hex(32))" > "%TEMP%\wakaf_kunci.tmp"
if errorlevel 1 goto gagal_kunci
set /p KUNCI=<"%TEMP%\wakaf_kunci.tmp"
del "%TEMP%\wakaf_kunci.tmp" >nul 2>&1
if not defined KUNCI goto gagal_kunci
(
echo # Konfigurasi lokal Windows. Dibuat otomatis oleh siapkan-lingkungan.bat.
echo # Berkas ini masuk .gitignore - jangan dikirim ke repo.
echo SECRET_KEY=!KUNCI!
echo DB_PATH=%AKAR%wakaf.db
echo UPLOAD_DIR=%AKAR%data_berkas
echo DATA_SUMBER_DIR=%AKAR%data_master
echo TZ=Asia/Makassar
echo # DEBUG=1 wajib untuk jalan lokal lewat http:// -- kalau 0, cookie
echo # sesi dikunci https_only dan login lewat http selalu gagal.
echo DEBUG=1
echo NAMA_KANTOR=Kantor Pertanahan Kabupaten Bone Bolango
echo # Sandi admin awal. Kosongkan supaya dibuatkan acak dan
echo # dicetak sekali ke konsol saat database masih kosong.
echo ADMIN_PASSWORD=
) > "%AKAR%.env"

rem ---------- 4. Muat .env ke environment proses ----------
:muat_env
for /f "usebackq eol=# tokens=1,* delims==" %%A in ("%AKAR%.env") do set "%%A=%%B"
exit /b 0

rem ---------- Penanganan galat ----------
:tanpa_python
echo.
echo   GAGAL: Python tidak ditemukan.
echo   Pasang Python 3.11+ dari https://www.python.org/downloads/windows/
echo   dan centang "Add python.exe to PATH" saat memasang.
exit /b 1

:gagal_venv
echo.
echo   GAGAL: virtual environment tidak bisa dibuat.
echo   Coba hapus folder venv\ lalu jalankan lagi.
exit /b 1

:gagal_pip
echo.
echo   GAGAL: pemasangan dependensi tidak selesai.
echo   Periksa koneksi internet, lalu jalankan ulang dengan: jalankan.bat --pasang-ulang
exit /b 1

:gagal_kunci
echo.
echo   GAGAL: SECRET_KEY tidak bisa dibuat.
exit /b 1
