#!/usr/bin/env python3
"""
test_fpa_guide.py — ingesta de la guía de análisis (coffe-gen.3, change
update-fpa-site-integration: guía a 4 niveles en el sitio)

Cubre el alcance del ticket coffe-gen.3:
- parser stdlib del markdown español (19 análisis × 4 niveles, IDs FPA-xxx
  extraídos del heading)
- render de data/fpa-guide.html autocontenida en el tema compartido, con
  site_name del config, sin 'FP&A' visible, anchors por análisis y sin
  cifras del snapshot 10-jun
- mapping análisis→superficie declarado: todo análisis en ≥1 superficie y
  cada análisis del mapeo existente en la guía
- --check-docs extendido: mapeo con análisis inexistente o umbral citado
  distinto del real en config/código → error (exit non-zero lo maneja el
  caller de viz-fpa.py)
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


guide = _load("viz_fpa_guide", "scripts/viz_fpa_guide.py")
viz = _load("viz_fpa", "scripts/viz-fpa.py")
theme = _load("site_theme", "scripts/site_theme.py")

REPORT = json.loads((REPO / "data" / "usage_report_v3.json").read_text())
CONFIG = json.loads((REPO / "config" / "fpa.json").read_text())
GUIDE_MD = (REPO / "docs" / "fpa-analyses-guide.md").read_text()

NIVELS = ("1 · ELI5", "2 · Cotidiano", "3 · Practicante", "4 · Experto")


class TestParser(unittest.TestCase):
    """El markdown español se parsea completo, sin contentido perdido."""

    def setUp(self):
        self.guide = guide.load_guide(GUIDE_MD)

    def test_20_entradas_19_numeros(self):
        """19 números de análisis; el 10 tiene variantes a/b (20 entradas)."""
        flat = [a for s in self.guide["sections"] for a in s["analyses"]]
        self.assertEqual(20, len(flat))
        nums = {a["num"] for a in flat}
        self.assertEqual({str(i) for i in range(1, 10)} | {"10a", "10b"}
                         | {str(i) for i in range(11, 20)}, nums)

    def test_cuatro_niveles_por_analisis(self):
        for s in self.guide["sections"]:
            for a in s["analyses"]:
                self.assertEqual(4, len(a["levels"]),
                                 f"análisis {a['num']} sin 4 niveles")

    def test_ids_fpa_extraidos(self):
        flat = [a for s in self.guide["sections"] for a in s["analyses"]]
        by_num = {a["num"]: a for a in flat}
        self.assertEqual("FPA-002", by_num["1"]["ids"][0])
        self.assertEqual("FPA-116", by_num["10a"]["ids"][0])
        self.assertIn("FPA-080", by_num["13"]["ids"])

    def test_titulos_y_secciones(self):
        self.assertEqual("A", self.guide["sections"][0]["key"])
        titles = [a["title"] for s in self.guide["sections"]
                  for a in s["analyses"]]
        self.assertIn("Costo efectivo, costo real y apalancamiento", titles)


class TestMapping(unittest.TestCase):
    """Mapeo análisis→superficie: cobertura total y referencias válidas."""

    def test_todos_los_analisis_en_al_menos_una_superficie(self):
        flat = {a["num"] for s in guide.load_guide(GUIDE_MD)["sections"]
                for a in s["analyses"]}
        mapped = {num for num, _ in guide.ANALYSIS_SURFACES}
        self.assertEqual(flat, mapped)

    def test_superficies_validas(self):
        valid = {"summary", "cost", "breakdown", "habits", "outlook",
                 "data", "gantt"}
        for _, surfaces in guide.ANALYSIS_SURFACES:
            self.assertTrue(set(surfaces) <= valid)

    def test_multitasking_y_ritmo_tambien_en_gantt(self):
        surfaces = dict(guide.ANALYSIS_SURFACES)
        self.assertIn("gantt", surfaces["8"])
        self.assertIn("gantt", surfaces["9"])


class TestCheckDocumentation(unittest.TestCase):
    """check_documentation(): mapeo roto o umbral divergente → errores."""

    def test_guia_ok_sin_errores(self):
        self.assertEqual([], guide.check_documentation(CONFIG, GUIDE_MD))

    def test_umbral_citado_distinto_del_config(self):
        """Valor del config que no está citado en la guía → error."""
        cfg = dict(CONFIG)
        cfg["alert_thresholds"] = dict(CONFIG["alert_thresholds"],
                                       plan_usage_multiple=99)
        errors = guide.check_documentation(cfg, GUIDE_MD)
        self.assertTrue(any("99" in e and "plan_usage_multiple" in e
                            for e in errors), errors)

    def test_lifecycle_citado(self):
        cfg = dict(CONFIG)
        cfg["lifecycle"] = dict(CONFIG["lifecycle"], dormant_days=97)
        errors = guide.check_documentation(cfg, GUIDE_MD)
        self.assertTrue(any("97" in e for e in errors), errors)

    def test_mapping_vs_guia(self):
        """Un análisis del mapeo que no exista en la guía → error."""
        errors = guide.check_documentation(CONFIG, GUIDE_MD,
                                           mapping_override=[("99", ["cost"])])
        self.assertTrue(any("99" in e for e in errors), errors)


class TestRenderGuideHtml(unittest.TestCase):
    """data/fpa-guide.html: autocontenida, en el tema, sin FP&A."""

    def setUp(self):
        self.html = guide.render_guide_html(
            guide.load_guide(GUIDE_MD), CONFIG, generated="2026-09-20 12:00")

    def test_anchors_por_analisis(self):
        self.assertIn('id="analisis-1"', self.html)
        self.assertIn('id="analisis-10a"', self.html)
        self.assertIn('id="analisis-19"', self.html)

    def test_en_tema_compartido(self):
        self.assertEqual(dict(theme.TOKENS), _root := dict(re.findall(
            r"(--[a-z0-9-]+)\s*:\s*([^;]+)",
            re.search(r":root\s*\{(.*?)\}", self.html, flags=re.S).group(1))))

    def test_site_name_y_sin_fpa(self):
        self.assertIn(CONFIG["site_name"], self.html)
        body = re.sub(r"<(style|script)[^>]*>.*?</\1>", "", self.html,
                      flags=re.S)
        self.assertNotIn("FP&A", re.sub(r"<[^>]+>", " ", body))

    def test_contenido_niveles_presente(self):
        self.assertIn("ELI5", self.html)
        self.assertIn("Practicante", self.html)
        self.assertIn("Experto", self.html)

    def test_sin_cifras_del_snapshot(self):
        """El snapshot 10-jun no aparece como verdad (cifras reemplazadas)."""
        self.assertNotIn("$65.58", self.html)
        self.assertNotIn("$3,160.94", self.html)

    def test_determinista(self):
        again = guide.render_guide_html(
            guide.load_guide(GUIDE_MD), CONFIG, generated="2026-09-20 12:00")
        self.assertEqual(self.html, again)


if __name__ == "__main__":
    unittest.main()
