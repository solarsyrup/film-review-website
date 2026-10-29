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


def split_book_title_and_volume(title, override=None):
    """Return (series/book title, requested volume, explicitly_requested).

    Explicit volume in CMS or the title is authoritative: do not substitute a
    different volume if that exact one cannot be found.
    """
    explicit = override is not None and override != ""
    number = None
    if explicit:
        number = int(override)
        if number < 1 or number > 500:
            raise ValueError("Reading volume must be between 1 and 500")
    found = re.search(r"(?i)(?:\bvol(?:ume)?\.?\s*|\b(?:book|volume)\s*|#)([1-9]\d{0,2})\b", title)
    if found:
        if not explicit:
            number = int(found.group(1))
            explicit = True
        title = (title[:found.start()] + " " + title[found.end():]).strip(" .,:;—–-() ")
    return title.strip(), number, explicit


def reading_matches_title(candidate, title, volume):
    """Require the right base title and the right volume, if specified."""
    text = normalized(candidate)
    base = normalized(title)
    if not text or not base:
        return False
    # Matches 'Jojolion', 'JoJolion Volume 1', 'JoJolion, Vol. 1', or 'JoJolion 1'.
    if text == base:
        return volume is None
    if not text.startswith(base + " "):
        return False
    suffix = text[len(base) + 1:]
    found = re.fullmatch(r"(?:(?:vol|volume|book)\s+)?([1-9]\d{0,2})", suffix)
    if not found:
        return False
    return volume is None or int(found.group(1)) == volume


def manga_series_fallback(title, author):
    """Use a manga series' default cover only when no volume is specified."""
    try:
        data = get_json("https://api.jikan.moe/v4/manga?" + urllib.parse.urlencode({
            "q": title, "limit": 12,
        }))
    except urllib.error.URLError as exc:
        print("Manga fallback unavailable: " + str(exc), file=sys.stderr)
        return None
    candidates = []
    for entry in data.get("data", []):
        titles = [entry.get("title"), entry.get("title_english")]
        titles += [alt.get("title") for alt in entry.get("titles", []) if isinstance(alt, dict)]
        if not any(
            normalized(t) == normalized(title)
            or normalized(t).endswith(" " + normalized(title))
            or normalized(t).endswith(" " + normalized("Part 8: " + title))
            for t in titles if t
        ):
            continue
        authors = [x.get("name", "") for x in entry.get("authors", [])]
        if author:
            author_parts = normalized(author).split()
            author_text = normalized(" ".join(authors))
            if not all(part in author_text for part in author_parts):
                # Anime databases sometimes write Japanese names surname-first.
                continue
        url = ((entry.get("images") or {}).get("jpg") or {}).get("large_image_url")
        if not url:
            url = ((entry.get("images") or {}).get("jpg") or {}).get("image_url")
        if url:
            parsed = urllib.parse.urlparse(url)
            if parsed.scheme == "https" and parsed.hostname == "cdn.myanimelist.net":
                candidates.append(url)
    return candidates[0] if len(candidates) == 1 else None


def reading_art(meta):
    title = str(meta["currentlyReading"]).strip()
    author = str(meta.get("currentlyReadingAuthor") or "").strip()
    # Recognize 'JoJolion - Hirohiko Araki' without requiring a separate field.
    if not author:
        for separator in (" — ", " - "):
            if separator in title:
                possible_title, possible_author = (part.strip() for part in title.rsplit(separator, 1))
                if possible_title and possible_author:
                    title, author = possible_title, possible_author
                break
    title, volume, explicit = split_book_title_and_volume(title, meta.get("currentlyReadingVolume"))
    if not title:
        return None

    # For unspecified manga volumes, prefer Volume 1 before the series cover.
    preferred_volume = volume if explicit else 1
    params = {
        "title": title, "fields": "title,author_name,cover_i",
        "limit": "60",
    }
    docs = get_json("https://openlibrary.org/search.json?" + urllib.parse.urlencode(params)).get("docs", [])
    good = []
    for item in docs:
        if not item.get("cover_i"):
            continue
        if author and not any(
            set(normalized(author).split()).issubset(set(normalized(name).split()))
            for name in item.get("author_name", [])
        ):
            continue
        candidate_title = item.get("title", "")
        if reading_matches_title(candidate_title, title, preferred_volume):
            good.append(item)
    if not good and not explicit:
        good = [item for item in docs if item.get("cover_i") and
                reading_matches_title(item.get("title", ""), title, None) and
                (not author or any(
                    set(normalized(author).split()).issubset(set(normalized(name).split()))
                    for name in item.get("author_name", [])
                ))]
    if good:
        # Multiple editions for the same book can have different cover art.
        # Open Library search is relevance ranked; use its top exact title match.
        return "https://covers.openlibrary.org/b/id/" + str(int(good[0]["cover_i"])) + "-L.jpg"

    if explicit:
        print(f"Reading: volume {volume} of {title} not found; refusing a different volume.")
        return None
    return manga_series_fallback(title, author)


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
            "volume": meta.get("currentlyReadingVolume") if category == "reading" else None,
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
