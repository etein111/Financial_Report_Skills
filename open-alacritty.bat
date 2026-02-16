@echo off
REM Open Alacritty terminal in NeoLyst project directory
REM Double-click this file to open Alacritty

echo Opening Alacritty in NeoLyst project...

REM Open Alacritty with WSL in the project directory
alacritty.exe --working-directory /mnt/c/_code/neolyst

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Failed to open Alacritty.
    echo Make sure Alacritty is installed and in PATH.
    pause
)
