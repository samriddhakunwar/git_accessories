"""Quick layout checks for git_banner.build_svg with fake data. Run: python test_git_banner.py"""
import xml.etree.ElementTree as ET

from git_banner import build_svg, compact

assert [compact(n) for n in (0, 999, 1000, 1234, 2_500_000)] == ["0", "999", "1k", "1.2k", "2.5M"]

full = {"username": "a<&>b", "stars": 1234, "forks": 5, "repos": 12, "followers": 40,
        "contributions": 1284, "streak": 1, "top_repo": ("x&y-very-long-repository-name", 99),
        "languages": [("Python", 500), ("JavaScript", 300), ("Brainfuck", 10)]}
for theme in ("dark", "light"):
    svg = build_svg(full, theme)
    ET.fromstring(svg)  # well-formed despite <, & in names
    assert "a&lt;&amp;&gt;b" in svg and "1.2k" in svg and "1 day" in svg and "@keyframes" in svg

empty = build_svg({"username": "nobody", "repos": 0, "stars": 0}, animate=False)
ET.fromstring(empty)
assert "clipPath" not in empty and "@keyframes" not in empty and "Contributions" not in empty
assert "http" not in empty.replace("http://www.w3.org/2000/svg", "")  # no external refs
print("ok")
