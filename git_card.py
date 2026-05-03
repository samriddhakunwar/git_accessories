import requests
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

load_dotenv()  # loads variables from .env into environment

USERNAME = os.getenv("GITHUB_USERNAME")

# Optional (recommended to avoid rate limits)
TOKEN = os.getenv("GITHUB_TOKEN")  # or set to None

headers = {
    "Authorization": f"token {TOKEN}" if TOKEN else None
}

def get_repos(username):
    repos = []
    page = 1
    while True:
        url = f"https://api.github.com/users/{username}/repos?per_page=100&page={page}"
        res = requests.get(url, headers=headers)
        data = res.json()

        if not data:
            break

        repos.extend(data)
        page += 1

    return repos

def count_commits(repo_name):
    count = 0
    page = 1
    since_date = (datetime.utcnow() - timedelta(days=365)).isoformat() + "Z"

    while True:
        url = f"https://api.github.com/repos/{USERNAME}/{repo_name}/commits?since={since_date}&per_page=100&page={page}"
        res = requests.get(url, headers=headers)

        if res.status_code != 200:
            break

        commits = res.json()

        if not commits:
            break

        count += len(commits)
        page += 1

    return count

def main():
    repos = get_repos(USERNAME)
    total_commits = 0

    for repo in repos:
        repo_name = repo["name"]
        print(f"Checking {repo_name}...")
        total_commits += count_commits(repo_name)

    print("\n🔥 Total commits in last 12 months:", total_commits)

if __name__ == "__main__":
    main()
