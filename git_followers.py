"""
git_followers.py — Follower Tracker

Fetches your followers and following lists, compares them with the snapshot
saved on the previous run, and reports new followers, unfollowers, people who
don't follow you back and fans you don't follow back. Each run is appended to
a history log so you can see growth over time. Read-only: it never follows or
unfollows anyone.

Usage:
    python git_followers.py                    # report changes since the last run
    python git_followers.py --show-all         # list every name in every section
    python git_followers.py --json             # full report as JSON
    python git_followers.py --history          # last 10 runs with follower trend
    python git_followers.py --snapshot my.json # custom snapshot file
"""
import argparse
import json
import os
import sys
import textwrap
from datetime import datetime
from pathlib import Path

from git_langs import TOKEN, USERNAME, api_request

HISTORY_FILE = Path(".followers_history.json")
MAX_NAMES = 10


def fetch_all(username, kind):
    """Return every login in /users/{username}/{kind} (followers or following).
    Any failure exits (via api_request), so partial data never reaches the snapshot."""
    logins, page = [], 1
    while True:
        data = api_request(f"https://api.github.com/users/{username}/{kind}?per_page=100&page={page}")
        if data is None:
            sys.exit(f"❌ GitHub user '{username}' not found.")
        logins += [u["login"] for u in data]
        if len(data) < 100:
            return logins
        page += 1


def read_json(path, log):
    """Return parsed JSON from path, None if missing, or False (after a warning) if unreadable."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except (OSError, ValueError) as e:
        print(f"⚠️  Couldn't read {path} ({e}).", file=log)
        return False


def write_json(path, data):
    """Write atomically: a crash mid-write leaves the old file intact."""
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def load_snapshot(path, username, log):
    """Return the previous snapshot, or None if there isn't a usable one for this user."""
    snap = read_json(path, log)
    if snap is False or (snap is not None and not (isinstance(snap, dict) and
                                                    {"username", "timestamp", "followers", "following"} <= snap.keys())):
        print("⚠️  Snapshot is corrupted — treating this as a first run.\n", file=log)
        return None
    if snap and snap["username"].lower() != username.lower():
        print(f"⚠️  Snapshot belongs to '{snap['username']}', not '{username}' — starting fresh.\n", file=log)
        return None
    return snap


def save_snapshot(path, snap):
    write_json(path, snap)


def by_name(names):
    return sorted(names, key=str.lower)


def diff_snapshots(old, new):
    """Compare two snapshots (old may be None). Pure: returns sorted name lists per section."""
    followers, following = set(new["followers"]), set(new["following"])
    old_followers = set(old["followers"]) if old else followers
    return {
        "new_followers": by_name(followers - old_followers),
        "unfollowers": by_name(old_followers - followers),
        "not_following_back": by_name(following - followers),
        "fans": by_name(followers - following),
    }


def append_history(snap, diff, log):
    history = read_json(HISTORY_FILE, log)
    if history is False or (history is not None and not isinstance(history, list)):
        print(f"⚠️  Not updating {HISTORY_FILE} so its contents aren't lost.", file=log)
        return
    (history := history or []).append({
        "username": snap["username"], "timestamp": snap["timestamp"],
        "followers": len(snap["followers"]), "following": len(snap["following"]),
        "added": len(diff["new_followers"]), "removed": len(diff["unfollowers"]),
    })
    write_json(HISTORY_FILE, history)


def ago(timestamp, now):
    days = (now - datetime.fromisoformat(timestamp)).days
    return "today" if days < 1 else f"{days} day{'' if days == 1 else 's'} ago"


def print_section(title, names, prefix, show_all):
    print(f"\n{title} ({len(names)})")
    if not names:
        print("   (none)")
        return
    shown = names if show_all else names[:MAX_NAMES]
    more = len(names) - len(shown)
    if prefix:
        print("\n".join(f"   {prefix} {n}" for n in shown))
        if more:
            print(f"   ...and {more} more  (use --show-all to list everyone)")
    else:
        line = ", ".join(shown) + (f", ...and {more} more  (use --show-all to list everyone)" if more else "")
        print(textwrap.fill(line, width=80, initial_indent="   ", subsequent_indent="   "))


