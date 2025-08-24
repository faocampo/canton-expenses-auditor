# Methodology: Clean Architecture – CLI interface
from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import List, Optional

from ..application.use_case import consolidate
from ..infrastructure.fx_loader import load_fx_series
from .io import collect_input_files, write_output_rows

logger = logging.getLogger("pipeline.interface.cli")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Consolida gastos desde planillas XLSX")
    parser.add_argument("--inputs", nargs="+", default=["expenses"], help="Rutas o patrones a archivos/directorios XLSX")
    parser.add_argument("--fx", required=True, help="CSV de tipo de cambio (docs/Info Financiera - Tipo de cambio USD-ARS.csv)")
    parser.add_argument("--from-year", type=int, dest="from_year", default=None)
    parser.add_argument("--to-year", type=int, dest="to_year", default=None)
    parser.add_argument("--append", type=str, default=None, help="CSV previo al que se agregarán filas (sin encabezado)")
    parser.add_argument("--output", type=str, default=None, help="CSV de salida (si no se especifica, se imprime a stdout)")
    parser.add_argument("--skip-enrich", action="store_true", help="No realizar enriquecimiento CUIT online")
    parser.add_argument("--rate-limit", type=float, default=1.0, help="Segundos entre requests de enriquecimiento CUIT")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = build_parser()
    args = parser.parse_args(argv)

    input_files = collect_input_files(args.inputs)
    if not input_files:
        logger.error("No se encontraron archivos XLSX en %s", args.inputs)
        return 2

    fx_path = Path(args.fx)
    if not fx_path.exists():
        logger.error("No existe archivo de tipo de cambio: %s", fx_path)
        return 2

    fx_series = load_fx_series(fx_path)

    rows = consolidate(
        files=input_files,
        fx=fx_series,
        from_year=args.from_year,
        to_year=args.to_year,
        enrich=not args.skip_enrich,
        rate_limit=args.rate_limit,
    )

    output_path = Path(args.output) if args.output else None
    append_path = Path(args.append) if args.append else None
    write_output_rows(rows, output=output_path, append=append_path)

    return 0
