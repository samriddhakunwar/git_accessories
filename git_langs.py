"""
git_langs.py — Language Breakdown

Fetches all public repositories for GITHUB_USERNAME (from .env), sums the
bytes of code per language reported by GitHub, and prints a sorted ASCII
bar chart of the top languages.

Usage:
    python git_langs.py                  # top 8 languages, forks skipped
    python git_langs.py --top 5          # show top 5, group the rest as "Other"
    python git_langs.py --include-forks  # also count forked repos
"""
import argparse
import os
import sys
from collections import Counter
from datetime import datetime

import requests
from dotenv import load_dotenv

load_dotenv()  # loads variables from .env into environment

USERNAME = os.getenv("GITHUB_USERNAME")
TOKEN = os.getenv("GITHUB_TOKEN")

headers = {"Authorization": f"token {TOKEN}"} if TOKEN else {}

BAR_WIDTH = 25


def exit_on_auth_or_rate_limit(res):
    """Exit with a clear message on a rejected token (401) or a rate limit (prints reset time in local time)."""
    if res.status_code == 401:
        sys.exit("❌ GitHub rejected GITHUB_TOKEN (401): it is invalid or expired. Generate a new one and update .env.")
    if res.status_code in (403, 429) or (res.headers.get("X-RateLimit-Remaining") == "0" and not res.ok):
        reset = res.headers.get("X-RateLimit-Reset")
        when = datetime.fromtimestamp(int(reset)).strftime("%Y-%m-%d %H:%M:%S") if reset else "unknown"
        sys.exit(f"⏳ GitHub API rate limit hit. Resets at {when} (local time).")


def api_request(url, payload=None):
    """GET a GitHub API URL (or POST `payload` as JSON). Returns parsed JSON, or None on 404/409 (missing/empty repo).
    Exits on bad token, rate limit and network errors."""
    try:
        if payload is None:
            res = requests.get(url, headers=headers, timeout=15)
        else:
            res = requests.post(url, headers=headers, json=payload, timeout=30)
    except requests.RequestException as e:
        sys.exit(f"❌ Network error: {e}")

    exit_on_auth_or_rate_limit(res)
    if res.status_code in (404, 409):
        return None
    if not res.ok:
        sys.exit(f"❌ GitHub API error {res.status_code}: {res.text[:200]}")
    return res.json()


def get_repos(username, include_forks=False):
    repos = []
    page = 1
    while True:
        data = api_request(f"https://api.github.com/users/{username}/repos?per_page=100&page={page}")
        if data is None:
            sys.exit(f"❌ GitHub user '{username}' not found.")
        if not data:
            break
        repos.extend(data)
        page += 1

    return [r for r in repos if include_forks or not r["fork"]]


def get_languages(owner, repo_name):
    # Empty repos return {}; a vanished repo returns 404 -> treat as no languages
    return api_request(f"https://api.github.com/repos/{owner}/{repo_name}/languages") or {}


def render_chart(totals, top):
    grand_total = sum(totals.values())
    rows = totals.most_common(top)
    other = grand_total - sum(n for _, n in rows)
    if other > 0:
        rows.append(("Other", other))

    lines = []
    for lang, n in rows:
        pct = n / grand_total * 100
        filled = round(pct / 100 * BAR_WIDTH)
        bar = "█" * filled + "░" * (BAR_WIDTH - filled)
        lines.append(f"{lang:<12} {bar} {pct:5.1f}%")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Show language breakdown across your public GitHub repos.")
    parser.add_argument("--top", type=int, default=8, help="number of languages to show (default: 8)")
    parser.add_argument("--include-forks", action="store_true", help="include forked repos")
    args = parser.parse_args()

    if not USERNAME:
        sys.exit("❌ GITHUB_USERNAME is not set. Add it to your .env file.")
    if args.top < 1:
        sys.exit("❌ --top must be at least 1.")
    if not TOKEN:
        print("⚠️  No GITHUB_TOKEN set — unauthenticated requests are limited to 60/hour.\n")

    repos = get_repos(USERNAME, args.include_forks)
    totals = Counter()

    for repo in repos:
        repo_name = repo["name"]
        print(f"Checking {repo_name}...")
        totals.update(get_languages(repo["owner"]["login"], repo_name))

    if not totals:
        print(f"\nNo language data found across {len(repos)} repos.")
        return

    print(f"\n📊 Language breakdown across {len(repos)} repos:\n")
    print(render_chart(totals, args.top))


if __name__ == "__main__":
    main()
