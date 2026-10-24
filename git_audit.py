"""
git_audit.py — Repo Health Audit

Checks each of your public repositories for common gaps (stale, no README,
no description, no license, no topics, missing homepage for websites, empty)
and gives it a health score out of 100. Read-only: it never modifies a repo.

Usage:
    python git_audit.py                     # table sorted by score, lowest first
    python git_audit.py --stale-months 12   # only flag repos untouched for a year
    python git_audit.py --min-score 80      # only show repos scoring below 80
    python git_audit.py --json              # full results as JSON, for piping
    python git_audit.py --include-forks --include-archived
"""
import argparse
import json
import sys
from datetime import datetime, timezone

import requests

from git_langs import TOKEN, USERNAME, exit_on_auth_or_rate_limit, get_repos, headers

# Points subtracted per failed check. Order here is the order issues are listed in.
WEIGHTS = {
    "empty": 50,
    "stale": 15,
    "no_readme": 25,
    "no_description": 20,
    "no_license": 15,
    "no_topics": 10,
    "no_homepage": 10,
}
FIXES = {
    "empty": "push some code to",
    "stale": "push an update to",
    "no_readme": "add a README to",
    "no_description": "add a description to",
    "no_license": "add a license to",
    "no_topics": "add topics to",
    "no_homepage": "add a homepage URL to",
}
WEB_LANGUAGES = {"HTML", "CSS", "JavaScript", "TypeScript"}
WEB_NAME_HINTS = ("portfolio", "site", "web")
NAME_WIDTH = 22


def has_readme(owner, repo_name):
    """True/False if the README exists/is missing; None if the check failed for another reason."""
    try:
        res = requests.get(f"https://api.github.com/repos/{owner}/{repo_name}/readme", headers=headers, timeout=15)
    except requests.RequestException:
        return None
    exit_on_auth_or_rate_limit(res)
    if res.status_code == 404:
        return False
    return True if res.ok else None


def audit_repo(repo, readme, stale_months, now):
    """Return a dict of check results. True = problem, False = fine, None = unknown (README only)."""
    pushed = datetime.fromisoformat((repo["pushed_at"] or repo["created_at"]).replace("Z", "+00:00"))
    age_days = (now - pushed).days
    looks_like_site = repo["language"] in WEB_LANGUAGES or any(h in repo["name"].lower() for h in WEB_NAME_HINTS)
    return {
        "empty": repo["size"] == 0,
        "stale": age_days > stale_months * 365 / 12,
        "no_readme": None if readme is None else not readme,
        "no_description": not (repo["description"] or "").strip(),
        "no_license": repo["license"] is None,
        "no_topics": not repo.get("topics"),
        "no_homepage": looks_like_site and not (repo["homepage"] or "").strip(),
        "age_days": age_days,
    }


def score_repo(checks):
    return max(0, 100 - sum(w for k, w in WEIGHTS.items() if checks[k] is True))


def format_age(days):
    return f"{days // 365}y" if days >= 365 else f"{days // 30}mo"


def describe_issues(checks):
    issues = []
    for k in WEIGHTS:
        if k == "stale" and checks[k]:
            issues.append(f"stale ({format_age(checks['age_days'])})")
        elif k == "no_readme" and checks[k] is None:
            issues.append("README unknown")
        elif checks[k]:
            issues.append(k.replace("_", " ").replace("readme", "README"))
    return ", ".join(issues) or "✓ all good"


def render_table(results):
    lines = ["Score  Repo" + " " * (NAME_WIDTH - 3) + "Issues"]
    for r in results:
        name = r["name"] if len(r["name"]) <= NAME_WIDTH else r["name"][:NAME_WIDTH - 1] + "…"
        lines.append(f"{r['score']:>3}    {name:<{NAME_WIDTH}} {r['issues']}")
    return "\n".join(lines)


def print_summary(results, stale_months):
    def count(k):
        n = sum(1 for r in results if r["checks"][k] is True)
        return f"{n} repo{'' if n == 1 else 's'}"

    print("\n📋 Summary")
    print(f"   Average health:   {round(sum(r['score'] for r in results) / len(results))} / 100")
    print(f"   Missing README:   {count('no_readme')}")
    print(f"   Missing license:  {count('no_license')}")
    print(f"   {f'Stale (>{stale_months} mo):':<18}{count('stale')}")

    # Quick win = the single fix that raises the summed score the most (respects the 0 floor)
    def gain(k):
        return sum(score_repo({**r["checks"], k: False}) - r["score"] for r in results)

    best = max(WEIGHTS, key=gain)
    if gain(best) > 0:
        print(f"\n💡 Quick win: {FIXES[best]} {count(best)} for +{WEIGHTS[best]} each")


def main():
    parser = argparse.ArgumentParser(description="Audit the health of your public GitHub repos (read-only).")
    parser.add_argument("--stale-months", type=int, default=6, help="flag repos not pushed in N months (default: 6)")
    parser.add_argument("--min-score", type=int, help="only show repos scoring below N")
    parser.add_argument("--json", action="store_true", help="print full results as JSON instead of a table")
    parser.add_argument("--include-forks", action="store_true", help="include forked repos")
    parser.add_argument("--include-archived", action="store_true", help="include archived repos")
    args = parser.parse_args()
    log = sys.stderr if args.json else sys.stdout  # keep stdout pure JSON when piping

    if not USERNAME:
        sys.exit("❌ GITHUB_USERNAME is not set. Add it to your .env file.")
    if args.stale_months < 1:
        sys.exit("❌ --stale-months must be at least 1.")
    if not TOKEN:
        print("⚠️  No GITHUB_TOKEN set — unauthenticated requests are limited to 60/hour.\n", file=log)

    repos = [r for r in get_repos(USERNAME, args.include_forks) if args.include_archived or not r["archived"]]
    if not repos:
        print(f"No repos to audit for {USERNAME} (forks/archived are skipped unless you pass the flags).", file=log)
        return

    now = datetime.now(timezone.utc)
    results = []
    for repo in repos:
        print(f"Checking {repo['name']}...", file=log)
        # Empty repos can't have a README, skip the request
        readme = False if repo["size"] == 0 else has_readme(repo["owner"]["login"], repo["name"])
        checks = audit_repo(repo, readme, args.stale_months, now)
        results.append({"name": repo["name"], "url": repo["html_url"], "score": score_repo(checks),
                        "issues": describe_issues(checks), "checks": checks})
    results.sort(key=lambda r: (r["score"], r["name"].lower()))
    shown = [r for r in results if args.min_score is None or r["score"] < args.min_score]

    if args.json:
        print(json.dumps(shown, indent=2, ensure_ascii=False))
        return

    print(f"\n🩺 Repo health audit for {USERNAME} ({len(results)} repos)\n")
    print(render_table(shown) if shown else f"No repos scoring below {args.min_score}. 🎉")
    print_summary(results, args.stale_months)


if __name__ == "__main__":
    main()
