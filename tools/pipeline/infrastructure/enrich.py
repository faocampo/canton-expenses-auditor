# Methodology: Clean Architecture – infrastructure adapters (network)
from __future__ import annotations

import logging
import re
from typing import Optional

import requests
from bs4 import BeautifulSoup

from ..domain.models import normalize_text

logger = logging.getLogger("pipeline.infrastructure.enrich")


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
        logger.debug("[enrich] GET %s", url)
        resp = sess.get(url, headers=headers, timeout=timeout)
        logger.debug("[enrich] status=%s bytes=%s", resp.status_code, len(resp.text) if hasattr(resp, "text") else "?")
        if resp.status_code != 200:
            logger.debug("[enrich] Non-200 status for %s: %s", cuit, resp.status_code)
            return None
        soup = BeautifulSoup(resp.text, "html.parser")

        # Prefer structured extraction from the first search hit
        container = soup.select_one("div.hit")
        name = ""
        cuit_text = ""
        cat = ""
        tipo = ""
        if container:
            h2 = container.select_one("h2.denominacion")
            if h2:
                name = h2.get_text(" ", strip=True).strip()
                logger.debug("[enrich] name(h2.denominacion)=%s", name)
            cuit_node = container.select_one("span.cuit")
            if cuit_node:
                cuit_text = cuit_node.get_text(" ", strip=True).strip()
                logger.debug("[enrich] cuit(span.cuit)=%s", cuit_text)
            facets = container.select_one("div.doc-facets")
            if facets:
                facets_text = normalize_text(facets.get_text(" ", strip=True))
                # Category detection
                if "monotribut" in facets_text:
                    m = re.search(r"categor[íi]a\s*([a-z0-9]+)", facets_text)
                    if m:
                        cat = f"Monotributista (Categoría {m.group(1).upper()})"
                    else:
                        cat = "Monotributista"
                elif "responsable" in facets_text:
                    # e.g., responsable inscripto
                    cat = "Responsable Inscripto"
                elif "exento" in facets_text:
                    cat = "Exento"
                elif "consumidor" in facets_text:
                    cat = "Consumidor Final"

                # Person type detection
                if "persona fisica" in facets_text:
                    tipo = "Persona Física"
                elif "persona juridica" in facets_text or "sociedad" in facets_text:
                    tipo = "Persona Jurídica"
                logger.debug("[enrich] facets -> cat=%s tipo=%s", cat, tipo)

        # Fallback heuristic over the whole page if structured nodes not present
        if not any([name, cuit_text, cat, tipo]):
            # Try to extract 'Nombre: ...' from the element that contains it, to avoid capturing following tags
            name_elem = None
            for tag in soup.find_all(["p", "li", "div", "span", "td"]):
                txt = normalize_text(tag.get_text(" ", strip=True))
                if "nombre:" in txt:
                    name_elem = txt
                    break
            page_text = " ".join(t.get_text(" ", strip=True) for t in soup.find_all(["p", "li", "td", "span"]))
            text_norm = normalize_text(page_text)

            if name_elem:
                m_name = re.search(r"nombre\s*:\s*(.+)", name_elem)
                if m_name:
                    name = name or m_name.group(1).strip().title()
            else:
                m_name = re.search(r"nombre\s*:\s*([^|\n]+)", text_norm)
                if m_name:
                    name = name or m_name.group(1).strip().title()

            cat_match = re.search(r"(monotrib|responsable|autonom|exento|consumidor)", text_norm)
            tipo_match = re.search(r"(persona\s+juridica|persona\s+fisica|sociedad)", text_norm)
            cat = cat or ((cat_match.group(1).strip().title() if cat_match else "").replace("Responsable", "Responsable"))
            if not tipo:
                tipo = tipo_match.group(1).strip().title() if tipo_match else ""

        # Prefer CUIT from page; fallback to input CUIT
        cuit_final = cuit_text or cuit
        parts = [p for p in [name, cuit_final, cat, tipo] if p]
        result = " / ".join(parts) if parts else None
        logger.debug("[enrich] extracted for %s -> %s", cuit, result)
        return result
    except Exception as e:
        logger.debug("[enrich] exception for %s: %s", cuit, e, exc_info=True)
        return None
