# Methodology: TDD – tests for enrich_cuit DOM parsing and fallbacks
from __future__ import annotations

from typing import Any

import pytest

from tools.pipeline.infrastructure.enrich import enrich_cuit


class FakeResponse:
    def __init__(self, status_code: int, text: str) -> None:
        self.status_code = status_code
        self.text = text


class FakeSession:
    def __init__(self, response: FakeResponse) -> None:
        self._response = response

    def get(self, url: str, headers: dict[str, Any] | None = None, timeout: float | None = None) -> FakeResponse:
        return self._response


def test_enrich_cuit_parses_dom_structure_with_category_letter() -> None:
    html = (
        '<div class="hit">'
        '  <div class="denominacion">'
        '    <a href="#" class="denominacion">'
        '      <h2 class="denominacion">OCAMPO FEDERICO ANDRES</h2>'
        "    </a>"
        "  </div>"
        '  <div class="doc-facets">'
        '    <span class="linea-cuit-persona">CUIT: <span class="cuit">20-29288390-1</span></span><br>'
        '    <span class="linea-monotributo-persona">Monotributista CATEGORÍA B</span><br>'
        '    <span>Persona Física</span>'
        "  </div>"
        "</div>"
    )
    sess = FakeSession(FakeResponse(200, html))
    out = enrich_cuit("20-29288390-1", session=sess)
    assert (
        out
        == "OCAMPO FEDERICO ANDRES / 20-29288390-1 / Monotributista (Categoría B) / Persona Física"
    )


def test_enrich_cuit_parses_dom_structure_without_category_letter() -> None:
    html = (
        '<div class="hit">'
        '  <div class="denominacion">'
        '    <h2 class="denominacion">ACME SRL</h2>'
        "  </div>"
        '  <div class="doc-facets">'
        '    <span class="linea-cuit-persona">CUIT: <span class="cuit">30-12345678-9</span></span><br>'
        '    <span>Monotributista</span><br>'
        '    <span>Persona Jurídica</span>'
        "  </div>"
        "</div>"
    )
    sess = FakeSession(FakeResponse(200, html))
    out = enrich_cuit("30-12345678-9", session=sess)
    assert out == "ACME SRL / 30-12345678-9 / Monotributista / Persona Jurídica"


def test_enrich_cuit_fallback_parsing_when_no_hit_container() -> None:
    html = (
        "<html><body>"
        "<p>Nombre: empresa de servicios sa</p>"
        "<span>Persona Juridica</span>"
        "<span>Responsable Inscripto</span>"
        "</body></html>"
    )
    sess = FakeSession(FakeResponse(200, html))
    out = enrich_cuit("30-00000000-0", session=sess)
    # Fallback title-cases the extracted 'nombre' value; tipo resolved from the text
    assert out == "Empresa De Servicios Sa / 30-00000000-0 / Responsable / Persona Juridica"


def test_enrich_cuit_non_200_returns_none() -> None:
    sess = FakeSession(FakeResponse(404, "not found"))
    assert enrich_cuit("20-11111111-1", session=sess) is None


def test_enrich_cuit_empty_input_returns_none() -> None:
    assert enrich_cuit("") is None
