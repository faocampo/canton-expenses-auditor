# Methodology: TDD – tests for infrastructure.excel
from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from tools.pipeline.domain.models import FxSeries
from tools.pipeline.infrastructure.excel import extract_from_workbook


def _build_sample_xlsx(path: Path) -> None:
    # Build a DataFrame mimicking columns B..J at indices 1..9 (we'll leave col A empty)
    # Row: B(cat), C(sub), D(sub2), E(tipo), F(fecha), G(codigo), H(acreedor+CUIT), I(memo), J(importe)
    data = [
        [None, "Categoría", "Subcat", "Subsub", "Operativo", "15/01/2024", "001", "Proveedor SA CUIT 30-12345678-9", "Servicio mensual", "1.000,00"],
        [None, "Total", None, None, None, None, None, None, None, None],  # total row to be ignored
    ]
    df = pd.DataFrame(data)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Gastos del Mes", index=False, header=False)


def test_extract_from_workbook_parses_basic_fields(tmp_path):
    xlsx = tmp_path / "sample.xlsx"
    _build_sample_xlsx(xlsx)

    fx = FxSeries(dates=[date(2024, 1, 15)], values=[1000.0])

    rows = extract_from_workbook(
        xlsx_path=xlsx,
        fx=fx,
        y_m_from_name=None,
        enrich=False,
        rate_limit_s=0.0,
        cache={},
    )

    assert len(rows) == 1
    r = rows[0]
    assert r.id_acreedor == "30-12345678-9"
    assert r.monto_ars == 1000.0
    assert r.monto_usd == 1.0
    assert r.fecha == date(2024, 1, 15)
