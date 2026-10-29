#!/usr/bin/env python3
"""Fetch missing film/TV artwork from TMDB and save it to the repository.
Requires TMDB_API_TOKEN (TMDB API Read Access Token) and PyYAML.
Does not replace existing manually selected covers.
"""
import os
import re
import sys
import mimetypes
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
TOKEN = os.getenv("TMDB_API_TOKEN", "").strip()
MAX_POSTER_BYTES = 3_000_000
HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/json",
    "User-Agent": "AfterTheCreditsPosterImport/1.0",
}

def get_json(url):
    import json
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=18) as response:
        return json.load(response)

def normalized(value):
    return re.sub(r"[^a-z0-9]+", " ", str(value).casefold()).strip()

def choose_match(results, title, year, kind, override_id):
    if override_id:
        return next((result for result in results if int(result.get("id", -1)) == override_id), None)
    candidates = []
    for result in results:
        found_title = result.get("title" if kind == "movie" else "name") or ""
        if normalized(found_title) != normalized(title):
            continue
        date = result.get("release_date" if kind == "movie" else "first_air_date") or ""
        found_year = int(date[:4]) if re.match(r"^\d{4}", date) else None
        # Never silently choose the wrong remake or a similarly named TV series.
        if year and found_year != year:
            continue
        if not result.get("poster_path"):
            continue
        candidates.append(result)
    return candidates[0] if len(candidates) == 1 else None

def process(filepath):
    raw = filepath.read_text(encoding="utf-8")
    match = re.match(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|\Z)", raw, flags=re.S)
    if not match:
        return
    meta = yaml.safe_load(match.group(1))
    if not isinstance(meta, dict) or meta.get("cover") or meta.get("autoPoster") is False:
        return
    medium = meta.get("medium") or ("Film" if "reviews" in filepath.parts else None)
    if medium not in ("Film", "TV"):
        return
    title = str(meta.get("posterTitle") or meta.get("title") or "").strip()
    if not title:
        return
    kind = "movie" if medium == "Film" else "tv"
    year = meta.get("year")
    try:
        year = int(year) if year else None
    except (ValueError, TypeError):
        year = None
    override_id = meta.get("tmdbId")
    if override_id:
        try:
            override_id = int(override_id)
        except (ValueError, TypeError):
            print(f"Skipping {filepath.name}: invalid TMDB ID")
            return
        match_result = get_json(f"https://api.themoviedb.org/3/{kind}/{override_id}?language=en-US")
    else:
        params = {"query": title, "language": "en-US", "include_adult": "false"}
        if year:
            params["year" if kind == "movie" else "first_air_date_year"] = str(year)
        url = f"https://api.themoviedb.org/3/search/{kind}?" + urllib.parse.urlencode(params)
        match_result = choose_match(get_json(url).get("results", []), title, year, kind, None)
    if not match_result:
        print(f"No confident TMDB match: {filepath.name} ({title}, {year}, {kind})")
        return
    poster_path = match_result.get("poster_path") or ""
    if not re.fullmatch(r"/[A-Za-z0-9_-]+\.(?:jpg|jpeg|png|webp)", poster_path):
        print(f"Skipping unusual poster path for {filepath.name}")
        return
    ext = poster_path.rsplit(".", 1)[1].lower()
    safe_slug = re.sub(r"[^a-z0-9-]", "-", str(meta.get("slug") or filepath.stem).lower()).strip("-")
    if not safe_slug:
        return
    bucket = "reviews" if "reviews" in filepath.parts else "diary"
    dest = ROOT / "public" / "images" / "posters" / f"{bucket}-{safe_slug}.{ext}"
    image_url = f"https://image.tmdb.org/t/p/w500{poster_path}"
    req = urllib.request.Request(image_url, headers={"User-Agent": HEADERS["User-Agent"]})
    with urllib.request.urlopen(req, timeout=20) as response:
        if not response.headers.get("Content-Type", "").lower().startswith("image/"):
            raise ValueError("Poster URL did not return an image")
        data = response.read(MAX_POSTER_BYTES + 1)
    if not data or len(data) > MAX_POSTER_BYTES:
        raise ValueError("Poster download empty or too large")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    local_url = "/images/posters/" + dest.name
    frontmatter_end = match.end(1)
    updated = raw[:frontmatter_end].rstrip("\r\n") + f"\ncover: {local_url}" + raw[frontmatter_end:]
    filepath.write_text(updated, encoding="utf-8")
    print(f"Added {kind} poster to {filepath.relative_to(ROOT)} -> {local_url}")

def main():
    if not TOKEN:
        print("TMDB_API_TOKEN not configured. Set the GitHub Actions repository secret; skipping poster imports.")
        return
    sources = list((ROOT / "src/content/reviews").glob("*.md")) + list((ROOT / "src/content/diary").glob("*.md"))
    failures = []
    for file in sources:
        try:
            process(file)
        except (urllib.error.URLError, ValueError, OSError, KeyError) as exc:
            print(f"Poster lookup failed for {file.name}: {exc}", file=sys.stderr)
            failures.append(file.name)
    if failures:
        print(f"Poster lookups had {len(failures)} failure(s); existing entries were preserved.", file=sys.stderr)

if __name__ == "__main__":
    main()
