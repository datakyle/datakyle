"""Rebuild the "Things I've built" table in README.md from your public GitHub repos.

Runs in GitHub Actions (see .github/workflows/update-readme.yml).
Standard library only, nothing to install.

Rules:
- Public, non-fork, non-archived repos you own are listed, newest first.
- The profile repo itself (datakyle/datakyle) is skipped.
- Add the topic `hide` to any repo you want left off the list.
- projects.json (optional) overrides a repo's display name, one-liner,
  play link and "learned" line. Anything not in it falls back to the
  repo's "About" description and "Website" field, so new repos still
  show up on their own.
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
OVERRIDES_PATH = os.environ.get("OVERRIDES_PATH", "projects.json")


def load_overrides():
    try:
        with open(OVERRIDES_PATH, encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return {}
    return {k: v for k, v in data.items() if not k.startswith("_")}


OVERRIDES = load_overrides()


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
    o = OVERRIDES.get(repo["name"], {})
    pretty = o.get("name") or repo["name"].replace("-", " ").replace("_", " ")
    line = clean(o.get("line") or repo.get("description")) or "Details soon"
    learned = clean(o.get("learned"))
    if learned:
        line += f"<br><sub><i>What I learned: {learned}</i></sub>"
    site = (o.get("play") or repo.get("homepage") or "").strip()
    if site and not site.startswith(("http://", "https://")):
        site = "https://" + site
    play = f"[Play]({site})" if site else ""
    code = f"[Code]({repo['html_url']})"
    links = " · ".join(x for x in (play, code) if x)
    return f"| **{clean(pretty)}** | {line} | {links} |"


def build_table(repos):
    lines = ["| Project | What it is | |", "| ------- | ---------- | - |"]
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
