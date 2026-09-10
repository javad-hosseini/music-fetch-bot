@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Telegram Music Downloader Bot - Control Panel
color 0A

:: Locate Python executable
set "PYTHON_EXE="
if exist "%~dp0venv\Scripts\python.exe" (
    set "PYTHON_EXE=%~dp0venv\Scripts\python.exe"
) else if exist "%~dp0.venv\Scripts\python.exe" (
    set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"
) else (
    where python >nul 2>&1
    if not errorlevel 1 (
        set "PYTHON_EXE=python"
    )
)

if not defined PYTHON_EXE (
    echo.
    echo ==================================================================
    echo  [ERROR] Python was not found on this system!
    echo ==================================================================
    echo  Please install Python 3.10+ or set up the virtual environment:
    echo    python -m venv venv
    echo    venv\Scripts\pip.exe install -r requirements.txt
    echo.
    pause
    exit /b 1
)

:MENU
cls
echo ==================================================================
echo           TELEGRAM MUSIC DOWNLOADER CONTROL PANEL
echo ==================================================================
echo   Platforms : Radio Javan / SoundCloud / Spotify
echo   Date      : %DATE%
echo   Time      : %TIME:~0,8%
echo ==================================================================
echo.
echo   [1] Start Bot (Production)
echo   [2] Run System Diagnostics (--check)
echo   [3] Run Unit Tests (tests/)
echo   [4] Install / Update Dependencies (pip)
echo   [5] Exit
echo.
echo ==================================================================
echo.

set "choice="
set /p choice=Select Option [1-5]: 

if not defined choice goto MENU

:: Strip spaces and double quotes
set "choice=%choice: =%"
set "choice=%choice:"=%"

if "%choice%"=="1" goto RUNBOT
if "%choice%"=="2" goto DIAGNOSTICS
if "%choice%"=="3" goto TESTS
if "%choice%"=="4" goto INSTALL_DEPS
if "%choice%"=="5" goto QUIT
if /i "%choice%"=="q" goto QUIT
if /i "%choice%"=="exit" goto QUIT

echo.
echo [*] Invalid option '%choice%'. Please choose an option between 1 and 5.
ping 127.0.0.1 -n 2 >nul
goto MENU

:RUNBOT
cls
echo ==================================================================
echo                       BOT STATUS: ONLINE
echo ==================================================================
echo.
echo [+] Launching Telegram Music Downloader Bot...
echo [+] Press CTRL + C to stop the bot.
echo.
"%PYTHON_EXE%" run.py
echo.
echo ==================================================================
echo                       BOT STOPPED
echo ==================================================================
echo.
echo Press any key to return to menu...
pause >nul
goto MENU

:DIAGNOSTICS
cls
echo ==================================================================
echo                       SYSTEM DIAGNOSTICS
echo ==================================================================
echo.
"%PYTHON_EXE%" run.py --check
echo.
echo Press any key to return to menu...
pause >nul
goto MENU

:TESTS
cls
echo ==================================================================
echo                       RUNNING UNIT TESTS
echo ==================================================================
echo.
echo [*] Executing test discovery in tests/ directory...
echo.
"%PYTHON_EXE%" -m unittest discover -s tests
echo.
echo Press any key to return to menu...
pause >nul
goto MENU

:INSTALL_DEPS
cls
echo ==================================================================
echo                    UPDATING DEPENDENCIES
echo ==================================================================
echo.
echo [*] Installing / upgrading packages from requirements.txt...
echo.
"%PYTHON_EXE%" -m pip install -r requirements.txt
echo.
echo Press any key to return to menu...
pause >nul
goto MENU

:QUIT
exit /b 0
