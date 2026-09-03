@echo off
rem  tes.bat - menjalankan seluruh tes: python -m unittest discover tests
setlocal EnableDelayedExpansion
chcp 65001 >nul
cd /d "%~dp0"
title Tes - Aplikasi Wakaf
set "PYTHONUTF8=1"

call "%~dp0siapkan-lingkungan.bat"
if errorlevel 1 goto akhir

echo.
echo ------------------------------------------------------------
"%VPY%" -m unittest discover tests
echo ------------------------------------------------------------

:akhir
echo.
pause
