#!/usr/bin/env python3
"""Import homepage 'Currently experiencing' artwork from public metadata APIs.

TMDB (watching), Open Library (reading), MusicBrainz/Cover Art Archive
(listening), RAWG (playing). Downloads are committed into this repo by Actions.
Manual CMS artwork is never overwritten.
"""
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
HOME = ROOT / "src/content/pages/home.md"
DEST = ROOT / "public/images/currently"
MANIFEST = DEST / "manifest.json"
TMDB_TOKEN = os.environ.get("TMDB_API_TOKEN", "").strip()
RAWG_KEY = os.environ.get("RAWG_API_KEY", "").strip()
USER_AGENT = "AfterTheCredits/1.0 (https://afterthecredits.pages.dev/about/)"
MAX_IMAGE_BYTES = 3_000_000
IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
CATEGORIES = {
    "watching": ("currentlyWatching", "currentlyWatchingCover", "currentlyWatchingAutoArtwork"),
    "reading": ("currentlyReading", "currentlyReadingCover", "currentlyReadingAutoArtwork"),
    "listening": ("currentlyListening", "currentlyListeningCover", "currentlyListeningAutoArtwork"),
    "playing": ("currentlyPlaying", "currentlyPlayingCover", "currentlyPlayingAutoArtwork"),
}


def normalized(value):
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").casefold()).strip()


def get_json(url, headers=None):
    req = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
        **(headers or {}),
    })
    with urllib.request.urlopen(req, timeout=18) as response:
        return json.load(response)


def unique_match(results, title, title_key, extra_check=None):
    matches = [
        item for item in results
        if normalized(item.get(title_key)) == normalized(title)
        and (extra_check is None or extra_check(item))
    ]
    # Do not associate artwork with a different edition, remake or artist.
    return matches[0] if len(matches) == 1 else None


def match_year(value, target):
    if not target:
        return True
    year = str(value or "")[:4]
    return year == str(target)


def watching_art(meta):
    if not TMDB_TOKEN:
        print("Watching: TMDB_API_TOKEN is not set; skipping.")
        return None
    title = str(meta["currentlyWatching"]).strip()
    kind = "movie" if meta.get("currentlyWatchingType") == "Film" else "tv"
    year = meta.get("currentlyWatchingYear")
    params = {"query": title, "language": "en-US", "include_adult": "false"}
    if year:
        params["year" if kind == "movie" else "first_air_date_year"] = str(year)
    url = "https://api.themoviedb.org/3/search/" + kind + "?" + urllib.parse.urlencode(params)
    data = get_json(url, {"Authorization": "Bearer " + TMDB_TOKEN})
    result = unique_match(
        data.get("results", []), title,
        "title" if kind == "movie" else "name",
        lambda item: bool(item.get("poster_path")) and match_year(
            item.get("release_date" if kind == "movie" else "first_air_date"), year
        ),
    )
    if not result:
        return None
    poster = result.get("poster_path", "")
    if not re.fullmatch(r"/[A-Za-z0-9_-]+\.(jpg|jpeg|png|webp)", poster):
        return None
    return "https://image.tmdb.org/t/p/w500" + poster


def reading_art(meta):
    title = str(meta["currentlyReading"]).strip()
    author = str(meta.get("currentlyReadingAuthor") or "").strip()
    params = {"title": title, "fields": "title,author_name,cover_i", "limit": "15"}
    data = get_json("https://openlibrary.org/search.json?" + urllib.parse.urlencode(params))
    result = unique_match(
        data.get("docs", []), title, "title",
        lambda item: bool(item.get("cover_i")) and (
            not author or any(normalized(author) in normalized(name) for name in item.get("author_name", []))
        ),
    )
    if not result:
        return None
    return "https://covers.openlibrary.org/b/id/" + str(int(result["cover_i"])) + "-L.jpg"


def listening_art(meta):
    title = str(meta["currentlyListening"]).strip()
    artist = str(meta.get("currentlyListeningArtist") or "").strip()
    # Human-friendly "Artist — Album" is supported if the optional artist field is empty.
    if not artist and " — " in title:
        artist, title = (part.strip() for part in title.split(" — ", 1))
    if not title:
        return None
    query = 'releasegroup:"' + title.replace('"', "") + '"'
    if artist:
        query += ' AND artist:"' + artist.replace('"', "") + '"'
    params = {"query": query, "fmt": "json", "limit": 15}
    result = get_json("https://musicbrainz.org/ws/2/release-group/?" + urllib.parse.urlencode(params))
    candidates = []
    for item in result.get("release-groups", []):
        if normalized(item.get("title")) != normalized(title):
            continue
        names = " ".join(
            credit.get("name", "")
            for credit in item.get("artist-credit", [])
            if isinstance(credit, dict)
        )
        if artist and normalized(artist) not in normalized(names):
            continue
        if item.get("primary-type") not in ("Album", "EP"):
            continue
        uuid = item.get("id") or ""
        if re.fullmatch(r"[0-9a-fA-F-]{36}", uuid):
            candidates.append(uuid)
    if len(candidates) != 1:
        return None
    return "https://coverartarchive.org/release-group/" + candidates[0] + "/front-500"


