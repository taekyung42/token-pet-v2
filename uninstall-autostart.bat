@echo off
rem token-pet-v2 autostart uninstaller (launcher).
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0uninstall-autostart.ps1"
pause
