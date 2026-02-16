#!/bin/bash
# Open Alacritty terminal from VS Code/WSL
# Usage: Run this script to open Alacritty in the current directory

echo "Opening Alacritty terminal..."

# Get current directory
CURRENT_DIR="$(pwd)"

echo "Current directory: $CURRENT_DIR"

# Method 1: Using Windows executable directly
ALACRITTY_EXE="/mnt/c/Users/user/scoop/shims/alacritty.exe"

if [[ -f "$ALACRITTY_EXE" ]]; then
    # Convert WSL path to Windows path for --working-directory
    WIN_DIR="${CURRENT_DIR}"

    # Open Alacritty with WSL in current directory
    "$ALACRITTY_EXE" --working-directory "$WIN_DIR" &
    echo "✓ Alacritty opened"
else
    echo "✗ Alacritty not found at: $ALACRITTY_EXE"
    exit 1
fi
