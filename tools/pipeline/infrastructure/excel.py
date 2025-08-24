# Methodology: Clean Architecture – infrastructure adapters (Excel parsing)
from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

from ..domain.models import (
    ExtractedRow,
    detect_rubro,
    is_total_marker,
    normalize_date_ddmmyyyy,
    parse_ars_number,
    parse_cuit_from_payee,
)
from .enrich import enrich_cuit

logger = logging.getLogger("pipeline.infrastructure.excel")


def find_target_sheet(xlsx_path: Path) -> Optional[str]:
    try:
        xl = pd.ExcelFile(xlsx_path)
    except Exception as e:
        logger.warning("No se pudo abrir %s: %s", xlsx_path.name, e)
        return None
    # try exact/normalized match
    def normalize_text(s: str) -> str:
        import re, unicodedata

        nk = unicodedata.normalize("NFKD", s or "")
        s2 = "".join(ch for ch in nk if not unicodedata.combining(ch))
        return re.sub(r"\s+", " ", s2.strip().lower())

    normalized = {normalize_text(name): name for name in xl.sheet_names}
    for norm, orig in normalized.items():
        if "gastos del mes" in norm:
            return orig
    # fallback: first sheet containing "gastos"
    for norm, orig in normalized.items():
        if "gastos" in norm:
            return orig
    # fallback: first sheet
    return xl.sheet_names[0] if xl.sheet_names else None


def extract_from_workbook(
    xlsx_path: Path,
    fx,
    y_m_from_name: Optional[Tuple[int, int]],
    enrich: bool,
    rate_limit_s: float,
    cache: Dict[str, str],
) -> List[ExtractedRow]:
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
    session = None  # created lazily in enrich_cuit

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
        if isinstance(B, str) and B.strip():
            last_cat = str(B).strip()
        if isinstance(C, str) and C.strip() and not is_total_marker(C):
            last_sub = str(C).strip()
        if isinstance(D, str) and D.strip() and not is_total_marker(D):
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
                info = enrich_cuit(cuit_norm)
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
