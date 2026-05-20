@echo off
chcp 65001 >nul
cd /d "%~dp0.."
python hd_update_all_new.py
pause
