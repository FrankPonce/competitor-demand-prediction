"""Generate the SIGNALS radar logo ("spectrum sweep") as static SVGs.

    python assets/brand/make_logo.py

Writes dashboard/assets/logo.svg (no tile, for the top bar; made for the dark #0d1117 surface) and dashboard/assets/favicon.svg (on a dark tile).
SVG has no conic gradient, so the sweep's trail is built from thin wedges whose colour runs through the four company
colours (Anthropic → OpenAI → Google → NVIDIA) and whose opacity rises toward the leading edge.
"""

from math import cos, radians, sin
from pathlib import Path

OUT = Path(__file__).resolve().parents[2] / "dashboard" / "assets"
STOPS = ["#b95115", "#9c7bd2", "#2d6ac1", "#5ea529"]
C, R_OUT, R_IN = 32.0, 23.0, 13.0          # viewBox 64 × 64
LEAD = 40.0                                 # leading edge, degrees clockwise from 12 o'clock
TRAIL = 150.0                               # how far the colour trail reaches behind it
N = 48                                      # wedges


def hex2rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def mix(t):
    """Colour at t in [0, 1] along the four stops."""
    x = t * (len(STOPS) - 1)
    i = min(int(x), len(STOPS) - 2)
    f = x - i
    a, b = hex2rgb(STOPS[i]), hex2rgb(STOPS[i + 1])
    return "#%02x%02x%02x" % tuple(round(a[k] + (b[k] - a[k]) * f) for k in range(3))


def over_bg(colour: str, alpha: float, bg: str = "#0d1117") -> str:
    """The colour as it looks at `alpha` over the dark surface, as an opaque fill (semi-transparent slices that
    overlap would show thin seam lines)."""
    c, b = hex2rgb(colour), hex2rgb(bg)
    return "#%02x%02x%02x" % tuple(round(b[k] + (c[k] - b[k]) * alpha) for k in range(3))


def pt(angle_deg, r):
    a = radians(angle_deg - 90)
    return C + r * cos(a), C + r * sin(a)


def wedges() -> str:
    out = []
    for k in range(N):
        t0, t1 = k / N, (k + 1) / N
        a0, a1 = LEAD - TRAIL * (1 - t0), LEAD - TRAIL * (1 - t1) + 0.8   # overlap: opaque fills, so no seams
        (x0, y0), (x1, y1) = pt(a0, R_OUT), pt(a1, R_OUT)
        op = 0.16 + 0.8 * ((t0 + t1) / 2) ** 1.15
        out.append(f'<path d="M{C} {C}L{x0:.2f} {y0:.2f}A{R_OUT} {R_OUT} 0 0 1 {x1:.2f} {y1:.2f}Z" '
                   f'fill="{over_bg(mix((t0 + t1) / 2), op)}"/>')
    return "".join(out)


def radar(ring: str) -> str:
    bx, by = pt(LEAD + 24, 17.0)            # the blip: just ahead of the sweep, a fresh signal
    return (f'<circle cx="{C}" cy="{C}" r="{R_IN}" fill="none" stroke="{ring}" stroke-opacity=".55" stroke-width="1.6"/>'
            f'{wedges()}'
            f'<circle cx="{C}" cy="{C}" r="{R_OUT}" fill="none" stroke="{ring}" stroke-width="2.2"/>'
            f'<circle cx="{C}" cy="{C}" r="2.6" fill="#e6edf3"/>'
            f'<circle cx="{bx:.2f}" cy="{by:.2f}" r="5.6" fill="none" stroke="#e6edf3" stroke-opacity=".4" stroke-width="1.4"/>'
            f'<circle cx="{bx:.2f}" cy="{by:.2f}" r="2.9" fill="#e6edf3"/>')


def main() -> None:
    head = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">'
    (OUT / "logo.svg").write_text(head + "<title>SIGNALS</title>" + radar("#4a525d") + "</svg>\n", encoding="utf-8")
    (OUT / "favicon.svg").write_text(head + '<rect width="64" height="64" rx="15" fill="#0d1117"/>' + radar("#4a525d")
                                     + "</svg>\n", encoding="utf-8")
    print("wrote", OUT / "logo.svg", OUT / "favicon.svg")


if __name__ == "__main__":
    main()
