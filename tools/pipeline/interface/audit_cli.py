# Methodology: Clean Architecture – CLI interface for audit
from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import List, Optional

from ..application.audit import run_audit

logger = logging.getLogger("pipeline.interface.audit_cli")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Audita gastos de consorcio y genera un Excel con múltiples solapas")
    parser.add_argument("--consolidated-data", required=True, help="CSV de gastos consolidados")
    parser.add_argument("--inflation-data", required=True, help="CSV de inflación mensual")
    parser.add_argument("--output-excel", required=True, help="Archivo Excel de salida")
    parser.add_argument("--output-report", help="Archivo markdown de informe de auditoría (opcional)")
    parser.add_argument("--debug", action="store_true", help="Habilita logging DEBUG detallado")
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    
    # Configure logging after parsing so we can honor --debug
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format='%(asctime)s %(levelname)s %(name)s %(message)s',
    )
    
    if args.debug:
        logger.debug("Debug ENABLED. Args: consolidated_data=%s inflation_data=%s output_excel=%s output_report=%s",
                     args.consolidated_data, args.inflation_data, args.output_excel, args.output_report)
    
    # Convert string paths to Path objects
    consolidated_data_path = Path(args.consolidated_data)
    inflation_data_path = Path(args.inflation_data)
    output_excel_path = Path(args.output_excel)
    output_report_path = Path(args.output_report) if args.output_report else None
    
    # Validate input files exist
    if not consolidated_data_path.exists():
        logger.error("No existe archivo de gastos consolidados: %s", consolidated_data_path)
        return 2
    
    if not inflation_data_path.exists():
        logger.error("No existe archivo de inflación: %s", inflation_data_path)
        return 2
    
    # Run audit process
    return run_audit(
        consolidated_data_path=consolidated_data_path,
        inflation_data_path=inflation_data_path,
        output_excel_path=output_excel_path,
        output_report_path=output_report_path
    )
