"""
git_inbox.py — Open Issues & PRs Inbox

Lists every open issue and pull request across the repositories you own,
oldest first, so nothing waiting on you gets forgotten. Uses the search API,
so it's one request per 100 items instead of one per repo. Read-only.

Usage:
    python git_inbox.py                 # all open issues and PRs, oldest first
    python git_inbox.py --prs           # only pull requests
    python git_inbox.py --issues        # only issues
    python git_inbox.py --min-age 30    # only items open for 30+ days
    python git_inbox.py --json          # full list as JSON, for piping
"""
import argparse
import json
import sys
from datetime import datetime, timezone

from git_langs import TOKEN, USERNAME, api_request

SEARCH_LIMIT = 1000  # GitHub search returns at most 1000 results


def fetch_open(username, kind=None):
    """Raw search results for open items in repos owned by `username`, oldest first."""
    q = f"user:{username}+is:open" + (f"+is:{kind}" if kind else "")
    items, page = [], 1
    while len(items) < SEARCH_LIMIT:
        data = api_request(f"https://api.github.com/search/issues?q={q}&sort=created&order=asc"
                           f"&per_page=100&page={page}")
        if data is None:
            sys.exit(f"❌ GitHub user '{username}' not found.")
        items += data["items"]
        if len(data["items"]) < 100:
            break
        page += 1
    return items


def simplify(item, now):
    """Flatten a search result into the fields the report needs."""
    created = datetime.fromisoformat(item["created_at"].replace("Z", "+00:00"))
    return {
        "type": "pr" if "pull_request" in item else "issue",
        "repo": item["repository_url"].rsplit("/", 1)[-1],
        "number": item["number"],
        "title": item["title"],
        "author": item["user"]["login"],
        "age_days": (now - created).days,
        "comments": item["comments"],
        "url": item["html_url"],
    }


def print_section(label, rows):
    if not rows:
        return
    print(f"\n{label} ({len(rows)})")
    width = max(len(f"{r['repo']}#{r['number']}") for r in rows)
    for r in rows:
        title = r["title"] if len(r["title"]) <= 60 else r["title"][:57] + "..."
        print(f"   {r['age_days']:>4}d  {r['repo'] + '#' + str(r['number']):<{width}}  {title}  (@{r['author']})")


def main():
    parser = argparse.ArgumentParser(description="List open issues and PRs across your GitHub repos.")
    only = parser.add_mutually_exclusive_group()
    only.add_argument("--prs", action="store_true", help="only pull requests")
    only.add_argument("--issues", action="store_true", help="only issues")
    parser.add_argument("--min-age", type=int, default=0, help="only items open for at least N days")
    parser.add_argument("--json", action="store_true", help="print the list as JSON")
    args = parser.parse_args()

    if not USERNAME:
        sys.exit("❌ GITHUB_USERNAME is not set. Add it to your .env file.")
    if not TOKEN:
        print("⚠️  No GITHUB_TOKEN set — unauthenticated search is limited to 10 requests/minute.\n",
              file=sys.stderr if args.json else sys.stdout)

    kind = "pr" if args.prs else "issue" if args.issues else None
    now = datetime.now(timezone.utc)
    rows = [r for r in (simplify(i, now) for i in fetch_open(USERNAME, kind)) if r["age_days"] >= args.min_age]

    if args.json:
        print(json.dumps(rows, indent=2, ensure_ascii=False))
        return
    if not rows:
        print(f"📭 Inbox zero — no open {'items' if not kind else kind + 's'} in {USERNAME}'s repos.")
        return

    print(f"📬 Open items in {USERNAME}'s repos")
    print_section("🔀 Pull requests", [r for r in rows if r["type"] == "pr"])
    print_section("🐛 Issues", [r for r in rows if r["type"] == "issue"])
    oldest = rows[0]
    print(f"\n⏳ Oldest: {oldest['repo']}#{oldest['number']}, open {oldest['age_days']} days — {oldest['url']}")


if __name__ == "__main__":
    main()
