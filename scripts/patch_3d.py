#!/usr/bin/env python3
"""Rework the 3D contribution SVG so it reflects private work too.

GitHub's API reports private contributions only as an opaque "restricted" count, so the upstream
action sees public commits alone. This recounts commits per repository (public and private) from
each default branch, then rebuilds the language donut, fixes the radar's Commit/Repo axes and
replaces the stars/forks footer with commit, pull request, review and issue totals.
"""
import json
import math
import os
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET

NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", NS)
Q = lambda tag: f"{{{NS}}}{tag}"

WIDTH, HEIGHT = 1280, 850
PIE_HEIGHT = 200 * 1.3
RADAR_HEIGHT = (400 * 1.3) * 3 / 4
OTHER_COLOR = "#444444"

QUERY = """query($login: String!, $since: GitTimestamp!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar { totalContributions }
      totalPullRequestContributions totalPullRequestReviewContributions totalIssueContributions
      totalRepositoryContributions
    }
    repositories(first: 100, ownerAffiliations: [OWNER, COLLABORATOR, ORGANIZATION_MEMBER], isFork: false) {
      nodes {
        nameWithOwner createdAt isPrivate owner { login }
        primaryLanguage { name color }
        defaultBranchRef { target { ... on Commit { history(since: $since, author: {id: "%s"}) { totalCount } } } }
      }
    }
  }
}"""


def graphql(query, variables, token):
    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        body = json.loads(response.read())
    if body.get("errors"):
        sys.exit(f"GraphQL error: {body['errors']}")
    return body["data"]


def collect(login, token, since):
    user_id = graphql("query($l: String!) { user(login: $l) { id } }", {"l": login}, token)["user"]["id"]
    user = graphql(QUERY % user_id, {"login": login, "since": f"{since}T00:00:00Z"}, token)["user"]
    contrib = user["contributionsCollection"]
    languages, history_total, private_repos = {}, 0, 0
    for repo in user["repositories"]["nodes"]:
        if repo["isPrivate"] and repo["owner"]["login"].lower() == login.lower() and repo["createdAt"][:10] >= since:
            private_repos += 1
        target = (repo.get("defaultBranchRef") or {}).get("target") or {}
        count = (target.get("history") or {}).get("totalCount", 0)
        lang = repo.get("primaryLanguage")
        if count and lang:
            history_total += count
            entry = languages.setdefault(lang["name"], {"color": lang["color"] or OTHER_COLOR, "count": 0})
            entry["count"] += count

    # Keep every number consistent with the calendar total: commits are whatever is left after the
    # countable non-commit contributions; branch history only provides the per-language split.
    repos = contrib["totalRepositoryContributions"] + private_repos
    pulls, reviews, issues = (contrib["totalPullRequestContributions"],
                              contrib["totalPullRequestReviewContributions"], contrib["totalIssueContributions"])
    commits = max(0, contrib["contributionCalendar"]["totalContributions"] - repos - pulls - reviews - issues)
    scale = commits / history_total if history_total else 0
    ranked = sorted(languages.items(), key=lambda kv: -kv[1]["count"])
    return {
        "commits": commits, "repos": repos, "pulls": pulls, "reviews": reviews, "issues": issues,
        "languages": [(name, info["color"], round(info["count"] * scale)) for name, info in ranked
                      if round(info["count"] * scale) > 0],
    }


def fmt(value):
    return f"{value:.2f}".rstrip("0").rstrip(".")


def opacity_steps(index, n):
    return ";".join(fmt(0 if i < index else min((i - index) / 5, 1)) for i in range(n + 5))


def rebuild_pie(group, stats):
    languages = stats["languages"][:5]
    other = stats["commits"] - sum(c for _, _, c in languages)
    if other > 0:
        languages.append(("other", OTHER_COLOR, other))
    total = sum(c for _, _, c in languages) or 1
    for child in list(group):
        group.remove(child)

    radius = PIE_HEIGHT / 2
    margin = radius / 10
    row = 8
    offset = (row - len(languages)) / 2 + 0.5
    font = PIE_HEIGHT / row / 1.5
    n = len(languages)

    labels = ET.SubElement(group, Q("g"), transform=f"translate({fmt(radius * 2.1)}, 0)")
    for i, (name, color, _) in enumerate(languages):
        y = (i + offset) * (PIE_HEIGHT / row)
        rect = ET.SubElement(labels, Q("rect"), x="0", y=fmt(y - font / 2), width=fmt(font), height=fmt(font),
                             fill=color, **{"class": "stroke-bg", "stroke-width": "1px"})
        ET.SubElement(rect, Q("animate"), attributeName="fill-opacity", values=opacity_steps(i, n), dur="3s", repeatCount="1")
        text = ET.SubElement(labels, Q("text"), x=fmt(font * 1.2), y=fmt(y),
                             **{"dominant-baseline": "middle", "class": "fill-fg", "font-size": f"{fmt(font)}px"})
        text.text = name
        ET.SubElement(text, Q("animate"), attributeName="fill-opacity", values=opacity_steps(i, n), dur="3s", repeatCount="1")

    outer, inner = radius - margin, radius / 2
    pie = ET.SubElement(group, Q("g"), transform=f"translate({fmt(radius)}, {fmt(radius)})")
    start = 0.0
    for i, (name, color, count) in enumerate(languages):
        end = start + 2 * math.pi * count / total
        path = ET.SubElement(pie, Q("path"), d=arc(start, min(end, start + 2 * math.pi - 1e-4), inner, outer),
                             style=f"fill: {color};", **{"class": "stroke-bg", "stroke-width": "2px"})
        title = ET.SubElement(path, Q("title"))
        title.text = f"{name} {count}"
        ET.SubElement(path, Q("animate"), attributeName="fill-opacity", values=opacity_steps(i, n), dur="3s", repeatCount="1")
        start = end


