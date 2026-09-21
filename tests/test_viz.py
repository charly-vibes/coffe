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

import html as html_mod
import importlib.util
import json
import re
import sys
import unittest
from html.parser import HTMLParser
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

    def _tops(self, pg, sel):
        """Filas visuales: número de top-positions distintas de los hijos."""
        return pg.evaluate(
            f"[...document.querySelectorAll('{sel} > *')]"
            ".map(e => Math.round(e.getBoundingClientRect().top))")

    def test_fpa_summary_cards_grid(self):
        """coffe-efw F2: a 1280px los KPI cards renderizan en >=3 columnas
        y la grilla de Summary no contiene items no-card (marginalia,
        headings y CTAs quedan fuera de .cards-grid)."""
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
            tops = self._tops(pg, "#kpi-cards")
            self.assertGreaterEqual(len(tops), 3,
                "fpa: #kpi-cards sin al menos 3 cards")
            max_row = max(tops.count(t) for t in set(tops))
            self.assertGreaterEqual(max_row, 3,
                f"fpa 1280: KPI cards en {max_row} por fila, se esperaban >=3")
            # La grilla dedicada existe y TODO su contenido es card
            self.assertIsNotNone(
                pg.query_selector("#summary .cards-grid"),
                "fpa: Summary sin .cards-grid dedicada")
            non_card = pg.evaluate(
                "[...document.querySelectorAll('#summary .cards-grid > *')]"
                ".filter(e => !e.classList.contains('headline')).length")
            self.assertEqual(non_card, 0,
                "fpa: .cards-grid contiene items no-card")
            # Marginalia, headings y CTAs fuera de la grilla
            outside = pg.evaluate(
                """() => {
                  const g = document.querySelector('#summary .cards-grid');
                  const out = (sel) => !g.contains(document.querySelector(sel));
                  return {m: out('#m-summary'), h: out('#summary h2'),
                          c: out('#view-ctas')};
                }""")
            self.assertEqual(outside, {"m": True, "h": True, "c": True},
                f"fpa: marginalia/headings/CTAs dentro de la grilla: {outside}")
            browser.close()

    def test_fpa_ctas_compact_row(self):
        """coffe-efw F2: los CTAs miden <=64px de alto y quedan en una sola
        linea a >=600px de viewport."""
        page_path = REPO / "data" / "fpa-dashboard.html"
        if not page_path.exists():
            self.skipTest("fpa-dashboard.html no generado")
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=self.chrome,
                                        args=["--no-sandbox"])
            for width in (1280, 600):
                pg = browser.new_page()
                pg.set_viewport_size({"width": width, "height": 900})
                pg.goto(f"file://{page_path}")
                pg.wait_for_timeout(300)
                h = pg.evaluate(
                    "Math.round(document.querySelector('#view-ctas')"
                    ".getBoundingClientRect().height)")
                self.assertLessEqual(h, 64,
                    f"fpa {width}px: fila de CTAs mide {h}px (> 64)")
                tops = self._tops(pg, "#view-ctas")
                self.assertLessEqual(len(set(tops)), 1,
                    f"fpa {width}px: CTAs en {len(set(tops))} lineas")
                pg.close()
            browser.close()

    def test_fpa_marginalia_single_strip(self):
        """coffe-efw F2: cada vista tiene un unico strip de marginalia."""
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
            counts = pg.evaluate(
                "Object.fromEntries(%s.map(v => [v, document.querySelectorAll('#' + v + ' .marginalia').length]))"
                % repr(list(self.VIEWS)))
            for v, n in counts.items():
                self.assertLessEqual(n, 1,
                    f"fpa: vista {v} con {n} strips de marginalia")
            self.assertEqual(counts.get("summary"), 1,
                f"fpa: Summary sin strip de marginalia: {counts}")
            browser.close()

    def test_fpa_kpi_single_band(self):
        """coffe-esc F3: cada cifra KPI aparece en exactamente UN card del
        primer viewport de Summary. Los headline cards desaparecieron: la
        banda KPI ES el resumen ejecutivo. Los claims quedan fuera del
        check (sus cifras pueden coincidir legitimamente con un KPI)."""
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
            # Todo card de Summary vive en la banda KPI (sin headline cards)
            cards = pg.eval_on_selector_all(
                "#summary .headline", "els => els.map(e => e.textContent)")
            kpi_cards = pg.eval_on_selector_all(
                "#kpi-cards .headline", "els => els.map(e => e.textContent)")
            self.assertEqual(cards, kpi_cards,
                "fpa: Summary tiene cards fuera de la banda KPI "
                "(headline cards residuales)")
            vals = pg.eval_on_selector_all(
                "#kpi-cards .val",
                "els => els.map(e => e.textContent.trim()).filter(t => t)")
            self.assertGreaterEqual(len(vals), 3,
                f"fpa: banda KPI con {len(vals)} cifras, se esperaban >= 3")
            for v in set(vals):
                hits = sum(1 for c in kpi_cards if v in c)
                self.assertEqual(hits, 1,
                    f"fpa: cifra {v!r} aparece en {hits} cards, se esperaba 1")
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


