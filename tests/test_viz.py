#!/usr/bin/env python3
"""
test_viz.py — smoke test de los HTML generados en un Chromium real.

Este test existe porque el smoke test con DOM stub dejó pasar 4 bugs de
runtime JS a producción (createElementNS sin namespace, fmtK indefinido,
TDZ, id equivocado). Solo un navegador real ejecuta el JS de verdad.

Requiere playwright + chromium (opcional en CI):
    uv tool install playwright  # o pip install playwright
    python3 -m playwright install chromium

Uso: python3 tests/test_viz.py
Salta con SKIPPED si playwright no está instalado.
"""

import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PAGES = [
    REPO / "data" / "gantt-multitasking.html",
    REPO / "data" / "fpa-dashboard.html",
]

try:
    from playwright.sync_api import sync_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False


def find_chromium():
    """Busca un chromium instalado por playwright (varias versiones)."""
    import glob
    for pat in ("~/.cache/ms-playwright/chromium-*/chrome-linux*/chrome",
                "~/.cache/ms-playwright/chromium_headless_shell-*/chrome-linux*/headless_shell"):
        found = sorted(glob.glob(str(Path(pat).expanduser())))
        if found:
            return found[-1]
    return None


@unittest.skipUnless(HAS_PLAYWRIGHT, "playwright no instalado (opcional)")
class TestVizPages(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.chrome = find_chromium()
        if not cls.chrome:
            raise unittest.SkipTest("chromium de playwright no encontrado")

    VIEWS = ("summary", "cost", "breakdown", "habits", "outlook", "data")

    def _fpa_view_state(self, pg):
        """Mapa vista -> visible para las 6 secciones .fpa-view."""
        return {v: pg.is_visible(f"#{v}") for v in self.VIEWS}

    def test_fpa_desktop_one_view_at_a_time(self):
        """coffe-dqz F1: a 1280x900 el tab 'Hábitos' deja solo esa vista
        visible y la página mide < 2 viewports (toggle a todo ancho)."""
        page_path = REPO / "data" / "fpa-dashboard.html"
        if not page_path.exists():
            self.skipTest("fpa-dashboard.html no generado")
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=self.chrome,
                                        args=["--no-sandbox"])
            pg = browser.new_page()
            pg.set_viewport_size({"width": 1280, "height": 900})
            pg.goto(f"file://{page_path}")
            pg.wait_for_timeout(300)
            pg.click("a.tab[data-view='habits']")
            pg.wait_for_timeout(200)
            state = self._fpa_view_state(pg)
            self.assertEqual(state,
                dict.fromkeys(self.VIEWS, False) | {"habits": True},
                f"fpa 1280x900: tras click en Hábitos el estado es {state}")
            height = pg.evaluate("document.body.scrollHeight")
            self.assertLess(height, 2 * 900,
                f"fpa 1280x900: página mide {height}px (>= 2 viewports)")
            browser.close()

    def test_fpa_deeplink_view_param(self):
        """coffe-dqz F1: con ?view=habits la vista activa al cargar es
        Habits (contrato vigente de share-URL por query params)."""
        page_path = REPO / "data" / "fpa-dashboard.html"
        if not page_path.exists():
            self.skipTest("fpa-dashboard.html no generado")
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=self.chrome,
                                        args=["--no-sandbox"])
            pg = browser.new_page()
            pg.set_viewport_size({"width": 1280, "height": 900})
            pg.goto(f"file://{page_path}?view=habits")
            pg.wait_for_timeout(300)
            state = self._fpa_view_state(pg)
            self.assertEqual(state,
                dict.fromkeys(self.VIEWS, False) | {"habits": True},
                f"fpa ?view=habits: estado al cargar es {state}")
            self.assertEqual(
                pg.get_attribute("a.tab[data-view='habits']", "aria-current"),
                "true", "fpa ?view=habits: tab sin aria-current")
            browser.close()

    def test_fpa_mobile_toggle_regression(self):
        """coffe-dqz F1: el toggle a 390x844 (mobile) sigue funcionando."""
        page_path = REPO / "data" / "fpa-dashboard.html"
        if not page_path.exists():
            self.skipTest("fpa-dashboard.html no generado")
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=self.chrome,
                                        args=["--no-sandbox"])
            pg = browser.new_page()
            pg.set_viewport_size({"width": 390, "height": 844})
            pg.goto(f"file://{page_path}")
            pg.wait_for_timeout(300)
            pg.click("a.tab[data-view='cost']")
            pg.wait_for_timeout(200)
            state = self._fpa_view_state(pg)
            self.assertEqual(state,
                dict.fromkeys(self.VIEWS, False) | {"cost": True},
                f"fpa 390x844: tras click en Costo el estado es {state}")
            browser.close()

    def test_page_renders_without_errors(self):
        """Cada página: 0 pageerror, y produce su contenido esperado."""
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=self.chrome,
                                        args=["--no-sandbox"])
            for page_path in PAGES:
                if not page_path.exists():
                    continue  # viz no generada aún; no es fallo de este test
                pg = browser.new_page()
                errors = []
                pg.on("pageerror", lambda e: errors.append(str(e)))
                pg.goto(f"file://{page_path}")
                pg.wait_for_timeout(500)
                self.assertEqual(errors, [],
                                 f"{page_path.name}: errores de JS en runtime: {errors}")
                if page_path.name == "fpa-dashboard.html":
                    # FPA-108: resumen ejecutivo no vacío y sin placeholders sin valor
                    vals = pg.eval_on_selector_all(
                        ".headline .val",
                        "els => els.map(e => e.textContent.trim()).filter(t => t !== '')")
                    self.assertGreaterEqual(len(vals), 3,
                        f"fpa: {len(vals)} headlines con valor, se esperaban ≥ 3")
                    nas = pg.eval_on_selector_all(
                        ".headline .na",
                        "els => els.map(e => e.textContent.trim()).filter(t => t !== '')")
                    headlines = pg.eval_on_selector_all(
                        ".headline", "els => els.length")
                    self.assertEqual(len(vals) + len(nas), headlines,
                        "fpa: headline sin valor ni n/a con razón (FPA-108)")
                    n_ph = pg.eval_on_selector_all(
                        "[class~='ph']", "els => els.length")
                    self.assertEqual(0, n_ph, "fpa: placeholders sin valor")
                else:  # gantt
                    n = pg.eval_on_selector_all(".cell", "els => els.length")
                    self.assertGreater(n, 100, f"gantt: solo {n} celdas")
                    # sticky labels: pinned a CUALQUIER scrollLeft (viewport móvil,
                    # donde el bug era visible). Con containing block = fila flex
                    # completa el label queda en el borde izquierdo del scroller.
                    pg.set_viewport_size({"width": 375, "height": 800})
                    for sl in (600, 1500):
                        pg.evaluate(f"document.querySelector('.wrap').scrollLeft = {sl}")
                        pg.wait_for_timeout(100)
                        off = pg.evaluate("""() => {
                          const wrap = document.querySelector('.wrap');
                          const l = document.querySelectorAll('.row')[1].querySelector('.label');
                          return Math.round(l.getBoundingClientRect().left - wrap.getBoundingClientRect().left);
                        }""")
                        self.assertGreaterEqual(off, 0,
                            f"gantt: sticky label se despega a scrollLeft={sl} (offset {off})")
                pg.close()
            browser.close()


if __name__ == "__main__":
    unittest.main()
