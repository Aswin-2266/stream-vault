import os
import time
import shutil
import asyncio
import logging
import datetime
import config
from bot.utils.database import db

logger = logging.getLogger("StorageCleaner")

def get_disk_usage(path: str = ".") -> dict:
    """Returns disk usage stats in GB and percentage."""
    try:
        stat_path = path if os.path.exists(path) else "."
        total, used, free = shutil.disk_usage(stat_path)
        pct = (used / total) * 100 if total > 0 else 0
        return {
            "total_gb": round(total / (1024 ** 3), 2),
            "used_gb": round(used / (1024 ** 3), 2),
            "free_gb": round(free / (1024 ** 3), 2),
            "percent_used": round(pct, 2)
        }
    except Exception as e:
        logger.warning(f"Could not calculate disk usage for {path}: {e}")
        return {"total_gb": 0, "used_gb": 0, "free_gb": 0, "percent_used": 0}

def clean_storage() -> dict:
    """
    Automated FIFO Rolling Storage Purge:
    1. Removes files older than config.STORAGE_RETENTION_DAYS (default 3 days).
    2. If disk usage exceeds config.MAX_DISK_USAGE_PERCENT (default 75%),
       deletes oldest files first until disk usage drops below the safe threshold.
    Note: Media is already permanently safe in Telegram Vault channel!
    """
    download_dir = config.DOWNLOAD_DIR
    if not os.path.exists(download_dir):
        return {"deleted_files": 0, "freed_mb": 0.0, "reason": "dir_not_found"}

    now = time.time()
    retention_seconds = config.STORAGE_RETENTION_DAYS * 86400
    deleted_files = 0
    freed_bytes = 0

    # Collect all video and media files with metadata
    candidates = []
    for root, _, files in os.walk(download_dir):
        for f in files:
            filepath = os.path.join(root, f)
            try:
                st = os.stat(filepath)
                candidates.append({
                    "path": filepath,
                    "name": f,
                    "mtime": st.st_mtime,
                    "size": st.st_size
                })
            except Exception:
                pass

    # Pass 1: Retention-based purge (> STORAGE_RETENTION_DAYS old)
    remaining_candidates = []
    for item in candidates:
        age_sec = now - item["mtime"]
        if age_sec > retention_seconds:
            try:
                os.remove(item["path"])
                deleted_files += 1
                freed_bytes += item["size"]
                logger.info(f"[Retention Purge] Deleted cached file older than {config.STORAGE_RETENTION_DAYS}d: {item['name']}")
            except Exception as e:
                logger.warning(f"Could not delete {item['path']}: {e}")
        else:
            remaining_candidates.append(item)

    # Pass 2: Disk threshold purge (if disk usage > MAX_DISK_USAGE_PERCENT)
    usage = get_disk_usage(download_dir)
    target_pct = max(10, config.MAX_DISK_USAGE_PERCENT - 10)  # e.g. purge until 65%

    if usage["percent_used"] > config.MAX_DISK_USAGE_PERCENT:
        logger.warning(f"Disk usage ({usage['percent_used']}%) exceeds threshold ({config.MAX_DISK_USAGE_PERCENT}%). Initiating FIFO purge...")
        # Sort remaining candidates by modification time (oldest first)
        remaining_candidates.sort(key=lambda x: x["mtime"])

        for item in remaining_candidates:
            try:
                os.remove(item["path"])
                deleted_files += 1
                freed_bytes += item["size"]
                logger.info(f"[FIFO Threshold Purge] Deleted oldest cached file: {item['name']}")
            except Exception as e:
                logger.warning(f"Could not delete {item['path']}: {e}")

            # Re-check disk usage
            usage = get_disk_usage(download_dir)
            if usage["percent_used"] <= target_pct:
                break

    # Clean up empty subdirectories
    for root, dirs, _ in os.walk(download_dir, topdown=False):
        for d in dirs:
            dirpath = os.path.join(root, d)
            try:
                if not os.listdir(dirpath):
                    os.rmdir(dirpath)
            except Exception:
                pass

    freed_mb = round(freed_bytes / (1024 * 1024), 2)
    if deleted_files > 0:
        logger.info(f"Storage Cleaner Summary: Deleted {deleted_files} files, freed {freed_mb} MB.")

    return {
        "deleted_files": deleted_files,
        "freed_mb": freed_mb,
        "current_usage": usage
    }

async def periodic_cleaner_task():
    """Background task running every 1 hour to enforce rolling cache retention."""
    logger.info(f"Starting Storage Cleaner Daemon (Retention: {config.STORAGE_RETENTION_DAYS} days, Max Disk: {config.MAX_DISK_USAGE_PERCENT}%)...")
    while True:
        try:
            res = clean_storage()
            if res.get("deleted_files", 0) > 0 and db.db is not None:
                try:
                    await db.db["system_logs"].insert_one({
                        "level": "INFO",
                        "source": "storage_cleaner",
                        "module": "Cleaner",
                        "message": f"Purged {res['deleted_files']} cached files, freed {res['freed_mb']} MB",
                        "context": res,
                        "created_at": datetime.datetime.utcnow()
                    })
                except Exception:
                    pass
        except Exception as e:
            logger.error(f"Error in periodic cleaner task: {e}")

        # Sleep for 1 hour
        await asyncio.sleep(3600)

_cleaner_task = None

def start_storage_cleaner():
    """Initializes and schedules the cleaner background task in the active asyncio event loop."""
    global _cleaner_task
    if _cleaner_task is None or _cleaner_task.done():
        _cleaner_task = asyncio.create_task(periodic_cleaner_task())
        logger.info("Storage Cleaner scheduled in background loop.")
