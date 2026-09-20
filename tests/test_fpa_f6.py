#!/usr/bin/env python3
"""
test_fpa_f6.py — tests de viz-fpa.py F6 (ticket coffe-lat.7)

Alcance: arquitectura de información 5 vistas + Data & method (FPA-150/151),
presets de periodo YTD/Q/rango custom (FPA-090), selector único fijo
(FPA-153), top-5 + Mostrar todo (FPA-155), merges (FPA-156), sin duplicación
Pareto (FPA-158), títulos-hallazgo con fallback (FPA-160/161), idioma única
(FPA-162), CTAs con targets del config y fail si vacío (FPA-165…168, 172),
export CSV/SVG (FPA-169), share view (FPA-170/171, JS validado),
accesibilidad (FPA-175…179, 094), numeración de figuras (FPA-144/106) y
check-docs (FPA-143/107).
Smoke Playwright (FPA-109, share restaurado) en test_fpa_f6_smoke.py.
Golden: REGEN_GOLDEN=1 python3 tests/test_fpa_f6.py
"""

import importlib.util
import json
import os
import re
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
GOLDEN = Path(__file__).resolve().parent / "golden" / "fpa-f6-snapshot.json"
REGEN_GOLDEN = os.environ.get("REGEN_GOLDEN") == "1"


def _load(name, relpath):
    spec = importlib.util.spec_from_file_location(name, REPO / relpath)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


viz = _load("viz_fpa_f6", "scripts/viz-fpa.py")
f2 = _load("test_fpa_f2", "tests/test_fpa_f2.py")
fpa_config = _load("fpa_config_f6", "scripts/fpa_config.py")
CONFIG = json.loads((REPO / "config" / "fpa.json").read_text())


def f6_fixture():
    """Fixture F6: f2 + 7 skills y 7 proyectos (para probar top-5 + Mostrar
    todo, FPA-155)."""
    fx = f2.f2_fixture()
    fx["skills"] = {f"skill-{i}": 100 - i * 10 for i in range(7)}
    fx["projects"] = {
        f"charly-proy-{i}": {"cost_effective": 90.0 - i * 10,
                             "first_seen": "2026-05-01",
                             "last_seen": "2026-07-10"}
        for i in range(7)
    }
    return fx


class F6Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = f6_fixture()
        cls.model = viz.build_model(cls.fixture, CONFIG)
        cls.html = viz.render_html(cls.fixture, CONFIG, generated="T")

    def _section(self, sec_id):
        """Contenido <section id="...">…</section> del HTML."""
        m = re.search(rf'<section id="{sec_id}"[^>]*>(.*?)</section>',
                      self.html, re.S)
        self.assertIsNotNone(m, f"falta sección {sec_id}")
        return m.group(1)


# ======================================================================
# Arquitectura de información (FPA-150/151/152/157/158)
# ======================================================================

class TestInfoArchitecture(F6Base):

    def test_cinco_vistas_en_orden(self):
        """FPA-150: Summary, Cost, Breakdown, Habits, Outlook + Data & method,
        en ese orden."""
        ids = ["summary", "cost", "breakdown", "habits", "outlook"]
        pos = [self.html.index(f'<section id="{i}"') for i in ids]
        dm = self.html.index('id="data-method"')
        self.assertEqual(pos + [dm], sorted(pos + [dm]))

    def test_pregunta_encabezando_cada_vista(self):
        """FPA-151: cada vista abre con la pregunta que responde (es)."""
        preguntas = ["¿Cuál es el estado de las cosas?",
                     "¿Qué estoy gastando?",
                     "¿A dónde va el gasto?",
                     "¿Cómo trabajo?",
                     "¿Qué viene después?"]
        for p in preguntas:
            self.assertIn(p, self.html)

    def test_data_method_colapsado(self):
        """FPA-157: Data & method colapsado por default (sin `open`)."""
        m = re.search(r'<details[^>]*id="data-method"[^>]*>', self.html)
        self.assertIsNotNone(m)
        self.assertNotIn("open", m.group(0))

    def test_timeline_en_data_method(self):
        """FPA-157: el timeline de tools vive dentro de Data & method."""
        dm = self.html.index('id="data-method"')
        tl = self.html.index('id="timeline"')
        self.assertGreater(tl, dm)
        self.assertLess(tl, self.html.index("</main>"))

    def test_pareto_sin_duplicar_top_n(self):
        """FPA-158: solo una vista Pareto de proyectos; ningún chart top-N
        aparte que duplique árbol + Pareto."""
        self.assertEqual(1, self.html.count('id="pareto"'))
        self.assertEqual(1, self.html.count('data-tree="pareto"'))
        self.assertNotIn("Top proyectos", self.html)

    def test_tabs_y_secuencia(self):
        """FPA-152: tablist de vistas + CSS mobile una-vista-a-la-vez,
        desktop secuencia completa."""
        self.assertIn('role="tablist"', self.html)
        self.assertIn("body[data-view", self.html)
        self.assertIn("@media (max-width:599px)", self.html)


