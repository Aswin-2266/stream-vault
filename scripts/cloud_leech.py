#!/usr/bin/env python3
"""
Cloud Leech Runner
Executed in GitHub Actions (Microsoft Azure Cloud) or Google Colab.
Downloads torrent via aria2c, splits if >1.95 GB, uploads to Telegram Vault,
indexes into MongoDB Atlas, and notifies user with direct stream link.
Uses 0 MB of user mobile hotspot data!
"""

import os
import sys
import math
import shutil
import argparse
import asyncio
import logging
import datetime
import subprocess
import traceback
import certifi
from motor.motor_asyncio import AsyncIOMotorClient

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(message)s")
logger = logging.getLogger("CloudLeech")

# Safe Telegram Free Upload limit (1.95 GB)
TELEGRAM_MAX_BYTES = 1950 * 1024 * 1024

def format_size(bytes_size: int) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} PB"

def apply_crypto_patch():
    try:
        import cryptg
        import hydrogram.crypto.aes as aes
        aes.ige256_encrypt = cryptg.encrypt_ige
        aes.ige256_decrypt = cryptg.decrypt_ige
        logger.info("cryptg MTProto AES acceleration enabled!")
    except Exception as e:
        logger.warning(f"Could not load cryptg: {e}")

def run_aria2c(magnet: str, download_dir: str):
    os.makedirs(download_dir, exist_ok=True)
    aria2 = shutil.which("aria2c")
    if not aria2:
        raise RuntimeError("aria2c not installed on system.")

    logger.info("Starting aria2c cloud torrent download with Tier-1 peer acceleration...")
    cmd = [
        aria2,
        "--seed-time=0",
        "--bt-stop-timeout=120",
        "--bt-tracker-connect-timeout=10",
        "--bt-tracker-timeout=10",
        "--bt-max-peers=100",
        "--enable-dht=true",
        "--dht-listen-port=6881",
        "--enable-peer-exchange=true",
        "--max-connection-per-server=16",
        "--split=16",
        "--min-split-size=1M",
        "--summary-interval=5",
        "--dir", download_dir,
        magnet
    ]
    res = subprocess.run(cmd)
    if res.returncode != 0:
        raise RuntimeError("Torrent download stalled or timed out (no active seeders available). Please choose a release with higher seeds.")

def find_all_video_files(download_dir: str) -> list[str]:
    """Finds all valid video files in the download directory, filtering out tiny sample clips"""
    video_files = []
    for root, _, files in os.walk(download_dir):
        for f in files:
            p = os.path.join(root, f)
            if f.lower().endswith((".mp4", ".mkv", ".avi", ".webm", ".ts", ".m4v")):
                size = os.path.getsize(p)
                video_files.append((p, size))

    if not video_files:
        raise FileNotFoundError("Download completed but no valid video files found.")

    # Filter out sample/trailer clips (< 25 MB) if main files exist
    main_files = [p for p, size in video_files if size >= 25 * 1024 * 1024]
    if not main_files:
        main_files = [p for p, size in video_files]

    # Sort naturally by filename (e.g. S01E01, S01E02...)
    main_files.sort(key=lambda x: os.path.basename(x).lower())
    logger.info(f"Detected {len(main_files)} video file(s) to process.")
    return main_files

def split_video(file_path: str) -> list[str]:
    file_size = os.path.getsize(file_path)
    if file_size <= TELEGRAM_MAX_BYTES:
        return [file_path]

    logger.info(f"File exceeds 1.95 GB ({format_size(file_size)}). Performing lossless ffmpeg split...")
    # Get duration
    try:
        cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", file_path]
        duration = float(subprocess.check_output(cmd).decode().strip())
    except Exception:
        duration = 0.0

    num_parts = math.ceil(file_size / TELEGRAM_MAX_BYTES)
    if num_parts < 2 or duration <= 0:
        return [file_path]

    segment_time = duration / num_parts
    base_name, ext = os.path.splitext(file_path)
    out_pattern = f"{base_name}.part%02d{ext}"

    split_cmd = [
        "ffmpeg", "-i", file_path,
        "-c", "copy", "-map", "0",
        "-f", "segment", "-segment_time", str(segment_time),
        "-reset_timestamps", "1",
        out_pattern
    ]
    subprocess.run(split_cmd, check=True)

    directory = os.path.dirname(file_path) or "."
    base_fn = os.path.basename(base_name)
    parts = []
    for f in sorted(os.listdir(directory)):
        if f.startswith(base_fn + ".part") and f.endswith(ext):
            parts.append(os.path.join(directory, f))

    return parts or [file_path]

