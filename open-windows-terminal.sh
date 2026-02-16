#!/bin/bash
# Open Windows Terminal from VS Code/WSL
# Usage: Double-click in VS Code file explorer, or run: ./open-windows-terminal.sh

echo "Opening Windows Terminal..."

# Get current directory
CURRENT_DIR="$(pwd)"

# Convert WSL path to Windows path if in /mnt/c
if [[ "$CURRENT_DIR" == /mnt/c/* ]]; then
    WIN_DIR="${CURRENT_DIR#/mnt/c}"
    WIN_DIR="C:${WIN_DIR//\//\\}"
else
    WIN_DIR="$CURRENT_DIR"
fi

echo "Current directory: $CURRENT_DIR"
echo "Windows path: $WIN_DIR"

# Open Windows Terminal in current directory
# Method 1: Using wt.exe (recommended)
if command -v wt.exe &> /dev/null; then
    # Option A: Open new tab in current window
    wt.exe -w 0 nt bash -c "cd '$CURRENT_DIR' && exec bash"

    # Option B: Open new window (uncomment if you prefer)
    # wt.exe -w 1 nt bash -c "cd '$CURRENT_DIR' && exec bash"

    echo "✓ Windows Terminal opened"
else
    echo "✗ wt.exe not found. Please ensure Windows Terminal is installed."
    echo "  Install from: https://aka.ms/terminal"
    exit 1
fi
