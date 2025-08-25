#!/usr/bin/env zsh
set -e
set -u
set -o pipefail

# Methodology: TDD – test runner helper script
# Purpose: Create/activate venv, install deps, and run all tests.

# Resolve project root as the directory of this script
SCRIPT_DIR="${0:a:h}"
cd "$SCRIPT_DIR"

step() { echo "[$1] $2"; }

step 1 "Setting up virtual environment (.venv)..."
if [[ ! -d .venv ]]; then
  if command -v uv >/dev/null 2>&1; then
    echo " - Creating venv with uv..."
    uv venv .venv
  else
    echo " - Creating venv with python -m venv..."
    python3 -m venv .venv
  fi
else
  echo " - .venv already exists."
fi

step 2 "Activating virtual environment..."
source .venv/bin/activate

echo " - Python: $(python -V 2>&1)"

step 3 "Installing dependencies from requirements.txt..."
if [[ -f requirements.txt ]]; then
  export PIP_DISABLE_PIP_VERSION_CHECK=1
  python -m pip install --upgrade pip
  python -m pip install -r requirements.txt
else
  echo " ! requirements.txt not found; skipping dependency installation."
fi

step 4 "Ensuring pytest is installed..."
if ! python - <<'PY'
import importlib
import sys
sys.exit(0 if importlib.util.find_spec('pytest') else 1)
PY
then
  echo " - Installing pytest..."
  python -m pip install pytest
fi

step 5 "Running tests..."
# Default to quiet if no args; otherwise pass all provided args through to pytest
if [[ "$#" -eq 0 ]]; then
  python -m pytest -q
else
  python -m pytest "$@"
fi
