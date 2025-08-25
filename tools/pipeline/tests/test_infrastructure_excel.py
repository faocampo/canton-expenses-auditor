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
        [None, " A-Intendencia y Administración", "Bienes de uso", None, "Bill", "23/12/2024", "C0000200000202", "Corti Oscar Alberto 20-26395374-7", "Transfer - Para reemplazo de computadoras de porticos y puestos de trabajo que presentan deterio...", "453.336"],
        [None, " A-Intendencia y Administración", "Bienes de uso", None, "Credit", "23/12/2024", "NCC0000200000003", "Corti Oscar Alberto 20-26395374-7", "Aplica a la fc 202. Error de imputación.", "-453.336"],
        [None, " A-Intendencia y Administración", "Bienes de uso", None, "Bill", "23/12/2024", "C0000200000203", "Corti Oscar Alberto 20-26395374-7", "Transfer - Para reemplazo de computadoras de porticos y puestos de trabajo que presentan deterio...", "450.640"],
        [None, "Total", None, None, None, None, None, None, None, None],  # total row to be ignored
    ]
   	 
    df = pd.DataFrame(data)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Gastos del Mes", index=False, header=False)


def test_extract_from_workbook_parses_basic_fields(tmp_path):
    xlsx = tmp_path / "sample.xlsx"
    _build_sample_xlsx(xlsx)

    fx = FxSeries(dates=[date(2024, 12, 23)], values=[1000.0])

    rows = extract_from_workbook(
        xlsx_path=xlsx,
        fx=fx,
        y_m_from_name=None,
        enrich=False,
        rate_limit_s=0.0,
        cache={},
    )

    assert len(rows) == 3
    r = rows[0]
    assert r.id_acreedor == "20-26395374-7"
    assert r.monto_ars == 453336
    assert r.monto_usd == 453336 / 1000.0
    assert r.fecha == date(2024, 12, 23)
    assert r.tipo_gasto == "Bill"
    assert r.tipo_cambio == 1000.0
    assert r.rubro == "Bienes de uso"
    assert r.categoria == "A-Intendencia y Administración"
    assert r.subcategoria == "Bienes de uso"
    assert r.subsubcategoria == ""
    assert r.codigo == "C0000200000202"
    assert r.acreedor == "Corti Oscar Alberto"
    assert r.descripcion == "Transfer - Para reemplazo de computadoras de porticos y puestos de trabajo que presentan deterio..."
    
    r = rows[1]
    assert r.id_acreedor == "20-26395374-7"
    assert r.monto_ars == -453336
    assert r.monto_usd == -453336 / 1000.0
    assert r.fecha == date(2024, 12, 23)
    assert r.tipo_gasto == "Credit"
    assert r.tipo_cambio == 1000.0
    assert r.rubro == "Bienes de uso"
    assert r.categoria == "A-Intendencia y Administración"
    assert r.subcategoria == "Bienes de uso"
    assert r.subsubcategoria == ""
    assert r.codigo == "NCC0000200000003"
    assert r.acreedor == "Corti Oscar Alberto"
    assert r.descripcion == "Aplica a la fc 202. Error de imputación."

    r = rows[2]
    assert r.id_acreedor == "20-26395374-7"
    assert r.monto_ars == 450640
    assert r.monto_usd == 450640 / 1000.0
    assert r.fecha == date(2024, 12, 23)
    assert r.tipo_gasto == "Bill"
    assert r.tipo_cambio == 1000.0
    assert r.rubro == "Bienes de uso"
    assert r.categoria == "A-Intendencia y Administración"
    assert r.subcategoria == "Bienes de uso"
    assert r.subsubcategoria == ""
    assert r.codigo == "C0000200000203"
    assert r.acreedor == "Corti Oscar Alberto"
    assert r.descripcion == "Transfer - Para reemplazo de computadoras de porticos y puestos de trabajo que presentan deterio..."
