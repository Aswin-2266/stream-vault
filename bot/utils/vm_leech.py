import os
import re
import math
import time
import html
import shutil
import asyncio
import hashlib
import logging
import datetime
import subprocess
import requests
from hydrogram import Client
import config
from bot.utils.database import db
from bot.utils.cleaner import clean_storage
from bot.handlers.indexer import format_size

logger = logging.getLogger("VMLeech")

# Safe Telegram Free Upload limit (1.95 GB)
TELEGRAM_MAX_BYTES = 1950 * 1024 * 1024
VIDEO_EXTS = (".mp4", ".mkv", ".avi", ".webm", ".ts", ".m4v", ".mov")

def make_progress_bar(pct: int, length: int = 14) -> str:
    filled = int(round(length * pct / 100))
    return "█" * filled + "░" * (length - filled)

def send_telegram_progress(
    bot_token: str,
    chat_id: int,
    message_id: int,
    title: str,
    size: str,
    seeds: str,
    magnet: str,
    pct: int,
    speed: str = "",
    eta: str = "",
    status_text: str = "",
    is_failed: bool = False,
    stream_url: str = ""
):
    """Sends a fast, non-blocking HTTP REST call to edit the Telegram message with live progress."""
    if not (bot_token and chat_id and message_id):
        return

    bar = make_progress_bar(pct)
    speed_text = f" • 🚀 <code>{html.escape(speed)}/s</code>" if speed else ""
    eta_text = f" • ⏳ ETA: <code>{html.escape(eta)}</code>" if eta else ""

    if not status_text:
        status_line = f"<code>[{bar}] {pct}%</code>{speed_text}{eta_text}"
    else:
        status_line = f"<code>[{bar}] {pct}%</code>\n{status_text}"

    stream_section = ""
    if stream_url:
        stream_section = f"\n🔗 <b>Direct Stream Link:</b>\n<code>{html.escape(stream_url)}</code>\n"

    html_text = (
        f"⚡ <b>Oracle Cloud Native Leech</b>\n\n"
        f"🎬 <b>Title:</b> <code>{html.escape(title)}</code>\n"
        f"📦 <b>Size:</b> <code>{html.escape(str(size))}</code> • 🌱 <b>Seeds:</b> <code>{html.escape(str(seeds))}</code>\n\n"
        f"🚀 <b>Live Leech Status:</b>\n"
        f"{status_line}\n"
        f"{stream_section}"
        f"🌐 <b>Server:</b> Oracle Cloud (<code>140.245.193.224</code>)\n"
        f"📱 <b>Mobile Hotspot Data Used:</b> <b>0 MB</b>"
    )

    # Extract hash for the Copy Magnet button
    hash_m = re.search(r"urn:btih:([a-zA-Z0-9]+)", magnet)
    info_hash = hash_m.group(1).upper() if hash_m else ""

    url = f"https://api.telegram.org/bot{bot_token}/editMessageText"
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": html_text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    keyboard = []
    if info_hash:
        keyboard.append([{"text": "📋 Copy Magnet Link", "callback_data": f"copy_mag_{info_hash}"}])
    if keyboard:
        payload["reply_markup"] = {"inline_keyboard": keyboard}
    try:
        res = requests.post(url, json=payload, timeout=5)
        if res.status_code == 429:
            retry_after = res.json().get("parameters", {}).get("retry_after", 1.5)
            time.sleep(retry_after)
            res = requests.post(url, json=payload, timeout=5)
        if res.status_code != 200 and "message is not modified" not in res.text:
            logger.warning(f"Telegram progress edit returned {res.status_code}: {res.text}")
    except Exception as e:
        logger.warning(f"Telegram progress edit failed: {e}")

