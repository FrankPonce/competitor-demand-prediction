"""Project-wide visual identity: dark theme + one fixed colour per company.

Every chart, table marker and README element uses these tokens, so a company is
the same colour everywhere.

Company colours are brand-inspired and were validated for the dark surface below
(lightness band, chroma, colour-blind separation across *all* pairs, normal-vision
separation, contrast ≥ 3:1) with the dataviz palette validator:

    node validate_palette.js "#b95115,#9c7bd2,#5ea529,#2d6ac1" --mode dark --surface "#0d1117" --pairs all
    -> ALL CHECKS PASS (worst CVD ΔE 8.2 deutan, worst normal ΔE 15.7)

OpenAI's brand is monochrome, so it gets lavender (a hue no other company uses).
"""

from __future__ import annotations

COMPANIES = ["Anthropic", "OpenAI", "NVIDIA", "Google"]

COMPANY_COLOR = {
    "Anthropic": "#b95115",  # burnt orange
    "OpenAI": "#9c7bd2",     # lavender
    "NVIDIA": "#5ea529",     # green
    "Google": "#2d6ac1",     # blue
}
COMPANY_DOT = {"Anthropic": "🟠", "OpenAI": "🟣", "NVIDIA": "🟢", "Google": "🔵"}

# Dark theme tokens (aligned with GitHub's dark canvas so charts sit seamlessly in the README).
THEME = {
    "surface": "#0d1117",
    "panel": "#161b22",
    "grid": "#21262d",
    "axis": "#30363d",
    "text": "#e6edf3",
    "text2": "#9198a1",
    "muted": "#6e7681",
    "zero": "#6e7681",
}


def label(company: str) -> str:
    """Company name with its colour marker, for Markdown tables and headings."""
    return f"{COMPANY_DOT.get(company, '')} {company}".strip()


def colorize_markdown(md: str) -> str:
    """Prefix company names with their colour marker in Markdown tables and headings."""
    import re

    rx = re.compile(r"(?<![🟠🟣🟢🔵] )\b(" + "|".join(COMPANIES) + r")\b(?![\w-])")
    out = []
    for line in md.split("\n"):
        if line.startswith("|") or line.startswith("#") or line.startswith("**"):
            line = rx.sub(lambda m: label(m.group(1)), line)
        out.append(line)
    return "\n".join(out)


def _available_fonts(preferred: list[str]) -> list[str]:
    """Keep only installed fonts, so matplotlib doesn't warn about missing ones."""
    from matplotlib import font_manager

    installed = {f.name for f in font_manager.fontManager.ttflist}
    return [f for f in preferred if f in installed] or ["DejaVu Sans"]


def apply_matplotlib() -> None:
    import matplotlib.pyplot as plt

    t = THEME
    plt.rcParams.update({
        "figure.facecolor": t["surface"], "axes.facecolor": t["surface"], "savefig.facecolor": t["surface"],
        "axes.edgecolor": t["axis"], "axes.labelcolor": t["text2"], "xtick.color": t["text2"],
        "ytick.color": t["text2"], "text.color": t["text"], "axes.titlecolor": t["text"],
        "axes.grid": True, "grid.color": t["grid"], "grid.linewidth": 0.8, "axes.axisbelow": True,
        "axes.spines.top": False, "axes.spines.right": False, "axes.spines.left": False,
        "font.family": "sans-serif",
        "font.sans-serif": _available_fonts(["Inter", "Segoe UI", "Helvetica Neue", "Arial", "DejaVu Sans"]),
        "font.size": 10, "axes.titlesize": 12.5, "axes.titleweight": "bold", "axes.titlelocation": "left",
        "axes.titlepad": 12, "legend.frameon": False, "legend.labelcolor": t["text"],
        "lines.linewidth": 2.2, "lines.solid_capstyle": "round", "figure.dpi": 100, "savefig.dpi": 160,
    })


def footnote(fig, text: str) -> None:
    """Small source line in the bottom-left corner of a figure."""
    fig.text(0.01, 0.01, text, ha="left", va="bottom", fontsize=7.5, color=THEME["muted"])
