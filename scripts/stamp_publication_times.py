#!/usr/bin/env python3
"""Stamp first publication times on content without moving entries on edits.

Uses each file's earliest Git addition commit, never the last modification time.
Run from the repository root with a full-history checkout.
"""
from pathlib import Path
import re
import subprocess

CONTENT_DIRS = ("reviews", "diary", "commonplace", "projects")
BASE = Path("src/content")

def initial_commit_time(path: Path) -> str | None:
    result = subprocess.run(
        ["git", "log", "--follow", "--diff-filter=A", "--format=%aI", "--", str(path)],
        text=True, capture_output=True, check=True,
    )
    dates = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return dates[-1] if dates else None

def stamp(path: Path) -> bool:
    content = path.read_text(encoding="utf-8")
    if not content.startswith("---\n") or re.search(r"(?m)^publishedAt\s*:", content):
        return False
    timestamp = initial_commit_time(path)
    if not timestamp:
        print(f"Skipped (no original add commit): {path}")
        return False
    match = re.match(r"\A---\n([\s\S]*?)\n---", content)
    if not match:
        return False
    head = match.group(1)
    date_field = re.search(r"(?m)^date\s*:.*$", head)
    pos = date_field.end() if date_field else len(head)
    head = head[:pos] + f"\npublishedAt: '{timestamp}'" + head[pos:]
    path.write_text("---\n" + head + content[match.end()-4:], encoding="utf-8")
    print(f"Stamped {path}: {timestamp}")
    return True

def main() -> None:
    count = 0
    for name in CONTENT_DIRS:
        for path in sorted((BASE / name).glob("*.md")):
            count += int(stamp(path))
    print(f"Stamped {count} new entries")

if __name__ == "__main__":
    main()