def find_all_video_files(download_dir: str) -> list[str]:
    video_files = []
    for root, _, files in os.walk(download_dir):
        for f in files:
            p = os.path.join(root, f)
            if f.lower().endswith(VIDEO_EXTS):
                size = os.path.getsize(p)
                video_files.append((p, size))

    if not video_files:
        raise FileNotFoundError("Download completed but no valid video files found.")

    # Filter out sample/trailer clips (< 25 MB) if larger main files exist
    main_files = [p for p, size in video_files if size >= 25 * 1024 * 1024]
    if not main_files:
        main_files = [p for p, size in video_files]

    main_files.sort(key=lambda x: os.path.basename(x).lower())
    return main_files

def split_video_lossless(file_path: str) -> list[str]:
    file_size = os.path.getsize(file_path)
    if file_size <= TELEGRAM_MAX_BYTES:
        return [file_path]

    logger.info(f"File exceeds 1.95 GB ({format_size(file_size)}). Performing lossless ffmpeg split...")
    duration = 0.0
    try:
        cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", file_path]
        res = subprocess.check_output(cmd, stderr=subprocess.DEVNULL).decode().strip()
        duration = float(res)
    except Exception as e:
        logger.warning(f"ffprobe duration lookup failed: {e}")

    num_parts = math.ceil(file_size / TELEGRAM_MAX_BYTES)
    if num_parts < 2 or duration <= 0:
        return [file_path]

    segment_time = duration / num_parts
    base_name, ext = os.path.splitext(file_path)
    out_pattern = f"{base_name}.part%02d{ext}"

    split_cmd = [
        "ffmpeg", "-y", "-i", file_path,
        "-c", "copy", "-map", "0",
        "-f", "segment", "-segment_time", str(segment_time),
        "-reset_timestamps", "1",
        out_pattern
    ]
    try:
        subprocess.run(split_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True)
    except Exception as e:
        logger.error(f"ffmpeg split execution failed: {e}")

    directory = os.path.dirname(file_path) or "."
    base_fn = os.path.basename(base_name)
    parts = []
    for f in sorted(os.listdir(directory)):
        if f.startswith(base_fn + ".part") and f.endswith(ext):
            parts.append(os.path.join(directory, f))

    return parts or [file_path]

