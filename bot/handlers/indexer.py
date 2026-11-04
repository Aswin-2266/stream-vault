import asyncio
from hydrogram import Client, filters
from hydrogram.types import Message
from hydrogram.errors import (
    UsernameNotOccupied,
    UsernameInvalid,
    ChatAdminRequired,
    ChannelPrivate,
    PeerIdInvalid
)
import config
from bot.utils.database import db
from bot.handlers.start import is_authorized

VIDEO_EXTENSIONS = (".mkv", ".mp4", ".avi", ".mov", ".flv", ".webm", ".ts", ".m4v", ".wmv", ".3gp")

def format_size(bytes_size: int) -> str:
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if bytes_size < 1024.0:
            return f"{bytes_size:.2f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.2f} PB"

def is_video_media(msg: Message) -> bool:
    """Helper to detect if a message contains video media, whether sent as Video or Document"""
    if msg.video:
        return True
    if msg.document:
        mime = (msg.document.mime_type or "").lower()
        if "video" in mime or "octet-stream" in mime or "matroska" in mime:
            fn = (msg.document.file_name or "").lower()
            if fn.endswith(VIDEO_EXTENSIONS) or "video" in mime or "matroska" in mime:
                return True
        elif (msg.document.file_name or "").lower().endswith(VIDEO_EXTENSIONS):
            return True
    return False

async def index_single_channel(client: Client, channel_target: str, status_msg: Message, batch_idx: int = 1, total_batch: int = 1) -> dict:
    """
    Lightning-speed channel crawler:
    Indexes video file_ids directly into MongoDB Atlas in seconds without hitting FloodWait limits.
    """
    prefix = f"[{batch_idx}/{total_batch}] " if total_batch > 1 else ""
    await status_msg.edit_text(f"⏳ {prefix}**Connecting to** `{channel_target}`...")

    try:
        chat = await client.get_chat(channel_target)
    except UsernameNotOccupied:
        err = "Username not occupied (channel deleted, banned, or changed handle)"
        return {"success": False, "channel": channel_target, "error": err, "indexed": 0}
    except UsernameInvalid:
        err = "Invalid Telegram username"
        return {"success": False, "channel": channel_target, "error": err, "indexed": 0}
    except ChannelPrivate:
        err = "Channel is private (must add bot as Admin)"
        return {"success": False, "channel": channel_target, "error": err, "indexed": 0}
    except Exception as e:
        return {"success": False, "channel": channel_target, "error": str(e), "indexed": 0}

    await status_msg.edit_text(f"📥 {prefix}**Indexing media from:** `{chat.title}`...\n(Lightning Ingestion • Zero FloodWait)")

    total_indexed = 0
    total_scanned = 0

    try:
        async for msg in client.get_chat_history(chat.id):
            total_scanned += 1
            if is_video_media(msg):
                media = msg.video or msg.document
                file_name = getattr(media, "file_name", None) or f"video_{msg.id}.mp4"
                file_size = media.file_size
                file_id = media.file_id
                unique_id = media.file_unique_id
                mime_type = getattr(media, "mime_type", "video/mp4")

                file_info = {
                    "file_name": file_name,
                    "file_size": file_size,
                    "file_id": file_id,
                    "unique_id": unique_id,
                    "source_chat_id": chat.id,
                    "source_message_id": msg.id,
                    "source_chat_title": chat.title,
                    "mime_type": mime_type,
                    "caption": msg.caption or file_name
                }
                await db.save_file(file_info)
                total_indexed += 1

                if total_indexed % 50 == 0:
                    try:
                        await status_msg.edit_text(
                            f"🔄 {prefix}**Indexing Progress for** `{chat.title}`:\n"
                            f"• Scanned: `{total_scanned}` messages\n"
                            f"• Saved Movies: `{total_indexed}`"
                        )
                    except Exception:
                        pass

        await status_msg.edit_text(
            f"✅ {prefix}**Indexing Complete!**\n\n"
            f"• **Channel:** `{chat.title}`\n"
            f"• **Total Messages Scanned:** `{total_scanned}`\n"
            f"• **Movies Added to Vault:** `{total_indexed}`"
        )
        return {"success": True, "channel": chat.title, "indexed": total_indexed, "scanned": total_scanned}
    except ChatAdminRequired:
        err = "Bot must be an Administrator to read chat history"
        return {"success": False, "channel": chat.title or channel_target, "indexed": total_indexed, "error": err}
    except Exception as e:
        return {"success": False, "channel": chat.title or channel_target, "indexed": total_indexed, "error": str(e)}

@Client.on_message(filters.command("index") & filters.private)
async def index_channel_handler(client: Client, message: Message):
    """
    Crawls and indexes all media from a public Telegram channel into the private vault.
    Usage: /index @channel_username
    """
    if not is_authorized(message.from_user.id):
        await message.reply_text("⛔ Unauthorized.")
        return

    args = message.text.split()
    if len(args) < 2:
        await message.reply_text("ℹ️ **Usage:** `/index @channel_username`\nOr use `/index_batch @ch1 @ch2 @ch3` for multiple channels.")
        return

    channel_target = args[1].strip()
    status_msg = await message.reply_text(f"⏳ Connecting to `{channel_target}`...")
    await index_single_channel(client, channel_target, status_msg)

