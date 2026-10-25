"""
git_banner.py — Profile Stats SVG Card

Fetches your GitHub stats (stars, forks, repos, followers, top languages, most
starred repo and, with a token, last-year contributions and current streak) and
writes a self-contained SVG card you can embed in your profile README.

Usage:
    python git_banner.py                     # writes banner.svg, dark theme
    python git_banner.py --theme light       # light theme
    python git_banner.py --output card.svg   # custom output path
    python git_banner.py --no-animation      # disable the fade-in

GITHUB_USERNAME (required) and GITHUB_TOKEN (optional) are read from .env or the
environment. Contributions and streak need the token (GraphQL rejects anonymous
requests); without it they are left off the card.
"""
import argparse
import sys
from collections import Counter
from datetime import datetime, timedelta
from xml.sax.saxutils import escape

from git_langs import TOKEN, USERNAME, api_request, get_languages, get_repos
from git_streak import current_streak, fetch_calendar

THEMES = {
    "dark": {"bg": "#0d1117", "border": "#30363d", "title": "#58a6ff", "text": "#c9d1d9",
             "icon": "#8b949e", "track": "#30363d"},
    "light": {"bg": "#ffffff", "border": "#d0d7de", "title": "#0969da", "text": "#24292f",
              "icon": "#57606a", "track": "#eaeef2"},
}

LANG_COLORS = {
    "Python": "#3572A5", "JavaScript": "#f1e05a", "TypeScript": "#3178c6", "HTML": "#e34c26",
    "CSS": "#663399", "SCSS": "#c6538c", "Java": "#b07219", "Kotlin": "#A97BFF", "C": "#555555",
    "C++": "#f34b7d", "C#": "#178600", "Go": "#00ADD8", "Rust": "#dea584", "Ruby": "#701516",
    "PHP": "#4F5D95", "Shell": "#89e051", "Swift": "#F05138", "Dart": "#00B4AB", "Vue": "#41b883",
    "Jupyter Notebook": "#DA5B0B",
}
FALLBACK_COLOR = "#8b949e"

# 16x16 stroked icons (simple paths, no external images)
ICONS = {
    "stars": '<path d="M8 1l2 5h5l-4 3.5 1.5 5.5L8 11.5 3.5 15 5 9.5 1 6h5z"/>',
    "forks": '<circle cx="4" cy="3" r="2"/><circle cx="12" cy="3" r="2"/><circle cx="8" cy="13" r="2"/>'
             '<path d="M4 5v1a2 2 0 0 0 2 2h4a2 2 0 0 0 2-2V5M8 8v3"/>',
    "repos": '<path d="M3 2h9v12H5a2 2 0 0 1-2-2zM3 12a2 2 0 0 1 2-2h7"/>',
    "followers": '<circle cx="8" cy="5" r="3"/><path d="M2 15a6 6 0 0 1 12 0"/>',
    "contributions": '<rect x="2" y="3" width="12" height="11" rx="1"/><path d="M2 7h12M5 1v3M11 1v3"/>',
    "streak": '<path d="M8 1c1 3 5 5 5 9a5 5 0 0 1-10 0c0-2 1-3 2-4 0 2 1 3 2 3 0-3-1-5 1-8z"/>',
    "top_repo": '<path d="M4 1h8v14l-4-3-4 3z"/>',
}

WIDTH, PAD, ROW_H = 495, 25, 24


def compact(n):
    """1234 -> '1.2k', 2500000 -> '2.5M'; small numbers unchanged."""
    for div, suffix in ((1_000_000_000, "B"), (1_000_000, "M"), (1_000, "k")):
        if n >= div:
            return f"{n / div:.1f}".rstrip("0").rstrip(".") + suffix
    return str(n)


def try_fetch(label, fn, *args):
    """Run a fetch; on failure (the shared helpers sys.exit with a message) warn and return None."""
    try:
        return fn(*args)
    except SystemExit as e:
        print(f"⚠️  Couldn't fetch {label}: {e} — leaving it off the card.", file=sys.stderr)
        return None


def fetch_user(username):
    user = api_request(f"https://api.github.com/users/{username}")
    if user is None:
        sys.exit(f"❌ GitHub user '{username}' not found.")
    return user


def fetch_repos(username):
    return get_repos(username)  # non-fork public repos


def fetch_languages(repos):
    totals = Counter()
    for repo in repos:
        print(f"Checking {repo['name']}...")
        totals.update(get_languages(repo["owner"]["login"], repo["name"]))
    return totals


def fetch_contributions(username):
    """Return (total contributions in the last year, current streak in days)."""
    tz = datetime.now().astimezone().tzinfo
    today = datetime.now(tz).date()
    days = fetch_calendar(username, today - timedelta(days=364), today, tz)
    return sum(n for _, n in days), current_streak(days, today)[0]


