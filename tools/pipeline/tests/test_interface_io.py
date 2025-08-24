# Methodology: TDD – tests for interface.io
from __future__ import annotations

from pathlib import Path

from tools.pipeline.interface.io import collect_input_files, write_output_rows
from tools.pipeline.domain.models import REQUIRED_COLUMNS_OUT


def _sample_row() -> dict[str, object]:
    row = {k: "" for k in REQUIRED_COLUMNS_OUT}
    row.update({
        "fecha": "15/01/2024",
        "código": "001",
        "categoría": "Cat",
        "subcategoría": "Sub",
        "sub-subcategoría": "Sub2",
        "rubro": "",
        "acreedor": "Proveedor SA",
        "ID acreedor": "30-12345678-9",
        "tipo de gasto": "Operativo",
        "descripción": "Servicio",
        "monto ARS": "1000.00",
        "monto USD": "1.00",
        "tipo de cambio": "1000.00",
        "datos fiscales": "",
        "observaciones": "",
        "origen": "test.xlsx",
    })
    return row


def test_collect_input_files_filters_xlsx_only(tmp_path):
    # Create files
    (tmp_path / "a.xlsx").write_text("x")
    (tmp_path / "b.xls").write_text("x")
    (tmp_path / "c.txt").write_text("x")

    files = collect_input_files([str(tmp_path)])
    names = {p.name for p in files}
    assert names == {"a.xlsx"}


def test_write_output_rows_write_and_append(tmp_path):
    out = tmp_path / "out.csv"
    rows1 = [_sample_row()]
    rows2 = [_sample_row()]

    # Write
    write_output_rows(rows1, output=out, append=None)
    assert out.exists()
    text1 = out.read_text().strip().splitlines()
    assert text1[0].startswith(",".join(REQUIRED_COLUMNS_OUT[:3]))  # has header
    assert len(text1) == 2  # header + one row

    # Append (no header)
    write_output_rows(rows2, output=None, append=out)
    text2 = out.read_text().strip().splitlines()
    assert len(text2) == 3  # + one row, header not duplicated
