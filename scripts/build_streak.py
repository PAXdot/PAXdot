#!/usr/bin/env python3
"""Render the streak panel as a terminal window from the same calendar the 3D chart uses."""
import json
import math
import os
import sys
import urllib.request
from datetime import date
from xml.sax.saxutils import escape

BG = "#0a0a0f"
PINK = "#ff1e8c"
HOT = "#ff5fb0"
DEEP = "#b3005e"
DARK = "#4a0026"
CYAN = "#00f0ff"
TEXT = "#c9d1d9"
DIM = "#6e7681"
MONO = "'JetBrains Mono','Fira Code',Consolas,Menlo,'DejaVu Sans Mono',monospace"
LEVEL_COLORS = {"FIRST_QUARTILE": DARK, "SECOND_QUARTILE": DEEP, "THIRD_QUARTILE": PINK, "FOURTH_QUARTILE": HOT}

QUERY = """query($login: String!) { user(login: $login) { contributionsCollection { contributionCalendar {
  totalContributions weeks { contributionDays { date contributionCount contributionLevel } } } } } }"""


def calendar(login, token):
    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": login}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        cal = json.loads(response.read())["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    days = [d for week in cal["weeks"] for d in week["contributionDays"]]
    return cal["totalContributions"], days


def streaks(days):
    """Current streak (today may still be empty without breaking it) and the longest run."""
    runs, start = [], None
    for i, day in enumerate(days):
        if day["contributionCount"] > 0:
            start = i if start is None else start
        elif start is not None:
            runs.append((start, i - 1))
            start = None
    if start is not None:
        runs.append((start, len(days) - 1))
    last = len(days) - 1
    current = None
    if runs and runs[-1][1] >= last - (1 if days[last]["contributionCount"] == 0 else 0):
        current = runs[-1]
    longest = max(runs, key=lambda r: (r[1] - r[0], r[1]), default=None)
    return current, longest


def short(iso):
    return date.fromisoformat(iso).strftime("%b %d").replace(" 0", " ")


def stat_box(x, w, label, value, unit, sub, accent):
    border = PINK if accent else "#30363d"
    color = PINK if accent else "#ffffff"
    return (
        f'<g class="l" style="animation-delay:{0.25 + x / 2000:.2f}s">'
        f'<rect x="{x}" y="98" width="{w}" height="118" rx="8" fill="#0d1117" stroke="{border}"/>'
        + (f'<rect x="{x}" y="98" width="{w}" height="3" rx="1.5" fill="{PINK}"/>' if accent else "")
        + f'<text x="{x + 20}" y="126" fill="{DIM}" font-size="12" letter-spacing="1.5">{escape(label)}</text>'
        f'<text x="{x + 20}" y="174"><tspan fill="{color}" font-size="40" font-weight="700">{value}</tspan>'
        f'<tspan fill="{TEXT}" font-size="15" dx="10">{escape(unit)}</tspan></text>'
        f'<text x="{x + 20}" y="200" fill="{DIM}" font-size="12">{escape(sub)}</text></g>'
    )