def playing_art(meta):
    if not RAWG_KEY:
        print("Playing: RAWG_API_KEY is not set; skipping.")
        return None
    title = str(meta["currentlyPlaying"]).strip()
    params = {"key": RAWG_KEY, "search": title, "page_size": "12", "search_precise": "true"}
    data = get_json("https://api.rawg.io/api/games?" + urllib.parse.urlencode(params))
    year = meta.get("currentlyPlayingYear")
    result = unique_match(
        data.get("results", []), title, "name",
        lambda item: bool(item.get("background_image"))
        and match_year(item.get("released"), year),
    )
    if not result:
        return None
    url = result["background_image"]
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname or not (
        parsed.hostname == "rawg.io" or parsed.hostname.endswith(".rawg.io")
    ):
        return None
    return url


LOOKUPS = {
    "watching": watching_art,
    "reading": reading_art,
    "listening": listening_art,
    "playing": playing_art,
}


def image_bytes(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=25) as response:
        kind = response.headers.get("Content-Type", "").split(";")[0].strip().lower()
        if kind not in IMAGE_TYPES:
            raise ValueError("Unexpected artwork MIME type: " + kind)
        content = response.read(MAX_IMAGE_BYTES + 1)
        if not content or len(content) > MAX_IMAGE_BYTES:
            raise ValueError("Artwork missing or larger than 3 MB")
        return content, IMAGE_TYPES[kind]


def frontmatter(text):
    match = re.match(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|\Z)", text, re.S)
    if not match:
        raise ValueError("Homepage has no YAML frontmatter")
    return yaml.safe_load(match.group(1)) or {}, match


def set_field(text, key, value):
    """Preserve all existing YAML and Markdown, replacing one single-line field."""
    meta, front = frontmatter(text)
    header = front.group(1)
    pattern = re.compile(r"(?m)^" + re.escape(key) + r":[^\n]*(?=\n|\Z)")
    replacement = key + ": " + json.dumps(value, ensure_ascii=False)
    if pattern.search(header):
        header = pattern.sub(lambda _: replacement, header, count=1)
    else:
        header += "\n" + replacement
    return text[:front.start(1)] + header + text[front.end(1):]


def remove_field(text, key):
    _, front = frontmatter(text)
    header = front.group(1)
    header = re.sub(r"(?m)^" + re.escape(key) + r":[^\n]*(?:\n|\Z)", "", header)
    return text[:front.start(1)] + header.rstrip("\r\n") + text[front.end(1):]


def main():
    raw = HOME.read_text(encoding="utf-8")
    meta, _ = frontmatter(raw)
    previous = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}
    updated = dict(previous)
    for category, (field, cover_field, enabled_field) in CATEGORIES.items():
        title = str(meta.get(field) or "").strip()
        old = previous.get(category) or {}
        current_cover = str(meta.get(cover_field) or "").strip()
        old_cover = old.get("cover", "")
        if meta.get(enabled_field) is False:
            print(category + ": auto artwork disabled.")
            continue
        if current_cover and current_cover != old_cover:
            print(category + ": using manually chosen artwork.")
            continue
        query = json.dumps({
            "title": title,
            "kind": meta.get("currentlyWatchingType", "TV") if category == "watching" else category,
            "year": meta.get("currentlyWatchingYear") if category == "watching" else meta.get("currentlyPlayingYear") if category == "playing" else None,
            "creator": meta.get("currentlyReadingAuthor") if category == "reading" else meta.get("currentlyListeningArtist") if category == "listening" else None,
        }, sort_keys=True, ensure_ascii=False)
        if current_cover and current_cover == old_cover and old.get("query") == query:
            print(category + ": artwork is current.")
            continue
        if not title:
            if current_cover and current_cover == old_cover:
                raw = remove_field(raw, cover_field)
                meta.pop(cover_field, None)
            updated.pop(category, None)
            continue
        try:
            url = LOOKUPS[category](meta)
            if not url:
                print(category + ": no confident artwork match for " + title)
                if current_cover == old_cover and old_cover:
                    raw = remove_field(raw, cover_field)
                    meta.pop(cover_field, None)
                updated.pop(category, None)
                continue
            data, ext = image_bytes(url)
            DEST.mkdir(parents=True, exist_ok=True)
            destination = DEST / (category + ext)
            destination.write_bytes(data)
            path = "/images/currently/" + destination.name
            raw = set_field(raw, cover_field, path)
            meta[cover_field] = path
            updated[category] = {"query": query, "cover": path, "source": {
                "watching": "TMDB", "reading": "Open Library",
                "listening": "MusicBrainz / Cover Art Archive", "playing": "RAWG",
            }[category]}
            old_file = DEST / Path(old_cover).name if old_cover.startswith("/images/currently/") else None
            if old_file and old_file != destination and old_file.exists():
                old_file.unlink()
            print(category + ": added artwork for " + title)
        except (urllib.error.URLError, ValueError, KeyError, OSError) as exc:
            print(category + ": lookup failed: " + str(exc), file=sys.stderr)
    if raw != HOME.read_text(encoding="utf-8"):
        HOME.write_text(raw, encoding="utf-8")
    if updated != previous:
        DEST.mkdir(parents=True, exist_ok=True)
        MANIFEST.write_text(json.dumps(updated, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
