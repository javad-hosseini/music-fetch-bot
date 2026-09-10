@echo off
chcp 65001 >nul
title JAVAD - RJ Downloader Control Panel
color 0A

:BOOT
cls

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║                    INITIALIZING SYSTEM                       ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.
echo [■□□□□□□□□□] 10%%
timeout /t 1 >nul

cls
echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║                    INITIALIZING SYSTEM                       ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.
echo [■■■■□□□□□□] 40%%
timeout /t 1 >nul

cls
echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║                    INITIALIZING SYSTEM                       ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.
echo [■■■■■■■■□□] 80%%
timeout /t 1 >nul

cls
echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║                    INITIALIZING SYSTEM                    	║
echo ╚══════════════════════════════════════════════════════════════╝
echo.
echo [■■■■■■■■■■] 100%%
timeout /t 1 >nul

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
echo ║                 RJ DOWNLOADER CONTROL PANEL             	    ║
echo ╠══════════════════════════════════════════════════════════════╣
echo ║ STATUS : OFFLINE                                    			║
echo ║ DATE   : %date%                                        	    ║
echo ║ TIME   : %time:~0,8%                                    		║
echo ╚══════════════════════════════════════════════════════════════╝
echo.
echo                    [1] RUN BOT
echo                    [2] EXIT
echo.

set /p choice=Select Option ^> 

if "%choice%"=="1" goto RUNBOT
if "%choice%"=="2" exit

echo.
echo Invalid Option!
timeout /t 2 >nul
goto MENU

:RUNBOT
cls

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║                      BOT STATUS: ONLINE                      ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.
echo [+] Launching RJ Downloader...
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