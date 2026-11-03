import os
import re
import math
import time
import hashlib
import logging
from typing import Optional
from hydrogram import Client, enums
from hydrogram.types import Message
from hydrogram.errors import FloodWait, RPCError

import config
from bot.utils.database import db

logger = logging.getLogger("UserbotHarvester")

VIDEO_EXTS = (".mkv", ".mp4", ".avi", ".mov", ".flv", ".webm", ".ts", ".m4v")

def format_size(bytes_size: int) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} PB"

def extract_media_info(msg: Message) -> Optional[dict]:
    """
    Inspects a Telegram message and extracts video metadata if valid.
    Supports both native Video messages and Document video files (.mkv, .mp4, etc.).
    """
    media = msg.video or msg.document
    if not media:
        return None

    # Determine file name
    file_name = getattr(media, "file_name", None)
    if not file_name:
        caption = (msg.caption or "").strip()
        first_line = caption.split("\n")[0] if caption else ""
        if any(first_line.lower().endswith(ext) for ext in VIDEO_EXTS):
            file_name = first_line
        else:
            ext = ".mp4" if msg.video else ".mkv"
            file_name = f"Movie_{msg.id}{ext}"

    fn_lower = file_name.lower()

    # If it's a document, verify it has a video extension or video mime type
    if msg.document:
        mime = (msg.document.mime_type or "").lower()
        is_vid = any(fn_lower.endswith(ext) for ext in VIDEO_EXTS) or "video" in mime or "matroska" in mime or "octet-stream" in mime
        if not is_vid:
            return None

    file_size = getattr(media, "file_size", 0)
    # Ignore tiny sample files or clips under 25MB
    if file_size < 25 * 1024 * 1024:
        return None

    # Detect resolution
    quality = "HD"
    if "2160p" in fn_lower or "4k" in fn_lower:
        quality = "4K"
    elif "1080p" in fn_lower:
        quality = "1080p"
    elif "720p" in fn_lower:
        quality = "720p"
    elif "480p" in fn_lower:
        quality = "480p"

    # Detect languages
    languages = []
    text_corpus = f"{file_name} {msg.caption or ''}".lower()
    if "telugu" in text_corpus:
        languages.append("Telugu")
    if "tamil" in text_corpus:
        languages.append("Tamil")
    if "hindi" in text_corpus:
        languages.append("Hindi")
    if "malayalam" in text_corpus:
        languages.append("Malayalam")
    if "kannada" in text_corpus:
        languages.append("Kannada")
    if "english" in text_corpus or "eng" in text_corpus:
        languages.append("English")
    if "multi" in text_corpus:
        languages.append("Multi Audio")
    if "dual" in text_corpus:
        languages.append("Dual Audio")

    lang_str = " + ".join(dict.fromkeys(languages)) if languages else "Original Audio"
    chat_title = getattr(msg.chat, "title", None) or getattr(msg.chat, "username", "Public Channel")

    return {
        "file_name": file_name,
        "size_bytes": file_size,
        "size": format_size(file_size),
        "quality": quality,
        "languages": lang_str,
        "source_chat_id": msg.chat.id,
        "source_chat_title": chat_title,
        "message_id": msg.id,
        "caption": msg.caption or file_name
    }

