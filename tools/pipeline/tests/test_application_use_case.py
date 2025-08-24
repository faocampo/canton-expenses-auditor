# Methodology: TDD – tests for application.use_case
from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from tools.pipeline.application.use_case import consolidate
from tools.pipeline.domain.models import FxSeries


def _build_sample_xlsx(path: Path) -> None:
    data = [
        [None, "Categoría", "Subcat", "Subsub", "Operativo", "15/01/2024", "001", "Proveedor SA CUIT 30-12345678-9", "Servicio mensual", "1.000,00"],
    ]
    df = pd.DataFrame(data)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Gastos del Mes", index=False, header=False)


def test_consolidate_end_to_end_basic(tmp_path):
    xlsx1 = tmp_path / "a.xlsx"
    _build_sample_xlsx(xlsx1)
    xlsx2 = tmp_path / "b.xlsx"
    _build_sample_xlsx(xlsx2)

    fx = FxSeries(dates=[date(2024, 1, 15)], values=[1000.0])

    rows = consolidate(
        files=[xlsx1, xlsx2],
        fx=fx,
        enrich=False,
        rate_limit=0.0,
    )

    assert len(rows) == 2
    # keys present
    assert rows[0]["ID acreedor"] == "30-12345678-9"
    assert rows[0]["monto ARS"] == "1000.00"
    assert rows[0]["monto USD"] == "1.00"
    assert rows[0]["fecha"] == "15/01/2024"


def test_consolidate_year_filter(tmp_path):
    xlsx = tmp_path / "c.xlsx"
    data = [
        [None, "Cat", "Sub", "Sub2", "Operativo", "15/01/2023", "001", "Proveedor SA CUIT 30-12345678-9", "Servicio", "1.000,00"],
        [None, "Cat", "Sub", "Sub2", "Operativo", "15/01/2024", "001", "Proveedor SA CUIT 30-12345678-9", "Servicio", "1.000,00"],
    ]
    df = pd.DataFrame(data)
    with pd.ExcelWriter(xlsx, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Gastos del Mes", index=False, header=False)

    fx = FxSeries(dates=[date(2024, 1, 15)], values=[1000.0])

    rows = consolidate(files=[xlsx], fx=fx, from_year=2024, to_year=2024, enrich=False, rate_limit=0.0)
    assert len(rows) == 1
    assert rows[0]["fecha"] == "15/01/2024"
