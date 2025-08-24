# Methodology: Clean Architecture – infrastructure adapters (network)
from __future__ import annotations

import re
from typing import Optional

import requests
from bs4 import BeautifulSoup

from ..domain.models import normalize_text


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
        # Heuristic extraction
        text = " ".join(t.get_text(" ", strip=True) for t in soup.find_all(["p", "li", "td", "span"]))
        text_norm = normalize_text(text)
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
