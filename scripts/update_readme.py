"""Rebuild the "Things I've built" table in README.md from your public GitHub repos.

Runs in GitHub Actions (see .github/workflows/update-readme.yml).
Standard library only, nothing to install.

Rules:
- Public, non-fork, non-archived repos you own are listed, newest first.
- The profile repo itself (datakyle/datakyle) is skipped.
- Add the topic `hide` to any repo you want left off the list.
- The repo's "About" description becomes the Description column.
- The repo's "Website" field (homepage) shows up as a (site) link.
"""

import json
import os
import re
import sys
import urllib.request
from datetime import datetime

USER = os.environ.get("GH_USER", "datakyle")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
README = os.environ.get("README_PATH", "README.md")
START = "<!-- PROJECTS:START -->"
END = "<!-- PROJECTS:END -->"
HIDE_TOPICS = {"hide", "hide-from-profile"}


def fetch_repos():
    repos, page = [], 1
    while True:
        url = (
            f"https://api.github.com/users/{USER}/repos"
            f"?type=owner&sort=created&direction=desc&per_page=100&page={page}"
        )
        req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json"})
        if TOKEN:
            req.add_header("Authorization", f"Bearer {TOKEN}")
        with urllib.request.urlopen(req) as resp:
            batch = json.load(resp)
        if not batch:
            break
        repos.extend(batch)
        page += 1
    return repos


def keep(repo):
    return not (
        repo.get("fork")
        or repo.get("archived")
        or repo.get("private")
        or repo["name"].lower() == USER.lower()
        or HIDE_TOPICS & set(repo.get("topics") or [])
    )


def clean(text):
    # Pipes would break the markdown table.
    return (text or "").replace("|", "/").strip()


def row(repo):
    started = datetime.strptime(repo["created_at"][:10], "%Y-%m-%d").strftime("%b %Y")
    pretty = repo["name"].replace("-", " ").replace("_", " ")
    name = f"[{pretty}]({repo['html_url']})"
    if repo.get("homepage"):
        name += f" ([site]({repo['homepage']}))"
    return f"| {started} | {name} | {clean(repo.get('description')) or 'Details soon'} |"


def build_table(repos):
    lines = ["| Started | Project | Description |", "| ------- | ------- | ----------- |"]
    lines += [row(r) for r in repos]
    return "\n".join(lines)


def main():
    repos = sorted(
        (r for r in fetch_repos() if keep(r)),
        key=lambda r: r["created_at"],
        reverse=True,
    )
    with open(README, encoding="utf-8") as f:
        text = f.read()
    if START not in text or END not in text:
        sys.exit(f"Markers {START} / {END} not found in {README}")
    block = f"{START}\n{build_table(repos)}\n{END}"
    new = re.sub(re.escape(START) + r".*?" + re.escape(END), lambda _: block, text, flags=re.S)
    if new != text:
        with open(README, "w", encoding="utf-8") as f:
            f.write(new)
        print(f"README updated with {len(repos)} projects.")
    else:
        print("No changes.")


if __name__ == "__main__":
    main()
