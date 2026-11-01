import os
import requests
import subprocess
import shutil

YTS_API_URL = "https://yts.mx/api/v2/list_movies.json"

def search_torrents(query: str, limit: int = 5) -> list[dict]:
    """
    Search for high-seed movies via the YTS API.
    Returns clean metadata: title, year, quality, size, magnet/download link, seeds.
    """
    results = []
    try:
        response = requests.get(
            YTS_API_URL,
            params={"query_term": query, "limit": limit, "sort_by": "seeds"},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            movies = data.get("data", {}).get("movies", [])
            for movie in movies:
                title = movie.get("title")
                year = movie.get("year")
                for torrent in movie.get("torrents", []):
                    quality = torrent.get("quality", "720p")
                    size = torrent.get("size", "N/A")
                    seeds = torrent.get("seeds", 0)
                    torrent_url = torrent.get("url")
                    torrent_hash = torrent.get("hash")
                    
                    magnet = (
                        f"magnet:?xt=urn:btih:{torrent_hash}&dn="
                        f"{requests.utils.quote(f'{title} ({year}) [{quality}]')}"
                        f"&tr=udp://open.demonii.com:1337/announce"
                        f"&tr=udp://tracker.openbittorrent.com:80"
                        f"&tr=udp://tracker.coppersurfer.tk:6969"
                        f"&tr=udp://glotorrents.pw:6969/announce"
                    )

                    results.append({
                        "title": f"{title} ({year}) [{quality}]",
                        "quality": quality,
                        "size": size,
                        "seeds": seeds,
                        "magnet": magnet,
                        "torrent_url": torrent_url
                    })
    except Exception as e:
        print(f"[!] Torrent search error: {e}")

    return results

def download_torrent_file(torrent_source: str, download_dir: str = "downloads") -> str:
    """
    Downloads torrent/magnet using aria2c into download_dir.
    Returns the absolute path of the downloaded video file.
    """
    os.makedirs(download_dir, exist_ok=True)
    
    # Check if aria2c is installed
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
            # Filter for common video extensions
            if f.lower().endswith((".mp4", ".mkv", ".avi", ".webm")) and size > max_size:
                max_size = size
                largest_file = full_path

    if not largest_file:
        raise FileNotFoundError("Download completed but no valid video file found.")

    return largest_file
