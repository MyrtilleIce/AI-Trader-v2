#!/usr/bin/env bash
set -euo pipefail

PYTHON="python3"
VENV=".venv"

if [ ! -d "$VENV" ]; then
  echo "Creating virtual environment in $VENV"
  $PYTHON -m venv "$VENV"
fi
source "$VENV/bin/activate"

pip install --upgrade pip

ARCH=$(uname -m)
OS=$(uname)
if [[ "$OS" == "Darwin" && "$ARCH" == "arm64" ]]; then
  echo "Detected Apple Silicon"
  pip install tensorflow-macos tensorflow-metal || true
else
  pip install tensorflow || true
fi

pip install -r requirements.txt

$PYTHON -m ai_trader.tools.preflight
