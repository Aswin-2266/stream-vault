from hydrogram import Client, filters
from hydrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
import config
from bot.utils.database import db
from bot.utils.torrent import search_torrents
from bot.handlers.start import is_authorized
from bot.handlers.indexer import format_size

@Client.on_message(filters.text & filters.private & ~filters.command(["start", "help", "index"]))
async def search_handler(client: Client, message: Message):
    """
    Handles user movie searches. Queries MongoDB first; offers torrent fallback if not found.
    """
    if not is_authorized(message.from_user.id):
        return

    query = message.text.replace("/search", "").strip()
    if len(query) < 2:
        await message.reply_text("ℹ️ Please enter at least 2 characters to search.")
        return

    status_msg = await message.reply_text(f"🔍 Searching vault for `{query}`...")
    results = await db.search_files(query, limit=10)

    if results:
        buttons = []
        for item in results:
            title = item.get("file_name", "Unknown")
            size_str = format_size(item.get("file_size", 0))
            unique_id = item.get("unique_id", item.get("file_id"))
            btn_text = f"📁 {title[:32]}... [{size_str}]" if len(title) > 32 else f"📁 {title} [{size_str}]"
            buttons.append([InlineKeyboardButton(btn_text, callback_data=f"get_{unique_id}")])

        await status_msg.edit_text(
            f"🎯 Found `{len(results)}` match(es) for **{query}** in your vault:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    else:
        total_vault = await db.count_files()
        help_text = (
            f"❌ No files found for **{query}** in your Telegram vault.\n\n"
            f"📊 **Vault Status:** `{total_vault}` files currently indexed.\n\n"
            f"💡 Tap below to search high-seed cloud torrents (0 MB mobile hotspot data):"
        )
        tor_button = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"⚡ Search Cloud Torrents for '{query[:20]}'", callback_data=f"tor_{query}")]
        ])
        await status_msg.edit_text(help_text, reply_markup=tor_button)

@Client.on_callback_query(filters.regex(r"^get_"))
async def deliver_file_callback(client: Client, callback: CallbackQuery):
    """
    Delivers the requested file from the vault along with the Direct Stream Link in caption.
    """
    unique_id = callback.data.split("get_")[1]
    file_doc = await db.get_file_by_id(unique_id)

    if not file_doc:
        await callback.answer("File not found in database.", show_alert=True)
        return

    await callback.answer("Delivering file...")
    file_name = file_doc.get("file_name", "movie.mp4")
    file_size = format_size(file_doc.get("file_size", 0))
    stream_link = f"{config.STREAM_URL}/stream/{unique_id}"

    caption = (
        f"🎬 **{file_name}**\n\n"
        f"📦 **Size:** `{file_size}`\n"
        f"🔗 **Direct Stream / Download (VLC/Browser):**\n`{stream_link}`"
    )

    try:
        await client.send_cached_media(
            chat_id=callback.message.chat.id,
            file_id=file_doc["file_id"],
            caption=caption
        )
    except Exception as e:
        await callback.message.reply_text(f"❌ Failed to deliver file: `{e}`")

@Client.on_callback_query(filters.regex(r"^tor_"))
async def torrent_search_callback(client: Client, callback: CallbackQuery):
    """
    Queries torrent indexers and returns high-seed releases.
    """
    query = callback.data.split("tor_")[1]
    await callback.answer("Searching online torrents...")
    await callback.message.edit_text(f"⚡ Searching high-seed torrents for `{query}`...")

    results = search_torrents(query, limit=6)
    if not results:
        await callback.message.edit_text(f"❌ No high-seed torrents found for `{query}`.")
        return

    card_lines = [f"⚡ **Available Cloud Releases for:** `{query}`\n"]
    buttons = []
    button_row = []

    for i, item in enumerate(results, start=1):
        num_emoji = f"{i}️⃣"
        title = item["title"]
        quality = item.get("quality", "HD")
        languages = item.get("languages", "Original Audio")
        size = item.get("size", "N/A")
        seed_badge = item.get("seed_badge", f"{item.get('seeds', 0)} Seeds")

        card_lines.append(
            f"{num_emoji} **{title}**\n"
            f"   🔊 **Audio:** `{languages}`\n"
            f"   📦 **Specs:** `{quality}` • `{size}` • {seed_badge}\n"
        )

        btn_label = f"⚡ #{i} ({quality})"
        button_row.append(InlineKeyboardButton(btn_label, callback_data=f"leech_{i-1}_{query[:25]}"))
        if len(button_row) == 2:
            buttons.append(button_row)
            button_row = []

    if button_row:
        buttons.append(button_row)

    full_text = "\n".join(card_lines)
    await callback.message.edit_text(
        full_text,
        reply_markup=InlineKeyboardMarkup(buttons)
    )
