# Methodology: Clean Architecture – refactor pipeline into separated layers
# Domain layer: entities and pure business rules (no I/O)
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Dict, List, Optional, Tuple
import math
import re

import numpy as np

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


# -------------------------- Entities --------------------------
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
        def _num_ok(x: object) -> bool:
            return isinstance(x, (int, float)) and not (isinstance(x, float) and math.isnan(x))

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
            "monto ARS": f"{self.monto_ars:.2f}" if _num_ok(self.monto_ars) else "",
            "monto USD": f"{self.monto_usd:.2f}" if _num_ok(self.monto_usd) else "",
            "tipo de cambio": f"{self.tipo_cambio:.2f}" if _num_ok(self.tipo_cambio) else "",
            "datos fiscales": self.datos_fiscales or "",
            "observaciones": "; ".join(self.observaciones) if self.observaciones else "",
            "origen": self.origen,
        }


# -------------------------- Pure domain functions --------------------------

def _strip_diacritics(s: str) -> str:
    import unicodedata

    nk = unicodedata.normalize("NFKD", s)
    return "".join(ch for ch in nk if not unicodedata.combining(ch))


def normalize_text(s: str) -> str:
    return re.sub(r"\s+", " ", _strip_diacritics(s or "").strip().lower())


def parse_ars_number(value: object) -> Optional[float]:
    # Numeric inputs: return as-is (guard NaN)
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    if isinstance(value, (int, float)):
        return float(value)
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
