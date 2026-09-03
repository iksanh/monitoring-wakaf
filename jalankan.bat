@echo off
rem ============================================================
rem  jalankan.bat - menjalankan Aplikasi Sertipikasi Tanah Wakaf
rem  di Windows. Klik dua kali, atau dari terminal:
rem      jalankan.bat [--port 8000] [--jaringan] [--pasang-ulang]
rem                   [--tanpa-browser] [--tanpa-reload] [--bantuan]
rem ============================================================
setlocal EnableDelayedExpansion
chcp 65001 >nul
cd /d "%~dp0"
title Aplikasi Sertipikasi Tanah Wakaf
set "PYTHONUTF8=1"

set "PORT=8000"
set "HOST=127.0.0.1"
set "PASANG_ULANG=0"
set "BUKA_BROWSER=1"
set "RELOAD=--reload"

:baca_arg
if "%~1"=="" goto arg_selesai
if /i "%~1"=="--port" ( set "PORT=%~2" & shift & shift & goto baca_arg )
if /i "%~1"=="--jaringan" ( set "HOST=0.0.0.0" & shift & goto baca_arg )
if /i "%~1"=="--pasang-ulang" ( set "PASANG_ULANG=1" & shift & goto baca_arg )
if /i "%~1"=="--tanpa-browser" ( set "BUKA_BROWSER=0" & shift & goto baca_arg )
if /i "%~1"=="--tanpa-reload" ( set "RELOAD=" & shift & goto baca_arg )
if /i "%~1"=="--bantuan" goto bantuan
if /i "%~1"=="-h" goto bantuan
echo Argumen tidak dikenal: %~1
echo.
goto bantuan
:arg_selesai

echo ============================================================
echo   Aplikasi Sertipikasi Tanah Wakaf
echo   Kantor Pertanahan Kabupaten Bone Bolango
echo ============================================================
echo.

call "%~dp0siapkan-lingkungan.bat"
if errorlevel 1 goto akhir_galat

echo.
echo   Database : !DB_PATH!
echo   Unggahan : !UPLOAD_DIR!
echo.
echo   Buka di browser  : http://127.0.0.1:%PORT%/
if "%HOST%"=="0.0.0.0" call :tampilkan_ip
echo   Hentikan server  : tekan Ctrl+C di jendela ini
echo.
echo   Kalau ini pertama kali dijalankan, sandi akun "admin" dicetak
echo   di bawah ini SEKALI SAJA - catat sebelum menutup jendela.
echo ------------------------------------------------------------
echo.

if "%BUKA_BROWSER%"=="1" start "" /min cmd /c "timeout /t 4 /nobreak >nul & rundll32 url.dll,FileProtocolHandler http://127.0.0.1:%PORT%/"

"%VPY%" -m uvicorn app:app %RELOAD% --host %HOST% --port %PORT%

echo.
echo   Server berhenti.
pause
exit /b 0

:tampilkan_ip
for /f "tokens=2 delims=:" %%I in ('ipconfig ^| findstr /c:"IPv4"') do (
    for /f "tokens=* delims= " %%J in ("%%I") do echo   Dari HP ^(satu wifi^): http://%%J:%PORT%/
)
exit /b 0

:bantuan
echo Cara pakai: jalankan.bat [pilihan]
echo.
echo   --port ^<nomor^>    Port server, bawaan 8000.
echo   --jaringan        Dengarkan di semua alamat (0.0.0.0) supaya bisa
echo                     dibuka dari HP yang satu wifi dengan PC ini.
echo   --pasang-ulang    Pasang ulang dependensi dari requirements.txt.
echo   --tanpa-browser   Jangan buka browser otomatis.
echo   --tanpa-reload    Matikan auto-reload (lebih hemat, untuk pemakaian biasa).
echo   --bantuan         Tampilkan pesan ini.
echo.
pause
exit /b 0

:akhir_galat
echo.
pause
exit /b 1