def arc(a0, a1, r0, r1):
    point = lambda r, a: f"{fmt(r * math.sin(a))},{fmt(-r * math.cos(a))}"
    large = 1 if a1 - a0 > math.pi else 0
    return (f"M{point(r1, a0)}A{fmt(r1)},{fmt(r1)},0,{large},1,{point(r1, a1)}"
            f"L{point(r0, a1)}A{fmt(r0)},{fmt(r0)},0,{large},0,{point(r0, a0)}Z")


def radar_level(value):
    return 0.8 if value < 1 else min(math.log10(value), 5) + 1


def fix_radar(root, stats):
    radius = (RADAR_HEIGHT / 2) * 0.8
    values = {0: stats["commits"], 4: stats["repos"]}
    polygon = root.find(f".//{Q('polygon')}[@class='radar']")
    points = polygon.get("points").split()
    for index, value in values.items():
        level = radar_level(value)
        angle = index / 5 * 2 * math.pi
        x = radius * (level / 5) * math.sin(angle)
        y = radius * (level / 5) * -math.cos(angle)
        points[index] = f"{fmt(x)},{fmt(y)}"
    polygon.set("points", " ".join(points))
    animate = polygon.find(Q("animate"))
    if animate is not None:
        animate.set("values", animate.get("values").split(";")[0] + ";" + polygon.get("points"))
    for text in root.iter(Q("text")):
        title = text.find(Q("title"))
        if title is not None and text.text in ("Commit", "Repo"):
            title.text = str(stats["commits"] if text.text == "Commit" else stats["repos"])


def replace_footer(root, stats):
    for group in root.iter(Q("g")):
        strong = [t for t in group.findall(Q("text")) if t.get("class") == "fill-strong"]
        if not strong:
            continue
        total = strong[0].text
        keep = [c for c in group if c.tag == Q("text") and "16px" in (c.get("style") or "")]
        for child in list(group):
            if child not in keep:
                group.remove(child)
        items = [(stats["commits"], "commits"), (stats["pulls"], "pull requests"),
                 (stats["reviews"], "reviews"), (stats["issues"], "issues")]
        parts = [f'<tspan class="fill-strong" style="font-size: 30px; font-weight: bold;">{total}</tspan>',
                 '<tspan class="fill-fg" dx="8">contributions</tspan>']
        for value, label in items:
            parts += ['<tspan class="fill-weak" dx="18">//</tspan>',
                      f'<tspan class="fill-fg" dx="18" style="font-size: 26px; font-weight: bold;">{value:,}</tspan>',
                      f'<tspan class="fill-weak" dx="8">{label}</tspan>']
        footer = ET.fromstring(f'<text xmlns="{NS}" x="{WIDTH // 2}" y="{HEIGHT - 20}" text-anchor="middle" '
                               f'style="font-size: 20px;">{"".join(parts)}</text>')
        group.insert(0, footer)
        return
    sys.exit("footer not found; the upstream SVG layout may have changed")


def main():
    path = sys.argv[1]
    root = ET.parse(path).getroot()
    period = next(t.text for t in root.iter(Q("text")) if t.text and re.match(r"\d{4}-\d\d-\d\d / ", t.text))
    stats = collect(os.environ.get("USERNAME", "PAXdot"), os.environ["GITHUB_TOKEN"], period[:10])

    pie_y = HEIGHT - PIE_HEIGHT - 70
    pie = next(g for g in root.iter(Q("g")) if g.get("transform") == f"translate(40, {fmt(pie_y)})")
    rebuild_pie(pie, stats)
    fix_radar(root, stats)
    replace_footer(root, stats)
    ET.ElementTree(root).write(path, encoding="unicode")
    print(json.dumps({k: v for k, v in stats.items() if k != "languages"}), stats["languages"][:6])


if __name__ == "__main__":
    main()