# ======================================================================
# Presets de periodo y selector único (FPA-090/153)
# ======================================================================

class TestPeriodo(F6Base):

    def test_presets_ytd_y_trimestres(self):
        """FPA-090: presets YTD y Q1–Q3 en el selector (los que tengan datos)."""
        for key in ("ytd:2026", "q:2026Q2", "q:2026Q3"):
            self.assertIn(f'<option value="{key}"', self.html)

    def test_rango_custom_precalculado(self):
        """FPA-090: rango custom contiguo disponible y con KPIs y árboles."""
        v = self.model["views"]["range:2026-05..2026-06"]
        self.assertEqual(["2026-05", "2026-06"], v["months"])
        self.assertTrue(v["kpis"])
        self.assertTrue(v["trees"]["time"]["children"])
        self.assertIn('value="range:2026-05..2026-06"', self.html)

    def test_rango_custom_prior_misma_longitud(self):
        """El delta del rango custom compara contra el rango inmediato
        anterior de la misma longitud."""
        wins = {k: (w, p) for k, _l, w, p in
                viz._windows(["2026-04", "2026-05", "2026-06", "2026-07"])}
        self.assertEqual(["2026-04", "2026-05"],
                         wins["range:2026-06..2026-07"][1])
        self.assertIsNone(wins["range:2026-05..2026-06"][1])

    def test_un_solo_selector_fijo_arriba(self):
        """FPA-153: un único period selector, fijo al inicio de la página
        (topbar), que aplica a todas las vistas."""
        self.assertEqual(1, self.html.count('id="period-select"'))
        topbar = self.html.index('class="topbar"')
        sel = self.html.index('id="period-select"')
        summary = self.html.index('<section id="summary"')
        self.assertLess(topbar, sel)
        self.assertLess(sel, summary)


# ======================================================================
# Top-5 + Mostrar todo (FPA-155)
# ======================================================================

class TestTop5(F6Base):

    def test_pareto_top5_mostrar_todo(self):
        """FPA-155: 7 proyectos → 5 visibles + filas ocultas + botón
        'Mostrar todo (2)'."""
        p = self._section("breakdown")
        self.assertIn("Mostrar todo (2)", p)
        self.assertIn('class="extra-row" hidden', p)

    def test_skills_top5(self):
        """FPA-155: skills con 7 filas → top-5 + Mostrar todo."""
        h = self._section("habits")
        self.assertIn("Mostrar todo (2)", h)

    def test_tabla_corta_sin_boton(self):
        """Tablas con ≤5 filas no llevan botón."""
        self.assertEqual(0, self._section("outlook").count("show-all"))

    def test_js_muestra_todo(self):
        """El botón revela las filas extra (JS)."""
        self.assertIn("extra-row", self.html.split("<script>")[-1])


# ======================================================================
# Merges (FPA-156)
# ======================================================================

