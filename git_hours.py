"""
git_hours.py — Coding Hours Heatmap

Fetches every commit you authored in your public repositories over the last
N months, converts the timestamps to your timezone, and prints a weekday x hour
heatmap plus a short summary (peak hour, busiest day, night owl score).

Usage:
    python git_hours.py                       # last 12 months, system timezone
    python git_hours.py --tz Asia/Kathmandu   # any IANA timezone name
    python git_hours.py --months 6            # shorter lookback window
    python git_hours.py --include-forks       # also count forked repos

This tool makes one request per 100 commits per repo, so a GITHUB_TOKEN is
strongly recommended (5,000 requests/hour instead of 60).
"""
import argparse
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from git_langs import TOKEN, USERNAME, api_request, get_repos

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
FULL_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
SHADES = "░▒▓█"
NIGHT_HOURS = {22, 23, 0, 1, 2, 3}  # 22:00–04:00


def get_commit_times(owner, repo_name, username, since):
    """Return UTC datetimes of commits authored by `username` since `since`."""
    times = []
    page = 1
    while True:
        url = (f"https://api.github.com/repos/{owner}/{repo_name}/commits"
               f"?author={username}&since={since}&per_page=100&page={page}")
        commits = api_request(url)  # None on 409 (empty repo) or 404
        if not commits:
            break
        for c in commits:
            times.append(datetime.fromisoformat(c["commit"]["author"]["date"].replace("Z", "+00:00")))
        page += 1
    return times


def build_grid(times, tz):
    """Count commits per (weekday, hour) in `tz` (None = system local time)."""
    grid = Counter()
    for t in times:
        local = t.astimezone(tz)
        grid[local.weekday(), local.hour] += 1
    return grid


def shade(n, peak):
    if n == 0:
        return " "
    return SHADES[-(-4 * n // peak) - 1]  # ceil(4n/peak) -> 1..4


def render_heatmap(grid):
    # One column per hour; labels every 3 hours are 3 chars wide, so "00" sits over hour 0, "03" over hour 3, ...
    peak = max(grid.values())
    lines = ["      " + "".join(f"{h:02d} " for h in range(0, 24, 3)).rstrip()]
    for d, day in enumerate(DAYS):
        lines.append(f"{day:<6}" + "".join(shade(grid[d, h], peak) for h in range(24)).rstrip())
    return "\n".join(lines)


def print_summary(grid):
    total = sum(grid.values())
    hours = Counter()
    days = Counter()
    for (d, h), n in grid.items():
        hours[h] += n
        days[d] += n
    peak_hour, peak_hour_n = hours.most_common(1)[0]
    peak_day, peak_day_n = days.most_common(1)[0]
    night = sum(hours[h] for h in NIGHT_HOURS)

    print(f"\n📈 {total} commits analyzed")
    print(f"⏰ Peak hour: {peak_hour:02d}:00–{(peak_hour + 1) % 24:02d}:00 ({peak_hour_n} commits)")
    print(f"📅 Busiest day: {FULL_DAYS[peak_day]} ({peak_day_n} commits)")
    print(f"🦉 Night owl score: {night / total:.0%} of commits between 22:00 and 04:00")


def main():
    parser = argparse.ArgumentParser(description="Show a weekday x hour heatmap of your GitHub commits.")
    parser.add_argument("--tz", help="IANA timezone name, e.g. Asia/Kathmandu (default: system timezone)")
    parser.add_argument("--months", type=int, default=12, help="lookback window in months (default: 12)")
    parser.add_argument("--include-forks", action="store_true", help="include forked repos")
    args = parser.parse_args()

    if not USERNAME:
        sys.exit("❌ GITHUB_USERNAME is not set. Add it to your .env file.")
    if args.months < 1:
        sys.exit("❌ --months must be at least 1.")
    try:
        tz = ZoneInfo(args.tz) if args.tz else None
    except (ZoneInfoNotFoundError, ValueError):
        sys.exit(f"❌ Unknown timezone '{args.tz}'. Use an IANA name like Asia/Kathmandu "
                 "(on Windows, `pip install tzdata` if valid names aren't found).")
    tz_label = args.tz or datetime.now().astimezone().tzname()

    if not TOKEN:
        print("⚠️  No GITHUB_TOKEN set — unauthenticated requests are limited to 60/hour.")
        print("   This tool makes many requests; adding a token to .env is strongly recommended.\n")

    since = (datetime.now(timezone.utc) - timedelta(days=args.months * 365 / 12)).strftime("%Y-%m-%dT%H:%M:%SZ")
    times = []
    for repo in get_repos(USERNAME, args.include_forks):
        print(f"Checking {repo['name']}...")
        times += get_commit_times(repo["owner"]["login"], repo["name"], USERNAME, since)

    if not times:
        print(f"\nNo commits by {USERNAME} found in the last {args.months} months.")
        return

    grid = build_grid(times, tz)
    print(f"\n🕒 Commit heatmap (last {args.months} months, {tz_label})\n")
    print(render_heatmap(grid))
    print_summary(grid)


if __name__ == "__main__":
    main()
