#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Methodology: TDD – implementing expense consolidation pipeline script

Consolidate expenses from monthly XLSX files with the following features:
- Locate sheet "Gastos del Mes" (case/diacritics-insensitive)
- Extract columns B..J as specified, carry-forward categories, ignore "Total..." rows
- Parse dates (DD/MM/YYYY), normalize ARS amounts, parse CUIT from payee (H)
- Map standardized 'rubro' by keywords
- Convert ARS to USD using official FX CSV from docs/
- Optional CUIT enrichment via web scraping (cuitonline.com) with caching and timeouts
- Quality controls: duplicates, missing fields, outlier amounts (IQR)
- Output CSV to file (with header), append to existing CSV (no header), or stdout if neither specified

Security by Design:
- No secrets; HTTP requests use simple GET with timeout and basic UA
- Input paths sanitized via pathlib; no shell execution

"""
from __future__ import annotations

import argparse
import csv
import logging
import math
import re
import sys
import time
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import requests
from bs4 import BeautifulSoup

# -------------------------- Logging --------------------------
logger = logging.getLogger("consolidate_expenses")

# -------------------------- Constants --------------------------
SHEET_TARGET = "gastos del mes"
CUIT_REGEX = re.compile(r"(20|2[3-7]|30|3[3-4])[- .]?(\d{8})[- .]?(\d)")
ES_NUMBER_THS = "."
ES_NUMBER_DEC = ","

REQUIRED_COLUMNS_OUT = [
    "fecha",
    "código",
    "categoría",
    "subcategoría",
    "sub-subcategoría",
    "rubro",
    "acreedor",
    "ID acreedor",
    "tipo de gasto",
    "descripción",
    "monto ARS",
    "monto USD",
    "tipo de cambio",
    "datos fiscales",
    "observaciones",
    "origen",
]

RUBRO_KEYWORDS = [
    ("segur", "Seguridad"),
    ("energ", "Energía"),
    ("jardin", "Jardinería"),
    ("manten", "Mantenimiento"),
    ("obra", "Obras"),
    ("legales", "Legales"),
    ("luz", "Energía"),
    ("electric", "Energía"),
    ("gas", "Energía"),
    ("impres", "Administración"),
    ("admin", "Administración"),
    ("correo", "Administración"),
    ("librer", "Administración"),
]

# -------------------------- Data Structures --------------------------
@dataclass
class FxSeries:
    dates: List[date]
    values: List[float]

    def get_rate_for(self, d: date) -> Optional[float]:
        """Return the FX for the given date or the most recent prior; if none, try next future; else None."""
        if not self.dates:
            return None
        # Binary search for rightmost <= d
        lo, hi = 0, len(self.dates) - 1
        ans_idx = -1
        while lo <= hi:
            mid = (lo + hi) // 2
            if self.dates[mid] <= d:
                ans_idx = mid
                lo = mid + 1
            else:
                hi = mid - 1
        if ans_idx >= 0:
            return self.values[ans_idx]
        # try first future
        for i, dd in enumerate(self.dates):
            if dd >= d:
                return self.values[i]
        return None

# -------------------------- Helpers --------------------------

def _strip_diacritics(s: str) -> str:
    import unicodedata

    nk = unicodedata.normalize("NFKD", s)
    return "".join(ch for ch in nk if not unicodedata.combining(ch))


def normalize_text(s: str) -> str:
    return re.sub(r"\s+", " ", _strip_diacritics(s or "").strip().lower())


def parse_ars_number(value: object) -> Optional[float]:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    s = str(value).strip()
    if not s:
        return None
    # Remove thousands sep, change decimal sep
    s = s.replace(ES_NUMBER_THS, "").replace(ES_NUMBER_DEC, ".")
    # Remove any stray spaces
    s = s.replace(" ", "")
    try:
        return float(s)
    except ValueError:
        # Some xl cells may already be numbers
        try:
            return float(value)  # type: ignore[arg-type]
        except Exception:
            return None


def parse_cuit_from_payee(payee: object) -> Tuple[str, Optional[str]]:
    name = str(payee or "").strip()
    text = normalize_text(name)
    m = CUIT_REGEX.search(text)
    if not m:
        return name, None
    parts = (m.group(1), m.group(2), m.group(3))
    normalized = f"{parts[0]}-{parts[1]}-{parts[2]}"
    return name, normalized


def normalize_date_ddmmyyyy(raw: object, fallback_from_file: Optional[Tuple[int, int]] = None) -> Tuple[Optional[date], Optional[str]]:
    """Return (date_obj, observation_if_any). Fallback can be (year, month) to set end-of-month."""
    if isinstance(raw, (datetime, date)):
        d = raw.date() if isinstance(raw, datetime) else raw
        return d, None
    s = str(raw or "").strip()
    fmts = ["%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"]
    for fmt in fmts:
        try:
            return datetime.strptime(s, fmt).date(), None
        except Exception:
            pass
    if fallback_from_file:
        y, m = fallback_from_file
        # use last day of month
        import calendar

        d = date(y, m, calendar.monthrange(y, m)[1])
        return d, "Fecha inferida por nombre de archivo (fin de mes)"
    return None, "Falta fecha"


def detect_rubro(categoria: str, subcat: str, memo: str) -> str:
    blob = normalize_text(" ".join([categoria or "", subcat or "", memo or ""]))
    for kw, rubro in RUBRO_KEYWORDS:
        if kw in blob:
            return rubro
    return ""


def is_total_marker(val: object) -> bool:
    s = normalize_text(str(val or ""))
    return s.startswith("total") or s in {"subtotal", "totales"}


def load_fx_series(path: Path) -> FxSeries:
    df = pd.read_csv(path)
    # Expect columns: Fecha, Valor ARS in es-AR format
    def to_date(x: str) -> date:
        return datetime.strptime(str(x).strip(), "%d/%m/%Y").date()

    def to_float(x: str) -> float:
        return parse_ars_number(x) or float("nan")

    df["_fecha"] = df["Fecha"].map(to_date)
    df["_valor"] = df["Valor ARS"].map(to_float)
    df = df.dropna(subset=["_fecha", "_valor"]).sort_values("_fecha").reset_index(drop=True)
    return FxSeries(dates=df["_fecha"].tolist(), values=df["_valor"].tolist())


def find_target_sheet(xlsx_path: Path) -> Optional[str]:
    try:
        xl = pd.ExcelFile(xlsx_path)
    except Exception as e:
        logger.warning("No se pudo abrir %s: %s", xlsx_path.name, e)
        return None
    normalized = {normalize_text(name): name for name in xl.sheet_names}
    for norm, orig in normalized.items():
        if SHEET_TARGET in norm:
            return orig
    # fallback: first sheet containing "gastos"
    for norm, orig in normalized.items():
        if "gastos" in norm:
            return orig
    # fallback: first sheet
    return xl.sheet_names[0] if xl.sheet_names else None


@dataclass
class ExtractedRow:
    fecha: Optional[date]
    codigo: str
    categoria: str
    subcategoria: str
    subsubcategoria: str
    rubro: str
    acreedor: str
    id_acreedor: Optional[str]
    tipo_gasto: str
    descripcion: str
    monto_ars: Optional[float]
    tipo_cambio: Optional[float]
    monto_usd: Optional[float]
    datos_fiscales: str
    observaciones: List[str]
    origen: str

    def to_csv_row(self) -> Dict[str, object]:
        return {
            "fecha": self.fecha.strftime("%d/%m/%Y") if self.fecha else "",
            "código": self.codigo or "",
            "categoría": self.categoria or "",
            "subcategoría": self.subcategoria or "",
            "sub-subcategoría": self.subsubcategoria or "",
            "rubro": self.rubro or "",
            "acreedor": self.acreedor or "",
            "ID acreedor": self.id_acreedor or "",
            "tipo de gasto": self.tipo_gasto or "",
            "descripción": self.descripcion or "",
            "monto ARS": f"{self.monto_ars:.2f}" if isinstance(self.monto_ars, (int, float)) and not pd.isna(self.monto_ars) else "",
            "monto USD": f"{self.monto_usd:.2f}" if isinstance(self.monto_usd, (int, float)) and not pd.isna(self.monto_usd) else "",
            "tipo de cambio": f"{self.tipo_cambio:.2f}" if isinstance(self.tipo_cambio, (int, float)) and not pd.isna(self.tipo_cambio) else "",
            "datos fiscales": self.datos_fiscales or "",
            "observaciones": "; ".join(self.observaciones) if self.observaciones else "",
            "origen": self.origen,
        }


def enrich_cuit(cuit: str, session: Optional[requests.Session] = None, timeout: float = 10.0) -> Optional[str]:
    """Fetch basic fiscal info from cuitonline.com. Returns formatted string or None on failure.
    NOTE: Best-effort; site structure may change. Respect robots/ToS and rate-limit callers.
    """
    if not cuit:
        return None
    sess = session or requests.Session()
    url = f"https://www.cuitonline.com/search/{cuit}"
    headers = {"User-Agent": "Mozilla/5.0 (expenses-consolidator)"}
    try:
        resp = sess.get(url, headers=headers, timeout=timeout)
        if resp.status_code != 200:
            return None
        soup = BeautifulSoup(resp.text, "html.parser")
        # Very heuristic: look for blocks containing CUIT and category
        text = " ".join(t.get_text(" ", strip=True) for t in soup.find_all(["p", "li", "td", "span"]))
        text_norm = normalize_text(text)
        # Attempt to extract some fields
        name_match = re.search(r"nombre\s*:\s*([^|\n]+)", text_norm)
        cat_match = re.search(r"(monotrib|responsable|autonom|exento|consumidor)", text_norm)
        tipo_match = re.search(r"(persona\s+juridica|persona\s+fisica|sociedad)", text_norm)
        name = name_match.group(1).strip().title() if name_match else ""
        cat = (cat_match.group(1).strip().title() if cat_match else "").replace("Responsable", "Responsable")
        tipo = tipo_match.group(1).strip().title() if tipo_match else ""
        parts = [p for p in [name, cuit, cat, tipo] if p]
        return " / ".join(parts) if parts else None
    except Exception:
        return None


def extract_from_workbook(xlsx_path: Path, fx: FxSeries, y_m_from_name: Optional[Tuple[int, int]], enrich: bool, rate_limit_s: float, cache: Dict[str, str]) -> List[ExtractedRow]:
    sheet_name = find_target_sheet(xlsx_path)
    if not sheet_name:
        logger.warning("No se encontró hoja en %s", xlsx_path.name)
        return []

    try:
        df = pd.read_excel(xlsx_path, sheet_name=sheet_name, header=None, dtype=object)
    except Exception as e:
        logger.warning("Error leyendo %s/%s: %s", xlsx_path.name, sheet_name, e)
        return []

    rows: List[ExtractedRow] = []
    last_cat = last_sub = last_subsub = ""
    session = requests.Session() if enrich else None

    for idx in range(len(df)):
        # Expect columns: B..J at indices 1..9
        B = df.iat[idx, 1] if df.shape[1] > 1 else None
        C = df.iat[idx, 2] if df.shape[1] > 2 else None
        D = df.iat[idx, 3] if df.shape[1] > 3 else None
        E = df.iat[idx, 4] if df.shape[1] > 4 else None
        F = df.iat[idx, 5] if df.shape[1] > 5 else None
        G = df.iat[idx, 6] if df.shape[1] > 6 else None
        H = df.iat[idx, 7] if df.shape[1] > 7 else None
        I = df.iat[idx, 8] if df.shape[1] > 8 else None
        J = df.iat[idx, 9] if df.shape[1] > 9 else None

        # Skip empty lines quickly
        if all((x is None or (isinstance(x, float) and pd.isna(x)) or str(x).strip() == "") for x in [B, C, D, E, F, G, H, I, J]):
            continue

        # Carry-forward categories
        if isinstance(B, str) and normalize_text(B):
            last_cat = str(B).strip()
        if isinstance(C, str) and normalize_text(C) and not is_total_marker(C):
            last_sub = str(C).strip()
        if isinstance(D, str) and normalize_text(D) and not is_total_marker(D):
            last_subsub = str(D).strip()

        # Ignore totals rows
        if is_total_marker(B) or is_total_marker(C) or is_total_marker(D):
            continue

        categoria = last_cat
        subcat = last_sub
        subsub = last_subsub
        tipo_gasto = str(E or "").strip()
        codigo = str(G or "").strip()
        payee_name, cuit_norm = parse_cuit_from_payee(H)
        memo = str(I or "").strip()
        monto_ars = parse_ars_number(J)

        # Skip rows lacking core fields
        if (not tipo_gasto) and (not memo) and (monto_ars is None):
            continue

        # Date handling
        ym = y_m_from_name
        dval, obs_date = normalize_date_ddmmyyyy(F, ym)

        # FX and USD conversion
        fx_rate = fx.get_rate_for(dval) if dval else None
        monto_usd = None
        if fx_rate and monto_ars is not None:
            try:
                monto_usd = monto_ars / fx_rate if fx_rate else None
            except Exception:
                monto_usd = None

        rubro = detect_rubro(categoria or "", subcat or "", memo or "")

        obs: List[str] = []
        if obs_date:
            obs.append(obs_date)
        if monto_ars is None:
            obs.append("Falta importe ARS")
        if not dval:
            obs.append("Falta fecha")

        datos_fiscales = ""
        if cuit_norm and enrich:
            if cuit_norm in cache:
                datos_fiscales = cache[cuit_norm]
            else:
                info = enrich_cuit(cuit_norm, session=session)
                if info:
                    datos_fiscales = info
                    cache[cuit_norm] = info
                else:
                    obs.append("Enriquecimiento CUIT fallido")
                time.sleep(rate_limit_s)

        row = ExtractedRow(
            fecha=dval,
            codigo=codigo,
            categoria=categoria or "",
            subcategoria=subcat or "",
            subsubcategoria=subsub or "",
            rubro=rubro,
            acreedor=payee_name or "",
            id_acreedor=cuit_norm,
            tipo_gasto=tipo_gasto,
            descripcion=memo,
            monto_ars=monto_ars,
            tipo_cambio=fx_rate,
            monto_usd=monto_usd,
            datos_fiscales=datos_fiscales,
            observaciones=obs,
            origen=xlsx_path.name,
        )
        rows.append(row)

    return rows


def mark_quality_observations(rows: List[ExtractedRow]) -> None:
    # Duplicates: by (fecha, id/acreedor, monto, descripcion[:40])
    def key(r: ExtractedRow) -> Tuple:
        k_id = r.id_acreedor or normalize_text(r.acreedor)
        desc = normalize_text(r.descripcion)[:40]
        return (r.fecha, k_id, round(r.monto_ars or 0.0, 2), desc)

    seen: Dict[Tuple, int] = {}
    for r in rows:
        k = key(r)
        seen[k] = seen.get(k, 0) + 1
    for r in rows:
        if seen[key(r)] > 1:
            r.observaciones.append("Posible duplicado")

    # Outliers: IQR on monto_ars > 0
    vals = np.array([r.monto_ars for r in rows if r.monto_ars and r.monto_ars > 0], dtype=float)
    if len(vals) >= 8:
        q1 = np.percentile(vals, 25)
        q3 = np.percentile(vals, 75)
        iqr = q3 - q1
        lo = q1 - 1.5 * iqr
        hi = q3 + 1.5 * iqr
        for r in rows:
            if r.monto_ars is not None and (r.monto_ars < lo or r.monto_ars > hi):
                r.observaciones.append("Monto atípico")


def parse_month_year_from_filename(name: str) -> Optional[Tuple[int, int]]:
    s = normalize_text(name)
    m = re.search(r"\b(0?[1-9]|1[0-2])[-_/](20\d{2})\b", s)
    if m:
        mm = int(m.group(1))
        yyyy = int(m.group(2))
        return yyyy, mm
    # months in Spanish
    sp_months = {
        "enero": 1,
        "febrero": 2,
        "marzo": 3,
        "abril": 4,
        "mayo": 5,
        "junio": 6,
        "julio": 7,
        "agosto": 8,
        "septiembre": 9,
        "setiembre": 9,
        "octubre": 10,
        "noviembre": 11,
        "diciembre": 12,
    }
    for mname, mnum in sp_months.items():
        if mname in s:
            y = re.search(r"(20\d{2})", s)
            if y:
                return int(y.group(1)), mnum
    return None


def to_dataframe(rows: List[ExtractedRow]) -> pd.DataFrame:
    out = [r.to_csv_row() for r in rows]
    df = pd.DataFrame(out, columns=REQUIRED_COLUMNS_OUT)
    return df


def write_output(df: pd.DataFrame, output: Optional[Path], append: Optional[Path]) -> None:
    if append and output:
        logger.warning("Se especificaron 'output' y 'append'. Se prioriza 'append'.")
    target = append or output
    if target:
        target.parent.mkdir(parents=True, exist_ok=True)
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
        csv_text = df.to_csv(index=False, quoting=csv.QUOTE_MINIMAL)
        sys.stdout.write(csv_text)


def filter_by_year(df: pd.DataFrame, from_year: Optional[int], to_year: Optional[int]) -> pd.DataFrame:
    if from_year is None and to_year is None:
        return df
    def year_of(s: str) -> Optional[int]:
        try:
            return datetime.strptime(s, "%d/%m/%Y").year
        except Exception:
            return None
    years = df["fecha"].map(year_of)
    mask = pd.Series([True] * len(df))
    if from_year is not None:
        mask &= years.fillna(-1) >= from_year
    if to_year is not None:
        mask &= years.fillna(9999) <= to_year
    return df[mask].reset_index(drop=True)


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
        if f not in seen:
            uniq.append(f)
            seen.add(f)
    # Restrict to .xlsx files; .xls is not supported by openpyxl
    uniq = [f for f in uniq if f.suffix.lower() == ".xlsx"]
    return uniq


def main(argv: Optional[List[str]] = None) -> int:
    """Delegate to the clean-architecture CLI implementation."""
    from .interface.cli import main as cli_main

    return cli_main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
