#!/usr/bin/env python3
"""Generate the profile SVGs (ASCII banner + neofetch terminal).

Requires: pip install pyfiglet
"""
import math
from html import escape
from pathlib import Path

import pyfiglet

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"

BG = "#0a0a0f"
PINK = "#ff1e8c"
HOT = "#ff5fb0"
DEEP = "#b3005e"
DARK = "#4a0026"
CYAN = "#00f0ff"
TEXT = "#c9d1d9"
DIM = "#6e7681"
MONO = "'JetBrains Mono','Fira Code',Consolas,Menlo,'DejaVu Sans Mono',monospace"

# Double-line box glyphs drawn as strokes so the art never depends on the viewer's font.
A, B = 0.32, 0.68
BOX = {
    "═": [((0, A), (1, A)), ((0, B), (1, B))],
    "║": [((A, 0), (A, 1)), ((B, 0), (B, 1))],
    "╔": [((1, A), (A, A), (A, 1)), ((1, B), (B, B), (B, 1))],
    "╗": [((0, A), (B, A), (B, 1)), ((0, B), (A, B), (A, 1))],
    "╚": [((A, 0), (A, B), (1, B)), ((B, 0), (B, A), (1, A))],
    "╝": [((B, 0), (B, B), (0, B)), ((A, 0), (A, A), (0, A))],
}


def figlet_shapes(text, x0, y0, cw, ch):
    rows = [r for r in pyfiglet.figlet_format(text, font="ansi_shadow", width=300).split("\n") if r.strip()]
    rects, paths = [], []
    for r, row in enumerate(rows):
        c = 0
        while c < len(row):
            if row[c] == "█":
                start = c
                while c < len(row) and row[c] == "█":
                    c += 1
                rects.append(f'<rect x="{x0 + start * cw:.1f}" y="{y0 + r * ch:.1f}" width="{(c - start) * cw + 0.6:.1f}" height="{ch + 0.6:.1f}"/>')
                continue
            for seg in BOX.get(row[c], []):
                pts = " L ".join(f"{x0 + (c + px) * cw:.1f} {y0 + (r + py) * ch:.1f}" for px, py in seg)
                paths.append(f"M {pts}")
            c += 1
    width = max(len(r.rstrip()) for r in rows) * cw
    return "".join(rects), " ".join(paths), width, len(rows) * ch


def banner():
    W, H = 1000, 320
    cw, ch = 17, 26
    _, _, art_w, art_h = figlet_shapes("PAXDOT", 0, 0, cw, ch)
    x0, y0 = (W - art_w) / 2, 62
    rects, paths, _, _ = figlet_shapes("PAXDOT", x0, y0, cw, ch)
    sub_y = y0 + art_h + 48
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<defs>
  <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0" stop-color="{HOT}"/><stop offset="0.5" stop-color="{PINK}"/><stop offset="1" stop-color="{DEEP}"/>
  </linearGradient>
  <pattern id="grid" width="24" height="24" patternUnits="userSpaceOnUse">
    <path d="M24 0H0V24" fill="none" stroke="{PINK}" stroke-opacity="0.07"/>
  </pattern>
  <pattern id="scan" width="4" height="4" patternUnits="userSpaceOnUse">
    <rect width="4" height="1" fill="#000" fill-opacity="0.35"/>
  </pattern>
  <linearGradient id="bar" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0" stop-color="{PINK}" stop-opacity="0"/><stop offset="0.5" stop-color="{PINK}" stop-opacity="0.12"/><stop offset="1" stop-color="{PINK}" stop-opacity="0"/>
  </linearGradient>
  <filter id="glow" x="-10%" y="-30%" width="120%" height="160%">
    <feGaussianBlur stdDeviation="5" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
  <clipPath id="frame"><rect width="{W}" height="{H}" rx="14"/></clipPath>
</defs>
<style>
  .art {{ animation: flicker 6s infinite steps(1); }}
  .gl1 {{ animation: g1 4.5s infinite steps(1); opacity: 0; }}
  .gl2 {{ animation: g2 4.5s infinite steps(1); opacity: 0; }}
  .bar {{ animation: sweep 5s linear infinite; }}
  .cur {{ animation: blink 1s infinite steps(1); }}
  .t {{ font-family: {MONO}; }}
  @keyframes flicker {{ 0%,100% {{opacity:1}} 41% {{opacity:.75}} 42% {{opacity:1}} 77% {{opacity:.85}} 78% {{opacity:1}} }}
  @keyframes g1 {{ 0%,88%,100% {{opacity:0; transform:translate(0,0)}} 89% {{opacity:.8; transform:translate(-7px,2px)}} 91% {{opacity:.6; transform:translate(5px,-3px)}} 93% {{opacity:0}} }}
  @keyframes g2 {{ 0%,88%,100% {{opacity:0; transform:translate(0,0)}} 89% {{opacity:.7; transform:translate(6px,-2px)}} 91% {{opacity:.5; transform:translate(-4px,3px)}} 93% {{opacity:0}} }}
  @keyframes sweep {{ from {{transform:translateY(-120px)}} to {{transform:translateY({H + 40}px)}} }}
  @keyframes blink {{ 0%,49% {{opacity:1}} 50%,100% {{opacity:0}} }}
