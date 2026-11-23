#!/usr/bin/env python3
"""Track the most recent change to the homepage phrase, not unrelated edits.

Runs in GitHub Actions with a full-history checkout. The timestamp is based
on the commit that actually changed todaysPhrase, and is not CMS-editable.
"""
from pathlib import Path
import re
import subprocess

PATH = Path("src/content/pages/home.md")
KEY = "todaysPhrase"
STAMP = "todaysPhraseUpdatedAt"

def git(*args: str) -> str:
    return subprocess.run(["git", *args], text=True, capture_output=True, check=True).stdout

def field(content: str, key: str) -> str:
    match = re.search(r"(?m)^" + re.escape(key) + r":\s*(.*)$", content)
    return match.group(1).strip() if match else ""

def main() -> None:
    content = PATH.read_text(encoding="utf-8")
    phrase = field(content, KEY)
    if not phrase or phrase in ("''", '""', "null", "~"):
        new_content = re.sub(r"(?m)^" + STAMP + r":.*\n?", "", content)
    else:
        commits = git("log", "--format=%H", "--", str(PATH)).splitlines()
        latest = None
        for index, commit in enumerate(commits):
            this = git("show", f"{commit}:{PATH}")
            old = git("show", f"{commits[index+1]}:{PATH}") if index+1 < len(commits) else ""
            if field(this, KEY) != field(old, KEY):
                latest = git("show", "-s", "--format=%aI", commit).strip()
                break
        if not latest:
            print("No phrase change commit found; leaving timestamp as is.")
            return
        if re.search(r"(?m)^" + STAMP + r":", content):
            new_content = re.sub(r"(?m)^" + STAMP + r":.*$", f"{STAMP}: '{latest}'", content)
        else:
            new_content = re.sub(r"(?m)^" + KEY + r":.*$", lambda m: m.group() + f"\n{STAMP}: '{latest}'", content, count=1)
    if new_content != content:
        PATH.write_text(new_content, encoding="utf-8")
        print("Updated homepage phrase change timestamp")
    else:
        print("Homepage phrase timestamp is current")

if __name__ == "__main__":
    main()
