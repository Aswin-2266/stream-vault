import os
import re
import requests
import subprocess
import shutil
import urllib.parse
import functools
from bot.handlers.indexer import format_size

YTS_API_URL = "https://yts.mx/api/v2/list_movies.json"
APIBAY_API_URL = "https://apibay.org/q.php"
BITSEARCH_API_URL = "https://bitsearch.to/api/v1/search"

# In-memory torrent release cache keyed by info_hash for instant 0ms lookups
TORRENT_CACHE: dict[str, dict] = {}

# 30+ Tier-1 Live BitTorrent DHT Trackers for peer acceleration
STANDARD_TRACKERS = [
    "udp://tracker.opentrackr.org:1337/announce",
    "udp://open.stealth.si:80/announce",
    "udp://tracker.torrent.eu.org:451/announce",
    "udp://open.demonii.com:1337/announce",
    "udp://tracker.qu.ax:6969/announce",
    "udp://open.tracker.cl:1337/announce",
    "udp://tracker.ducks.party:1984/announce",
    "udp://tracker.bittor.pw:1337/announce",
    "udp://explodie.org:6969/announce",
    "udp://tracker.tryhackx.org:6969/announce",
    "udp://tracker.therarbg.com:6969/announce",
    "udp://tracker.filemail.com:6969/announce",
    "udp://tracker.moeking.me:6969/announce",
    "udp://tracker-udp.gbitt.info:80/announce",
    "udp://p4p.arenabg.com:1337/announce",
    "udp://opentracker.i2p.rocks:6969/announce",
    "udp://tracker.openbittorrent.com:6969/announce",
    "udp://tracker.dler.org:6969/announce",
    "udp://bt1.archive.org:6969/announce",
    "udp://newton.baskerville.pro:2710/announce",
    "udp://free-tracker.zooki.xyz:6969/announce",
    "udp://ep2020.ddns.net:6969/announce",
    "udp://ch3oh.ru:6969/announce",
    "udp://bubu.mapfactor.com:6969/announce",
    "udp://amigacity.xyz:6969/announce",
    "udp://admin.videoenpoche.info:6969/announce",
    "udp://9.rarbg.to:2920/announce",
    "http://tracker.openbittorrent.com:80/announce",
    "https://tracker.tamersunion.org:443/announce",
    "http://tracker.bt4g.com:2095/announce"
]

LANGUAGE_MAP = {
    "tamil": ["tamil", "tam"],
    "telugu": ["telugu", "tel"],
    "hindi": ["hindi", "hin"],
    "malayalam": ["malayalam", "mal"],
    "kannada": ["kannada", "kan"],
    "english": ["english", "eng"]
}

@functools.lru_cache(maxsize=512)
def get_imdb_meta(query: str) -> dict | None:
    """
    Queries IMDb open suggestions API and returns metadata including canonical IMDb ID,
    title, and release year.
    e.g. 'Jailer' -> {'id': 'tt11663228', 'title': 'Jailer', 'year': 2023}
    """
    if not query or len(query.strip()) < 2:
        return None

    clean = query.strip()
    first_char = clean[0].lower() if clean[0].isalnum() else "a"
    slug = clean.lower().replace(" ", "_")
    url = f"https://v3.sg.media-imdb.com/suggestion/{first_char}/{urllib.parse.quote(slug)}.json"

    try:
        resp = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
            timeout=2.5
        )
        if resp.status_code == 200:
            items = resp.json().get("d", [])
            candidates = [
                x for x in items
                if x.get("q") in ["feature", "TV series", "movie", "tv movie", "tv mini series", "podcastSeries"]
            ]
            if not candidates and items:
                candidates = items
            if not candidates:
                return None

            # 1. Prioritize exact title matches (excluding unreleased future years if released exists)
            exact = [x for x in candidates if x.get("l", "").strip().lower() == clean.lower()]
            if exact:
                exact.sort(key=lambda x: (x.get("y", 0) > 2026, x.get("rank", 9999999)))
                chosen = exact[0]
                return {"id": chosen.get("id"), "title": chosen.get("l"), "year": chosen.get("y")}

            # 2. Otherwise pick the highest-ranked (most popular) title
            candidates.sort(key=lambda x: x.get("rank", 9999999))
            chosen = candidates[0]
            return {"id": chosen.get("id"), "title": chosen.get("l"), "year": chosen.get("y")}
    except Exception:
        pass

    return None