</style>
<g clip-path="url(#frame)">
  <rect width="{W}" height="{H}" fill="{BG}"/>
  <rect width="{W}" height="{H}" fill="url(#grid)"/>
  <g class="gl1" fill="{CYAN}">{rects}</g>
  <g class="gl2" fill="{PINK}">{rects}</g>
  <g class="art" filter="url(#glow)">
    <path d="{paths}" fill="none" stroke="{DEEP}" stroke-width="2.2" stroke-linecap="square" stroke-linejoin="miter"/>
    <g fill="url(#g)">{rects}</g>
  </g>
  <text class="t" x="{W / 2}" y="{sub_y}" text-anchor="middle" font-size="20" fill="{TEXT}">
    <tspan fill="{PINK}">&gt;</tspan> full-stack developer <tspan fill="{PINK}">//</tspan> compass solutions <tspan class="cur" fill="{PINK}">&#9608;</tspan>
  </text>
  <text class="t" x="24" y="30" font-size="12" fill="{DIM}">[ SYS://PAXDOT ]</text>
  <text class="t" x="{W - 24}" y="30" font-size="12" fill="{DIM}" text-anchor="end">BUILD 2026.10 · UTC-3</text>
  <circle class="cur" cx="30" cy="{H - 26}" r="4" fill="{PINK}"/>
  <text class="t" x="42" y="{H - 22}" font-size="12" fill="{DIM}">STATUS: <tspan fill="{PINK}">ONLINE</tspan></text>
  <text class="t" x="{W - 24}" y="{H - 22}" font-size="12" fill="{DIM}" text-anchor="end">CRMs · BOTS · AUTOMATION · INFRA</text>
  <rect class="bar" width="{W}" height="120" fill="url(#bar)"/>
  <rect width="{W}" height="{H}" fill="url(#scan)"/>
</g>
<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="14" fill="none" stroke="{PINK}" stroke-opacity="0.45" stroke-width="1.5"/>
</svg>
"""


def ascii_planet(cols=50, rows=25, cell_ratio=15.5 / 8.2):
    """A shaded ASCII 'dot' with a tilted ring, lit from the top-left."""
    cx, cy = cols / 2 - 0.5, rows / 2 - 0.5
    ry = 8.8
    rx = ry * cell_ratio
    ramp = ".,:-=+*#%@"
    light = (-0.55, -0.6, 0.58)
    norm = math.sqrt(sum(v * v for v in light))
    lx, ly, lz = (v / norm for v in light)
    tilt, a, b = math.radians(-16), 1.5, 0.42
    shades = [DARK, DEEP, DEEP, PINK, PINK, PINK, HOT, HOT, "#ffc2e0", "#ffffff"]
    grid = []
    for r in range(rows):
        line = []
        for c in range(cols):
            x, y = (c - cx) / rx, (r - cy) / ry
            xr = x * math.cos(tilt) - y * math.sin(tilt)
            yr = x * math.sin(tilt) + y * math.cos(tilt)
            d = math.sqrt((xr / a) ** 2 + (yr / b) ** 2)
            inside = x * x + y * y <= 1
            cell = None
            if inside:
                z = math.sqrt(max(0.0, 1 - x * x - y * y))
                diffuse = max(0.0, x * lx + y * ly + z * lz)
                spec = max(0.0, 2 * diffuse * z - lz) ** 18
                v = min(0.999, 0.06 + 0.8 * diffuse + 0.6 * spec)
                i = int(v * len(ramp))
                cell = (ramp[i], shades[i])
            if 0.80 < d < 1.12 and (yr > 0 or not inside):
                cell = ("=", CYAN) if 0.9 < d < 1.02 else ("-", "#00a8b5")
            line.append(cell)
        grid.append(line)
    return [row for row in grid if any(row)]


def neofetch():
    W, H = 1000, 500
    cw, lh = 8.2, 15.5
    planet = ascii_planet()
    ax, ay = 30, 112 + (16 * 22 - len(planet) * lh) / 2 + 10
    avatar = []
    for r, line in enumerate(planet):
        c = 0
        while c < len(line):
            if not line[c]:
                c += 1
                continue
            start, color = c, line[c][1]
            while c < len(line) and line[c] and line[c][1] == color:
                c += 1
            text = escape("".join(cell[0] for cell in line[start:c]))
            avatar.append(
                f'<text x="{ax + start * cw:.1f}" y="{ay + r * lh:.1f}" fill="{color}" '
                f'textLength="{(c - start) * cw:.1f}" lengthAdjust="spacing">{text}</text>'
            )

    info = [
        ("OS", "Linux · Debian 12 · always SSH'd in"),
        ("Host", "Compass Solutions"),
        ("Role", "Full-Stack Developer"),
        ("Uptime", "on GitHub since 2022"),
        ("Shell", "bash + way too many cron jobs"),
        ("Languages", "TypeScript · JavaScript · Kotlin · SQL"),
        ("Frontend", "Next.js · React · Tailwind · Three.js"),
        ("Backend", "Node.js · Express · Prisma"),
        ("Data", "PostgreSQL · SQLite · Supabase"),
        ("Mobile", "Android (Kotlin)"),
        ("Automation", "Playwright · Telegram bots · scrapers"),
        ("Infra", "Nginx · PM2 · GitHub Actions"),
        ("Focus", "CRMs · bots · dashboards · automation"),
        ("Web", "compasssolutions.io"),
    ]
    ix, iy, step = 455, 112, 22
    lines = [
        f'<text x="{ix}" y="{iy}" class="l" style="animation-delay:.2s"><tspan fill="{PINK}" font-weight="700">paxdot</tspan><tspan fill="{TEXT}">@</tspan><tspan fill="{PINK}" font-weight="700">compass</tspan></text>',
        f'<text x="{ix}" y="{iy + step}" class="l" style="animation-delay:.3s" fill="{DIM}">──────────────────────</text>',
    ]
    for i, (key, value) in enumerate(info, start=2):
        lines.append(
            f'<text x="{ix}" y="{iy + i * step}" class="l" style="animation-delay:{0.2 + i * 0.12:.2f}s">'
            f'<tspan fill="{PINK}" font-weight="700">{escape(key)}</tspan><tspan fill="{TEXT}">: {escape(value)}</tspan></text>'
        )
    py = iy + (len(info) + 2) * step + 4
    palette = [BG, DARK, DEEP, PINK, HOT, CYAN, TEXT, "#ffffff"]
    swatches = "".join(
        f'<rect x="{ix + i * 30}" y="{py}" width="26" height="16" rx="2" fill="{c}" stroke="#30363d"/>' for i, c in enumerate(palette)
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<style>
  .t {{ font-family: {MONO}; font-size: 14px; }}
  .a text {{ font-family: {MONO}; font-size: 13px; font-weight: 700; }}
  .l {{ animation: in .35s ease-out both; }}
  .a {{ animation: pulse 4s ease-in-out infinite; }}
  .cur {{ animation: blink 1s infinite steps(1); }}
  @keyframes in {{ from {{opacity:0; transform:translateX(-6px)}} to {{opacity:1; transform:none}} }}
  @keyframes pulse {{ 0%,100% {{opacity:1}} 50% {{opacity:.82}} }}
  @keyframes blink {{ 0%,49% {{opacity:1}} 50%,100% {{opacity:0}} }}
</style>
<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="12" fill="#0d1117" stroke="#30363d"/>
<path d="M1 13 a12 12 0 0 1 12 -12 H{W - 13} a12 12 0 0 1 12 12 V38 H1 Z" fill="#161b22"/>
<circle cx="24" cy="20" r="6" fill="#ff5f57"/><circle cx="44" cy="20" r="6" fill="#febc2e"/><circle cx="64" cy="20" r="6" fill="#28c840"/>
<text class="t" x="{W / 2}" y="25" text-anchor="middle" fill="{DIM}" font-size="13">paxdot@compass: ~</text>
<text class="t" x="34" y="72"><tspan fill="{PINK}" font-weight="700">paxdot@compass</tspan><tspan fill="{TEXT}">:~$&#160;</tspan><tspan fill="#ffffff">neofetch</tspan></text>
<g class="a">{''.join(avatar)}</g>
<g class="t">{''.join(lines)}{swatches}</g>
<text class="t" x="34" y="{H - 24}"><tspan fill="{PINK}" font-weight="700">paxdot@compass</tspan><tspan fill="{TEXT}">:~$&#160;</tspan><tspan class="cur" fill="{PINK}">&#9608;</tspan></text>
</svg>
"""


def main():
    ASSETS.mkdir(exist_ok=True)
    (ASSETS / "banner.svg").write_text(banner())
    (ASSETS / "neofetch.svg").write_text(neofetch())
    print("wrote", ", ".join(p.name for p in ASSETS.glob("*.svg")))


if __name__ == "__main__":
    main()
