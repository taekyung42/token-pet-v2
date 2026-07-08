@echo off
rem token-pet-v2 autostart installer (launcher). Keep next to token-pet-v2.exe.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install-autostart.ps1"
pause
