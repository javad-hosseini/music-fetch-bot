@echo off
chcp 65001 >nul
title Music Downloader Bot - Control Panel
color 0A

:MENU
cls
echo.
echo      ██╗ █████╗ ██╗   ██╗ █████╗ ██████╗ 
echo      ██║██╔══██╗██║   ██║██╔══██╗██╔══██╗
echo      ██║███████║██║   ██║███████║██║  ██║
echo ██   ██║██╔══██║╚██╗ ██╔╝██╔══██║██║  ██║
echo ╚█████╔╝██║  ██║ ╚████╔╝ ██║  ██║██████╔╝
echo  ╚════╝ ╚═╝  ╚═╝  ╚═══╝  ╚═╝  ╚═╝╚═════╝ 
echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║             TELEGRAM MUSIC DOWNLOADER CONTROL PANEL          ║
echo ╠══════════════════════════════════════════════════════════════╣
echo ║ PLATFORMS : Radio Javan • SoundCloud • Spotify               ║
echo ║ DATE      : %date%                                           ║
echo ║ TIME      : %time:~0,8%                                      ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.
echo   [1] Start Bot (Production)
echo   [2] Run System Diagnostics (--check)
echo   [3] Run Unit Tests (test_services.py)
echo   [4] Install / Update Dependencies (pip)
echo   [5] Exit
echo.

set /p choice=Select Option ^> 

if "%choice%"=="1" goto RUNBOT
if "%choice%"=="2" goto DIAGNOSTICS
if "%choice%"=="3" goto TESTS
if "%choice%"=="4" goto INSTALL_DEPS
if "%choice%"=="5" exit

echo.
echo Invalid Option!
timeout /t 1 >nul
goto MENU

:RUNBOT
cls
echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║                      BOT STATUS: ONLINE                      ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.
echo [+] Launching Telegram Music Downloader Bot...
echo [+] Press CTRL + C to stop the bot.
echo.

cd /d "%~dp0"
venv\Scripts\python.exe run.py

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║                      BOT STOPPED                             ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.
pause
goto MENU

:DIAGNOSTICS
cls
echo.
cd /d "%~dp0"
venv\Scripts\python.exe run.py --check
echo.
pause
goto MENU

:TESTS
cls
echo.
echo 🧪 Running Service Unit Tests...
echo.
cd /d "%~dp0"
venv\Scripts\python.exe -m unittest discover -s tests
echo.
pause
goto MENU

:INSTALL_DEPS
cls
echo.
echo 📦 Updating Dependencies from requirements.txt...
echo.
cd /d "%~dp0"
venv\Scripts\python.exe -m pip install -r requirements.txt
echo.
pause
goto MENU