class _VisibleText(HTMLParser):
    """Recolecta el texto visible: ignora atributos (los ids viajan a
    title), <title>, <script>/<style> (CDATA) y los chips de marginalia
    (que sí llevan ids por diseño — coffe-6lz anti-goal)."""

    SKIP_TAGS = {"title", "script", "style"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.stack = []  # (tag, skip_subtree: bool)

    def handle_starttag(self, tag, attrs):
        marg = "marginalia" in dict(attrs).get("class", "").split()
        skip = tag in self.SKIP_TAGS or marg or any(s for _, s in self.stack)
        self.stack.append((tag, skip))

    def handle_startendtag(self, tag, attrs):
        pass

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                return

    def handle_data(self, data):
        if any(s for _, s in self.stack):
            return
        self.parts.append(data)


class TestFpaIdHierarchy(unittest.TestCase):
    """coffe-6lz F4: jerarquía tipográfica — los ids FPA-xxx dejan de
    competir con las cifras primarias: cero matches en el texto visible;
    siguen machine-readable en atributos title."""

    PAGE = REPO / "data" / "fpa-dashboard.html"

    def setUp(self):
        if not self.PAGE.exists():
            self.skipTest("fpa-dashboard.html no generado")
        self.html = self.PAGE.read_text()

    def test_fpa_ids_out_of_visible_body(self):
        p = _VisibleText()
        p.feed(self.html)
        visible = " ".join(p.parts)
        refs = re.findall(r"FPA-\d{3}", visible)
        self.assertEqual(
            refs, [],
            f"FPA-ids en texto visible del cuerpo ({len(refs)}): "
            + ", ".join(sorted(set(refs))[:8]))

    def test_fpa_ids_still_machine_readable(self):
        """Anti-goal: no borrar ids — deben quedar en title/footnotes."""
        titles = " ".join(re.findall(r'title="([^"]*)"', self.html))
        ids = re.findall(r"FPA-\d{3}", html_mod.unescape(titles))
        self.assertGreaterEqual(
            len(ids), 10,
            f"solo {len(ids)} ids FPA en titles; el movimiento los perdió")


class _DisclosureMap(HTMLParser):
    """Recolecta los <details data-tree> de sección y su estado open por
    defecto (coffe-x6l F5). Ignora <script>/<style> (el JS de viz-fpa.py
    re-crea trees en re-render) y los details anidados de filas (tlabel,
    sin data-tree por diseño)."""

    SKIP_TAGS = {"script", "style"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.details = {}  # data-tree -> bool open
        self.stack = []

    def handle_starttag(self, tag, attrs):
        skip = tag in self.SKIP_TAGS or any(s for _, s in self.stack)
        self.stack.append((tag, skip))
        if tag == "details" and not skip:
            d = dict(attrs)
            if "data-tree" in d:
                self.details[d["data-tree"]] = "open" in d

    def handle_startendtag(self, tag, attrs):
        pass

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                return


class TestFpaDisclosure(unittest.TestCase):
    """coffe-x6l F5 (D5): disclosure por defecto y summaries estilizados.

    - Solo la sección primaria por vista abre expandida (Cost→Presupuesto,
      Breakdown→Árbol Portfolio, Habits→Heatmap, Outlook→Forecast,
      Data→Data y método); el resto colapsado.
    - Sin marcador huérfano: ningún nodo de texto de disclosure (▼/▸/▾)
      fuera de un <summary> — el marcador vive en el ::before del CSS.
    - Summaries colapsados con target táctil >=44px (group-box 90s).
    """

    PAGE = REPO / "data" / "fpa-dashboard.html"

    # Sección primaria por vista → abierta por defecto
    OPEN = {"budget", "portfolio", "heatmap", "forecast", "data-method"}
    # Resto de secciones disclosure → colapsadas por defecto
    CLOSED = {"bridge", "alerts", "plan-economy", "reconciliation",
              "time", "tool", "pareto", "weekly", "skills-commands",
              "sessions", "concurrency", "lifecycle", "timeline"}

    def setUp(self):
        if not self.PAGE.exists():
            self.skipTest("fpa-dashboard.html no generado")
        self.html = self.PAGE.read_text()

    def test_fpa_disclosure_defaults_por_vista(self):
        p = _DisclosureMap()
        p.feed(self.html)
        for name in self.OPEN:
            self.assertIn(name, p.details, f"{name}: sección sin data-tree")
            self.assertTrue(p.details[name], f"{name}: primaria, debe abrir")
        for name in self.CLOSED:
            if name in p.details:  # secciones condicionales (n/a no emiten)
                self.assertFalse(p.details[name],
                                 f"{name}: no-primaria, debe colapsar")
        desconocidas = set(p.details) - self.OPEN - self.CLOSED
        self.assertEqual(desconocidas, set(),
                         f"details[data-tree] sin política declarada: "
                         f"{sorted(desconocidas)}")

    def test_fpa_no_orphan_disclosure_marker(self):
        """Ningún nodo de texto de disclosure fuera de un <summary>: el
        marcador ▸/▾ va integrado al summary vía ::before del CSS; los
        markers de varianza (▼) viajan con su texto, nunca solos."""

        class _Orphans(_VisibleText):
            SUMMARY_TAGS = {"summary"}

            def __init__(self):
                super().__init__()
                self.in_summary = 0
                self.orphans = []

            def handle_starttag(self, tag, attrs):
                if tag in self.SUMMARY_TAGS and not any(
                        s for _, s in self.stack):
                    self.in_summary += 1
                super().handle_starttag(tag, attrs)

            def handle_endtag(self, tag):
                if tag in self.SUMMARY_TAGS and self.in_summary:
                    self.in_summary -= 1
                super().handle_endtag(tag)

            def handle_data(self, data):
                super().handle_data(data)
                if not self.in_summary and data.strip() in {"▼", "▸", "▾"}:
                    self.orphans.append(data.strip())

        p = _Orphans()
        p.feed(self.html)
        self.assertEqual(p.orphans, [],
                         "marcadores de disclosure huérfanos (fuera de "
                         f"summary): {p.orphans[:8]}")
        # y el marcador integrado existe en el CSS del summary
        self.assertIn("summary::before", self.html,
                      "summary sin marcador integrado (::before)")

    def test_fpa_summaries_target_44px(self):
        """Summaries (abiertos y colapsados) con target táctil >=44px:
        group-box 90s con min-height en el summary mismo."""
        if not HAS_PLAYWRIGHT:
            self.skipTest("playwright no instalado (opcional)")
        chrome = find_chromium()
        if not chrome:
            self.skipTest("chromium de playwright no encontrado")
        with sync_playwright() as pw:
            browser = pw.chromium.launch(executable_path=chrome,
                                         args=["--no-sandbox"])
            pg = browser.new_page()
            pg.set_viewport_size({"width": 1280, "height": 900})
            pg.goto(f"file://{self.PAGE}")
            pg.wait_for_timeout(300)
            n_collapsed = 0
            for view in ("cost", "breakdown", "habits", "outlook", "data"):
                pg.click(f"a.tab[data-view='{view}']")
                pg.wait_for_timeout(150)
                heights = pg.evaluate(
                    "Array.from(document.querySelectorAll("
                    f"'#{view} details.tree > summary')).map(s => "
                    "s.getBoundingClientRect().height)")
                self.assertTrue(heights,
                                f"{view}: sin summaries de secciones tree")
                for h in heights:
                    self.assertGreaterEqual(h, 44,
                        f"{view}: summary con {h}px (< 44px)")
                n_collapsed += pg.evaluate(
                    f"document.querySelectorAll(" 
                    f"'#{view} details.tree:not([open]) > summary').length")
            browser.close()
        self.assertGreaterEqual(
            n_collapsed, 5,
            f"solo {n_collapsed} summaries colapsados; "
            "los defaults no-primarios debían colapsar")


def _money(s):
    """'+$1,110.03' / '-$455.17' -> float."""
    return float(s.replace("$", "").replace(",", ""))


class TestFpaBridgeSelector(unittest.TestCase):
    """coffe-8nw F6/D6: bridge con selector de mes — un único waterfall
    visible, montado desde <template data-bridge-month> sin recarga;
    identidad Volume+Mix+Rate por mes; sin ningún mes con mix → n/a con
    razón y sin selector vacío."""

    PAGE = REPO / "data" / "fpa-dashboard.html"
    CONFIG = json.loads((REPO / "config" / "fpa.json").read_text())

    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location(
            "viz_fpa_bridge", REPO / "scripts" / "viz-fpa.py")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        cls.viz = mod

    def setUp(self):
        if not self.PAGE.exists():
            self.skipTest("fpa-dashboard.html no generado")

    def _open_bridge(self, pg):
        pg.click("a.tab[data-view='cost']")
        pg.click("#bridge > summary")
        pg.wait_for_timeout(100)

    def test_fpa_bridge_un_waterfall_visible(self):
        """Exactamente un waterfall visible a la vez; cambiar de mes
        re-renderiza sin recarga; los meses sin mix quedan fuera del
        selector (cada template tiene su opción y viceversa)."""
        if not HAS_PLAYWRIGHT:
            self.skipTest("playwright no instalado (opcional)")
        chrome = find_chromium()
        if not chrome:
            self.skipTest("chromium de playwright no encontrado")
        with sync_playwright() as pw:
            browser = pw.chromium.launch(executable_path=chrome,
                                         args=["--no-sandbox"])
            pg = browser.new_page()
            pg.set_viewport_size({"width": 1280, "height": 900})
            pg.goto(f"file://{self.PAGE}")
            pg.wait_for_timeout(300)
            self._open_bridge(pg)
            svgs = "document.querySelectorAll('#bridge svg.wf.chart')"
            self.assertEqual(1, pg.evaluate(f"{svgs}.length"),
                "fpa bridge: debe haber exactamente un waterfall en el DOM")
            visibles = pg.evaluate(
                f"[...{svgs}].filter(e => e.getClientRects().length > 0).length")
            self.assertEqual(1, visibles,
                "fpa bridge: el waterfall montado no es visible")
            opts = pg.eval_on_selector_all(
                "#bridge-month option", "els => els.map(e => e.value)")
            tms = pg.evaluate(
                "[...document.querySelectorAll(" 
                "'template[data-bridge-month]')].map(t => "
                "t.getAttribute('data-bridge-month'))")
            self.assertGreaterEqual(len(opts), 1,
                "fpa bridge: selector vacío (debería ser n/a sin selector)")
            self.assertEqual(sorted(opts), sorted(tms),
                "fpa bridge: templates y opciones del selector no casan 1:1")
            # cambiar mes re-renderiza sin recarga (sigue habiendo 1 solo)
            label0 = pg.get_attribute("#bridge svg.wf.chart", "aria-label")
            otro = next(o for o in opts if o != pg.input_value("#bridge-month"))
            pg.select_option("#bridge-month", otro)
            pg.wait_for_timeout(100)
            self.assertEqual(1, pg.evaluate(f"{svgs}.length"),
                "fpa bridge: cambiar de mes dejó más de un waterfall")
            label1 = pg.get_attribute("#bridge svg.wf.chart", "aria-label")
            self.assertNotEqual(label0, label1,
                "fpa bridge: el waterfall no cambió de mes al seleccionar")
            browser.close()

    def test_fpa_bridge_identidad_por_mes(self):
        """Identidad Volume+Mix+Rate = Δ (cost₁ − cost₀) dentro de $0.01
        para cada mes del selector (golden existente, FPA-065)."""
        if not HAS_PLAYWRIGHT:
            self.skipTest("playwright no instalado (opcional)")
        chrome = find_chromium()
        if not chrome:
            self.skipTest("chromium de playwright no encontrado")
        with sync_playwright() as pw:
            browser = pw.chromium.launch(executable_path=chrome,
                                         args=["--no-sandbox"])
            pg = browser.new_page()
            pg.set_viewport_size({"width": 1280, "height": 900})
            pg.goto(f"file://{self.PAGE}")
            pg.wait_for_timeout(300)
            self._open_bridge(pg)
            opts = pg.eval_on_selector_all(
                "#bridge-month option", "els => els.map(e => e.value)")
            self.assertGreaterEqual(len(opts), 1,
                "fpa bridge: sin selector de mes, no hay identidad que verificar")
            for opt in opts:
                pg.select_option("#bridge-month", opt)
                pg.wait_for_timeout(50)
                vals = pg.evaluate(
                    "() => { const out = {}; document.querySelector("
                    "'#bridge svg.wf.chart').querySelectorAll("
                    "'rect[data-label]').forEach(r => "
                    "out[r.getAttribute('data-label')] = "
                    "r.getAttribute('data-value')); return out; }")
                total = (_money(vals["cost₀"])
                         + _money(vals["Volumen"]) + _money(vals["Mix"])
                         + _money(vals["Rate"]))
                # Los componentes display están redondeados a 2dp por su
                # cuenta: la identidad FPA-065 se verifica exacta (sin
                # redondeo) en el generador — acá tolera 0.02 (4 redondeos).
                self.assertLessEqual(abs(total - _money(vals["cost₁"])), 0.02,
                    f"fpa bridge {opt}: identidad PVM rota ({vals})")
            browser.close()

    def test_fpa_bridge_na_sin_meses_con_mix(self):
        """Con ningún mes con datos de mix, la sección muestra n/a con la
        razón — sin selector vacío ni templates (FPA-008)."""
        spec = importlib.util.spec_from_file_location(
            "test_fpa_f2_bridge", REPO / "tests" / "test_fpa_f2.py")
        f2 = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(f2)
        fx = f2.f2_fixture()
        # el caso real del reporte: modelos con coste $0 en todos los meses
        for mo in fx["monthly"].values():
            mo["models"] = {"amp": {"interactions": mo["interactions"],
                                    "cost_effective": 0.0}}
            mo["cost_effective"] = 0.0
        html = self.viz.render_html(fx, self.CONFIG, generated="T")
        i = html.index('data-tree="bridge"')
        section = html[i:html.index("</details>", i)]
        self.assertIn("n/a", section,
            "fpa bridge: sin meses con mix debe mostrar n/a con razón")
        self.assertIn("ningún mes con datos de mix", section)
        self.assertNotIn('id="bridge-month"', html,
            "fpa bridge: selector vacío emitido sin meses con mix")
        self.assertNotIn("<template data-bridge-month", html,
            "fpa bridge: templates emitidos sin meses con mix")


if __name__ == "__main__":
    unittest.main()
