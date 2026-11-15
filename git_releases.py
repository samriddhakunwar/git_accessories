"""
git_releases.py — Unreleased Changes

For each of your public repositories with a release, shows the latest release,
how long ago it was published and how many commits the default branch is ahead
of it, so you can see which projects are overdue for a new release. Read-only.

Usage:
    python git_releases.py                  # repos with releases, most unreleased commits first
    python git_releases.py --include-forks  # also check forked repos
    python git_releases.py --json           # full results as JSON, for piping
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from urllib.parse import quote

from git_langs import TOKEN, USERNAME, api_request, get_repos


def check_repo(repo, now):
    """Latest release info and commits since it, or None if the repo has no releases."""
    base = f"https://api.github.com/repos/{repo['owner']['login']}/{repo['name']}"
    release = api_request(f"{base}/releases/latest")  # 404 -> None: no releases
    if not release:
        return None
    published = datetime.fromisoformat(release["published_at"].replace("Z", "+00:00"))
    diff = api_request(f"{base}/compare/{quote(release['tag_name'], safe='')}...{quote(repo['default_branch'])}")
    return {
        "repo": repo["name"],
        "tag": release["tag_name"],
        "days_ago": (now - published).days,
        "unreleased_commits": diff["ahead_by"] if diff else None,  # None: tag missing or unreachable
        "url": release["html_url"],
    }


def main():
    parser = argparse.ArgumentParser(description="Show commits since the latest release of each of your repos.")
    parser.add_argument("--include-forks", action="store_true", help="include forked repos")
    parser.add_argument("--json", action="store_true", help="print results as JSON")
    args = parser.parse_args()
    log = sys.stderr if args.json else sys.stdout  # keep stdout pure JSON when piping

    if not USERNAME:
        sys.exit("❌ GITHUB_USERNAME is not set. Add it to your .env file.")
    if not TOKEN:
        print("⚠️  No GITHUB_TOKEN set — unauthenticated requests are limited to 60/hour.\n", file=log)

    now = datetime.now(timezone.utc)
    repos = get_repos(USERNAME, args.include_forks)
    rows = []
    for repo in repos:
        print(f"Checking {repo['name']}...", file=log)
        if repo["size"] and (row := check_repo(repo, now)):
            rows.append(row)
    rows.sort(key=lambda r: -(r["unreleased_commits"] or 0))

    if args.json:
        print(json.dumps(rows, indent=2, ensure_ascii=False))
        return
    if not rows:
        print(f"\nNone of {USERNAME}'s {len(repos)} repos have a release yet.")
        return

    print(f"\n🏷️  Releases for {USERNAME} ({len(rows)} of {len(repos)} repos have one)\n")
    name_w = max(len(r["repo"]) for r in rows)
    tag_w = max(len(r["tag"]) for r in rows)
    print(f"{'Repo':<{name_w}}  {'Latest':<{tag_w}}  {'Released':>9}  Unreleased")
    for r in rows:
        ahead = "?" if r["unreleased_commits"] is None else r["unreleased_commits"] or "✓ up to date"
        print(f"{r['repo']:<{name_w}}  {r['tag']:<{tag_w}}  {str(r['days_ago']) + 'd ago':>9}  {ahead}")

    due = [r for r in rows if r["unreleased_commits"]]
    if due:
        print(f"\n💡 {len(due)} repo{'s' if len(due) > 1 else ''} with unreleased commits — "
              f"{due[0]['repo']} leads with {due[0]['unreleased_commits']}.")


if __name__ == "__main__":
    main()