def print_report(old, new, diff, show_all):
    now = datetime.fromisoformat(new["timestamp"])
    print(f"👥 Follower report for {new['username']}")
    if old:
        print(f"   Last checked: {datetime.fromisoformat(old['timestamp']):%b %d, %Y} ({ago(old['timestamp'], now)})")
    delta = len(new["followers"]) - len(old["followers"]) if old else None
    print(f"\nFollowers: {len(new['followers'])}" + (f" ({delta:+d})" if delta is not None else "")
          + f"   Following: {len(new['following'])}")
    if old:
        print_section("🎉 New followers", diff["new_followers"], "+", show_all)
        print_section("👋 Unfollowed you", diff["unfollowers"], "-", show_all)
    else:
        print("\n📸 First run: snapshot saved. New followers and unfollowers will show from the next run.")
    print_section("🔁 You follow, they don't follow back", diff["not_following_back"], "", show_all)
    print_section("💜 Fans you don't follow back", diff["fans"], "", show_all)


def print_history(username):
    history = read_json(HISTORY_FILE, sys.stdout)
    rows = [h for h in history or [] if h.get("username", "").lower() == username.lower()]
    if not rows:
        print(f"No history yet for {username}. Run `python git_followers.py` to start one.")
        return
    print(f"📈 Follower history for {username} (last {min(len(rows), 10)} runs)\n")
    print(f"{'Date':<14}{'Followers':>10}{'Trend':>7}{'Following':>11}{'+New':>6}{'-Lost':>7}")
    start = max(len(rows) - 10, 0)
    for i in range(start, len(rows)):
        h = rows[i]
        trend = f"{h['followers'] - rows[i - 1]['followers']:+d}" if i else "—"
        print(f"{datetime.fromisoformat(h['timestamp']):%b %d, %Y}  {h['followers']:>10}{trend:>7}"
              f"{h['following']:>11}{h['added']:>6}{h['removed']:>7}")


def main():
    parser = argparse.ArgumentParser(description="Track your GitHub followers between runs (read-only).")
    parser.add_argument("--snapshot", default=".followers_snapshot.json",
                        help="snapshot file (default: .followers_snapshot.json)")
    parser.add_argument("--history", action="store_true", help="show the last 10 runs and exit")
    parser.add_argument("--show-all", action="store_true", help="list every name instead of the first 10")
    parser.add_argument("--json", action="store_true", help="print the full report as JSON")
    args = parser.parse_args()
    log = sys.stderr if args.json else sys.stdout  # keep stdout pure JSON when piping

    if not USERNAME:
        sys.exit("❌ GITHUB_USERNAME is not set. Add it to your .env file.")
    if args.history:
        return print_history(USERNAME)
    if not TOKEN:
        print("⚠️  No GITHUB_TOKEN set — unauthenticated requests are limited to 60/hour.\n", file=log)

    path = Path(args.snapshot)
    old = load_snapshot(path, USERNAME, log)
    new = {
        "username": USERNAME,
        "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
        "followers": by_name(fetch_all(USERNAME, "followers")),
        "following": by_name(fetch_all(USERNAME, "following")),
    }
    diff = diff_snapshots(old, new)

    if args.json:
        print(json.dumps({"username": USERNAME, "checked_at": new["timestamp"],
                          "previous_check": old["timestamp"] if old else None, "first_run": old is None,
                          "followers": len(new["followers"]), "following": len(new["following"]), **diff},
                         indent=2, ensure_ascii=False))
    else:
        print_report(old, new, diff, args.show_all)

    save_snapshot(path, new)
    append_history(new, diff, log)


if __name__ == "__main__":
    main()
