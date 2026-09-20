#!/usr/bin/env python3
"""
site_theme.py — tokens del tema compartido del sitio (Corporate
Infographics™ 1996).

Purpose: única fuente de definición de la identidad visual del sitio
(tema "90s corporate" extraído de viz-dashboard.py, coffe-gen.2 / change
update-fpa-site-integration).

Responsibilities:
- exponer TOKENS: las variables CSS canónicas (--bg silver, --accent granate,
  --accent2/--navy navy, --good teal, --yellow, más los alias semánticos que
  consumen viz-fpa.py: --card, --line, --acc, --ok, --bad)
- emitir el bloque :root (css_vars()) y las reglas base compartidas
  (base_css(): box-sizing, tipografía Arial del sitio) para que cada
  generador (viz-fpa.py, viz-index.py, viz-gantt.py) las interpolate en su
  <style> en lugar de duplicar definiciones divergentes

Rationale: copiar el CSS a mano garantiza divergencia futura entre los
dashboards; un módulo stdlib es el patrón del repo (fpa_config.py). Un solo
modo (sin dark mode, decisión D2 del change) y contraste AA verificado por
tests/test_fpa_theme.py.
"""

TOKENS = {
    # === Corporate Infographics™ 1996 (extraído de viz-dashboard.py) ===
    "--bg": "#c0c0c0", "--panel": "#ffffff", "--fg": "#000000",
    "--muted": "#404040", "--accent": "#800000", "--accent2": "#000080",
    "--good": "#008080", "--grid": "#c0c0c0", "--navy": "#000080",
    "--yellow": "#ffff00",
    # Alias semánticos (nombres previos de viz-fpa.py) mapeados al tema:
    # panel blanco, borde gris, acento granate, ok teal, bad granate.
    "--card": "#ffffff", "--line": "#c0c0c0", "--acc": "#800000",
    "--ok": "#008080", "--bad": "#800000",
    # Tipografía del sitio como token para que ningún generador la duplique.
    "--font-stack": "Arial, Helvetica, 'MS Sans Serif', sans-serif",
}

FONT_STACK = ('Arial, Helvetica, "MS Sans Serif", sans-serif')


def css_vars():
    """Bloque :root con exactamente las variables de TOKENS (orden estable)."""
    body = "".join(f"{k}:{v};" for k, v in TOKENS.items())
    return ":root {" + body + "}"


def base_css():
    """Reglas base compartidas: box-sizing + tipografía del sitio.

    Cada generador añade sus reglas específicas DESPUÉS de esta base;
    ninguna define su propia paleta ni font-family alternativa.
    """
    return (
        css_vars() + "\n"
        "* { box-sizing: border-box; }\n"
        "body { font-family: var(--font-stack); }"
    )
