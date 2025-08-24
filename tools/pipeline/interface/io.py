# Methodology: Clean Architecture – interface I/O utilities (CLI adapters)
from __future__ import annotations

import csv
import logging
import sys
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

from ..domain.models import REQUIRED_COLUMNS_OUT

logger = logging.getLogger("pipeline.interface.io")


def collect_input_files(paths: List[str]) -> List[Path]:
    files: List[Path] = []
    for p in paths:
        path = Path(p)
        if path.is_dir():
            files.extend(sorted(path.glob("*.xlsx")))
        else:
            # Allow glob patterns
            if any(ch in p for ch in "*?["):
                files.extend(sorted(Path().glob(p)))
            else:
                if path.suffix.lower() == ".xlsx":
                    files.append(path)
    # Deduplicate while keeping order
    seen = set()
    uniq: List[Path] = []
    for f in files:
        if f not in seen and f.suffix.lower() == ".xlsx":
            uniq.append(f)
            seen.add(f)
    return uniq


def rows_to_dataframe(rows: List[Dict[str, object]]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=REQUIRED_COLUMNS_OUT)


def write_output_rows(rows: List[Dict[str, object]], output: Optional[Path], append: Optional[Path]) -> None:
    if append and output:
        logger.warning("Se especificaron 'output' y 'append'. Se prioriza 'append'.")
    target = append or output
    if target:
        target.parent.mkdir(parents=True, exist_ok=True)
        df = rows_to_dataframe(rows)
        if append:
            file_exists = target.exists()
            df.to_csv(
                target,
                index=False,
                header=not file_exists,
                mode="a",
                quoting=csv.QUOTE_MINIMAL,
            )
        else:
            df.to_csv(target, index=False, header=True, mode="w", quoting=csv.QUOTE_MINIMAL)
        logger.info("Escribí %d filas en %s", len(df), target)
    else:
        # stdout
        df = rows_to_dataframe(rows)
        csv_text = df.to_csv(index=False, quoting=csv.QUOTE_MINIMAL)
        sys.stdout.write(csv_text)