@functools.lru_cache(maxsize=512)
def get_imdb_suggestion(query: str) -> str | None:
    """
    Queries IMDb open suggestions API and returns an optional suggested canonical title
    only if it differs from the user's typed query.
    Returns None if no suggestion is needed or if already matched.
    """
    meta = get_imdb_meta(query)
    if not meta:
        return None
    suggested = meta.get("title")
    if suggested and suggested.strip().lower() != query.strip().lower():
        return suggested
    return None

def extract_language_and_title(query: str) -> tuple[str, str | None]:
    """
    Separates language keywords from the core movie search query.
    Leaves user's typed title 100% exact without forced auto-correction.
    e.g. 'Shashank redemption tamil' -> ('Shashank redemption', 'tamil')
         'Jailer' -> ('Jailer', None)
    """
    tokens = query.strip().split()
    detected_lang = None
    clean_tokens = []

    for t in tokens:
        matched = False
        t_low = t.lower()
        for lang_name, aliases in LANGUAGE_MAP.items():
            if t_low in aliases or t_low == lang_name:
                detected_lang = lang_name
                matched = True
                break
        if not matched:
            clean_tokens.append(t)

    clean_query = " ".join(clean_tokens)
    return clean_query or query, detected_lang

def get_cached_torrent(info_hash: str) -> dict | None:
    """Retrieves a cached torrent release by info hash"""
    return TORRENT_CACHE.get(info_hash.upper())

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

def search_torrentio(imdb_id: str, requested_lang: str | None = None) -> list[dict]:
    """
    Queries Torrentio Stream Aggregator for verified Indian Regional,
    Bollywood, and Hollywood releases across TamilBlasters, TamilMV, 1337x,
    TorrentGalaxy, EZTV, and ThePirateBay.
    """
    results = []
    endpoints = [
        f"https://torrentio.strem.fun/stream/movie/{imdb_id}.json",
        f"https://torrentio.strem.fun/stream/series/{imdb_id}:1:1.json"
    ]

    for url in endpoints:
        try:
            resp = requests.get(
                url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
                timeout=4
            )
            if resp.status_code == 200:
                streams = resp.json().get("streams", [])
                if not streams:
                    continue

                for s in streams:
                    info_hash = s.get("infoHash", "").upper()
                    if not info_hash or len(info_hash) != 40:
                        continue

                    raw_title = s.get("title", "")
                    lines = [l.strip() for l in raw_title.split("\n") if l.strip()]
                    name = lines[0] if lines else f"Release {info_hash[:8]}"

                    # Extract seeders: 👤 (\d+)
                    seed_m = re.search(r"[👤👥]\s*(\d+)", raw_title)
                    seeds = int(seed_m.group(1)) if seed_m else 5

                    # Extract file size: 💾 ([\d\.]+ ?[GMK]B)
                    size_m = re.search(r"💾\s*([\d\.]+\s*[GMK]B)", raw_title, re.IGNORECASE)
                    size_str = size_m.group(1).upper() if size_m else "N/A"

                    # Extract provider/tracker tag: ⚙️ ([^\n]+)
                    src_m = re.search(r"⚙️\s*([^\n]+)", raw_title)
                    source_tag = src_m.group(1).strip() if src_m else "Torrentio"

                    if seeds >= 15:
                        seed_badge = f"⚡ {seeds} Seeds"
                    elif seeds >= 3:
                        seed_badge = f"⚡ {seeds} Seeds"
                    elif seeds > 0:
                        seed_badge = f"⚠️ {seeds} Seeds (Slow)"
                    else:
                        seed_badge = "❌ 0 Seeds (Dead)"

                    languages = detect_audio_languages(name + " " + raw_title)
                    resolution = detect_resolution(name)
                    magnet = build_magnet(info_hash, name)

                    has_requested_lang = False
                    if requested_lang:
                        aliases = LANGUAGE_MAP.get(requested_lang, [requested_lang])
                        full_haystack = (name + " " + raw_title).lower()
                        if any(a in full_haystack for a in aliases) or "multi" in full_haystack or "dual" in full_haystack:
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
                        "source": f"Torrentio ({source_tag})"
                    })

                # If movie results were found, skip series endpoint check
                if results:
                    break
        except Exception:
            pass

    return results