def render(total, days):
    W, H = 1000, 420
    current, longest = streaks(days)
    cur_len = current[1] - current[0] + 1 if current else 0
    cur_sub = f"since {short(days[current[0]]['date'])}" if current else "starts with the next commit"
    long_len = longest[1] - longest[0] + 1 if longest else 0
    long_sub = f"{short(days[longest[0]]['date'])} → {short(days[longest[1]]['date'])}" if longest else "-"
    total_sub = f"{short(days[0]['date'])} {days[0]['date'][:4]} → {short(days[-1]['date'])} {days[-1]['date'][:4]}"

    gap, bw = 14, (W - 68 - 28) / 3
    boxes = (stat_box(34, bw, "TOTAL CONTRIBUTIONS", f"{total:,}", "last year", total_sub, False)
             + stat_box(34 + bw + gap, bw, "CURRENT STREAK", cur_len, "days" if cur_len != 1 else "day", cur_sub, True)
             + stat_box(34 + 2 * (bw + gap), bw, "LONGEST STREAK", long_len, "days" if long_len != 1 else "day", long_sub, False))

    recent = days[-30:]
    peak = max((d["contributionCount"] for d in recent), default=0) or 1
    week = sum(d["contributionCount"] for d in days[-7:])
    left, right, base, top = 34, W - 34, 338, 262
    slot = (right - left) / len(recent)
    bars = []
    for i, day in enumerate(recent):
        x = left + i * slot + 3
        count = day["contributionCount"]
        if count == 0:
            bars.append(f'<rect x="{x:.1f}" y="{base - 2}" width="{slot - 6:.1f}" height="2" fill="#30363d"/>')
            continue
        h = max(6, (base - top) * math.sqrt(count / peak))
        bars.append(
            f'<rect class="b" style="animation-delay:{0.6 + i * 0.03:.2f}s" x="{x:.1f}" y="{base - h:.1f}" '
            f'width="{slot - 6:.1f}" height="{h:.1f}" rx="2" fill="{LEVEL_COLORS.get(day["contributionLevel"], PINK)}">'
            f'<title>{day["date"]}: {count}</title></rect>'
        )

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<style>
  .t {{ font-family: {MONO}; font-size: 14px; }}
  .l {{ animation: in .4s ease-out both; }}
  .b {{ transform-box: fill-box; transform-origin: bottom; animation: grow .5s ease-out both; }}
  .cur {{ animation: blink 1s infinite steps(1); }}
  @keyframes in {{ from {{opacity:0; transform:translateY(6px)}} to {{opacity:1; transform:none}} }}
  @keyframes grow {{ from {{transform:scaleY(0)}} to {{transform:scaleY(1)}} }}
  @keyframes blink {{ 0%,49% {{opacity:1}} 50%,100% {{opacity:0}} }}
</style>
<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="12" fill="#0d1117" stroke="#30363d"/>
<path d="M1 13 a12 12 0 0 1 12 -12 H{W - 13} a12 12 0 0 1 12 12 V38 H1 Z" fill="#161b22"/>
<circle cx="24" cy="20" r="6" fill="#ff5f57"/><circle cx="44" cy="20" r="6" fill="#febc2e"/><circle cx="64" cy="20" r="6" fill="#28c840"/>
<text class="t" x="{W / 2}" y="25" text-anchor="middle" fill="{DIM}" font-size="13">~/streak.log</text>
<g class="t">
<text x="34" y="72"><tspan fill="{PINK}" font-weight="700">paxdot@compass</tspan><tspan fill="{TEXT}">:~$</tspan><tspan fill="#ffffff" dx="9">./streak --live</tspan></text>
{boxes}
<text x="34" y="250" class="l" style="animation-delay:.5s"><tspan fill="{PINK}" font-weight="700">&gt;</tspan><tspan fill="{TEXT}" dx="9">last 30 days</tspan><tspan fill="{DIM}" dx="14">·</tspan><tspan fill="{DIM}" dx="14">{week} this week</tspan><tspan fill="{DIM}" dx="14">·</tspan><tspan fill="{DIM}" dx="14">peak {peak}/day</tspan></text>
<line x1="{left}" y1="{base + 1}" x2="{right}" y2="{base + 1}" stroke="#21262d"/>
{''.join(bars)}
<text x="{left}" y="{base + 20}" fill="{DIM}" font-size="11">{short(recent[0]['date'])}</text>
<text x="{right}" y="{base + 20}" fill="{DIM}" font-size="11" text-anchor="end">today</text>
<text x="34" y="{H - 24}"><tspan fill="{PINK}" font-weight="700">paxdot@compass</tspan><tspan fill="{TEXT}">:~$</tspan><tspan class="cur" fill="{PINK}" dx="9">&#9608;</tspan></text>
</g>
</svg>
"""


def main():
    total, days = calendar(os.environ.get("USERNAME", "PAXdot"), os.environ["GITHUB_TOKEN"])
    with open(sys.argv[1], "w", encoding="utf-8") as fh:
        fh.write(render(total, days))


if __name__ == "__main__":
    main()