class TestMerges(F6Base):

    def test_skills_y_comandos_una_vista_toggle(self):
        """FPA-156: skills y comandos en una sola vista con toggle."""
        m = re.search(r'<details[^>]*id="skills-commands".*?</details>',
                      self.html, re.S)
        self.assertIsNotNone(m)
        blob = m.group(0)
        self.assertEqual(2, blob.count('class="ptoggle'))
        self.assertIn('id="skills-panel"', blob)
        self.assertIn('id="commands-panel" hidden', blob)
        # ya no hay secciones separadas
        self.assertEqual(0, self.html.count('id="skills"'))
        self.assertEqual(0, self.html.count('id="commands"'))

    def test_sesiones_distribucion_y_largas_juntas(self):
        """FPA-156: buckets de longitud + sesiones más largas en una vista."""
        s = self._section("habits")
        i = s.index('id="sessions"')
        self.assertIn("Distribución de longitud", s[i:])
        self.assertIn("Sesiones más largas", s[i:])

    def test_coste_por_tool_sin_duplicar(self):
        """FPA-156: un solo visual de coste por tool (el árbol)."""
        main = self.html[self.html.index("<main"):self.html.index("</main>")]
        self.assertEqual(1, main.count("Árbol Tool"))


# ======================================================================
# Títulos-hallazgo (FPA-160/161)
# ======================================================================

class TestFindingTitles(F6Base):

    def test_finding_heatmap(self):
        """FPA-160: título del heatmap computado del after-hours share con
        threshold del config (FPA-009), con métrica nombrada visible."""
        h = self._section("habits")
        m = re.search(r'<h2 class="finding">([^<]+)</h2>'
                      r'(?:</summary>)?\s*'
                      r'<p class="small finding-meta">([^<]+)</p>', h)
        self.assertIsNotNone(m)
        self.assertIn("fuera del horario laboral", m.group(1))
        self.assertIn("after_hours_share", m.group(2))
        self.assertIn("threshold", m.group(2))

    def test_finding_pareto(self):
        """FPA-160: concentración top-3 como título-hallazgo con threshold."""
        b = self._section("breakdown")
        m = re.search(r'<h2 class="finding">([^<]+)</h2>'
                      r'(?:</summary>)?\s*'
                      r'<p class="small finding-meta">([^<]+)</p>', b)
        self.assertIsNotNone(m)
        self.assertIn("concentran", m.group(1))
        self.assertIn("top3_share", m.group(2))
        self.assertIn("50%", m.group(2))

    def test_fallback_sin_valor(self):
        """FPA-161: valor no disponible → fallback al label descriptivo."""
        out = viz.finding(None, "after_hours_share", "25% del uso",
                          "El {0} del uso ocurre fuera del horario laboral",
                          "After-hours y weekend", _fmt=lambda v: f"{v:.1%}")
        self.assertIn("After-hours y weekend", out)
        self.assertIn("n/a", out)
        self.assertNotIn("El", out.split("</h2>")[0])

    def test_finding_con_valor(self):
        out = viz.finding(0.389, "after_hours_share", "25% del uso",
                          "El {0} del uso ocurre fuera del horario laboral",
                          "After-hours y weekend", _fmt=lambda v: f"{v:.1%}")
        self.assertIn("38.9%", out)
        self.assertIn("after_hours_share", out)


# ======================================================================
# Idioma única (FPA-162)
# ======================================================================

class TestIdioma(F6Base):

    def test_lang_es(self):
        self.assertIn('<html lang="es">', self.html)

    def test_sin_texto_de_ui_en_ingles(self):
        """FPA-162: ninguna cadena de UI en inglés (mostrar todo, leer la
        serie, compartir vista, exportar)."""
        js = self.html.split("<script>")[-1]
        for en in ("Show all", "Read the series", "Share view",
                   "Export CSV", "Download SVG"):
            self.assertNotIn(f">{en}<", self.html)
            self.assertNotIn(f'"{en}"', js)


# ======================================================================
# CTAs (FPA-165…168, 172)
# ======================================================================