class UserbotHarvester:
    """
    Telegram MTProto Userbot Harvester Engine.
    Executes instant cloud-to-cloud media ingestion across Telegram movie channels
    with 0 MB mobile hotspot data usage and 0 MB server disk/bandwidth consumption.
    """
    def __init__(self):
        self.client: Optional[Client] = None
        self._cache: dict[str, dict] = {}
        self._is_started = False

    def is_available(self) -> bool:
        """Returns True if the userbot is initialized and connected"""
        return self._is_started and self.client is not None and getattr(self.client, "is_connected", False)

    async def start(self):
        """Starts the userbot MTProto client if configured in .env"""
        session_str = config.TELEGRAM_SESSION_STRING
        if not session_str:
            logger.info("Userbot Harvester disabled (TELEGRAM_SESSION_STRING not configured).")
            return

        try:
            self.client = Client(
                name="stream_vault_userbot",
                session_string=session_str,
                api_id=config.API_ID,
                api_hash=config.API_HASH,
                no_updates=True
            )
            await self.client.start()
            self._is_started = True
            me = await self.client.get_me()
            logger.info(f"Userbot Harvester Online: {me.first_name} (@{me.username or 'NoUsername'}, ID: {me.id})")
        except Exception as e:
            logger.error(f"Failed to initialize Userbot Harvester: {e}")
            self.client = None
            self._is_started = False

    async def stop(self):
        """Gracefully disconnects userbot"""
        if self.client and self._is_started:
            try:
                await self.client.stop()
            except Exception as e:
                logger.warning(f"Error during userbot stop: {e}")
            self._is_started = False

    def get_cached_item(self, harvest_id: str) -> Optional[dict]:
        return self._cache.get(harvest_id)

    async def search_channels(self, query: str, limit: int = 25) -> list[dict]:
        """
        Searches Telegram movie channels for video releases matching the query.
        Scans both configured harvest channels and global public channel index.
        """
        if not self.is_available() or not self.client:
            return []

        results: list[dict] = []
        seen_keys = set()
        clean_q = query.strip()

        # 1. Search specified harvest channels
        for ch in config.HARVEST_CHANNELS:
            try:
                # Search videos
                async for msg in self.client.search_messages(chat_id=ch, query=clean_q, filter=enums.MessagesFilter.VIDEO, limit=10):
                    info = extract_media_info(msg)
                    if info:
                        key = (info["source_chat_id"], info["message_id"])
                        if key not in seen_keys:
                            seen_keys.add(key)
                            hid = hashlib.md5(f"{key[0]}_{key[1]}".encode()).hexdigest()[:10]
                            info["harvest_id"] = hid
                            self._cache[hid] = info
                            results.append(info)

                # Search documents (mkv uploads)
                async for msg in self.client.search_messages(chat_id=ch, query=clean_q, filter=enums.MessagesFilter.DOCUMENT, limit=10):
                    info = extract_media_info(msg)
                    if info:
                        key = (info["source_chat_id"], info["message_id"])
                        if key not in seen_keys:
                            seen_keys.add(key)
                            hid = hashlib.md5(f"{key[0]}_{key[1]}".encode()).hexdigest()[:10]
                            info["harvest_id"] = hid
                            self._cache[hid] = info
                            results.append(info)
            except Exception as e:
                logger.warning(f"Error searching channel {ch}: {e}")

        # 2. Search Telegram Global Public Index (VIDEO)
        try:
            async for msg in self.client.search_global(query=clean_q, filter=enums.MessagesFilter.VIDEO, limit=limit):
                info = extract_media_info(msg)
                if info:
                    key = (info["source_chat_id"], info["message_id"])
                    if key not in seen_keys:
                        seen_keys.add(key)
                        hid = hashlib.md5(f"{key[0]}_{key[1]}".encode()).hexdigest()[:10]
                        info["harvest_id"] = hid
                        self._cache[hid] = info
                        results.append(info)
                        if len(results) >= limit:
                            break
        except FloodWait as fw:
            logger.warning(f"Telegram FloodWait during global video search: {fw.value}s")
        except Exception as e:
            logger.warning(f"Global video search error: {e}")

        # 3. Search Telegram Global Public Index (DOCUMENT for MKV files)
        if len(results) < limit:
            try:
                async for msg in self.client.search_global(query=clean_q, filter=enums.MessagesFilter.DOCUMENT, limit=limit):
                    info = extract_media_info(msg)
                    if info:
                        key = (info["source_chat_id"], info["message_id"])
                        if key not in seen_keys:
                            seen_keys.add(key)
                            hid = hashlib.md5(f"{key[0]}_{key[1]}".encode()).hexdigest()[:10]
                            info["harvest_id"] = hid
                            self._cache[hid] = info
                            results.append(info)
                            if len(results) >= limit:
                                break
            except FloodWait as fw:
                logger.warning(f"Telegram FloodWait during global doc search: {fw.value}s")
            except Exception as e:
                logger.warning(f"Global doc search error: {e}")

        return results

    async def copy_to_vault(self, harvest_id: str, bot_client: Client) -> dict:
        """
        Executes cloud-to-cloud ingestion:
        1. Userbot copies media message into LOG_CHANNEL_ID (0-2s on Telegram cloud).
        2. Main Bot retrieves the message in LOG_CHANNEL_ID to capture the Bot API file_id.
        3. Document is indexed in MongoDB Atlas and returned.
        """
        if not self.is_available() or not self.client:
            raise RuntimeError("Telegram Userbot Harvester is not online or configured.")

        item = self.get_cached_item(harvest_id)
        if not item:
            raise ValueError("Harvest item session has expired. Please search again.")

        source_chat_id = item["source_chat_id"]
        source_message_id = item["message_id"]

        logger.info(f"Cloud-copying message {source_message_id} from {source_chat_id} to vault {config.LOG_CHANNEL_ID}...")
        start_t = time.time()

        # Step 1: MTProto cloud copy directly to LOG_CHANNEL_ID
        copied_msg = await self.client.copy_message(
            chat_id=config.LOG_CHANNEL_ID,
            from_chat_id=source_chat_id,
            message_id=source_message_id
        )

        copy_duration = time.time() - start_t
        logger.info(f"Telegram cloud copy complete in {copy_duration:.2f}s (Message ID: {copied_msg.id})")

        # Step 2: Main bot accesses the message in LOG_CHANNEL_ID
        bot_msg = await bot_client.get_messages(
            chat_id=config.LOG_CHANNEL_ID,
            message_ids=copied_msg.id
        )

        media = bot_msg.video or bot_msg.document
        if not media:
            raise RuntimeError("Copied message in storage vault does not contain valid video media.")

        file_id = media.file_id
        unique_id = media.file_unique_id
        file_name = item.get("file_name") or getattr(media, "file_name", "movie.mp4")
        file_size = getattr(media, "file_size", item.get("size_bytes", 0))
        mime_type = getattr(media, "mime_type", "video/mp4")

        # Step 3: Save file metadata into MongoDB Atlas Vault
        file_doc = {
            "file_name": file_name,
            "file_size": file_size,
            "file_id": file_id,
            "unique_id": unique_id,
            "source_chat_id": config.LOG_CHANNEL_ID,
            "source_message_id": copied_msg.id,
            "source_chat_title": item.get("source_chat_title", "Telegram Harvester"),
            "mime_type": mime_type,
            "caption": f"🎬 {file_name}"
        }
        await db.save_file(file_doc)
        logger.info(f"Successfully saved harvested movie to MongoDB: {file_name} ({unique_id})")

        return {
            "file_doc": file_doc,
            "unique_id": unique_id,
            "file_id": file_id,
            "file_name": file_name,
            "file_size": file_size,
            "duration": copy_duration
        }

userbot_harvester = UserbotHarvester()