def search_torrents(query: str, limit: int = 35) -> list[dict]:
    """
    Multi-Engine Search Aggregator with Smart Language Prioritization:
    1. Extracts requested language (e.g. 'tamil').
    2. Queries Torrentio (TamilBlasters, TamilMV, 1337x, TGx) via canonical IMDb ID.
    3. Aggregates releases across Apibay, BitSearch, and YTS.
    4. Injects 30+ Tier-1 DHT announce trackers into every magnet.
    5. Ranks matching language releases at the top, followed by seeders count.
    """
    clean_query, requested_lang = extract_language_and_title(query)
    results = []
    seen_hashes = set()

    # Query 0: Torrentio Regional Aggregator (TamilBlasters, TamilMV, 1337x, TGx)
    try:
        imdb_meta = get_imdb_meta(clean_query)
        if imdb_meta and imdb_meta.get("id"):
            torrentio_results = search_torrentio(imdb_meta["id"], requested_lang)
            for item in torrentio_results:
                info_hash = item["hash"]
                if info_hash not in seen_hashes:
                    seen_hashes.add(info_hash)
                    results.append(item)
    except Exception:
        pass

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
                    if seeds >= 15:
                        seed_badge = f"⚡ {seeds} Seeds"
                    elif seeds >= 3:
                        seed_badge = f"⚡ {seeds} Seeds"
                    elif seeds > 0:
                        seed_badge = f"⚠️ {seeds} Seeds (Slow)"
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

    # Query 2: BitSearch API (Indian Regional, TamilBlasters, Global Trackers)
    try:
        bit_resp = requests.get(
            BITSEARCH_API_URL,
            params={"q": clean_query, "page": 1},
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
            timeout=3
        )
        if bit_resp.status_code == 200:
            items = bit_resp.json().get("results", [])
            for item in items:
                info_hash = item.get("infohash", "").upper()
                if not info_hash or info_hash in seen_hashes:
                    continue

                try:
                    seeds = int(item.get("seeders", 0))
                except (ValueError, TypeError):
                    seeds = 0

                name = item.get("title", "Unknown Release")
                try:
                    size_bytes = int(item.get("size", 0))
                    size_str = format_size(size_bytes)
                except (ValueError, TypeError):
                    size_str = "N/A"

                if seeds >= 15:
                    seed_badge = f"⚡ {seeds} Seeds"
                elif seeds >= 3:
                    seed_badge = f"⚡ {seeds} Seeds"
                elif seeds > 0:
                    seed_badge = f"⚠️ {seeds} Seeds (Slow)"
                else:
                    seed_badge = "❌ 0 Seeds (Dead)"

                languages = detect_audio_languages(name)
                resolution = detect_resolution(name)
                magnet = build_magnet(info_hash, name)
                seen_hashes.add(info_hash)

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
                    "source": "BitSearch"
                })
    except Exception:
        pass  # Gracefully skip if ISP blocks torrent indexer domain

    # Query 3: YTS API (Hollywood releases)
    try:
        yts_resp = requests.get(
            YTS_API_URL,
            params={"query_term": clean_query, "limit": 20, "sort_by": "seeds"},
            timeout=3
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

                    if seeds >= 15:
                        seed_badge = f"⚡ {seeds} Seeds"
                    elif seeds >= 3:
                        seed_badge = f"⚡ {seeds} Seeds"
                    elif seeds > 0:
                        seed_badge = f"⚠️ {seeds} Seeds (Slow)"
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
    final_results = results[:limit]

    # Populate in-memory cache for instant 0ms retrieval by hash
    for item in final_results:
        TORRENT_CACHE[item["hash"]] = item

    return final_results

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
