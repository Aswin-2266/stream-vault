import os
import requests
from hydrogram import Client, filters
from hydrogram.types import CallbackQuery
import config
from bot.utils.database import db
from bot.utils.torrent import search_torrents, get_cached_torrent
from bot.utils.vm_leech import vm_leech_manager

def get_torrent_item(data_str: str) -> dict | None:
    """Helper to retrieve torrent metadata by hash or query index"""
    item = get_cached_torrent(data_str)
    if not item:
        parts = data_str.split("_", 2)
        if len(parts) >= 3:
            try:
                idx = int(parts[1])
                query = parts[2]
                torrents = search_torrents(query, limit=10)
                if torrents and idx < len(torrents):
                    item = torrents[idx]
            except Exception:
                pass
    return item

@Client.on_callback_query(filters.regex(r"^leech_vm_"))
async def leech_vm_callback_handler(client: Client, callback: CallbackQuery):
    """
    Native Oracle VM Cloud Leech:
    Downloads torrent on the Oracle Always Free VM with unblocked P2P ports,
    providing direct connections to Indian home seeders (Jio/Airtel CGNAT).
    """
    await callback.answer("Starting Oracle VM Leech...")
    status_msg = await callback.message.edit_text("⏳ Queuing download on Oracle Cloud VM...")

    info_hash = callback.data.replace("leech_vm_", "")
    item = get_torrent_item(info_hash)

    if not item:
        await status_msg.edit_text("❌ Selected torrent session has expired or is no longer available. Please search again.")
        return

    title = item["title"]
    magnet = item["magnet"]
    size = item.get("size", "N/A")
    seeds = item.get("seeds", 0)
    languages = item.get("languages", "Original Audio")

    task_data = {
        "task_id": info_hash,
        "title": title,
        "magnet": magnet,
        "size": size,
        "seeds": seeds,
        "user_id": callback.from_user.id,
        "chat_id": callback.message.chat.id,
        "message_id": callback.message.id
    }

    q_pos = vm_leech_manager.enqueue(task_data)

    init_text = (
        f"⚡ **Oracle Cloud Native Leech**\n\n"
        f"🎬 **Title:** `{title}`\n"
        f"📦 **Size:** `{size}` • 🌱 **Seeds:** `{seeds}`\n"
        f"🔊 **Audio:** `{languages}`\n\n"
        f"📋 **Magnet Link (Tap below to copy for external apps):**\n"
        f"`{magnet}`\n\n"
        f"🚀 **Live Leech Status:**\n"
        f"`[░░░░░░░░░░░░░░] 0%` • Queued on Oracle VM (Position #{q_pos})...\n"
        f"🌐 **Server:** Oracle Cloud (`140.245.193.224`) • Unblocked P2P\n"
        f"📱 **Mobile Hotspot Data Used:** **0 MB**"
    )
    await status_msg.edit_text(init_text)

@Client.on_callback_query(filters.regex(r"^leech_gh_"))
async def leech_gh_callback_handler(client: Client, callback: CallbackQuery):
    """
    GitHub Actions Cloud Leech:
    Dispatches a dedicated cloud runner in Microsoft Azure datacenter.
    """
    await callback.answer("Preparing GitHub Cloud Leech...")
    status_msg = await callback.message.edit_text("⏳ Contacting GitHub Actions runner...")

    info_hash = callback.data.replace("leech_gh_", "")
    item = get_torrent_item(info_hash)

    if not item:
        await status_msg.edit_text("❌ Selected torrent session has expired or is no longer available. Please search again.")
        return

    title = item["title"]
    magnet = item["magnet"]
    size = item.get("size", "N/A")
    seeds = item.get("seeds", 0)
    languages = item.get("languages", "Original Audio")

    if not config.GH_TOKEN:
        await status_msg.edit_text(
            "⚠️ **GitHub Actions Token Not Configured:**\n"
            "Please add `GH_TOKEN` in your `.env` or use the **Oracle VM Leech** option."
        )
        return

    init_text = (
        f"☁️ **GitHub Actions Cloud Leech**\n\n"
        f"🎬 **Title:** `{title}`\n"
        f"📦 **Size:** `{size}` • 🌱 **Seeds:** `{seeds}`\n"
        f"🔊 **Audio:** `{languages}`\n\n"
        f"📋 **Magnet Link (Tap below to copy for external apps):**\n"
        f"`{magnet}`\n\n"
        f"🚀 **Cloud Leech Status:**\n"
        f"`[░░░░░░░░░░░░░░] 0%` • Dispatching Azure Cloud Runner...\n"
        f"📱 **Mobile Hotspot Data Used:** **0 MB**"
    )
    await status_msg.edit_text(init_text)

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
                "size": str(size),
                "seeds": str(seeds),
                "user_id": callback.from_user.id,
                "chat_id": callback.message.chat.id,
                "message_id": callback.message.id
            }
        }
        res = requests.post(gh_url, json=payload, headers=headers, timeout=10)
        if res.status_code in [200, 204]:
            confirm_text = (
                f"☁️ **GitHub Actions Cloud Leech**\n\n"
                f"🎬 **Title:** `{title}`\n"
                f"📦 **Size:** `{size}` • 🌱 **Seeds:** `{seeds}`\n"
                f"🔊 **Audio:** `{languages}`\n\n"
                f"📋 **Magnet Link (Tap below to copy for external apps):**\n"
                f"`{magnet}`\n\n"
                f"🚀 **Cloud Leech Dispatched to GitHub Actions!**\n"
                f"⚡ **Speed:** ~80-120 MB/s (Azure Cloud Runner)\n"
                f"📱 **Mobile Hotspot Data Used:** **0 MB**\n\n"
                f"⏳ Downloading in Microsoft Azure cloud. Live progress updates will appear below:"
            )
            await status_msg.edit_text(confirm_text)
        else:
            await status_msg.edit_text(f"⚠️ GitHub Dispatch failed (Status `{res.status_code}`). Please try Oracle VM Leech.")
    except Exception as e:
        await status_msg.edit_text(f"⚠️ Cloud dispatch error: `{e}`. Please try Oracle VM Leech.")

@Client.on_callback_query(filters.regex(r"^leech_([a-fA-F0-9]+)$"))
async def legacy_leech_callback_handler(client: Client, callback: CallbackQuery):
    """Backwards compatibility fallback: routes legacy leech_ callbacks to Oracle VM"""
    callback.data = callback.data.replace("leech_", "leech_vm_")
    await leech_vm_callback_handler(client, callback)