class TestCTAs(F6Base):

    def test_summary_1_primario_mas_secundarios(self):
        """FPA-165: al final del Summary, 1 primario ('Leer la serie') +
        hasta 3 secundarios."""
        s = self._section("summary")
        self.assertEqual(1, s.count("cta-primary"))
        self.assertIn("Leer la serie", s)
        secundarios = s.count('class="cta"')
        self.assertGreaterEqual(secundarios, 1)
        self.assertLessEqual(secundarios, 3)

    def test_max_un_primario_en_todo_el_dashboard(self):
        """FPA-166/149: ningún view tiene más de un primario (solo Summary
        tiene CTAs de vista)."""
        main = self.html[self.html.index("<main"):self.html.index("</main>")]
        self.assertEqual(1, main.count("cta-primary"))

    def test_labels_verb_first_4_palabras(self):
        """FPA-172: labels de CTA con ≤4 palabras."""
        ctas = CONFIG["ctas"]
        labels = [ctas["primary"]["label"]]
        labels += [c["label"] for c in ctas["secondary"]]
        labels += [a["label"] for a in ctas.get("alert_actions", {}).values()]
        for lb in labels:
            self.assertLessEqual(len(lb.split()), 4, lb)

    def test_alertas_con_una_accion(self):
        """FPA-167: cada alerta lleva exactamente un botón de acción con
        target del config."""
        alerts = self.html[self.html.index('id="alerts"'):
                           self.html.index('id="plan-economy"')]
        n_alerts = alerts.count('<li class="alert')
        self.assertGreaterEqual(n_alerts, 1)
        self.assertEqual(n_alerts, alerts.count("alert-action"))

    def test_build_alerts_adjunta_accion(self):
        fx = f2.f2_fixture()
        alerts = viz.build_alerts(fx, CONFIG, today="2026-09-20")
        for a in alerts:
            self.assertIn("action", a, a["rule"])
            self.assertTrue(a["action"]["target"], a["rule"])

    def test_fpa168_target_vacio_falla(self):
        """FPA-168: target vacío → validate_config lo lista y el generador
        termina non-zero nombrando el CTA."""
        bad = json.loads(json.dumps(CONFIG))
        bad["ctas"]["secondary"][0]["target"] = ""
        errors = fpa_config.validate_config(bad)
        self.assertTrue(any("target vacío" in e for e in errors))

        viz_fpa168_target_vacio_falla(self)

    def test_fpa168_alert_action_vacio_falla(self):
        bad = json.loads(json.dumps(CONFIG))
        bad["ctas"]["alert_actions"]["budget"]["target"] = ""
        errors = fpa_config.validate_config(bad)
        self.assertTrue(any("budget" in e for e in errors), errors)


def viz_fpa168_target_vacio_falla(tc):
    """main() con config inválida → exit 1 nombrando el CTA."""
    import contextlib, io
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        report = tmp / "report.json"
        report.write_text(json.dumps(f2.f2_fixture(), ensure_ascii=False))
        bad_cfg = tmp / "bad.json"
        cfg = json.loads(json.dumps(CONFIG))
        cfg["ctas"]["secondary"][0]["target"] = ""
        bad_cfg.write_text(json.dumps(cfg))
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            rc = viz.main(["--report", str(report), "--config", str(bad_cfg),
                           "--out", str(tmp / "out.html")])
        tc.assertEqual(1, rc)
        tc.assertIn("target vacío", err.getvalue())
        tc.assertIn("Explorar el Gantt", err.getvalue())


# ======================================================================
# Numeración de figuras/tablas (FPA-144/106)
# ======================================================================

class TestNumeracion(F6Base):

    def test_numeros_unicos(self):
        """FPA-106: la suite falla si hay números de figura o tabla
        duplicados."""
        for kind in ("Tabla", "Figura"):
            nums = re.findall(rf"{kind} (\d+)", self.html)
            self.assertGreater(len(nums), 0, kind)
            self.assertEqual(len(nums), len(set(nums)),
                             f"{kind} duplicado: {nums}")

    def test_captions_numerados(self):
        """FPA-144: numeración automática sobre todos los captions."""
        n_caps = self.html.count("<caption>")
        self.assertEqual(n_caps,
                         len(re.findall(r"<caption>Tabla \d+", self.html)))


