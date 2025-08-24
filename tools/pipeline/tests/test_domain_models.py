# Methodology: TDD – unit tests for domain layer
from __future__ import annotations

from datetime import date

from tools.pipeline.domain.models import (
    ExtractedRow,
    FxSeries,
    detect_rubro,
    is_total_marker,
    mark_quality_observations,
    normalize_date_ddmmyyyy,
    parse_ars_number,
    parse_cuit_from_payee,
    parse_month_year_from_filename,
)


def test_parse_ars_number_es_formats():
    assert parse_ars_number("1.234,56") == 1234.56
    assert parse_ars_number("1 234,56") == 1234.56
    assert parse_ars_number(1234.56) == 1234.56
    assert parse_ars_number(None) is None


def test_parse_cuit_from_payee():
    name, cuit = parse_cuit_from_payee("Empresa SA - CUIT 30-12345678-9")
    assert name.startswith("Empresa")
    assert cuit == "30-12345678-9"
    name2, cuit2 = parse_cuit_from_payee("Proveedor Sin CUIT")
    assert cuit2 is None


def test_normalize_date_ddmmyyyy_with_fallback():
    d, obs = normalize_date_ddmmyyyy("15/01/2024")
    assert d == date(2024, 1, 15)
    d2, obs2 = normalize_date_ddmmyyyy("no-date", (2024, 2))
    assert d2 == date(2024, 2, 29)
    assert obs2 and "inferida" in obs2.lower()


def test_parse_month_year_from_filename():
    assert parse_month_year_from_filename("Liquidacion 02-2024 x mail.xlsx") == (2024, 2)
    assert parse_month_year_from_filename("Liquidación Febrero 2024.xls") == (2024, 2)


def test_fxseries_get_rate_for_prior_and_future():
    series = FxSeries(
        dates=[date(2024, 1, 1), date(2024, 2, 1)],
        values=[800.0, 900.0],
    )
    assert series.get_rate_for(date(2024, 1, 15)) == 800.0
    assert series.get_rate_for(date(2024, 2, 15)) == 900.0
    # before first -> first future
    assert series.get_rate_for(date(2023, 12, 15)) == 800.0
    # after last -> last
    assert series.get_rate_for(date(2024, 3, 1)) == 900.0


def test_mark_quality_observations_duplicates_and_outliers():
    base = ExtractedRow(
        fecha=date(2024, 1, 10),
        codigo="A",
        categoria="Cat",
        subcategoria="Sub",
        subsubcategoria="Sub2",
        rubro="",
        acreedor="Proveedor X",
        id_acreedor="30-12345678-9",
        tipo_gasto="Gasto",
        descripcion="Servicio",
        monto_ars=100.0,
        tipo_cambio=800.0,
        monto_usd=0.125,
        datos_fiscales="",
        observaciones=[],
        origen="file.xlsx",
    )
    rows = [
        base,
        ExtractedRow(**{**base.__dict__, "descripcion": "Servicio"}),
        ExtractedRow(**{**base.__dict__, "monto_ars": 105.0}),
        ExtractedRow(**{**base.__dict__, "monto_ars": 110.0}),
        ExtractedRow(**{**base.__dict__, "monto_ars": 115.0}),
        ExtractedRow(**{**base.__dict__, "monto_ars": 120.0}),
        ExtractedRow(**{**base.__dict__, "monto_ars": 130.0}),
        ExtractedRow(**{**base.__dict__, "monto_ars": 5000.0}),
    ]

    mark_quality_observations(rows)

    # Duplicates present for first two
    assert any("duplicado" in ";".join(r.observaciones).lower() for r in rows[:2])
    # Outlier marked for the extreme value
    assert "atípico" in ";".join(rows[-1].observaciones).lower()