@Client.on_message(filters.command("index_batch") & filters.private)
async def index_batch_handler(client: Client, message: Message):
    """
    Bulk channel crawler: Indexes multiple public Telegram channels sequentially.
    Usage: /index_batch @channel1 @channel2 @channel3
    """
    if not is_authorized(message.from_user.id):
        await message.reply_text("⛔ Unauthorized.")
        return

    args = message.text.split()[1:]
    if not args:
        await message.reply_text(
            "ℹ️ **Usage:** `/index_batch @channel1 @channel2 @channel3`\n\n"
            "Provide one or more public channel usernames or links to bulk-index into your vault."
        )
        return

    channels = [c.strip() for c in args if c.strip()]
    status_msg = await message.reply_text(f"🚀 Starting bulk ingestion for `{len(channels)}` channels...")

    summary_reports = []
    total_saved_all = 0

    for idx, target in enumerate(channels, start=1):
        res = await index_single_channel(client, target, status_msg, batch_idx=idx, total_batch=len(channels))
        summary_reports.append(res)
        total_saved_all += res.get("indexed", 0)
        await asyncio.sleep(1.5)  # Brief polite pause between channels

    report_lines = [
        f"🎉 **Bulk Ingestion Complete!**\n",
        f"📊 **Channels Processed:** `{len(channels)}`",
        f"📦 **Total Movies Added to Vault:** `{total_saved_all}`\n"
    ]
    for r in summary_reports:
        ch = r.get("channel", "Unknown")
        if r.get("success"):
            report_lines.append(f"✅ `{ch}`: `{r.get('indexed', 0)}` movies")
        else:
            err = r.get("error", "Error")
            report_lines.append(f"⚠️ `{ch}`: 0 movies ({err})")

    if total_saved_all == 0:
        report_lines.append(
            "\n💡 **Why 0 movies or failed to access?**\n"
            "• Telegram prevents bots from reading public channel history unless added as Admin.\n"
            "• Many public pirate channels get banned or delete usernames frequently.\n\n"
            "📌 **Guaranteed Solution:**\n"
            "1. Create your own private Telegram channel (e.g. *My Movies*).\n"
            "2. Add this bot as an **Administrator** with 'Post/Read' rights.\n"
            "3. Forward movie files from any public channel to your private channel!\n"
            "4. Run `/index @your_private_channel` or forward movies directly to this bot in chat!"
        )

    await status_msg.edit_text("\n".join(report_lines))

@Client.on_message((filters.video | filters.document) & filters.private)
async def auto_save_handler(client: Client, message: Message):
    """
    Auto-saves and indexes any video or document forwarded or sent directly to the bot.
    """
    if not is_authorized(message.from_user.id):
        return

    if not is_video_media(message):
        return

    media = message.video or message.document
    file_name = getattr(media, "file_name", None) or f"video_{message.id}.mp4"
    file_size = media.file_size
    unique_id = media.file_unique_id

    # 1. Check if file already exists in database (deduplicate & prevent duplicate channel copies)
    existing_file = await db.get_file_by_id(unique_id)
    if existing_file:
        saved_unique_id = existing_file.get("unique_id", unique_id)
        stream_link = f"{config.STREAM_URL}/stream/{saved_unique_id}"
        caption = (
            f"⚡ **Already in Vault!**\n\n"
            f"📁 **File:** `{existing_file.get('file_name', file_name)}`\n"
            f"📦 **Size:** `{format_size(existing_file.get('file_size', file_size))}`\n\n"
            f"🔗 **Direct Stream Link (VLC/Browser):**\n`{stream_link}`"
        )
        await message.reply_text(caption)
        return

    # 2. New file: Save to private channel ONCE and index
    status = await message.reply_text("💾 **Saving to StreamVault...**")

    # Copy to the permanent log channel
    try:
        copied = await message.copy(chat_id=config.LOG_CHANNEL_ID)
        vault_media = copied.video or copied.document
        vault_file_id = vault_media.file_id
    except Exception:
        vault_file_id = media.file_id

    file_info = {
        "file_name": file_name,
        "file_size": file_size,
        "file_id": vault_file_id,
        "unique_id": unique_id,
        "source_chat_id": message.chat.id,
        "mime_type": getattr(media, "mime_type", "video/mp4"),
        "caption": message.caption or file_name
    }

    await db.save_file(file_info)
    stream_link = f"{config.STREAM_URL}/stream/{unique_id}"

    caption = (
        f"✅ **Saved to Vault!**\n\n"
        f"📁 **File:** `{file_name}`\n"
        f"📦 **Size:** `{format_size(file_size)}`\n\n"
        f"🔗 **Direct Stream Link (VLC/Browser):**\n`{stream_link}`"
    )
    await status.edit_text(caption)