# ======================================================================
# Export CSV / Download SVG (FPA-169)
# ======================================================================

class TestExportShare(F6Base):

    def test_export_csv_en_toda_tabla(self):
        """FPA-169: cada <table> del main lleva un botón Exportar CSV
        delante (JS descarga sin recargar)."""
        main = self.html[self.html.index("<main"):self.html.index("</main>")]
        n_tables = len(re.findall(r"<table[ >]", main))
        n_btns = main.count('class="export-csv"')
        self.assertGreater(n_tables, 5)
        self.assertEqual(n_tables, n_btns)

    def test_download_svg_en_chart(self):
        """FPA-169: el chart SVG (waterfall) lleva botón Descargar SVG."""
        self.assertIn('class="dl-svg"', self.html)
        self.assertIn('class="wf chart"', self.html)

    def test_js_export_sin_deps(self):
        js = self.html.split("<script>")[-1]
        for fn in ("tableToCSV", "downloadText"):
            self.assertIn(fn, js)
        self.assertNotIn("http", js.replace("http://www.w3.org", ""))

    def test_share_view_js(self):
        """FPA-170: comparte URL con view, period y expansión; la restaura
        al cargar validando contra el modelo (FPA-171)."""
        js = self.html.split("<script>")[-1]
        self.assertIn("URLSearchParams", js)
        self.assertIn('id="share-view"', self.html)
        self.assertIn("MODEL.views[", js)      # periodo validado
        self.assertIn("VIEWS.indexOf(", js)    # vista validada
        self.assertIn("data-tree", js)         # expansión de árbol


# ======================================================================
# Accesibilidad (FPA-175…179, 094)
# ======================================================================

class TestAccesibilidad(F6Base):

    def test_skip_link_y_lang(self):
        """FPA-179: skip-to-content + lang del documento."""
        self.assertIn('<a class="skip"', self.html)
        self.assertIn('href="#summary"', self.html)
        self.assertIn('<html lang="es">', self.html)

    def test_targets_44px(self):
        """FPA-176: targets táctiles ≥ 44×44 px en CSS."""
        self.assertIn("min-height:44px", self.html)

    def test_primera_columna_fija(self):
        """FPA-177: <600px la primera columna queda fija con scroll."""
        self.assertIn("position:sticky", self.html)
        self.assertIn("th:first-child", self.html)

    def test_reduced_motion(self):
        """FPA-178: sin animación bajo prefers-reduced-motion."""
        self.assertIn("prefers-reduced-motion", self.html)

    def test_retro_confinado(self):
        """FPA-178: retro solo en header/footer (ya F1), sin animación."""
        header = self.html[:self.html.index("<main")]
        footer = self.html[self.html.index("<footer"):]
        body = self.html[self.html.index("<main"):self.html.index("<footer")]
        for zone in (header, footer):
            self.assertIn('class="retro', zone)
        self.assertNotIn('class="retro"', body)

    def test_readout_persistente(self):
        """FPA-175: chart inspeccionable por tap/focus/hover con readout
        persistente (no captions hover-only)."""
        self.assertIn('id="wf-readout"', self.html)
        self.assertIn('tabindex="0"', self.html)
        self.assertIn("aria-label", self.html)
        js = self.html.split("<script>")[-1]
        self.assertIn("wf-readout", js)
        self.assertIn("focus", js)

    def test_focus_visible(self):
        """FPA-094: focus visible por CSS."""
        self.assertIn(":focus-visible", self.html)

    def test_scroll_horizontal_contenedores(self):
        """FPA-092: contenedores con scroll horizontal < 600px."""
        self.assertIn("overflow-x:auto", self.html)


# ======================================================================
# Golden + determinismo (FPA-104)
# ======================================================================

