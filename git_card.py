"""
git_card.py — Commit Counter

Counts the commits you authored across your public repositories over the last
N months, and lists the repos you committed to most.

Usage:
    python git_card.py                  # last 12 months, top 5 repos
    python git_card.py --months 3       # shorter lookback window
    python git_card.py --top 10         # show more repos in the breakdown
    python git_card.py --include-forks  # also count forked repos
"""
import argparse
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone

from git_langs import TOKEN, USERNAME, api_request, get_repos


def count_commits(owner, repo_name, username, since):
    """Number of commits authored by `username` in the repo since `since`."""
    count, page = 0, 1
    while True:
        commits = api_request(f"https://api.github.com/repos/{owner}/{repo_name}/commits"
                              f"?author={username}&since={since}&per_page=100&page={page}")
        count += len(commits or [])
        if not commits or len(commits) < 100:
            return count
        page += 1


def main():
    parser = argparse.ArgumentParser(description="Count your commits across your public GitHub repos.")
    parser.add_argument("--months", type=int, default=12, help="lookback window in months (default: 12)")
    parser.add_argument("--top", type=int, default=5, help="repos to show in the breakdown (default: 5, 0 = none)")
    parser.add_argument("--include-forks", action="store_true", help="include forked repos")
    args = parser.parse_args()

    if not USERNAME:
        sys.exit("❌ GITHUB_USERNAME is not set. Add it to your .env file.")
    if args.months < 1:
        sys.exit("❌ --months must be at least 1.")
    if not TOKEN:
        print("⚠️  No GITHUB_TOKEN set — unauthenticated requests are limited to 60/hour.\n")

    since = (datetime.now(timezone.utc) - timedelta(days=args.months * 365 / 12)).strftime("%Y-%m-%dT%H:%M:%SZ")
    per_repo = Counter()
    for repo in get_repos(USERNAME, args.include_forks):
        print(f"Checking {repo['name']}...")
        per_repo[repo["name"]] = count_commits(repo["owner"]["login"], repo["name"], USERNAME, since)

    total = sum(per_repo.values())
    print(f"\n🔥 Total commits in last {args.months} months: {total}")
    top = [(name, n) for name, n in per_repo.most_common(args.top) if n]
    if top:
        print("\n🏆 Most active repos:")
        width = max(len(name) for name, _ in top)
        for name, n in top:
            print(f"   {name:<{width}}  {n:>5}  ({n / total:.0%})")


if __name__ == "__main__":
    main()
