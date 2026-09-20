#!/usr/bin/env python3
"""
test_fpa_theme.py — tema compartido del sitio (coffe-gen.2, change
update-fpa-site-integration: identidad visual + nomenclatura llana)

Cubre el alcance del ticket coffe-gen.2:
- paridad de tokens: los :root de fpa-dashboard.html, index.html y
  gantt-multitasking.html provienen de scripts/site_theme.py y son idénticos
  entre sí (scenario "paridad de tokens entre generadores")
- el CSS de viz-fpa.py ya no define su propia paleta ni modo oscuro
  (scenario "smoke visual del tema": base para los asserts de Playwright)
- nomenclatura: ningún label visible generado contiene "FP&A"
  (scenarios "label sin jerga" y "test de nomenclatura falla loud")
- contraste AA: pares de texto del tema compartido ≥ 4.5:1 sobre silver y
  blanco (scenario "contraste AA bajo el tema compartido")
"""

import importlib.util
import json
import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def _load(name, relpath):
    spec = importlib.util.spec_from_file_location(name, REPO / relpath)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


viz = _load("viz_fpa", "scripts/viz-fpa.py")
theme = _load("site_theme", "scripts/site_theme.py")

REPORT = json.loads((REPO / "data" / "usage_report_v3.json").read_text())
CONFIG = json.loads((REPO / "config" / "fpa.json").read_text())

ARTIFACTS = [
    REPO / "data" / "fpa-dashboard.html",
    REPO / "index.html",
    REPO / "data" / "gantt-multitasking.html",
]


def _rendered():
    """HTML real del reporte del repo (determinista: fecha fija)."""
    return viz.render_html(REPORT, CONFIG, generated="2026-09-19 12:00")


def _root_vars(html):
    """Dict de variables del primer bloque :root del HTML."""
    m = re.search(r":root\s*\{(.*?)\}", html, flags=re.S)
    assert m, "sin bloque :root en el HTML"
    return dict(re.findall(r"(--[a-z0-9-]+)\s*:\s*([^;]+)", m.group(1)))


def _visible_text(html):
    """Texto visible crudo (sin atributos, sin <style>/<script>)."""
    body = re.sub(r"<(style|script)[^>]*>.*?</\1>", "", html, flags=re.S)
    return re.sub(r"<[^>]+>", " ", body)


def _luminance(hex_color):
    """Luminancia relativa WCAG de un color #rrggbb."""
    h = hex_color.lstrip("#")
    rgb = [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
           for c in rgb]
    return (0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2])


def _contrast(fg, bg):
    l1, l2 = sorted((_luminance(fg), _luminance(bg)), reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)


class TestParidadDeTokens(unittest.TestCase):
    """Los tokens :root de todos los HTML vienen del módulo compartido."""

    def test_tokens_de_site_theme_son_la_fuente(self):
        self.assertIn("--bg", theme.TOKENS)
        self.assertEqual(theme.TOKENS["--bg"], "#c0c0c0")
        self.assertEqual(theme.TOKENS["--accent"], "#800000")
        self.assertEqual(theme.TOKENS["--navy"], "#000080")

    def test_vars_css_interpolan_el_módulo(self):
        """css_vars() emite exactamente las variables de TOKENS."""
        block = theme.css_vars()
        self.assertEqual(_root_vars(f"<style>{block}</style>"),
                         dict(theme.TOKENS))

    def test_paridad_entre_artefactos_generados(self):
        """Los tres HTML publicados comparten el mismo :root del módulo."""
        htmls = [(p, p.read_text(encoding="utf-8")) for p in ARTIFACTS]
        for path, html in htmls:
            self.assertEqual(_root_vars(html), dict(theme.TOKENS),
                             f"{path.name} no usa los tokens del tema")

    def test_fpa_css_sin_paleta_propia_ni_modo_oscuro(self):
        """El CSS del FPA no define colores de paleta ni dark mode."""
        css = viz.CSS
        self.assertNotIn("prefers-color-scheme", css)
        self.assertNotIn("system-ui", css)
        self.assertNotIn("#f4f2ec", css)  # paleta crema anterior
        self.assertIn("var(--acc)", css)  # sigue consumiendo tokens
        self.assertIn("Arial", css)       # tipografía del sitio


class TestNomenclaturaLlana(unittest.TestCase):
    """Ningún label visible generado contiene FP&A ni jerga sin explicar."""

    def test_render_no_contiene_fpa_en_labels(self):
        html = _rendered()
        text = _visible_text(html)
        self.assertNotIn("FP&A", text)

    def test_title_y_h1_usan_site_name(self):
        html = _rendered()
        site = CONFIG["site_name"]
        self.assertIn(site, html)
        self.assertNotIn("Dashboard FP&A", html)

    def test_artefactos_publicados_sin_fpa(self):
        for path in ARTIFACTS[:2]:
            self.assertNotIn("FP&A", _visible_text(path.read_text()),
                             f"{path.name} tiene labels con FP&A")


class TestContrasteAA(unittest.TestCase):
    """Texto normal del tema ≥ 4.5:1 sobre silver y blanco."""

    def test_pares_texto_fondo(self):
        t = theme.TOKENS
        pares = [
            (t["--fg"], t["--bg"]),
            (t["--fg"], t["--panel"]),
            (t["--muted"], t["--panel"]),
            (t["--muted"], t["--bg"]),
            (t["--accent"], t["--panel"]),
            (t["--accent2"], t["--panel"]),
        ]
        for fg, bg in pares:
            self.assertGreaterEqual(
                _contrast(fg, bg), 4.5, f"{fg} sobre {bg} no alcanza AA")


if __name__ == "__main__":
    unittest.main()
