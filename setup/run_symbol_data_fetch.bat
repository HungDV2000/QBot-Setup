@echo off
chcp 65001 >nul
cd /d "%~dp0.."
set /p SYM=Nhap ma (VD BTC, ETH/USDT): 
if "%SYM%"=="" (
  echo Thieu ma symbol.
  pause
  exit /b 1
)
python symbol_data_fetch.py "%SYM%"
pause
