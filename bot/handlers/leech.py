import os
import shutil
from hydrogram import Client, filters
from hydrogram.types import CallbackQuery
import config
from bot.utils.database import db
from bot.utils.torrent import search_torrents, download_torrent_file
from bot.utils.splitter import split_video_file
from bot.handlers.indexer import format_size

@Client.on_callback_query(filters.regex(r"^leech_"))
async def leech_callback_handler(client: Client, callback: CallbackQuery):
    """
    Downloads torrent to server, splits if > 2GB, uploads to vault, and sends to user.
    """
    parts = callback.data.split("_", 2)
    idx = int(parts[1])
    query = parts[2]

    await callback.answer("Starting cloud leech process...")
    status_msg = await callback.message.edit_text("⏳ Fetching torrent metadata...")

    torrents = search_torrents(query, limit=10)
    if not torrents or idx >= len(torrents):
        await status_msg.edit_text("❌ Torrent release no longer available. Please search again.")
        return

    item = torrents[idx]
    await status_msg.edit_text(f"⚡ **Downloading to Cloud:** `{item['title']}`\nPlease wait...")

    download_dir = f"downloads_{callback.from_user.id}"
    try:
        # Step 1: Download the torrent via aria2c
        downloaded_file = download_torrent_file(item["magnet"], download_dir=download_dir)
        file_size = os.path.getsize(downloaded_file)
        
        await status_msg.edit_text(f"📦 Downloaded `{format_size(file_size)}`. Checking 2GB size limit...")

        # Step 2: Split video if > 1.95 GB
        split_parts = split_video_file(downloaded_file)
        is_split = len(split_parts) > 1

        total_parts = len(split_parts)
        for i, part_path in enumerate(split_parts, start=1):
            part_name = os.path.basename(part_path)
            part_size = os.path.getsize(part_path)
            part_label = f" (Part {i}/{total_parts})" if is_split else ""

            await status_msg.edit_text(f"📤 Uploading{part_label} to your Telegram Vault...")

            # Upload to private storage channel
            uploaded = await client.send_document(
                chat_id=config.LOG_CHANNEL_ID,
                document=part_path,
                caption=f"🎬 {part_name}{part_label}"
            )
            media = uploaded.video or uploaded.document
            vault_file_id = media.file_id
            unique_id = media.file_unique_id

            # Save in database
            file_info = {
                "file_name": part_name,
                "file_size": part_size,
                "file_id": vault_file_id,
                "unique_id": unique_id,
                "source_chat_id": config.LOG_CHANNEL_ID,
                "mime_type": "video/mp4",
                "caption": f"🎬 {part_name}"
            }
            await db.save_file(file_info)

            # Deliver to user
            stream_link = f"{config.STREAM_URL}/stream/{unique_id}"
            user_caption = (
                f"🎬 **{part_name}**{part_label}\n\n"
                f"📦 **Size:** `{format_size(part_size)}`\n"
                f"🔗 **Direct Stream Link (VLC/Browser):**\n`{stream_link}`"
            )
            await client.send_cached_media(
                chat_id=callback.message.chat.id,
                file_id=vault_file_id,
                caption=user_caption
            )

        await status_msg.delete()

    except Exception as e:
        await status_msg.edit_text(f"❌ Leech failed: `{e}`")

    finally:
        # Step 3: Always clean up local temporary download directory
        if os.path.exists(download_dir):
            shutil.rmtree(download_dir, ignore_errors=True)
