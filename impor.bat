@echo off
rem  impor.bat - impor Rekapan Wakaf dari Excel.
rem      impor.bat "C:\path\Rekapan Wakaf Bone bolango.xlsx" --dry-run
rem      impor.bat "C:\path\Rekapan Wakaf Bone bolango.xlsx"
setlocal EnableDelayedExpansion
chcp 65001 >nul
cd /d "%~dp0"
title Impor Excel - Aplikasi Wakaf
set "PYTHONUTF8=1"

if "%~1"=="" goto bantuan

call "%~dp0siapkan-lingkungan.bat"
if errorlevel 1 goto akhir

echo.
echo ------------------------------------------------------------
"%VPY%" -m scripts.impor %*
echo ------------------------------------------------------------
goto akhir

:bantuan
echo Cara pakai:
echo   impor.bat "C:\path\Rekapan Wakaf Bone bolango.xlsx" --dry-run
echo   impor.bat "C:\path\Rekapan Wakaf Bone bolango.xlsx"
echo.
echo Jalankan --dry-run dulu untuk pratinjau; tidak ada yang ditulis ke database.

:akhir
echo.
pause
