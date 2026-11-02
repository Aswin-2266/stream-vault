import os
import re
import requests
import subprocess
import shutil
import urllib.parse
from bot.handlers.indexer import format_size

YTS_API_URL = "https://yts.mx/api/v2/list_movies.json"
APIBAY_API_URL = "https://apibay.org/q.php"

STANDARD_TRACKERS = [
    "udp://tracker.opentrackr.org:1337/announce",
    "udp://open.stealth.si:80/announce",
    "udp://tracker.openbittorrent.com:6969/announce",
    "udp://tracker.torrent.eu.org:451/announce",
    "udp://opentracker.i2p.rocks:6969/announce",
    "udp://open.demonii.com:1337/announce"
]

LANGUAGE_MAP = {
    "tamil": ["tamil", "tam"],
    "telugu": ["telugu", "tel"],
    "hindi": ["hindi", "hin"],
    "malayalam": ["malayalam", "mal"],
    "kannada": ["kannada", "kan"],
    "english": ["english", "eng"]
}

# Common spelling / alias corrections for popular titles
TITLE_CORRECTIONS = {
    "shashank": "shawshank",
    "shawshank redemption": "shawshank redemption",
    "avatar 2": "avatar the way of water",
    "spiderman": "spider-man",
    "jailer": "jailer"
}

def extract_language_and_title(query: str) -> tuple[str, str | None]:
    """
    Separates language keywords from the core movie search query.
    e.g. 'Shashank redemption tamil' -> ('shawshank redemption', 'tamil')
    """
    tokens = query.strip().lower().split()
    detected_lang = None
    clean_tokens = []

    for t in tokens:
        matched = False
        for lang_name, aliases in LANGUAGE_MAP.items():
            if t in aliases or t == lang_name:
                detected_lang = lang_name
                matched = True
                break
        if not matched:
            clean_tokens.append(t)

    clean_query = " ".join(clean_tokens)
    # Apply phonetic/alias corrections
    for wrong, right in TITLE_CORRECTIONS.items():
        if wrong in clean_query:
            clean_query = clean_query.replace(wrong, right)

    return clean_query or query, detected_lang

def detect_audio_languages(title: str) -> str:
    """Detects audio languages present in release title and returns clean string"""
    lower = title.lower()
    found = []

    if any(k in lower for k in ["tamil", "tam"]):
        found.append("Tamil")
    if any(k in lower for k in ["telugu", "tel"]):
        found.append("Telugu")
    if any(k in lower for k in ["hindi", "hin"]):
        found.append("Hindi")
    if any(k in lower for k in ["malayalam", "mal"]):
        found.append("Malayalam")
    if any(k in lower for k in ["kannada", "kan"]):
        found.append("Kannada")
    if any(k in lower for k in ["english", "eng", "yts", "yify", "bluray"]):
        found.append("English")

    if "multi" in lower or "dual" in lower:
        if not found:
            return "Multi-Audio"
        elif "Multi-Audio" not in found:
            found.insert(0, "Multi-Audio")

    return " + ".join(found) if found else "Original Audio"

def detect_resolution(title: str) -> str:
    lower = title.lower()
    if any(k in lower for k in ["2160p", "4k", "uhd"]):
        return "2160p (4K)"
    if "1080p" in lower:
        return "1080p"
    if "720p" in lower:
        return "720p"
    if "480p" in lower:
        return "480p"
    if "hdrip" in lower:
        return "HDRip"
    if "webrip" in lower or "web-dl" in lower or "webdl" in lower:
        return "WEB-DL"
    return "HD"

def build_magnet(info_hash: str, display_name: str) -> str:
    """Constructs a standard magnet URI with announce trackers"""
    params = [
        ("xt", f"urn:btih:{info_hash}"),
        ("dn", display_name)
    ]
    for tr in STANDARD_TRACKERS:
        params.append(("tr", tr))
    return f"magnet:?{urllib.parse.urlencode(params)}"

