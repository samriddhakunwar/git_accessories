# 🛠️ git_accessories

A collection of lightweight Python utilities for fetching and analyzing your GitHub activity.

## 📦 Current Tools

### `git_card.py` — Commit Counter

Fetches all your public GitHub repositories and counts your **total commits over the last 12 months** across all of them.

**Example output:**
```
Checking portfolio...
Checking git_accessories...
Checking hospital-management...

🔥 Total commits in last 12 months: 342
```

### `git_langs.py` — Language Breakdown

Fetches all your public GitHub repositories (forks skipped by default), sums the **bytes of code per language** across them, and prints a sorted bar chart of your top languages.

**Example output:**
```
Checking portfolio...
Checking git_accessories...
Checking hospital-management...

📊 Language breakdown across 12 repos:

Python       ████████████░░░░░░░░░░░░░  48.2%
JavaScript   █████░░░░░░░░░░░░░░░░░░░░  21.7%
HTML         ███░░░░░░░░░░░░░░░░░░░░░░  13.1%
CSS          ██░░░░░░░░░░░░░░░░░░░░░░░   9.4%
Other        ██░░░░░░░░░░░░░░░░░░░░░░░   7.6%
```

**Flags:**

| Flag | Description |
|------|-------------|
| `--top N` | Number of languages to show (default: 8). The rest are grouped into "Other". |
| `--include-forks` | Include forked repositories (skipped by default). |

### `git_hours.py` — Coding Hours Heatmap

Fetches every commit you authored in your public repositories over the last 12 months, converts the timestamps to **your timezone**, and prints a **weekday × hour heatmap** of when you code, plus a short summary.

> This tool makes one request per 100 commits per repo — a `GITHUB_TOKEN` is strongly recommended.

**Example output:**
```
Checking portfolio...
Checking git_accessories...

🕒 Commit heatmap (last 12 months, Asia/Kathmandu)

      00 03 06 09 12 15 18 21
Mon   ░▓░░  ░    ░░░ ░░▓▒█▓▓▒▒
Tue   ▓▒░░░░       ▒░▒░▒██▓▒░▒
Wed    ░     ░ ░░░░▒░░▓░░▒▒░▒▓
Thu   ░█░        ░░░░░░▒▒░▒▓▓░
Fri   ▒░░         ░ ░▒█▒▓█▒▓▓▒
Sat   ░░░░░      ░░▒░▒▒▓▓▒▓▒░░
Sun   ▒▒░         ░▓▓▒▒▓▓░▓░░░

📈 342 commits analyzed
⏰ Peak hour: 20:00–21:00 (33 commits)
📅 Busiest day: Monday (56 commits)
🦉 Night owl score: 28% of commits between 22:00 and 04:00
```

Each column is one hour; shades (` ░▒▓█`) are scaled to your busiest cell.

**Flags:**

| Flag | Description |
|------|-------------|
| `--tz NAME` | IANA timezone, e.g. `Asia/Kathmandu` (default: system timezone). On Windows, run `pip install tzdata` if valid names aren't recognized. |
| `--months N` | Lookback window in months (default: 12). |
| `--include-forks` | Include forked repositories (skipped by default). |

### `git_streak.py` — Contribution Streak Tracker

Fetches your GitHub **contribution calendar** via the GraphQL API and shows your **current streak**, **longest streak**, total contributions, active days, best day, and a strip of the last 30 days.

> 🔑 **This tool requires a token.** GitHub's GraphQL API does not accept unauthenticated requests. A classic token with the `read:user` scope is enough.

If you haven't contributed yet today, your streak isn't broken: it is counted up to yesterday and marked "(today not counted yet)".

**Example output:**
```
🔥 Contribution streaks for samriddhakunwar

Current streak:   12 days  (Oct 13 → Oct 24)
Longest streak:   27 days  (Mar 02 → Mar 28, 2026)
Total (1 year):   1,284 contributions
Active days:      231 / 365  (63%)
Best day:         Jun 14, 2026 — 41 contributions

Last 30 days:
░▒▓█▓▒ ░▒▓▓█▒░░▒▓▓█▓▒░▒▓█▓▒░
```

Shades (` ░▒▓█`) in the 30-day strip are scaled to your busiest day in that window.

**Flags:**

| Flag | Description |
|------|-------------|
| `--years N` | Years to look back (default: 1). Makes one GraphQL query per year. |
| `--tz NAME` | IANA timezone used to decide "today", e.g. `Asia/Kathmandu` (default: system timezone). |

---

## 🚀 Getting Started

### 1. Clone the repo

```bash
git clone https://github.com/samriddhakunwar/git_accessories.git
cd git_accessories
```

### 2. Install dependencies

```bash
pip install requests python-dotenv
```

### 3. Set up your environment

Create a `.env` file in the project root:

```env
GITHUB_USERNAME="your_github_username"
GITHUB_TOKEN="ghp_your_personal_access_token"
```

> **How to get a token:** GitHub → Settings → Developer settings → Personal access tokens → Generate new token (classic) → check `repo` scope (`git_streak.py` additionally needs `read:user`).
>
> The token is optional but **strongly recommended** — without it, GitHub's API rate limit is only 60 requests/hour, which won't be enough for users with many repositories.
>
> **`git_streak.py` requires the token** (GitHub's GraphQL API rejects unauthenticated requests) and needs the `read:user` scope.

### 4. Run

```bash
python git_card.py
python git_langs.py                    # or: --top 5 --include-forks
python git_hours.py                    # or: --tz Asia/Kathmandu --months 6
python git_streak.py                   # or: --years 3 --tz Asia/Kathmandu (requires token)
```

---

## 🔒 Security

- **Never commit your `.env` file.** It is already listed in `.gitignore`.
- Do not hardcode tokens directly in source files — always use environment variables.

---

## 📁 Project Structure

```
git_accessories/
├── git_card.py      # Counts total commits in the last 12 months
├── git_langs.py     # Language breakdown across your repos
├── git_hours.py     # Weekday x hour commit heatmap
├── git_streak.py    # Current/longest contribution streaks
├── .env             # Local secrets (gitignored)
├── .gitignore
└── README.md
```

---

## 🤝 Contributing

Pull requests are welcome! If you have ideas for more GitHub utility scripts to add to this collection, feel free to open an issue or PR.

---

## 📄 License

MIT
