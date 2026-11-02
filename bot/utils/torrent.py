import os
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
    Dual Search Aggregator:
    1. YTS (Clean Hollywood releases)
    2. Apibay / Open Trackers (Regional: Tamil, Telugu, Hindi, Multi-Audio, and Scene releases)
    Merges, deduplicates, and sorts by seed count.
    """
    results = []
    seen_hashes = set()

    # Query 1: Apibay (The Pirate Bay / Open Trackers) - excellent regional & Indian movie coverage
    try:
        resp = requests.get(
            APIBAY_API_URL,
            params={"q": query, "cat": "200"},  # Category 200 = Video
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

                    if seeds <= 0:
                        continue

                    try:
                        size_bytes = int(item.get("size", 0))
                        size_str = format_size(size_bytes)
                    except (ValueError, TypeError):
                        size_str = "N/A"

                    name = item.get("name", "Unknown Release")
                    magnet = build_magnet(info_hash, name)
                    seen_hashes.add(info_hash)

                    results.append({
                        "title": name,
                        "quality": "Multi-Audio / HD" if any(w in name.lower() for w in ["tamil", "telugu", "hindi", "multi"]) else "HD",
                        "size": size_str,
                        "size_bytes": size_bytes if 'size_bytes' in locals() else 0,
                        "seeds": seeds,
                        "magnet": magnet,
                        "hash": info_hash,
                        "source": "Apibay / OpenTracker"
                    })
    except Exception as e:
        print(f"[!] Apibay search error: {e}")

    # Query 2: YTS API (Hollywood releases, if accessible without ISP DNS blocks)
    try:
        yts_resp = requests.get(
            YTS_API_URL,
            params={"query_term": query, "limit": limit, "sort_by": "seeds"},
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
                    full_title = f"{title} ({year}) [{quality}]"
                    magnet = build_magnet(torrent_hash, full_title)
                    seen_hashes.add(torrent_hash)

                    results.append({
                        "title": full_title,
                        "quality": quality,
                        "size": size,
                        "size_bytes": 0,
                        "seeds": seeds,
                        "magnet": magnet,
                        "hash": torrent_hash,
                        "source": "YTS"
                    })
    except Exception as e:
        # Expected on Indian ISPs with DOT DNS blocks; Apibay acts as primary
        pass

    # Sort all results by seed count descending
    results.sort(key=lambda x: x.get("seeds", 0), reverse=True)
    return results[:limit]

def download_torrent_file(torrent_source: str, download_dir: str = "downloads") -> str:
    """
    Downloads torrent/magnet using aria2c into download_dir.
    Returns the absolute path of the downloaded video file.
    """
    os.makedirs(download_dir, exist_ok=True)
    
    aria2_path = shutil.which("aria2c")
    if not aria2_path:
        raise RuntimeError("aria2c executable is not installed or not in system PATH.")

    cmd = [
        "aria2c",
        "--seed-time=0",
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

    # Find the largest media file in the download directory
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