def build_svg(stats, theme="dark", animate=True):
    """Render the card. `stats` is a plain dict; any missing key is simply left off."""
    t = THEMES[theme]
    items = [(key, label, compact(stats[key])) for key, label in (
        ("stars", "Total stars"), ("forks", "Total forks"), ("repos", "Public repos"),
        ("followers", "Followers"), ("contributions", "Contributions (1y)")) if stats.get(key) is not None]
    if stats.get("streak") is not None:
        items.append(("streak", "Current streak", f"{stats['streak']} day{'' if stats['streak'] == 1 else 's'}"))
    if stats.get("top_repo"):
        name, stars = stats["top_repo"]
        name = name if len(name) <= 20 else name[:19] + "…"
        items.append(("top_repo", f"Top: {name}", f"★ {compact(stars)}"))

    col_w = (WIDTH - 2 * PAD) / 2
    parts = []
    for i, (key, label, value) in enumerate(items):
        x, y = PAD + (i % 2) * (col_w + 10), 58 + (i // 2) * ROW_H
        parts.append(
            f'<g class="fade" style="animation-delay:{i * 80}ms" transform="translate({x:.0f},{y})">'
            f'<g transform="translate(0,-12)" fill="none" stroke="{t["icon"]}" stroke-width="1.4" '
            f'stroke-linejoin="round">{ICONS[key]}</g>'
            f'<text x="24" class="label">{escape(label)}</text>'
            f'<text x="{col_w - 10:.0f}" class="value" text-anchor="end">{escape(value)}</text></g>')
    y = 58 + max(len(items) - 1, 0) // 2 * ROW_H + (ROW_H if items else 0)

    langs = [(lang, n) for lang, n in (stats.get("languages") or []) if n > 0][:5]
    total = sum(n for _, n in langs)
    if total:
        bar_w, slot = WIDTH - 2 * PAD, (WIDTH - 2 * PAD) / len(langs)
        x, segs, legend = PAD, [], []
        for i, (lang, n) in enumerate(langs):
            color, w = LANG_COLORS.get(lang, FALLBACK_COLOR), n / total * bar_w
            segs.append(f'<rect x="{x:.1f}" y="{y}" width="{w:.1f}" height="8" fill="{color}"/>')
            x += w
            name = lang if len(lang) <= 11 else lang[:10] + "…"
            lx = PAD + i * slot
            legend.append(f'<circle cx="{lx + 5:.1f}" cy="{y + 25}" r="5" fill="{color}"/>'
                          f'<text x="{lx + 14:.1f}" y="{y + 29}" class="lang">{escape(name)} {n / total:.0%}</text>')
        parts.append(f'<g class="fade" style="animation-delay:{len(items) * 80}ms">'
                     f'<clipPath id="bar"><rect x="{PAD}" y="{y}" width="{bar_w}" height="8" rx="4"/></clipPath>'
                     f'<rect x="{PAD}" y="{y}" width="{bar_w}" height="8" rx="4" fill="{t["track"]}"/>'
                     f'<g clip-path="url(#bar)">{"".join(segs)}</g>{"".join(legend)}</g>')
        y += 42
    height = max(y + 8, 90)

    fade = (".fade { opacity: 0; animation: fade 0.6s ease-in-out forwards; }\n"
            "  @keyframes fade { to { opacity: 1; } }") if animate else ""
    font = "-apple-system, 'Segoe UI', Helvetica, Arial, sans-serif"
    title = escape(f"{stats.get('username', '')}'s GitHub Stats")
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" viewBox="0 0 {WIDTH} {height}" role="img" aria-label="{title}">
<title>{title}</title>
<style>
  text {{ font-family: {font}; fill: {t["text"]}; }}
  .title {{ font-size: 18px; font-weight: 600; fill: {t["title"]}; }}
  .label {{ font-size: 13px; }}
  .value {{ font-size: 13px; font-weight: 600; }}
  .lang {{ font-size: 10px; }}
  {fade}
</style>
<rect x="0.5" y="0.5" width="{WIDTH - 1}" height="{height - 1}" rx="6" fill="{t["bg"]}" stroke="{t["border"]}"/>
<text x="{PAD}" y="32" class="title">{title}</text>
{chr(10).join(parts)}
</svg>
"""


def main():
    parser = argparse.ArgumentParser(description="Generate a GitHub profile stats SVG card.")
    parser.add_argument("--output", default="banner.svg", help="output file (default: banner.svg)")
    parser.add_argument("--theme", choices=THEMES, default="dark", help="color theme (default: dark)")
    parser.add_argument("--no-animation", action="store_true", help="disable the fade-in animation")
    args = parser.parse_args()

    if not USERNAME:
        sys.exit("❌ GITHUB_USERNAME is not set. Add it to your .env file or environment.")
    if not TOKEN:
        print("ℹ️  No GITHUB_TOKEN set — contributions and streak will be left off the card "
              "(GraphQL needs a token), and requests are limited to 60/hour.\n")

    user = fetch_user(USERNAME)
    stats = {"username": user.get("login", USERNAME), "followers": user.get("followers")}

    repos = try_fetch("repositories", fetch_repos, USERNAME)
    if repos is not None:
        stats["repos"] = len(repos)
        stats["stars"] = sum(r["stargazers_count"] for r in repos)
        stats["forks"] = sum(r["forks_count"] for r in repos)
        top = max(repos, key=lambda r: r["stargazers_count"], default=None)
        if top and top["stargazers_count"]:
            stats["top_repo"] = (top["name"], top["stargazers_count"])
        langs = try_fetch("languages", fetch_languages, repos)
        if langs:
            stats["languages"] = langs.most_common(5)

    if TOKEN:
        contrib = try_fetch("contributions", fetch_contributions, USERNAME)
        if contrib:
            stats["contributions"], stats["streak"] = contrib

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(build_svg(stats, args.theme, animate=not args.no_animation))
    print(f"\n✅ Saved {args.output} ({args.theme} theme)\n")
    print(f"Add this to your profile README:\n![My GitHub stats](./{args.output})")


if __name__ == "__main__":
    main()
