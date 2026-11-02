import os
import requests
from hydrogram import Client, filters
from hydrogram.types import CallbackQuery
import config
from bot.utils.database import db
from bot.utils.torrent import search_torrents, get_cached_torrent

@Client.on_callback_query(filters.regex(r"^leech_"))
async def leech_callback_handler(client: Client, callback: CallbackQuery):
    """
    Cloud Leech Handler:
    1. If GH_TOKEN is set: Dispatches GitHub Actions Cloud Runner (0 MB mobile hotspot data).
    2. If GH_TOKEN is not set: Queues task in MongoDB Atlas for the Google Colab worker.
    """
    await callback.answer("Preparing cloud leech...")
    status_msg = await callback.message.edit_text("⏳ Fetching release details...")

    # Fast O(1) hash lookup from in-memory cache
    info_hash = callback.data.replace("leech_", "")
    item = get_cached_torrent(info_hash)

    # Backwards compatibility fallback for legacy leech_{idx}_{query} buttons
    if not item:
        parts = callback.data.split("_", 2)
        if len(parts) >= 3:
            try:
                idx = int(parts[1])
                query = parts[2]
                torrents = search_torrents(query, limit=10)
                if torrents and idx < len(torrents):
                    item = torrents[idx]
            except Exception:
                pass

    if not item:
        await status_msg.edit_text("❌ Selected torrent session has expired or is no longer available. Please search again.")
        return

    title = item["title"]
    magnet = item["magnet"]
    size = item.get("size", "N/A")
    seeds = item.get("seeds", 0)

    # Path A: Automatic GitHub Actions Dispatch (Zero-Hotspot-Data Cloud Runner)
    if config.GH_TOKEN:
        await status_msg.edit_text(f"🚀 **Dispatching Cloud Leech Runner...**\n`{title}`")
        try:
            gh_url = f"https://api.github.com/repos/{config.GITHUB_REPO}/dispatches"
            headers = {
                "Authorization": f"Bearer {config.GH_TOKEN}",
                "Accept": "application/vnd.github.v3+json"
            }
            payload = {
                "event_type": "leech_torrent",
                "client_payload": {
                    "magnet": magnet,
                    "title": title,
                    "user_id": callback.from_user.id
                }
            }
            res = requests.post(gh_url, json=payload, headers=headers, timeout=10)
            if res.status_code in [200, 204]:
                confirm_text = (
                    f"🚀 **Cloud Leech Dispatched to GitHub Actions!**\n\n"
                    f"🎬 **Title:** `{title}`\n"
                    f"📦 **Size:** `{size}` (Seeds: `{seeds}`)\n"
                    f"⚡ **Speed:** ~80-120 MB/s (Gigabit Cloud)\n"
                    f"📱 **Mobile Hotspot Data Used:** **0 MB**\n\n"
                    f"⏳ Cloud runner is downloading and uploading to your vault. "
                    f"You will receive the file and streaming link directly here once ready!"
                )
                await status_msg.edit_text(confirm_text)
                return
            else:
                await status_msg.edit_text(f"⚠️ GitHub Dispatch failed (Status `{res.status_code}`). Falling back to database queue...")
        except Exception as e:
            await status_msg.edit_text(f"⚠️ Cloud dispatch error: `{e}`. Falling back to database queue...")

    # Path B: Queue in MongoDB Atlas (For Google Colab Worker or Manual Runner)
    task_doc = {
        "title": title,
        "magnet": magnet,
        "size": size,
        "seeds": seeds,
        "user_id": callback.from_user.id,
        "chat_id": callback.message.chat.id,
        "status": "queued"
    }
    task_id = await db.add_to_queue(task_doc)

    queue_text = (
        f"📥 **Added to Cloud Leech Queue!**\n\n"
        f"🎬 **Title:** `{title}`\n"
        f"📦 **Size:** `{size}`\n"
        f"🆔 **Task ID:** `{task_id}`\n\n"
        f"💡 **Next Steps (0 MB Hotspot Data):**\n"
        f"• **Instant 1-Tap Trigger:** Add `GH_TOKEN=your_github_token` to your `.env` so the bot triggers cloud runners automatically.\n"
        f"• **Google Colab Worker:** Open `notebooks/leech_colab.ipynb` and run it to process queued batch downloads at 100 MB/s!"
    )
    await status_msg.edit_text(queue_text)
