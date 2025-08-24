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
        logger.debug("Excel abierto %s; hojas disponibles: %s", xlsx_path.name, xl.sheet_names)
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
            logger.debug("Hoja seleccionada por coincidencia exacta/normalizada: %s", orig)
            return orig
    # fallback: first sheet containing "gastos"
    for norm, orig in normalized.items():
        if "gastos" in norm:
            logger.debug("Hoja seleccionada por coincidencia parcial: %s", orig)
            return orig
    # fallback: first sheet
    if xl.sheet_names:
        logger.debug("Hoja fallback (primera): %s", xl.sheet_names[0])
        return xl.sheet_names[0]
    logger.debug("Libro sin hojas: %s", xlsx_path.name)
    return None


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

    logger.debug("Extrayendo datos de '%s' hoja '%s'", xlsx_path.name, sheet_name)
    try:
        logger.debug("Leyendo hoja '%s' de %s", sheet_name, xlsx_path.name)
        df = pd.read_excel(xlsx_path, sheet_name=sheet_name, header=None, dtype=object)
        logger.debug("DataFrame leído: %s filas x %s columnas", df.shape[0], df.shape[1])
    except Exception as e:
        logger.warning("Error leyendo %s/%s: %s", xlsx_path.name, sheet_name, e)
        return []

    rows: List[ExtractedRow] = []
    last_cat = last_sub = last_subsub = ""
    session = None  # created lazily in enrich_cuit
    empty_skips = total_marker_skips = missing_core_skips = processed_rows = 0
    logger.debug("Comenzando procesamiento de filas en %s", xlsx_path.name)

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
            empty_skips += 1
            continue

        # Carry-forward categories
        if isinstance(B, str) and B.strip():
            new_cat = str(B).strip()
            if new_cat != last_cat:
                logger.debug("Fila %d: categoría -> %s", idx, new_cat)
            last_cat = new_cat
        if isinstance(C, str) and C.strip() and not is_total_marker(C):
            new_sub = str(C).strip()
            if new_sub != last_sub:
                logger.debug("Fila %d: subcategoría -> %s", idx, new_sub)
            last_sub = new_sub
        if isinstance(D, str) and D.strip() and not is_total_marker(D):
            new_subsub = str(D).strip()
            if new_subsub != last_subsub:
                logger.debug("Fila %d: sub-subcategoría -> %s", idx, new_subsub)
            last_subsub = new_subsub

        # Ignore totals rows
        if is_total_marker(B) or is_total_marker(C) or is_total_marker(D):
            total_marker_skips += 1
            logger.debug("Fila %d: ignorada por marcador de total/subtotal", idx)
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
            missing_core_skips += 1
            logger.debug("Fila %d: ignorada por faltar tipo/memo/importe", idx)
            continue

        # Date handling
        ym = y_m_from_name
        dval, obs_date = normalize_date_ddmmyyyy(F, ym)
        logger.debug("Fila %d: fecha normalizada=%s obs=%s (fallback ym=%s)", idx, dval, obs_date, y_m_from_name)

        # FX and USD conversion
        fx_rate = fx.get_rate_for(dval) if dval else None
        monto_usd = None
        if fx_rate and monto_ars is not None:
            try:
                monto_usd = monto_ars / fx_rate if fx_rate else None
            except Exception:
                monto_usd = None
        logger.debug("Fila %d: monto_ars=%s fx=%s monto_usd=%s", idx, monto_ars, fx_rate, monto_usd)

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
                logger.debug("Fila %d: enriquecimiento CUIT cache hit %s", idx, cuit_norm)
            else:
                logger.debug("Fila %d: enriqueciendo CUIT %s", idx, cuit_norm)
                info = enrich_cuit(cuit_norm)
                if info:
                    datos_fiscales = info
                    cache[cuit_norm] = info
                    logger.debug("Fila %d: enriquecimiento OK -> %s", idx, info)
                else:
                    obs.append("Enriquecimiento CUIT fallido")
                    logger.debug("Fila %d: enriquecimiento fallido", idx)
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
        processed_rows += 1
        logger.debug(
            "Fila %d agregada: codigo=%s cuit=%s fecha=%s ars=%s usd=%s tipo=%s memo=%s",
            idx, codigo, cuit_norm, dval, monto_ars, monto_usd, tipo_gasto, (memo[:40] + ("…" if len(memo) > 40 else "")),
        )

    logger.debug(
        "Finalizado %s: procesadas=%d, vacías=%d, totales=%d, faltantes=%d, resultado=%d",
        xlsx_path.name, processed_rows, empty_skips, total_marker_skips, missing_core_skips, len(rows)
    )
    return rows
