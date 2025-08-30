#!/usr/bin/env zsh
set -e
set -u
set -o pipefail

# Methodology: TDD – test runner helper script
# Purpose: Create/activate venv, install deps, and run all tests.

# Source common environment setup
source "$(dirname "$0")/scripts/setup_env.sh"

# Setup and activate virtual environment
setup_venv
activate_venv
install_dependencies

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