class VMLeechManager:
    """
    Manages native asynchronous torrent downloads on the Oracle Cloud VM.
    Enforces maximum concurrent downloads (MAX_PARALLEL_DOWNLOADS) with queueing.
    """
    def __init__(self):
        self.semaphore = asyncio.Semaphore(config.MAX_PARALLEL_DOWNLOADS)
        self.active_tasks: dict[str, dict] = {}
        self.queue: asyncio.Queue = asyncio.Queue()
        self._worker_running = False

    async def start_worker(self):
        if self._worker_running:
            return
        self._worker_running = True
        logger.info(f"VM Leech Worker initialized (Max Concurrent: {config.MAX_PARALLEL_DOWNLOADS}).")
        while True:
            task_data = await self.queue.get()
            asyncio.create_task(self._execute_task(task_data))

    def enqueue(self, task_data: dict) -> dict:
        """
        Adds a torrent task to the queue and returns slot/waiting position details.
        """
        active_count = len(self.active_tasks)
        max_slots = config.MAX_PARALLEL_DOWNLOADS
        if active_count < max_slots:
            slot_num = active_count + 1
            status_desc = f"Active Leech (Slot {slot_num}/{max_slots})"
            is_active = True
        else:
            q_pos = self.queue.qsize() + 1
            status_desc = f"Queued on Oracle VM (Position #{q_pos} in waiting line)"
            is_active = False

        self.queue.put_nowait(task_data)
        return {
            "is_active": is_active,
            "status": status_desc,
            "active_count": active_count,
            "queue_size": self.queue.qsize()
        }

    async def _execute_task(self, task: dict):
        async with self.semaphore:
            task_id = task.get("task_id", str(time.time()))
            title = task.get("title", "Torrent")
            magnet = task.get("magnet")
            size = task.get("size", "N/A")
            seeds = str(task.get("seeds", 0))
            chat_id = task.get("chat_id")
            message_id = task.get("message_id")
            user_id = task.get("user_id")

            self.active_tasks[task_id] = task
            task_dir = os.path.join("downloads", f"task_{task_id}")
            os.makedirs(task_dir, exist_ok=True)

            # Polite 1.0s pause to respect Telegram message edit rate limit
            await asyncio.sleep(1.0)

            logger.info(f"[Oracle VM Leech] Starting download: {title} (ID: {task_id})")
            send_telegram_progress(
                config.BOT_TOKEN, chat_id, message_id,
                title=title, size=size, seeds=seeds, magnet=magnet,
                pct=0,
                status_text="🚀 <b>Starting aria2c with unblocked P2P ports on Oracle Cloud...</b>"
            )

            try:
                # Run aria2c asynchronously
                await self._run_aria2c_process(
                    magnet=magnet,
                    download_dir=task_dir,
                    chat_id=chat_id,
                    message_id=message_id,
                    title=title,
                    size=size,
                    seeds=seeds
                )

                # Find videos & stage for upload
                video_files = find_all_video_files(task_dir)
                from bot.utils.streamer import get_bot_instance
                bot: Client = get_bot_instance()

                if not bot:
                    raise RuntimeError("Bot instance is not initialized.")

                # Phase 1: Deliver Instant Stream Links immediately (0s wait time!)
                pre_unique_map: dict[str, str] = {}
                primary_stream_url = ""
                for vid_idx, video_file in enumerate(video_files, start=1):
                    raw_fn = os.path.basename(video_file)
                    raw_sz = os.path.getsize(video_file)
                    unique_id = hashlib.md5(f"{task_id}_{vid_idx}_{raw_fn}".encode()).hexdigest()[:12]
                    pre_unique_map[video_file] = unique_id
                    stream_link = f"{config.STREAM_URL}/stream/{unique_id}"
                    if not primary_stream_url:
                        primary_stream_url = stream_link

                    # Save preliminary record with local_path for instant SSD playback
                    pre_doc = {
                        "file_name": raw_fn,
                        "file_size": raw_sz,
                        "file_id": "",
                        "unique_id": unique_id,
                        "source_chat_id": config.LOG_CHANNEL_ID,
                        "local_path": video_file,
                        "mime_type": "video/mp4",
                        "caption": f"🎬 {raw_fn}"
                    }
                    await db.save_file(pre_doc)

                    if user_id:
                        instant_notice = (
                            f"⚡ **Instant Stream Link Ready! (0s Wait)**\n\n"
                            f"🎬 **File:** `{raw_fn}`\n"
                            f"📦 **Size:** `{format_size(raw_sz)}`\n"
                            f"🚀 **Fast SSD Local Stream (VLC/Browser):**\n`{stream_link}`\n\n"
                            f"⏳ *Archiving to your Telegram Cloud Vault in background for permanent storage...*"
                        )
                        try:
                            await bot.send_message(chat_id=user_id, text=instant_notice, disable_web_page_preview=True)
                        except Exception as e:
                            logger.warning(f"Could not send instant stream message: {e}")

                # Update progress card with immediate 0s wait streaming button!
                send_telegram_progress(
                    config.BOT_TOKEN, chat_id, message_id,
                    title=title, size=size, seeds=seeds, magnet=magnet,
                    pct=100,
                    stream_url=primary_stream_url,
                    status_text="⚡ <b>Download Complete! Ready to Stream (0s Wait)</b>\nTap button below for instant VLC/Browser playback.\n⏳ <i>Archiving to Telegram Vault in background...</i>"
                )

                # Phase 2: Upload to Telegram Cloud Vault for permanent retention
                for vid_idx, video_file in enumerate(video_files, start=1):
                    file_label = f"[{vid_idx}/{len(video_files)}] " if len(video_files) > 1 else ""
                    if os.path.getsize(video_file) > TELEGRAM_MAX_BYTES:
                        send_telegram_progress(
                            config.BOT_TOKEN, chat_id, message_id,
                            title=title, size=size, seeds=seeds, magnet=magnet,
                            pct=100,
                            stream_url=primary_stream_url,
                            status_text=f"✂️ <b>Lossless Video Splitting:</b> File ({format_size(os.path.getsize(video_file))}) exceeds 1.95 GB. Splitting into parts..."
                        )
                    parts = split_video_lossless(video_file)
                    is_split = len(parts) > 1
                    base_unique_id = pre_unique_map.get(video_file, "")

                    for part_idx, part_path in enumerate(parts, start=1):
                        part_name = os.path.basename(part_path)
                        part_size = os.path.getsize(part_path)
                        part_label = f" (Part {part_idx}/{len(parts)})" if is_split else ""
                        actual_unique_id = base_unique_id if not is_split else hashlib.md5(f"{base_unique_id}_p{part_idx}".encode()).hexdigest()[:12]

                        logger.info(f"{file_label}Uploading {part_name}{part_label} to Telegram Vault...")
                        send_telegram_progress(
                            config.BOT_TOKEN, chat_id, message_id,
                            title=title, size=size, seeds=seeds, magnet=magnet,
                            pct=100,
                            stream_url=primary_stream_url,
                            status_text=f"📤 <b>Uploading to Telegram Vault:</b>\n<code>{html.escape(part_name)}{html.escape(part_label)}</code> ({format_size(part_size)})..."
                        )
                        last_up_update = [0.0]
                        def upload_progress(current, total):
                            now = time.time()
                            if now - last_up_update[0] >= 5.0 or current == total:
                                last_up_update[0] = now
                                pct_up = int(current * 100 / total) if total else 0
                                bar_up = make_progress_bar(pct_up)
                                send_telegram_progress(
                                    config.BOT_TOKEN, chat_id, message_id,
                                    title=title, size=size, seeds=seeds, magnet=magnet,
                                    pct=100,
                                    stream_url=primary_stream_url,
                                    status_text=f"📤 <b>Uploading to Telegram Vault:</b>\n<code>[{bar_up}] {pct_up}%</code> ({format_size(current)} / {format_size(total)})\n<code>{html.escape(part_name)}{html.escape(part_label)}</code>"
                                )

                        uploaded = await bot.send_document(
                            chat_id=config.LOG_CHANNEL_ID,
                            document=part_path,
                            caption=f"🎬 {part_name}{part_label}",
                            progress=upload_progress
                        )
                        media = uploaded.video or uploaded.document
                        vault_file_id = media.file_id

                        # Update MongoDB Atlas record with permanent Telegram file_id
                        file_doc = {
                            "file_name": part_name,
                            "file_size": part_size,
                            "file_id": vault_file_id,
                            "unique_id": actual_unique_id,
                            "source_chat_id": config.LOG_CHANNEL_ID,
                            "local_path": part_path,
                            "mime_type": "video/mp4",
                            "caption": f"🎬 {part_name}"
                        }
                        await db.save_file(file_doc)

                        # Deliver directly to user in Telegram
                        if user_id:
                            stream_link = f"{config.STREAM_URL}/stream/{actual_unique_id}"
                            msg_caption = (
                                f"✅ **Vault Backup Complete:** `{part_name}`{part_label}\n\n"
                                f"📦 **Size:** `{format_size(part_size)}`\n"
                                f"🔗 **Permanent Stream / Download Link:**\n`{stream_link}`"
                            )
                            try:
                                await bot.send_cached_media(
                                    chat_id=user_id,
                                    file_id=vault_file_id,
                                    caption=msg_caption
                                )
                            except Exception as e:
                                logger.warning(f"Could not send cached media to user: {e}")

                send_telegram_progress(
                    config.BOT_TOKEN, chat_id, message_id,
                    title=title, size=size, seeds=seeds, magnet=magnet,
                    pct=100,
                    stream_url=primary_stream_url,
                    status_text="🎉 <b>Leech &amp; Vault Backup Complete!</b>\nVideo file delivered below. Permanent streaming link active!"
                )
                logger.info(f"[Oracle VM Leech] Finished successfully: {title}")

                # Trigger rolling storage cleaner
                clean_storage()

            except Exception as e:
                logger.error(f"[Oracle VM Leech] Failed for {title}: {e}")
                fail_text = f"❌ <b>Cloud Leech Failed:</b> {html.escape(str(e))}\n\n💡 <b>Alternative:</b> Tap below to search Telegram movie channels for an instant 2-second cloud copy!"
                send_telegram_progress(
                    config.BOT_TOKEN, chat_id, message_id,
                    title=title, size=size, seeds=seeds, magnet=magnet,
                    pct=0,
                    status_text=fail_text,
                    is_failed=True
                )
            finally:
                self.active_tasks.pop(task_id, None)
                self.queue.task_done()

    async def _run_aria2c_process(
        self,
        magnet: str,
        download_dir: str,
        chat_id: int,
        message_id: int,
        title: str,
        size: str,
        seeds: str
    ):
        aria2 = shutil.which("aria2c") or "aria2c"
        cmd = [
            aria2,
            "--seed-time=0",
            "--bt-stop-timeout=600",
            "--bt-tracker-connect-timeout=30",
            "--bt-tracker-timeout=30",
            "--bt-max-peers=250",
            "--enable-dht=true",
            "--enable-dht6=false",
            "--dht-listen-port=50101-50109",
            "--listen-port=50101-50109",
            "--dht-entry-point=router.bittorrent.com:6881",
            "--enable-peer-exchange=true",
            "--bt-enable-lpd=true",
            "--file-allocation=none",
            "--max-connection-per-server=16",
            "--split=16",
            "--min-split-size=1M",
            "--summary-interval=2",
            "--dir", download_dir,
            magnet
        ]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT
        )

        pct_pattern = re.compile(r'\((\d{1,3})%\)')
        dl_pattern = re.compile(r'DL:([^\s]+)')
        eta_pattern = re.compile(r'ETA:([^\s\]]+)')

        start_time = time.time()
        last_update_time = 0.0
        last_pct = -1
        metadata_notified = False
        milestones_hit = set()

        while True:
            line = await proc.stdout.readline()
            if not line:
                break

            line_str = line.decode(errors="replace").strip()
            if not line_str:
                continue

            pct_match = pct_pattern.search(line_str)
            now = time.time()

            if not metadata_notified and (now - start_time >= 10.0) and last_pct < 0:
                metadata_notified = True
                send_telegram_progress(
                    config.BOT_TOKEN, chat_id, message_id,
                    title=title, size=size, seeds=seeds, magnet=magnet,
                    pct=0,
                    status_text="🔍 <b>Connecting to BitTorrent swarm &amp; discovering peer metadata...</b>"
                )

            if pct_match:
                try:
                    pct = int(pct_match.group(1))
                except ValueError:
                    continue

                dl_match = dl_pattern.search(line_str)
                eta_match = eta_pattern.search(line_str)
                speed = dl_match.group(1) if dl_match else ""
                eta = eta_match.group(1) if eta_match else ""

                now = time.time()
                is_quarter = False
                for m in [25, 50, 75, 100]:
                    if pct >= m and m not in milestones_hit:
                        milestones_hit.add(m)
                        is_quarter = True
                        break

                time_elapsed = now - last_update_time
                progress_delta = pct - last_pct

                if is_quarter or (time_elapsed >= 5.0 and progress_delta >= 5):
                    last_update_time = now
                    last_pct = pct
                    send_telegram_progress(
                        config.BOT_TOKEN, chat_id, message_id,
                        title=title, size=size, seeds=seeds, magnet=magnet,
                        pct=pct, speed=speed, eta=eta
                    )

        await proc.wait()
        if proc.returncode != 0:
            raise RuntimeError("Torrent download stalled or timed out (no active seeders available). Please choose a release with higher seeds.")

vm_leech_manager = VMLeechManager()
