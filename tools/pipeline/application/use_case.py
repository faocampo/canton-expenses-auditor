# Methodology: Clean Architecture – application use case orchestration
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

from ..domain.models import (
    ExtractedRow,
    FxSeries,
    mark_quality_observations,
)
from ..infrastructure.excel import extract_from_workbook


def _filter_rows_by_year(rows: List[ExtractedRow], from_year: Optional[int], to_year: Optional[int]) -> List[ExtractedRow]:
    if from_year is None and to_year is None:
        return rows
    out: List[ExtractedRow] = []
    for r in rows:
        if not r.fecha:
            continue
        y = r.fecha.year
        if from_year is not None and y < from_year:
            continue
        if to_year is not None and y > to_year:
            continue
        out.append(r)
    return out


def consolidate(
    files: List[Path],
    fx: FxSeries,
    *,
    from_year: Optional[int] = None,
    to_year: Optional[int] = None,
    enrich: bool = False,
    rate_limit: float = 1.0,
) -> List[Dict[str, object]]:
    """Run the consolidation end-to-end and return a list of CSV-row dictionaries."""
    all_rows: List[ExtractedRow] = []
    cache: Dict[str, str] = {}

    for f in files:
        # Infer (year, month) from filename to help date normalization
        from ..domain.models import parse_month_year_from_filename

        ym = parse_month_year_from_filename(f.name)
        part = extract_from_workbook(
            xlsx_path=f,
            fx=fx,
            y_m_from_name=ym,
            enrich=enrich,
            rate_limit_s=rate_limit,
            cache=cache,
        )
        all_rows.extend(part)

    if not all_rows:
        return []

    mark_quality_observations(all_rows)

    filtered = _filter_rows_by_year(all_rows, from_year, to_year)

    # Convert to CSV rows in a deterministic schema
    return [r.to_csv_row() for r in filtered]
