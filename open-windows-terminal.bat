@echo off
REM Open Windows Terminal in NeoLyst project directory
REM Double-click this file to open Windows Terminal in the current directory

echo Opening Windows Terminal in NeoLyst project...

REM Open Windows Terminal in WSL Ubuntu at the current directory
REM Method 1: Using wt (recommended)
wt.exe -w 0 nt wsl.exe -d Ubuntu --cd /mnt/c/_code/neolyst

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Failed to open Windows Terminal.
    echo Please ensure Windows Terminal is installed:
    echo https://aka.ms/terminal
    pause
)
