"""Quick checks for git_followers.diff_snapshots. Run: python test_git_followers.py"""
from git_followers import diff_snapshots

old = {"followers": ["alice", "Bob", "charlie"], "following": ["alice", "dave"]}
new = {"followers": ["alice", "Bob", "eve", "zed", "Adam"], "following": ["alice", "dave"]}

d = diff_snapshots(old, new)
assert d["new_followers"] == ["Adam", "eve", "zed"]  # case-insensitive sort
assert d["unfollowers"] == ["charlie"]
assert d["not_following_back"] == ["dave"]
assert d["fans"] == ["Adam", "Bob", "eve", "zed"]

first = diff_snapshots(None, new)  # first run: no changes, static sections still computed
assert first["new_followers"] == first["unfollowers"] == [] and first["not_following_back"] == ["dave"]
print("ok")
