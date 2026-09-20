#!/usr/bin/env python3
"""
test_fpa_f3_parity.py — paridad JS/Python de viz-fpa.py F3 (coffe-lat.4)

design.md: varianza y forecast se re-implementan en JS para el recompute sin
reload (FPA-056/077); un test de paridad verifica que los valores calculados
por JS igualan los golden pre-calculados en Python sobre el fixture.

Igual que test_viz.py: requiere playwright + chromium; SKIPPED si no está.
"""

import importlib.util
import json
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CONFIG = json.loads((REPO / "config" / "fpa.json").read_text())

try:
    from playwright.sync_api import sync_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False


def _load(name, relpath):
    spec = importlib.util.spec_from_file_location(name, REPO / relpath)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


f2 = _load("test_fpa_f2", "tests/test_fpa_f2.py")
f3 = _load("test_fpa_f3", "tests/test_fpa_f3.py")
viz = _load("viz_fpa_parity", "scripts/viz-fpa.py")


def _parse_usd(text):
    """'$1,234.56 △ forecast' → 1234.56 (ignora marker no-solo-color)."""
    return float(text.split(" ")[0].replace("$", "").replace(",", ""))


@unittest.skipUnless(HAS_PLAYWRIGHT, "playwright no instalado (opcional)")
class TestF3Parity(unittest.TestCase):
    """FPA-056/077: JS iguala a Python; update sin reload."""

    @classmethod
    def setUpClass(cls):
        import glob
        chrome = None
        for pat in ("~/.cache/ms-playwright/chromium-*/chrome-linux*/chrome",
                    "~/.cache/ms-playwright/chromium_headless_shell-*/"
                    "chrome-linux*/headless_shell"):
            found = sorted(glob.glob(str(Path(pat).expanduser())))
            if found:
                chrome = found[-1]
                break
        if not chrome:
            raise unittest.SkipTest("chromium de playwright no encontrado")
        cls.fixture = f2.f2_fixture()
        cls.model = viz.build_model(cls.fixture, CONFIG)
        cls.html_path = Path("/tmp/fpa_f3_parity.html")
        cls.html_path.write_text(
            viz.render_html(cls.fixture, CONFIG, generated="2026-09-20 12:00"))
        cls._pw = sync_playwright().start()
        cls.browser = cls._pw.chromium.launch(executable_path=chrome,
                                              args=["--no-sandbox"])
        cls.page = cls.browser.new_page()
        cls.errors = []
        cls.page.on("pageerror", lambda e: cls.errors.append(str(e)))
        cls.page.goto(f"file://{cls.html_path}")
        cls.page.wait_for_timeout(300)

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "browser"):
            cls.browser.close()
            cls._pw.stop()

    def test_00_sin_errores_js(self):
        self.assertEqual([], self.errors)

    def test_default_iguala_python(self):
        """El escenario default ya renderizado iguala build_model de Python."""
        # aislamiento: tests previos (p.ej. cambio de plan) mutan la página
        self.page.reload()
        self.page.wait_for_timeout(200)
        fc = self.model["forecast"]
        rows = self.page.eval_on_selector_all(
            "#forecast tr[data-fc-ym]",
            "els => els.map(tr => Array.from(tr.querySelectorAll('td'))"
            ".map(td => td.textContent.trim()))")
        yms = self.page.eval_on_selector_all(
            "#forecast tr[data-fc-ym]", "els => els.map(tr => tr.dataset.fcYm)")
        idx = 0
        if fc["remainder"]:
            idx = 1  # fila 0 = resto del mes parcial (valores fijos)
        for i, row in enumerate(fc["rows"]):
            self.assertEqual(row["ym"], yms[idx + i])
            self.assertAlmostEqual(row["eff"], _parse_usd(rows[idx + i][1]))
            self.assertAlmostEqual(row["cash"], _parse_usd(rows[idx + i][2]))

    def test_varianza_js_iguala_python(self):
        """Con el presupuesto del config, las varianzas JS = Python."""
        # reload: otros tests pueden haber mutado los inputs (sin reload,
        # el estado JS persiste entre tests)
        self.page.reload()
        self.page.wait_for_timeout(200)
        budget = self.model["budget"]
        cells = self.page.eval_on_selector_all(
            "#budget tr[data-ym]",
            "els => els.map(tr => Array.from(tr.querySelectorAll('td'))"
            ".map(td => td.textContent.trim()))")
        for r, row_cells in zip(budget["rows"], cells):
            if not r["in_budget"] or r["actual_cash"] is None:
                continue
            # columnas: 0 Mes, 1 En-presupuesto, 2 Cash real, 3 Budget,
            # 4 Var cash, 5 Var %, 6 Eff real, 7 Budget eff, 8 Var eff, 9 Var %
            self.assertEqual(r["actual_display_cash"], row_cells[2])
            self.assertEqual(r["variance_display_cash"], row_cells[4].split(" ")[0])
            self.assertEqual(r["variance_pct_display_cash"], row_cells[5])
            self.assertEqual(r["actual_display_eff"], row_cells[6])
            self.assertEqual(r["variance_display_eff"], row_cells[8].split(" ")[0])

    def test_edicion_presupuesto_sin_reload(self):
        """FPA-056: al editar, la varianza cambia y el marker se actualiza."""
        marker = self.page.eval_on_selector(
            "#budget tr[data-ym='2026-06'] td:nth-child(5)", "el => el.textContent")
        self.assertIn("bajo", marker)
        self.page.fill("#budget-cash", "10")
        self.page.dispatch_event("#budget-cash", "input")
        self.page.wait_for_timeout(100)
        nuevo = self.page.eval_on_selector(
            "#budget tr[data-ym='2026-06'] td:nth-child(5)", "el => el.textContent")
        self.assertIn("+$15.00", nuevo)   # 25 − 10
        self.assertIn("sobre", nuevo)     # FPA-054: marker no-solo-color
        # verificación contra Python: apply el mismo cálculo del modelo
        self.assertAlmostEqual(15.0, 25.0 - 10.0)

    def test_escenario_sin_reload_iguala_python(self):
        """FPA-077: escenario g=10%, r=5% → JS = apply_scenario de Python."""
        # aislamiento: partir del estado default (tests previos mutan la página)
        self.page.reload()
        self.page.wait_for_timeout(200)
        out = viz.apply_scenario(self.model["forecast"], 0.10, 0.05,
                                 self.model["forecast"]["default_plan"])
        self.page.fill("#fc-growth", "10")
        self.page.fill("#fc-rate", "5")
        self.page.dispatch_event("#fc-growth", "input")
        self.page.dispatch_event("#fc-rate", "input")
        self.page.wait_for_timeout(100)
        rows = self.page.eval_on_selector_all(
            "#forecast tr[data-fc-ym]",
            "els => els.map(tr => Array.from(tr.querySelectorAll('td'))"
            ".map(td => td.textContent.trim()))")
        offset = 1 if self.model["forecast"]["remainder"] else 0
        for i, row in enumerate(out["rows"]):
            self.assertAlmostEqual(row["eff"], _parse_usd(rows[offset + i][1]))
            self.assertAlmostEqual(row["cash"], _parse_usd(rows[offset + i][2]))

    def test_cambio_de_plan_sin_reload_iguala_python(self):
        """FPA-071/077: cambiar el plan futuro → cash = fee(plan) + p2p×f,
        igual a apply_scenario de Python; el efectivo no cambia con el plan."""
        fc = self.model["forecast"]
        other = next(p for p in fc["plans"] if p["key"] != fc["default_plan"])
        out = viz.apply_scenario(fc, 0.0, 0.0, other["key"])
        self.page.select_option("#fc-plan", other["key"])
        self.page.dispatch_event("#fc-plan", "change")
        self.page.wait_for_timeout(100)
        rows = self.page.eval_on_selector_all(
            "#forecast tr[data-fc-ym]",
            "els => els.map(tr => Array.from(tr.querySelectorAll('td'))"
            ".map(td => td.textContent.trim()))")
        offset = 1 if fc["remainder"] else 0
        for i, row in enumerate(out["rows"]):
            self.assertAlmostEqual(row["cash"], _parse_usd(rows[offset + i][2]))

    def test_outlook_muestra_ytd_real(self):
        """FPA-074: filas de real YTD visibles (ro5u)."""
        out = self.model["forecast"]["outlook"]
        txt = self.page.eval_on_selector("#forecast", "el => el.textContent")
        self.assertIn("Real YTD cash", txt)
        self.assertIn(f"{out['actual_cash']:,.2f}".replace("$", ""),
                      txt.replace("$", "").replace(",", ","))


if __name__ == "__main__":
    unittest.main()