def search_torrents(query: str, limit: int = 6) -> list[dict]:
    """
    Dual Search Aggregator with Smart Language Prioritization:
    1. Extracts requested language (e.g. 'tamil').
    2. Searches clean title on Apibay & YTS.
    3. Ranks matching language releases at the top.
    """
    clean_query, requested_lang = extract_language_and_title(query)
    results = []
    seen_hashes = set()

    # Query 1: Apibay (The Pirate Bay / Open Trackers)
    try:
        resp = requests.get(
            APIBAY_API_URL,
            params={"q": clean_query, "cat": "200"},
            timeout=8
        )
        if resp.status_code == 200:
            items = resp.json()
            if isinstance(items, list):
                for item in items:
                    info_hash = item.get("info_hash", "").upper()
                    if not info_hash or info_hash in seen_hashes or item.get("name") == "No results returned":
                        continue
                    
                    try:
                        seeds = int(item.get("seeders", 0))
                    except (ValueError, TypeError):
                        seeds = 0

                    name = item.get("name", "Unknown Release")
                    try:
                        size_bytes = int(item.get("size", 0))
                        size_str = format_size(size_bytes)
                    except (ValueError, TypeError):
                        size_str = "N/A"

                    # Calculate seed status badge
                    if seeds >= 10:
                        seed_badge = f"⚡ {seeds} Seeds"
                    elif seeds > 0:
                        seed_badge = f"⚠️ {seeds} Seeds (Low)"
                    else:
                        seed_badge = "❌ 0 Seeds (Dead)"

                    languages = detect_audio_languages(name)
                    resolution = detect_resolution(name)
                    magnet = build_magnet(info_hash, name)
                    seen_hashes.add(info_hash)

                    # Language match score
                    has_requested_lang = False
                    if requested_lang:
                        aliases = LANGUAGE_MAP.get(requested_lang, [requested_lang])
                        if any(a in name.lower() for a in aliases) or "multi" in name.lower() or "dual" in name.lower():
                            has_requested_lang = True

                    results.append({
                        "title": name,
                        "quality": resolution,
                        "languages": languages,
                        "size": size_str,
                        "seeds": seeds,
                        "seed_badge": seed_badge,
                        "magnet": magnet,
                        "hash": info_hash,
                        "has_requested_lang": has_requested_lang,
                        "source": "Apibay / OpenTracker"
                    })
    except Exception as e:
        print(f"[!] Apibay search error: {e}")

    # Query 2: YTS API (Hollywood releases)
    try:
        yts_resp = requests.get(
            YTS_API_URL,
            params={"query_term": clean_query, "limit": limit, "sort_by": "seeds"},
            timeout=5
        )
        if yts_resp.status_code == 200:
            movies = yts_resp.json().get("data", {}).get("movies", [])
            for movie in movies:
                title = movie.get("title")
                year = movie.get("year")
                for torrent in movie.get("torrents", []):
                    torrent_hash = torrent.get("hash", "").upper()
                    if not torrent_hash or torrent_hash in seen_hashes:
                        continue

                    quality = torrent.get("quality", "720p")
                    size = torrent.get("size", "N/A")
                    seeds = torrent.get("seeds", 0)
                    full_title = f"{title} ({year}) [{quality}] [YTS.MX]"
                    magnet = build_magnet(torrent_hash, full_title)
                    seen_hashes.add(torrent_hash)

                    if seeds >= 10:
                        seed_badge = f"⚡ {seeds} Seeds"
                    elif seeds > 0:
                        seed_badge = f"⚠️ {seeds} Seeds (Low)"
                    else:
                        seed_badge = "❌ 0 Seeds (Dead)"

                    has_requested_lang = (requested_lang == "english")

                    results.append({
                        "title": full_title,
                        "quality": quality,
                        "languages": "English",
                        "size": size,
                        "seeds": seeds,
                        "seed_badge": seed_badge,
                        "magnet": magnet,
                        "hash": torrent_hash,
                        "has_requested_lang": has_requested_lang,
                        "source": "YTS"
                    })
    except Exception:
        pass

    # Sort results: First prioritize requested language, then sort by seeds descending
    results.sort(key=lambda x: (x.get("has_requested_lang", False), x.get("seeds", 0)), reverse=True)
    return results[:limit]

def download_torrent_file(torrent_source: str, download_dir: str = "downloads") -> str:
    os.makedirs(download_dir, exist_ok=True)
    aria2_path = shutil.which("aria2c")
    if not aria2_path:
        raise RuntimeError("aria2c executable is not installed or not in system PATH.")

    cmd = [
        "aria2c",
        "--seed-time=0",
        "--bt-stop-timeout=120",
        "--max-connection-per-server=8",
        "--split=8",
        "--min-split-size=1M",
        "--dir", download_dir,
        torrent_source
    ]

    print(f"[+] Starting aria2c download for: {torrent_source[:60]}...")
    process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if process.returncode != 0:
        raise RuntimeError(f"aria2c download failed: {process.stderr.decode()[:200]}")

    largest_file = None
    max_size = 0
    for root, _, files in os.walk(download_dir):
        for f in files:
            full_path = os.path.join(root, f)
            size = os.path.getsize(full_path)
            if f.lower().endswith((".mp4", ".mkv", ".avi", ".webm", ".ts", ".m4v")) and size > max_size:
                max_size = size
                largest_file = full_path

    if not largest_file:
        raise FileNotFoundError("Download completed but no valid video file found.")

    return largest_file
