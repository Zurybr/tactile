#!/usr/bin/env bash
# Install tactile — a terminal-based touch-typing trainer.
#
# Installs tactile via `uv tool install` from GitHub. If uv is not present,
# installs uv first via the official installer.
#
# On Linux/Mac, make this script executable after checkout:
#     chmod +x install.sh
# (Git may already preserve the executable bit when committed from a Unix host.)
set -euo pipefail

echo "Installing tactile..."

# Check if uv is installed
if ! command -v uv &>/dev/null; then
    echo "uv not found. Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # Source the environment to get uv in PATH
    if [ -f "$HOME/.local/bin/env" ]; then
        source "$HOME/.local/bin/env"
    elif [ -f "$HOME/.cargo/env" ]; then
        source "$HOME/.cargo/env"
    fi
fi

# Install tactile
echo "Installing tactile from GitHub..."
uv tool install git+https://github.com/Zurybr/tactile

echo ""
echo "tactile installed successfully!"
echo "Run 'tactile' to start practicing."
echo "Run 'tactile update' to update to the latest version."
