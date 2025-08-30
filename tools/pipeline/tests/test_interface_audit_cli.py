# Methodology: TDD – tests for interface.audit_cli
from __future__ import annotations

import argparse
import pandas as pd
from pathlib import Path

from tools.pipeline.interface.audit_cli import build_parser


def test_build_parser():
    """Test building the audit CLI parser."""
    parser = build_parser()
    
    # Assertions
    assert isinstance(parser, argparse.ArgumentParser)
    
    # Test parsing with minimal required arguments
    args = parser.parse_args([
        "--consolidated-data", "consolidated.csv",
        "--inflation-data", "inflation.csv",
        "--output-excel", "output.xlsx"
    ])
    
    assert args.consolidated_data == "consolidated.csv"
    assert args.inflation_data == "inflation.csv"
    assert args.output_excel == "output.xlsx"
    assert args.output_report is None
    assert args.debug is False


def test_build_parser_with_optional_args():
    """Test building the audit CLI parser with optional arguments."""
    parser = build_parser()
    
    # Test parsing with all arguments
    args = parser.parse_args([
        "--consolidated-data", "consolidated.csv",
        "--inflation-data", "inflation.csv",
        "--output-excel", "output.xlsx",
        "--output-report", "report.md",
        "--debug"
    ])
    
    # Assertions
    assert args.consolidated_data == "consolidated.csv"
    assert args.inflation_data == "inflation.csv"
    assert args.output_excel == "output.xlsx"
    assert args.output_report == "report.md"
    assert args.debug is True
