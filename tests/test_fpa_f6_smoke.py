#!/usr/bin/env python3
"""
test_fpa_f6_smoke.py — smoke Playwright de viz-fpa.py F6 (coffe-lat.7)

Alcance: smoke 390×844 (FPA-109: título + period selector + primera headline
en el primer viewport, sin scroll horizontal ni errores de consola), tabs
mobile (FPA-152), Mostrar todo (FPA-155), share view con restauración y
parámetros inválidos ignorados (FPA-149/170/171), Export CSV / Download SVG
(FPA-169) y readout persistente (FPA-175).

Igual que test_viz.py / test_fpa_f3_parity.py: requiere playwright +
chromium; SKIPPED si no está.
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
f6 = _load("test_fpa_f6", "tests/test_fpa_f6.py")
viz = _load("viz_fpa_f6_smoke", "scripts/viz-fpa.py")


def _chrome():
    import glob
    for pat in ("~/.cache/ms-playwright/chromium-*/chrome-linux*/chrome",
                "~/.cache/ms-playwright/chromium_headless_shell-*/"
                "chrome-linux*/headless_shell"):
        found = sorted(glob.glob(str(Path(pat).expanduser())))
        if found:
            return found[-1]
    raise unittest.SkipTest("chromium de playwright no encontrado")


@unittest.skipUnless(HAS_PLAYWRIGHT, "playwright no instalado (opcional)")
class TestF6Smoke(unittest.TestCase):
    """FPA-109/149: smoke mobile + share view."""

    @classmethod
    def setUpClass(cls):
        chrome = _chrome()
        cls.html_path = Path("/tmp/fpa_f6_smoke.html")
        cls.html_path.write_text(
            viz.render_html(f6.f6_fixture(), CONFIG, generated="T"))
        cls._pw = sync_playwright().start()
        cls.browser = cls._pw.chromium.launch(executable_path=chrome,
                                              args=["--no-sandbox"])
        cls.page = cls.browser.new_page(viewport={"width": 390, "height": 844})
        cls.errors = []
        cls.page.on("pageerror", lambda e: cls.errors.append(str(e)))
        cls.url = f"file://{cls.html_path}"
        cls.page.goto(cls.url)
        cls.page.wait_for_timeout(300)

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, "browser"):
            cls.browser.close()
            cls._pw.stop()

    def _sin_errores(self):
        self.assertEqual([], self.errors, "errores JS en la página")

    def _fresh(self):
        """Recargar: cada test UI arranca del default (los tests comparten
        página y el estado JS persiste)."""
        self.page.goto(self.url)
        self.page.wait_for_timeout(200)

    def test_00_smoke_390x844(self):
        """FPA-109: primer viewport con título, selector y primera headline;
        sin scroll horizontal."""
        p = self.page
        for sel in ("header.site h1", "#period-select", ".headline"):
            box = p.locator(sel).first.bounding_box()
            self.assertIsNotNone(box, sel)
            self.assertLessEqual(box["y"] + box["height"], 844,
                                 f"{sel} fuera del primer viewport")
        width = p.evaluate("document.documentElement.scrollWidth")
        self.assertLessEqual(width, 390, "scroll horizontal en 390px")
        self._sin_errores()

    def test_tabs_mobile(self):
        """FPA-152: una vista a la vez en <600px; el tab cambia la vista."""
        self._fresh()
        p = self.page
        p.click('.tab[data-view="habits"]')
        p.wait_for_timeout(100)
        self.assertEqual("habits", p.get_attribute("body", "data-view"))
        self.assertTrue(p.locator("#habits").is_visible())
        self.assertFalse(p.locator("#summary").is_visible())
        self.assertFalse(p.locator("#outlook").is_visible())
        # volver al default
        p.click('.tab[data-view="summary"]')
        p.wait_for_timeout(100)

    def test_mostrar_todo(self):
        """FPA-155: el botón revela las filas extra sin recargar.
        coffe-2ni: el pareto ya no abre por defecto (política de
        disclosure D5/F5.1 — solo la primaria de la vista) → el test lo
        abre explícito antes de operar."""
        self._fresh()
        p = self.page
        p.click('.tab[data-view="breakdown"]')  # pareto vive en Breakdown
        p.wait_for_timeout(100)
        p.click("#pareto > summary")  # abrir sección colapsada por defecto
        p.wait_for_timeout(100)
        n_hidden = p.evaluate(
            "document.querySelectorAll('#pareto tr.extra-row').length")
        self.assertGreater(n_hidden, 0)
        p.click("#pareto button.show-all")
        p.wait_for_timeout(100)
        self.assertEqual(
            0, p.evaluate(
                "Array.from(document.querySelectorAll('#pareto tr.extra-row'))"
                ".filter(r => r.hidden).length"))
        self.assertEqual(
            0, p.evaluate("document.querySelectorAll('#pareto .show-all').length"))

    def test_skills_commands_toggle(self):
        """FPA-156: el toggle muestra comandos y oculta skills.
        coffe-2ni: skills-commands ya no abre por defecto (política de
        disclosure D5/F5.1) → se abre el summary antes de operar."""
        self._fresh()
        p = self.page
        p.click('.tab[data-view="habits"]')  # skills-commands vive en Habits
        p.click("#skills-commands > summary")  # abrir sección colapsada
        p.wait_for_timeout(100)
        self.assertFalse(p.locator("#commands-panel").is_visible())
        p.click('.ptoggle[data-panel="commands-panel"]')
        p.wait_for_timeout(100)
        self.assertFalse(p.locator("#skills-panel").is_visible())
        self.assertTrue(p.locator("#commands-panel").is_visible())

    def test_share_view_restaura(self):
        """FPA-149/170: la URL con view/period/open restaura el estado."""
        self._fresh()
        p = self.page
        url = p.evaluate("window.__fpa.shareUrl()")
        p.goto(url)
        p.wait_for_timeout(200)
        self.assertEqual("summary", p.get_attribute("body", "data-view"))
        self.assertEqual("all",
                         p.input_value("#period-select"))
        # estado compartido real: vista habits + periodo + árbol abierto
        p.evaluate("window.__fpa.setView('habits')")
        p.select_option("#period-select", "month:2026-06")
        p.evaluate("document.querySelector('details[data-tree=\\'heatmap\\']')"
                   ".open = false")  # cerrar uno para ver la restauración
        shared = p.evaluate("window.__fpa.shareUrl()")
        p.goto(shared)
        p.wait_for_timeout(200)
        self.assertEqual("habits", p.get_attribute("body", "data-view"))
        self.assertEqual("month:2026-06", p.input_value("#period-select"))
        self.assertFalse(
            p.evaluate(
                "document.querySelector('details[data-tree=\\'heatmap\\']')"
                ".open"))
        self._sin_errores()

    def test_params_invalidos_ignorados(self):
        """FPA-171: parámetros inválidos → defaults, sin errores."""
        self._fresh()
        p = self.page
        p.goto(f"{self.url}?view=bogus&period=zzz&open=<script>")
        p.wait_for_timeout(200)
        self.assertEqual("summary", p.get_attribute("body", "data-view"))
        self.assertEqual("all", p.input_value("#period-select"))
        self._sin_errores()

    def test_export_csv_y_svg(self):
        """FPA-169: CSV de tabla (filas visibles) y XML del chart, sin deps."""
        self._fresh()
        p = self.page
        csv = p.evaluate(
            "window.__fpa.tableToCSV(document.querySelector('#pareto table'))")
        lines = csv.strip().split("\n")
        self.assertGreaterEqual(len(lines), 2)
        self.assertIn("Proyecto", lines[0])
        # filas ocultas (extra-row) no van al CSV
        self.assertNotIn("charly-proy-5", "\n".join(lines[1:]))
        xml = p.evaluate("window.__fpa.svgXml("
                         "document.querySelector('.wf.chart'))")
        self.assertTrue(xml.startswith("<?xml"))
        self.assertIn("<svg", xml)
        self._sin_errores()

    def test_readout_persistente(self):
        """FPA-175: focus en una barra del chart actualiza el readout.
        coffe-2ni: el bridge ya no abre por defecto (D5/F5.1) → se abre
        el summary antes de enfocar una barra del waterfall."""
        self._fresh()
        p = self.page
        p.click('.tab[data-view="cost"]')  # el waterfall vive en Costo
        p.click("#bridge > summary")  # abrir sección colapsada
        p.wait_for_timeout(100)
        p.focus(".wf.chart rect[data-label]")
        p.wait_for_timeout(100)
        text = p.text_content("#wf-readout")
        self.assertTrue(text and text.strip(), "readout vacío")
        self._fresh()


if __name__ == "__main__":
    unittest.main()
