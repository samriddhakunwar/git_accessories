"""
git_streak.py — Contribution Streak Tracker

Fetches your GitHub contribution calendar via the GraphQL API and prints your
current streak, longest streak, totals, best day and a strip of the last 30 days.

Usage:
    python git_streak.py                      # last year, system timezone
    python git_streak.py --years 3            # look back 3 years
    python git_streak.py --tz Asia/Kathmandu  # decide "today" in this IANA timezone

Requires GITHUB_TOKEN in .env: GitHub's GraphQL API rejects unauthenticated
requests. A classic token with the `read:user` scope is enough.
"""
import argparse
import sys
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from git_hours import shade
from git_langs import TOKEN, USERNAME, api_request

GRAPHQL_URL = "https://api.github.com/graphql"
QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""


def fetch_calendar(username, start, end, tz):
    """Return [(date, count)] for start..end inclusive (one GraphQL query, max 1 year)."""
    variables = {
        "login": username,
        "from": datetime.combine(start, time.min, tz).isoformat(),
        "to": datetime.combine(end, time.max, tz).isoformat(),
    }
    data = api_request(GRAPHQL_URL, {"query": QUERY, "variables": variables})
    # GraphQL reports most failures (unknown user, rate limit, bad scope) as HTTP 200 + an `errors` array
    if data.get("errors"):
        sys.exit("❌ GitHub GraphQL error: " + "; ".join(e["message"] for e in data["errors"]))
    weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    return [(date.fromisoformat(d["date"]), d["contributionCount"]) for w in weeks for d in w["contributionDays"]]


def merge_days(chunks, start, end):
    """Merge per-year [(date, count)] lists into one sorted, de-duplicated list within start..end."""
    merged = {}
    for chunk in chunks:
        for d, n in chunk:
            if start <= d <= end:
                merged[d] = max(n, merged.get(d, 0))
    return sorted(merged.items())


def current_streak(days, today):
    """Return (length, start, end, today_counted). A zero today doesn't break the streak yet."""
    counts = dict(days)
    today_counted = counts.get(today, 0) > 0
    end = today if today_counted else today - timedelta(days=1)
    d = end
    while counts.get(d, 0) > 0:
        d -= timedelta(days=1)
    return (end - d).days, d + timedelta(days=1), end, today_counted


def longest_streak(days):
    """Return (length, start, end) of the longest run of consecutive active days; (0, None, None) if none."""
    best = (0, None, None)
    length, start, prev = 0, None, None
    for d, n in days:
        if n == 0:
            length = 0
        elif length and d - prev == timedelta(days=1):
            length += 1
        else:
            length, start = 1, d
        if length > best[0]:
            best = (length, start, d)
        prev = d
    return best


def days_str(n):
    return f"{n} day{'' if n == 1 else 's'}"


def render_strip(days, today, n=30):
    counts = dict(days)
    window = [counts.get(today - timedelta(days=i), 0) for i in range(n - 1, -1, -1)]
    peak = max(window)
    return "".join(shade(c, peak) for c in window)


def main():
    parser = argparse.ArgumentParser(description="Show your GitHub contribution streaks.")
    parser.add_argument("--years", type=int, default=1, help="years to look back (default: 1)")
    parser.add_argument("--tz", help="IANA timezone name, e.g. Asia/Kathmandu (default: system timezone)")
    args = parser.parse_args()

    if not USERNAME:
        sys.exit("❌ GITHUB_USERNAME is not set. Add it to your .env file.")
    if not TOKEN:
        sys.exit("❌ GITHUB_TOKEN is not set. git_streak.py uses GitHub's GraphQL API, which requires authentication.\n"
                 "   Create one at GitHub → Settings → Developer settings → Personal access tokens →\n"
                 "   Generate new token (classic) with the `read:user` scope, then add it to .env.")
    if args.years < 1:
        sys.exit("❌ --years must be at least 1.")
    try:
        tz = ZoneInfo(args.tz) if args.tz else datetime.now().astimezone().tzinfo
    except (ZoneInfoNotFoundError, ValueError):
        sys.exit(f"❌ Unknown timezone '{args.tz}'. Use an IANA name like Asia/Kathmandu "
                 "(on Windows, `pip install tzdata` if valid names aren't found).")

    today = datetime.now(tz).date()
    start = today - timedelta(days=365 * args.years - 1)
    # One query per 365-day block, newest first; blocks don't overlap
    chunks = []
    for i in range(args.years):
        block_end = today - timedelta(days=365 * i)
        chunks.append(fetch_calendar(USERNAME, block_end - timedelta(days=364), block_end, tz))
    days = merge_days(chunks, start, today)

    cur_len, cur_start, cur_end, today_counted = current_streak(days, today)
    long_len, long_start, long_end = longest_streak(days)
    total = sum(n for _, n in days)
    active = sum(1 for _, n in days if n > 0)
    best_day, best_n = max(days, key=lambda x: x[1])

    print(f"🔥 Contribution streaks for {USERNAME}\n")
    cur = days_str(cur_len) + (f"  ({cur_start:%b %d} → {cur_end:%b %d})" if cur_len else "")
    print(f"Current streak:   {cur}" + ("" if today_counted else "  (today not counted yet)"))
    if long_len:
        start_fmt = "%b %d" if long_start.year == long_end.year else "%b %d, %Y"
        print(f"Longest streak:   {days_str(long_len)}  ({long_start.strftime(start_fmt)} → {long_end:%b %d, %Y})")
    else:
        print("Longest streak:   0 days")
    label = f"Total ({args.years} year{'s' if args.years > 1 else ''}):"
    print(f"{label:<18}{total:,} contributions")
    print(f"Active days:      {active} / {len(days)}  ({active / len(days):.0%})")
    if best_n:
        print(f"Best day:         {best_day:%b %d, %Y} — {best_n} contributions")
    print(f"\nLast 30 days:\n{render_strip(days, today)}")


if __name__ == "__main__":
    main()
