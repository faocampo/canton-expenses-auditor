#!/usr/bin/env bash
# Common environment setup script
# This script is sourced by both run_tests.sh and run_program.sh

# Resolve project root as the directory of this script
# This works in both bash and zsh
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-${(%):-%x}}")" && pwd)"
cd "$SCRIPT_DIR/.."

# Function to print step messages
step() { echo "[$1] $2"; }

# Setup virtual environment
setup_venv() {
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
}

# Activate virtual environment
activate_venv() {
  step 2 "Activating virtual environment..."
  source .venv/bin/activate
  echo " - Python: $(python -V 2>&1)"
}

# Install dependencies
install_dependencies() {
  step 3 "Installing dependencies from requirements.txt..."
  if [[ -f requirements.txt ]]; then
    export PIP_DISABLE_PIP_VERSION_CHECK=1
    if command -v uv >/dev/null 2>&1; then
      echo " - Installing dependencies with uv pip..."
      uv pip install --upgrade pip
      uv pip install -r requirements.txt
    else
      echo " - Installing dependencies with pip..."
      python -m pip install --upgrade pip
      python -m pip install -r requirements.txt
    fi
  else
    echo " ! requirements.txt not found; skipping dependency installation."
  fi
}
