"""Dibuja la cotización de mis DARWINs (Darwinex Zero) en un SVG para el README.

Uso: python scripts/darwin_chart.py dist
Genera dist/darwins.svg (tema claro) y dist/darwins-dark.svg (tema oscuro).
Solo usa la librería estándar. Si Darwinex no responde, sale con error y la
Action no publica nada, así que en el perfil se queda el gráfico anterior.
"""

import datetime as dt
import json
import sys
import urllib.request
from pathlib import Path

API = "https://www.darwinexzero.com/api"
DARWINS = ["EGXL", "EZDK"]

W, H = 820, 320
PAD_L, PAD_R, PAD_T, PAD_B = 52, 20, 64, 36

THEMES = {
    "light": {"bg": "#ffffff", "text": "#24292f", "muted": "#6e7781", "grid": "#d8dee4",
              "lines": ["#a39a12", "#2f6fd6"]},
    "dark": {"bg": "#1a1b27", "text": "#c0caf5", "muted": "#7a82a8", "grid": "#2a2e42",
             "lines": ["#c8be25", "#7aa2f7"]},
}


def get_json(path):
    req = urllib.request.Request(f"{API}/{path}", headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def fetch(ticker):
    # El sufijo de versión (EGXL.5.18) puede cambiar, así que se pide cada vez
    product = get_json(f"products/basics/{ticker}")["productName"]
    data = get_json(f"charts/{product}/candles-return/ALL?candlesResolution=1D")["returnData"]
    if len(data) < 2:
        raise RuntimeError(f"{ticker}: sin cotizaciones")
    return [(dt.date.fromtimestamp(ms / 1000), float(v)) for ms, v in data]


def render(series, theme):
    t = THEMES[theme]
    d0 = min(s[0][0] for s in series.values())
    d1 = max(s[-1][0] for s in series.values())
    vals = [v for s in series.values() for _, v in s]
    lo, hi = min(vals), max(vals)
    step = 5 if hi - lo > 8 else 2
    lo = (int(lo) // step) * step
    hi = (int(hi) // step + 1) * step

    pw, ph = W - PAD_L - PAD_R, H - PAD_T - PAD_B
    x = lambda d: PAD_L + (d - d0).days / max((d1 - d0).days, 1) * pw
    y = lambda v: PAD_T + (hi - v) / (hi - lo) * ph

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
           f'font-family="Segoe UI, Helvetica, Arial, sans-serif">',
           f'<rect width="{W}" height="{H}" rx="8" fill="{t["bg"]}"/>']

    # Rejilla horizontal con la cotización; la línea de 100 (inicio) más marcada
    for v in range(lo, hi + 1, step):
        sw = "1.5" if v == 100 else "1"
        out.append(f'<line x1="{PAD_L}" x2="{W - PAD_R}" y1="{y(v):.1f}" y2="{y(v):.1f}" '
                   f'stroke="{t["grid"]}" stroke-width="{sw}"/>')
        out.append(f'<text x="{PAD_L - 8}" y="{y(v) + 4:.1f}" font-size="11" fill="{t["muted"]}" '
                   f'text-anchor="end">{v}</text>')

    # Eje X: una etiqueta cada trimestre
    m = dt.date(d0.year, d0.month, 1)
    while m <= d1:
        if m >= d0 and m.month in (1, 4, 7, 10):
            out.append(f'<text x="{x(m):.1f}" y="{H - 12}" font-size="11" fill="{t["muted"]}" '
                       f'text-anchor="middle">{m.strftime("%b %y")}</text>')
        m = dt.date(m.year + (m.month == 12), m.month % 12 + 1, 1)

    # Líneas y leyenda (nombre, cotización actual y rentabilidad desde el inicio)
    lx = PAD_L
    for (name, s), color in zip(series.items(), t["lines"]):
        pts = " ".join(f"{x(d):.1f},{y(v):.1f}" for d, v in s)
        out.append(f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="2" '
                   f'stroke-linejoin="round" stroke-linecap="round"/>')
        last = s[-1][1]
        ret = (last / s[0][1] - 1) * 100
        out.append(f'<circle cx="{x(s[-1][0]):.1f}" cy="{y(last):.1f}" r="3.5" fill="{color}"/>')
        out.append(f'<rect x="{lx}" y="22" width="12" height="12" rx="3" fill="{color}"/>')
        out.append(f'<text x="{lx + 18}" y="33" font-size="14" font-weight="600" fill="{t["text"]}">'
                   f'{name} <tspan fill="{t["muted"]}" font-weight="400">{last:.2f} '
                   f'({ret:+.1f}%)</tspan></text>')
        lx += 210

    out.append(f'<text x="{W - PAD_R}" y="33" font-size="11" fill="{t["muted"]}" text-anchor="end">'
               f'Darwinex Zero · {d1.strftime("%d/%m/%Y")}</text>')
    out.append("</svg>")
    return "\n".join(out)


def main():
    dest = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    dest.mkdir(parents=True, exist_ok=True)
    series = {name: fetch(name) for name in DARWINS}
    (dest / "darwins.svg").write_text(render(series, "light"), encoding="utf-8")
    (dest / "darwins-dark.svg").write_text(render(series, "dark"), encoding="utf-8")
    for name, s in series.items():
        print(f"{name}: {len(s)} cotizaciones, última {s[-1][1]} ({s[-1][0]})")


if __name__ == "__main__":
    main()
