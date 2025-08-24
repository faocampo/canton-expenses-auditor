# Methodology: Clean Architecture – infrastructure adapters
from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Optional

import pandas as pd

from ..domain.models import FxSeries
from ..domain.models import parse_ars_number


def load_fx_series(path: Path) -> FxSeries:
    """Load FX CSV with columns 'Fecha' (DD/MM/YYYY) and 'Valor ARS' (es-AR number).
    Returns a domain FxSeries.
    """
    df = pd.read_csv(path)

    def to_date(x: str) -> date:
        return datetime.strptime(str(x).strip(), "%d/%m/%Y").date()

    def to_float(x: str) -> Optional[float]:
        return parse_ars_number(x)

    df["_fecha"] = df["Fecha"].map(to_date)
    df["_valor"] = df.get("Valor ARS", df.get("Valor")).map(to_float)
    df = df.dropna(subset=["_fecha", "_valor"]).sort_values("_fecha").reset_index(drop=True)
    if df.isna().any().any():
        raise ValueError("DataFrame contains NaN values")
    return FxSeries(dates=df["_fecha"].tolist(), values=df["_valor"].tolist())
