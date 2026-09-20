#!/usr/bin/env python3
"""
test_fpa_f7.py — verificación final de viz-fpa.py (F7, coffe-lat.8)

Cubre el cierre del epic FP&A:
- determinismo byte-a-byte salvo timestamp, verificado con doble corrida
  real del CLI (FPA-104)
- método de render documentado en README y en el HTML (FPA-145)
- sin placeholders vacíos en el HTML final (FPA-146/108)
- cifras del README consistentes con el JSON (FPA-143, integración real)
- número de figura/tabla sin duplicados (FPA-144/106, HTML completo real)
"""

import importlib.util
import io
import json
import re
import unittest
from contextlib import redirect_stderr
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def _load(name, relpath):
    spec = importlib.util.spec_from_file_location(name, REPO / relpath)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


viz = _load("viz_fpa_f7", "scripts/viz-fpa.py")

REPORT = json.loads((REPO / "data" / "usage_report_v3.json").read_text())
CONFIG = json.loads((REPO / "config" / "fpa.json").read_text())
README = REPO / "README.md"

# el timestamp de generación en el HTML: "Generado: YYYY-MM-DD HH:MM"
GEN_RE = re.compile(r"Generado: \d{4}-\d{2}-\d{2} \d{2}:\d{2}")


def _rendered(generated="2026-09-20 12:00"):
    return viz.render_html(REPORT, CONFIG, generated=generated)


class TestDeterminismo(unittest.TestCase):
    """FPA-104: idéntico output para idéntico input, salvo el timestamp."""

    def test_render_con_timestamps_distintos_difiere_solo_en_ts(self):
        """FPA-104: dos renders con timestamps distintos difieren ÚNICAMENTE
        en la marca de generación (byte-a-byte tras enmascararla)."""
        a = _rendered("2026-09-20 10:00")
        b = _rendered("2026-09-20 11:00")
        self.assertNotEqual(a, b, "el timestamp no se propaga al HTML")
        ma = GEN_RE.sub("Generado: T", a)
        mb = GEN_RE.sub("Generado: T", b)
        self.assertEqual(ma, mb, "diferencia fuera del timestamp (FPA-104)")

    def test_doble_corrida_cli_byte_a_byte(self):
        """FPA-104: doble corrida real del CLI → byte-a-byte idéntico salvo
        el timestamp (que viene del reloj)."""
        out_a = "/tmp/fpa_f7_run_a.html"
        out_b = "/tmp/fpa_f7_run_b.html"
        with redirect_stderr(io.StringIO()):
            rc_a = viz.main(["--out", out_a])
            rc_b = viz.main(["--out", out_b])
        self.assertEqual(0, rc_a)
        self.assertEqual(0, rc_b)
        raw_a = Path(out_a).read_text()
        raw_b = Path(out_b).read_text()
        ts_a = GEN_RE.search(raw_a)
        ts_b = GEN_RE.search(raw_b)
        self.assertIsNotNone(ts_a, "doble corrida: sin timestamp en output A")
        self.assertIsNotNone(ts_b, "doble corrida: sin timestamp en output B")
        masked_a = raw_a.replace(ts_a.group(0), "Generado: T")
        masked_b = raw_b.replace(ts_b.group(0), "Generado: T")
        self.assertEqual(masked_a, masked_b,
                         "doble corrida difiere fuera del timestamp (FPA-104)")

    def test_timestamp_aparece_una_sola_vez(self):
        """FPA-104: hay exactamente una marca 'Generado:' por documento."""
        html = _rendered()
        self.assertEqual(1, len(GEN_RE.findall(html)))


class TestDocs(unittest.TestCase):
    """FPA-145/143/146/144: documentación y checks finales sobre el HTML real."""

    def test_metodo_render_documentado_en_html(self):
        """FPA-145: el HTML documenta el método de render real (SVG inline,
        stdlib-only, sin librería de charts externa)."""
        html = _rendered()
        self.assertIn("Método de render", html)
        self.assertIn("SVG inline", html)
        self.assertIn("stdlib-only", html)

    def test_metodo_render_documentado_en_readme(self):
        """FPA-145: el README describe viz-fpa.py con su método real y no
        menciona Chart.js para el dashboard FP&A."""
        readme = README.read_text()
        self.assertIn("viz-fpa.py", readme)
        self.assertIn("SVG inline", readme)
        # Chart.js solo puede aparecer tachado (decisión histórica descartada);
        # se eliminan los spans ~~...~~ y ninguna mención activa queda.
        sin_tachado = re.sub(r"~~.+?~~", "", readme, flags=re.S)
        self.assertNotIn("Chart.js", sin_tachado,
                         "README aún propone Chart.js activamente")

    def test_readme_consistente_con_json(self):
        """FPA-143 (integración real): check_docs contra el README del repo
        no reporta desvíos."""
        self.assertEqual([], viz.check_docs(REPORT, README))

    def test_check_docs_cli_exit_0(self):
        """FPA-143/107: --check-docs sobre el repo real termina 0."""
        with redirect_stderr(io.StringIO()):
            rc = viz.main(["--check-docs"])
        self.assertEqual(0, rc)

    def test_sin_placeholders_vacios_html_final(self):
        """FPA-146/108: el HTML final del repo no tiene placeholders vacíos
        ni headlines sin valor."""
        html = _rendered()
        self.assertEqual([], viz.check_placeholders(html))

    def test_numeracion_figuras_sin_duplicados_html_real(self):
        """FPA-144/106: numeración secuencial y sin duplicados sobre el HTML
        completo del reporte real."""
        html = _rendered()
        figs = [int(n) for n in re.findall(r"Figura (\d+)", html)]
        tabs = [int(n) for n in re.findall(r"Tabla (\d+)", html)]
        for seq, nombre in ((figs, "Figura"), (tabs, "Tabla")):
            self.assertEqual(sorted(set(seq)), seq,
                             f"{nombre}: numeración no secuencial/sin huecos")
        self.assertTrue(figs, "sin figuras numeradas")


if __name__ == "__main__":
    unittest.main()
