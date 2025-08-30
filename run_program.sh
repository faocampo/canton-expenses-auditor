#!/usr/bin/env bash
set -e
set -u
set -o pipefail

# Methodology: Environment setup and program runner
# Purpose: Create/activate venv, install deps, and run the expenses consolidation program.

# Source common environment setup
source "$(dirname "$0")/scripts/setup_env.sh"

# Setup and activate virtual environment
setup_venv
activate_venv
install_dependencies

step 4 "Running the expenses consolidation program..."

# Default values
DEFAULT_INPUTS="expenses"
DEFAULT_FX="docs/Info_Financiera-Tipo_de_cambio_USD-ARS.csv"
DEFAULT_FROM_YEAR="2020"
DEFAULT_TO_YEAR="2025"
DEFAULT_OUTPUT="output/consolidado_expensas_canton_2020-2025.csv"
DEFAULT_RATE_LIMIT="1.0"
DEFAULT_SKIP_ENRICH=false
DEFAULT_DEBUG=false

# Parse command line arguments
inputs="$DEFAULT_INPUTS"
fx="$DEFAULT_FX"
from_year="$DEFAULT_FROM_YEAR"
to_year="$DEFAULT_TO_YEAR"
append=""
output="$DEFAULT_OUTPUT"
skip_enrich="$DEFAULT_SKIP_ENRICH"
rate_limit="$DEFAULT_RATE_LIMIT"
debug="$DEFAULT_DEBUG"

# Check for --help flag
for arg in "$@"; do
  if [ "$arg" = "--help" ] || [ "$arg" = "-h" ]; then
    echo "Usage: run_program.sh [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --inputs PATHS        Rutas o patrones a archivos/directorios XLSX (default: expenses)"
    echo "  --fx PATH             CSV de tipo de cambio (default: docs/Info Financiera - Tipo de cambio USD-ARS.csv)"
    echo "  --from-year YEAR      Año inicial para filtrar datos (default: 2020)"
    echo "  --to-year YEAR        Año final para filtrar datos (default: 2025)"
    echo "  --append PATH         CSV previo al que se agregarán filas (sin encabezado)"
    echo "  --output PATH         CSV de salida (si no se especifica, se imprime a stdout)"
    echo "  --skip-enrich         No realizar enriquecimiento CUIT online"
    echo "  --rate-limit SECONDS  Segundos entre requests de enriquecimiento CUIT (default: 1.0)"
    echo "  --debug               Habilita logging DEBUG detallado"
    echo "  --help, -h            Muestra esta ayuda"
    echo ""
    echo "Ejemplo:"
    echo "  ./run_program.sh --inputs expenses --fx "docs/Info_Financiera-Tipo_de_cambio_USD-ARS.csv" --from-year 2020 --to-year 2025 --output output/consolidado_expensas_canton_2020-2025.csv --debug"
    exit 0
  fi
done

while [[ $# -gt 0 ]]; do
  case $1 in
    --inputs)
      inputs="$2"
      shift 2
      ;;
    --fx)
      fx="$2"
      shift 2
      ;;
    --from-year)
      from_year="$2"
      shift 2
      ;;
    --to-year)
      to_year="$2"
      shift 2
      ;;
    --append)
      append="$2"
      shift 2
      ;;
    --output)
      output="$2"
      shift 2
      ;;
    --skip-enrich)
      skip_enrich=true
      shift
      ;;
    --rate-limit)
      rate_limit="$2"
      shift 2
      ;;
    --debug)
      debug=true
      shift
      ;;
    -h|--help)
      shift
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# Build the command with provided or default arguments
CMD="python -m tools.pipeline.consolidate_expenses --inputs $inputs --fx "$fx" --from-year $from_year --to-year $to_year --output "$output" --rate-limit $rate_limit"

if [ "$skip_enrich" = true ]; then
  CMD="$CMD --skip-enrich"
fi

if [ "$debug" = true ]; then
  CMD="$CMD --debug"
fi

if [ -n "$append" ]; then
  CMD="$CMD --append "$append""
fi

# Execute the command
eval $CMD
