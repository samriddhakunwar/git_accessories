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

> **How to get a token:** GitHub → Settings → Developer settings → Personal access tokens → Generate new token (classic) → check `repo` scope.
>
> The token is optional but **strongly recommended** — without it, GitHub's API rate limit is only 60 requests/hour, which won't be enough for users with many repositories.

### 4. Run

```bash
python git_card.py
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