class TestGolden(unittest.TestCase):
    """Golden F6: vistas del selector (keys+labels), CTAs y hallazgos sobre
    el fixture F6. Regenerar:
    REGEN_GOLDEN=1 python3 tests/test_fpa_f6.py"""

    def test_golden_f6(self):
        fx = f6_fixture()
        model = viz.build_model(fx, CONFIG)
        html = viz.render_html(fx, CONFIG, generated="T")
        snapshot = {
            "windows": [{"key": k, "label": v["label"],
                         "months": v["months"], "has_prior": v["has_prior"]}
                        for k, v in model["views"].items()],
            "ctas_html": viz.ctas_html(CONFIG),
            # orden de secciones: breakdown (pareto) antes que habits (heatmap)
            "findings": re.findall(
                r'<h2 class="finding">[^<]+</h2>'
                r'<p class="small finding-meta">[^<]+</p>', html),
        }
        if REGEN_GOLDEN:
            GOLDEN.parent.mkdir(parents=True, exist_ok=True)
            GOLDEN.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False,
                                         sort_keys=True) + "\n")
            self.skipTest("golden regenerado; revisar diff antes de aceptar")
        if not GOLDEN.exists():
            self.fail("Falta golden; corre REGEN_GOLDEN=1 python3 tests/test_fpa_f6.py")
        golden = json.loads(GOLDEN.read_text())
        self.assertEqual(golden, snapshot)

    def test_determinismo_salvo_timestamp(self):
        """FPA-104: doble corrida → idéntico salvo fecha de generación."""
        fx = f6_fixture()
        a = viz.render_html(fx, CONFIG, generated="2026-09-20 12:00")
        b = viz.render_html(fx, CONFIG, generated="2026-09-20 12:00")
        self.assertEqual(a, b)


# ======================================================================
# check-docs (FPA-143/107)
# ======================================================================

class TestCheckDocs(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.report = json.loads((REPO / "data" / "usage_report_v3.json")
                                .read_text())

    def test_readme_consistente(self):
        """FPA-143: las cifras del bloque CHECK-DOCS del README salen del
        JSON."""
        self.assertEqual([], viz.check_docs(
            self.report, REPO / "README.md"))

    def test_cifra_obsoleta_falla(self):
        """FPA-143: cifra distinta → check_docs la lista."""
        with tempfile.TemporaryDirectory() as tmp:
            readme = Path(tmp) / "README.md"
            text = (REPO / "README.md").read_text()
            # cifra mal → error nombrando la figura
            readme.write_text(text.replace(
                viz.expected_doc_figures(self.report)["Proyectos"],
                "9999"))
            errors = viz.check_docs(self.report, readme)
            self.assertTrue(any("Proyectos" in e for e in errors), errors)

    def test_readme_sin_bloque_falla(self):
        with tempfile.TemporaryDirectory() as tmp:
            readme = Path(tmp) / "README.md"
            readme.write_text("hola\n")
            errors = viz.check_docs(self.report, readme)
            self.assertTrue(any("CHECK-DOCS" in e for e in errors))

    def test_main_check_docs_exit(self):
        """FPA-143/107: --check-docs termina 0 en verde, 1 en rojo."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            bad_readme = tmp / "README.md"
            text = (REPO / "README.md").read_text()
            bad_readme.write_text(text.replace(
                viz.expected_doc_figures(self.report)["Interacciones"],
                "12345"))
            rc = viz.main(["--check-docs", "--readme", str(bad_readme)])
            self.assertEqual(1, rc)
            rc = viz.main(["--check-docs"])
            self.assertEqual(0, rc)

    def test_ci_corre_check_docs(self):
        """FPA-107: el pipeline corre el chequeo de consistencia de docs y
        falla ante cualquier desvío."""
        yml = (REPO / ".github" / "workflows" / "deploy-pages.yml").read_text()
        self.assertIn("viz-fpa.py --check-docs", yml)


if __name__ == "__main__":
    unittest.main()
