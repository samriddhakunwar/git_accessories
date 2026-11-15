"""Quick checks for git_inbox.simplify. Run: python test_git_inbox.py"""
from datetime import datetime, timezone

from git_inbox import simplify

now = datetime(2026, 11, 15, tzinfo=timezone.utc)
base = {"repository_url": "https://api.github.com/repos/me/portfolio", "number": 7, "title": "Fix nav",
        "user": {"login": "alice"}, "created_at": "2026-10-16T12:00:00Z", "comments": 2,
        "html_url": "https://github.com/me/portfolio/pull/7"}

pr = simplify({**base, "pull_request": {}}, now)
assert pr["type"] == "pr" and pr["repo"] == "portfolio" and pr["age_days"] == 29 and pr["author"] == "alice"
assert simplify(base, now)["type"] == "issue"
print("ok")