async def process_cloud_leech(magnet: str, title: str, user_id: int, task_id: str = None):
    # Load required environment variables
    api_id = int(os.getenv("API_ID", "0"))
    api_hash = os.getenv("API_HASH", "")
    bot_token = os.getenv("BOT_TOKEN", "")
    raw_log = os.getenv("LOG_CHANNEL_ID", "0").strip()
    if raw_log and not raw_log.startswith("-"):
        raw_log = f"-{raw_log}"
    try:
        log_channel_id = int(raw_log)
    except ValueError:
        log_channel_id = 0
    mongo_uri = os.getenv("MONGO_URI", "")
    stream_url = os.getenv("STREAM_URL", "").rstrip("/")

    if not all([api_id, api_hash, bot_token, log_channel_id, mongo_uri]):
        logger.error("Missing credentials in environment variables.")
        sys.exit(1)

    apply_crypto_patch()

    from hydrogram import Client
    bot = Client(
        name="cloud_leech_runner",
        api_id=api_id,
        api_hash=api_hash,
        bot_token=bot_token,
        in_memory=True
    )

    mongo = AsyncIOMotorClient(mongo_uri, tlsCAFile=certifi.where())
    db = mongo["stream_vault"]
    files_col = db["files"]
    queue_col = db["leech_queue"]
    error_logs_col = db["error_logs"]
    system_logs_col = db["system_logs"]

    download_dir = "temp_cloud_leech"

    # Step 1: Initial user notification and MongoDB start log
    try:
        await system_logs_col.insert_one({
            "level": "INFO",
            "source": "github_actions",
            "module": "CloudLeech",
            "message": f"Cloud Leech Worker started for: {title}",
            "context": {"user_id": user_id, "task_id": task_id},
            "created_at": datetime.datetime.utcnow()
        })
    except Exception:
        pass

    if user_id:
        try:
            await bot.start()
            await bot.send_message(
                chat_id=user_id,
                text=f"⚡ **Cloud Leech Started:** `{title}`\nDownloading at gigabit cloud speeds (0 MB hotspot data)..."
            )
            await bot.stop()
        except Exception as e:
            logger.warning(f"Could not send start notification: {e}")

    try:
        # Step 2: Download torrent files via aria2c
        # (Bot is intentionally stopped during download so MTProto session timestamps never desynchronize!)
        run_aria2c(magnet, download_dir)

        # Step 3: Discover all video files (supports series packs and multi-episode torrents)
        video_files = find_all_video_files(download_dir)

        # Step 4: Fresh bot connection for synchronized, high-speed upload
        await bot.start()

        for vid_idx, video_file in enumerate(video_files, start=1):
            file_label = f"[{vid_idx}/{len(video_files)}] " if len(video_files) > 1 else ""
            parts = split_video(video_file)
            is_split = len(parts) > 1

            for part_idx, part_path in enumerate(parts, start=1):
                part_name = os.path.basename(part_path)
                part_size = os.path.getsize(part_path)
                part_label = f" (Part {part_idx}/{len(parts)})" if is_split else ""

                logger.info(f"{file_label}Uploading {part_name}{part_label} to Telegram Vault...")
                uploaded = await bot.send_document(
                    chat_id=log_channel_id,
                    document=part_path,
                    caption=f"🎬 {part_name}{part_label}"
                )
                media = uploaded.video or uploaded.document
                vault_file_id = media.file_id
                unique_id = media.file_unique_id

                # Save in database
                file_doc = {
                    "file_name": part_name,
                    "file_size": part_size,
                    "file_id": vault_file_id,
                    "unique_id": unique_id,
                    "source_chat_id": log_channel_id,
                    "mime_type": "video/mp4",
                    "caption": f"🎬 {part_name}"
                }
                await files_col.update_one({"unique_id": unique_id}, {"$set": file_doc}, upsert=True)

                # Deliver directly to user
                if user_id:
                    direct_link = f"{stream_url}/stream/{unique_id}" if stream_url else "Indexed in Vault"
                    msg_caption = (
                        f"✅ **Leech Complete:** `{part_name}`{part_label}\n\n"
                        f"📦 **Size:** `{format_size(part_size)}`\n"
                        f"🔗 **Direct Stream / Download Link:**\n`{direct_link}`"
                    )
                    try:
                        await bot.send_cached_media(
                            chat_id=user_id,
                            file_id=vault_file_id,
                            caption=msg_caption
                        )
                    except Exception as e:
                        logger.warning(f"Could not deliver cached media to user: {e}")

        # Update queue task if applicable
        if task_id:
            from bson import ObjectId
            try:
                await queue_col.update_one({"_id": ObjectId(task_id)}, {"$set": {"status": "completed"}})
            except Exception:
                pass

        logger.info("Cloud Leech completed successfully!")
        try:
            await system_logs_col.insert_one({
                "level": "INFO",
                "source": "github_actions",
                "module": "CloudLeech",
                "message": f"Cloud Leech completed successfully for: {title} ({len(video_files)} video file(s))",
                "context": {"user_id": user_id, "task_id": task_id, "videos_count": len(video_files)},
                "created_at": datetime.datetime.utcnow()
            })
        except Exception:
            pass

    except Exception as e:
        logger.error(f"Cloud Leech failed: {e}", exc_info=True)
        tb_str = traceback.format_exc()
        try:
            await error_logs_col.insert_one({
                "level": "ERROR",
                "source": "github_actions",
                "module": "CloudLeech",
                "message": str(e),
                "traceback": tb_str,
                "context": {"title": title, "user_id": user_id, "task_id": task_id},
                "created_at": datetime.datetime.utcnow()
            })
        except Exception:
            pass

        if user_id:
            try:
                if not bot.is_connected:
                    await bot.start()
                await bot.send_message(chat_id=user_id, text=f"❌ **Cloud Leech Failed:** `{e}`")
            except Exception:
                pass
        if task_id:
            from bson import ObjectId
            try:
                await queue_col.update_one({"_id": ObjectId(task_id)}, {"$set": {"status": "failed", "error": str(e)}})
            except Exception:
                pass
        sys.exit(1)

    finally:
        if bot.is_connected:
            await bot.stop()
        if os.path.exists(download_dir):
            shutil.rmtree(download_dir, ignore_errors=True)

def main():
    parser = argparse.ArgumentParser(description="Cloud Leech Runner")
    parser.add_argument("--magnet", required=True, help="Magnet URI or Torrent URL")
    parser.add_argument("--title", default="Movie", help="Display title")
    parser.add_argument("--user_id", type=int, default=0, help="Telegram User ID to notify")
    parser.add_argument("--task_id", default=None, help="MongoDB queue task ID")
    args = parser.parse_args()

    asyncio.run(process_cloud_leech(args.magnet, args.title, args.user_id, args.task_id))

if __name__ == "__main__":
    main()
