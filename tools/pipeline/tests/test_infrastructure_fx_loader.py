# Methodology: TDD – tests for infrastructure.fx_loader
from __future__ import annotations

from datetime import date

from tools.pipeline.infrastructure.fx_loader import load_fx_series


def test_load_fx_series_parses_dates_and_numbers(tmp_path):
    csv_path = tmp_path / "fx.csv"
    # Use quotes around values with comma decimal separator to avoid CSV field splitting
    csv_path.write_text(
        "\n".join([
            "Fecha,Valor ARS",
            "15/01/2024,\"1.000,00\"",
            "16/01/2024,\"1.100,00\"",
            "",
        ])
    )

    fx = load_fx_series(csv_path)
    assert len(fx.dates) == 2
    assert fx.get_rate_for(date(2024, 1, 15)) == 1000.0
    assert fx.get_rate_for(date(2024, 1, 17)) == 1100.0
