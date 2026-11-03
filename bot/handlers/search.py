import math
import hashlib
from hydrogram import Client, filters
from hydrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
import config
from bot.utils.database import db
from bot.utils.torrent import search_torrents, extract_language_and_title, get_imdb_suggestion, get_cached_torrent
from bot.handlers.start import is_authorized
from bot.handlers.indexer import format_size

# In-memory search session cache: qid -> search metadata & results
SEARCH_CACHE: dict[str, dict] = {}

def get_query_id(query: str) -> str:
    """Generates a compact 8-character hash for Telegram callback buttons"""
    return hashlib.md5(query.lower().strip().encode()).hexdigest()[:8]

def render_vault_view(qid: str, page: int = 0) -> tuple[str, InlineKeyboardMarkup | None]:
    data = SEARCH_CACHE.get(qid)
    if not data:
        return "❌ Search session expired. Please type the movie title again.", None

    vault_list = data["vault_results"]
    tor_count = len(data["torrent_results"])
    title = data["clean_title"]
    suggested = data.get("suggested_title")

    total_items = len(vault_list)
    total_pages = max(1, math.ceil(total_items / 5))
    page = max(0, min(page, total_pages - 1))
    data["vault_page"] = page

    start_idx = page * 5
    page_items = vault_list[start_idx:start_idx + 5]

    lines = [
        f"📁 **Instant Vault Files for:** `{title}`",
        f"📄 *Page {page + 1} of {total_pages} • Total {total_items} available*\n"
    ]

    buttons = []
    button_row = []

    for i, item in enumerate(page_items, start=1):
        file_name = item.get("file_name", "Unknown File")
        file_size = format_size(item.get("file_size", 0))
        unique_id = item.get("unique_id", item.get("file_id"))

        res = "HD"
        fn_low = file_name.lower()
        if "2160p" in fn_low or "4k" in fn_low:
            res = "4K"
        elif "1080p" in fn_low:
            res = "1080p"
        elif "720p" in fn_low:
            res = "720p"
        elif "480p" in fn_low:
            res = "480p"

        lines.append(
            f"{i}️⃣ **{file_name[:65]}**\n"
            f"   📦 **Size:** `{file_size}` • `{res}` • ⚡ Instant Stream\n"
        )

        btn_label = f"📁 #{i} ({res})"
        button_row.append(InlineKeyboardButton(btn_label, callback_data=f"get_{unique_id}"))
        if len(button_row) == 2:
            buttons.append(button_row)
            button_row = []

    if button_row:
        buttons.append(button_row)

    # Navigation Row (if multiple pages)
    if total_pages > 1:
        nav_row = []
        if page > 0:
            nav_row.append(InlineKeyboardButton("◀️ Prev", callback_data=f"pv_{page - 1}_{qid}"))
        nav_row.append(InlineKeyboardButton(f"{page + 1}/{total_pages}", callback_data=f"noop_{qid}"))
        if page < total_pages - 1:
            nav_row.append(InlineKeyboardButton("Next ▶️", callback_data=f"pv_{page + 1}_{qid}"))
        buttons.append(nav_row)

    # Tab Switcher Row
    tab_btn_text = f"⚡ Switch to Cloud Torrents ({tor_count})" if tor_count > 0 else "⚡ Search Cloud Torrents"
    buttons.append([InlineKeyboardButton(tab_btn_text, callback_data=f"sw_tor_{qid}")])

    # Optional "Did you mean?" suggestion
    if suggested:
        lines.append(f"\n💡 *Did you mean:* **{suggested}**?")
        buttons.append([InlineKeyboardButton(f"💡 Search '{suggested[:22]}'", callback_data=f"sug_{qid}")])

    return "\n".join(lines), InlineKeyboardMarkup(buttons)

def render_torrent_view(qid: str, page: int = 0) -> tuple[str, InlineKeyboardMarkup | None]:
    data = SEARCH_CACHE.get(qid)
    if not data:
        return "❌ Search session expired. Please type the movie title again.", None

    tor_list = data["torrent_results"]
    vault_count = len(data["vault_results"])
    title = data["clean_title"]
    suggested = data.get("suggested_title")

    total_items = len(tor_list)
    total_pages = max(1, math.ceil(total_items / 5))
    page = max(0, min(page, total_pages - 1))
    data["torrent_page"] = page

    start_idx = page * 5
    page_items = tor_list[start_idx:start_idx + 5]

    lines = [
        f"⚡ **Cloud Torrents for:** `{title}`",
        f"📄 *Page {page + 1} of {total_pages} • {total_items} releases found • 0 MB Hotspot Data*\n"
    ]

    buttons = []
    button_row = []

    for i, item in enumerate(page_items, start=1):
        name = item.get("title", "Unknown Release")
        quality = item.get("quality", "HD")
        languages = item.get("languages", "Original Audio")
        size = item.get("size", "N/A")
        seed_badge = item.get("seed_badge", f"{item.get('seeds', 0)} Seeds")
        info_hash = item.get("hash")

        lines.append(
            f"{i}️⃣ **{name[:65]}**\n"
            f"   🔊 **Audio:** `{languages}`\n"
            f"   📦 **Specs:** `{quality}` • `{size}` • {seed_badge}\n"
        )

        btn_label = f"🎬 #{i} ({quality})"
        button_row.append(InlineKeyboardButton(btn_label, callback_data=f"sel_tor_{info_hash}_{qid}_{page}"))
        if len(button_row) == 2:
            buttons.append(button_row)
            button_row = []

    if button_row:
        buttons.append(button_row)

    # Navigation Row (if multiple pages)
    if total_pages > 1:
        nav_row = []
        if page > 0:
            nav_row.append(InlineKeyboardButton("◀️ Prev", callback_data=f"pt_{page - 1}_{qid}"))
        nav_row.append(InlineKeyboardButton(f"{page + 1}/{total_pages}", callback_data=f"noop_{qid}"))
        if page < total_pages - 1:
            nav_row.append(InlineKeyboardButton("Next ▶️", callback_data=f"pt_{page + 1}_{qid}"))
        buttons.append(nav_row)

    # Tab Switcher Row
    if vault_count > 0:
        buttons.append([InlineKeyboardButton(f"📁 Switch to Vault Files ({vault_count})", callback_data=f"sw_vlt_{qid}")])
    else:
        buttons.append([InlineKeyboardButton("📁 Vault Files (0 in library)", callback_data=f"noop_{qid}")])

    # Optional "Did you mean?" suggestion
    if suggested:
        lines.append(f"\n💡 *Did you mean:* **{suggested}**?")
        buttons.append([InlineKeyboardButton(f"💡 Search '{suggested[:22]}'", callback_data=f"sug_{qid}")])

    return "\n".join(lines), InlineKeyboardMarkup(buttons)

@Client.on_message(filters.text & filters.private)
async def search_handler(client: Client, message: Message):
    """
    Handles user movie searches with Tabbed Paginated View:
    1. Extracts language tokens (e.g. 'tamil') without modifying movie title.
    2. Searches MongoDB vault and multi-engine torrents using exact user title.
    3. Fetches optional 'Did you mean?' suggestion without forcing any rewrites.
    """
    if not is_authorized(message.from_user.id):
        return

    text = (message.text or "").strip()
    # Ignore all slash commands (/errors, /logs, /start, /index, etc.) unless explicitly /search
    if text.startswith("/") and not text.lower().startswith("/search"):
        return

    query = text.replace("/search", "", 1).strip()
    if len(query) < 2:
        if text.lower().startswith("/search"):
            await message.reply_text("ℹ️ Please enter at least 2 characters to search.\nUsage: `/search <title>`")
        return

    # Extract language tokens without auto-correcting title
    clean_title, detected_lang = extract_language_and_title(query)
    search_term = clean_title if clean_title else query
    qid = get_query_id(query)

    # Optional suggestion lookup (never forced)
    suggested = get_imdb_suggestion(search_term)

    status_msg = await message.reply_text(f"🔍 Searching library for `{search_term}`...")
    vault_results = await db.search_files(search_term, limit=50)

    # If vault has results, render Vault Tab immediately (0ms delay)
    if vault_results:
        torrent_results = search_torrents(query, limit=35)
        SEARCH_CACHE[qid] = {
            "query": query,
            "clean_title": search_term,
            "suggested_title": suggested,
            "vault_results": vault_results,
            "torrent_results": torrent_results,
            "vault_page": 0,
            "torrent_page": 0
        }
        text, markup = render_vault_view(qid, page=0)
        await status_msg.edit_text(text, reply_markup=markup)
    else:
        # No vault files; search multi-engine cloud torrents
        await status_msg.edit_text(f"⚡ No vault files found. Searching 30+ online cloud releases for `{search_term}`...")
        torrent_results = search_torrents(query, limit=35)

        SEARCH_CACHE[qid] = {
            "query": query,
            "clean_title": search_term,
            "suggested_title": suggested,
            "vault_results": [],
            "torrent_results": torrent_results,
            "vault_page": 0,
            "torrent_page": 0
        }

        if torrent_results:
            text, markup = render_torrent_view(qid, page=0)
            await status_msg.edit_text(text, reply_markup=markup)
        else:
            total_vault = await db.count_files()
            sug_text = f"\n\n💡 *Did you mean:* **{suggested}**?" if suggested else ""
            help_text = (
                f"❌ No files found for **{search_term}** in your Vault or Online Indexers.{sug_text}\n\n"
                f"📊 **Vault Status:** `{total_vault}` files currently indexed.\n"
                f"💡 Tip: Check spelling or forward the movie video directly to the bot to index it!"
            )
            buttons = []
            if suggested:
                buttons.append([InlineKeyboardButton(f"💡 Search '{suggested[:22]}'", callback_data=f"sug_{qid}")])
            await status_msg.edit_text(help_text, reply_markup=InlineKeyboardMarkup(buttons) if buttons else None)

@Client.on_callback_query(filters.regex(r"^sug_"))
async def suggestion_search_callback(client: Client, callback: CallbackQuery):
    """Executes a fresh search for the suggested IMDb title when clicked by the user"""
    qid = callback.data.replace("sug_", "")
    data = SEARCH_CACHE.get(qid)
    if not data or not data.get("suggested_title"):
        await callback.answer("Suggestion is no longer available.", show_alert=True)
        return

    new_query = data["suggested_title"]
    await callback.answer(f"Searching for: {new_query}")
    new_qid = get_query_id(new_query)

    await callback.message.edit_text(f"🔍 Searching for suggested title `{new_query}`...")

    clean_title, detected_lang = extract_language_and_title(new_query)
    search_term = clean_title if clean_title else new_query
    vault_results = await db.search_files(search_term, limit=50)
    torrent_results = search_torrents(new_query, limit=35)

    SEARCH_CACHE[new_qid] = {
        "query": new_query,
        "clean_title": search_term,
        "suggested_title": None,
        "vault_results": vault_results,
        "torrent_results": torrent_results,
        "vault_page": 0,
        "torrent_page": 0
    }

    if vault_results:
        text, markup = render_vault_view(new_qid, page=0)
    elif torrent_results:
        text, markup = render_torrent_view(new_qid, page=0)
    else:
        text = f"❌ No releases found for **{search_term}**."
        markup = None

    await callback.message.edit_text(text, reply_markup=markup)

@Client.on_callback_query(filters.regex(r"^pv_"))
async def paginate_vault_callback(client: Client, callback: CallbackQuery):
    """Handles pagination for the Vault Tab"""
    parts = callback.data.split("_")
    page = int(parts[1])
    qid = parts[2]
    await callback.answer()
    text, markup = render_vault_view(qid, page=page)
    await callback.message.edit_text(text, reply_markup=markup)

@Client.on_callback_query(filters.regex(r"^pt_"))
async def paginate_torrents_callback(client: Client, callback: CallbackQuery):
    """Handles pagination for the Cloud Torrents Tab"""
    parts = callback.data.split("_")
    page = int(parts[1])
    qid = parts[2]
    await callback.answer()
    text, markup = render_torrent_view(qid, page=page)
    await callback.message.edit_text(text, reply_markup=markup)

@Client.on_callback_query(filters.regex(r"^sel_tor_"))
async def select_torrent_callback(client: Client, callback: CallbackQuery):
    """
    Renders the In-Place Details & Gateway view after user taps a release from search results.
    Displays:
    1. Full Release specs, seeders, audio.
    2. 1-Tap copyable magnet code block.
    3. Dual Leech buttons (Oracle VM vs GitHub Actions).
    4. '◀️ Back to Search Results' button to restore the search list.
    """
    parts = callback.data.split("_")
    # callback format: sel_tor_{info_hash}_{qid}_{page}
    if len(parts) >= 5:
        info_hash = parts[2]
        qid = parts[3]
        try:
            page = int(parts[4])
        except ValueError:
            page = 0
    elif len(parts) >= 3:
        info_hash = parts[2]
        qid = ""
        page = 0
    else:
        await callback.answer("Invalid release selection.", show_alert=True)
        return

    item = get_cached_torrent(info_hash)
    if not item and qid and qid in SEARCH_CACHE:
        for t in SEARCH_CACHE[qid].get("torrent_results", []):
            if t.get("hash") == info_hash:
                item = t
                break

    if not item:
        await callback.answer("Release details expired. Please search again.", show_alert=True)
        return

    await callback.answer()

    title = item.get("title", "Unknown Release")
    quality = item.get("quality", "HD")
    languages = item.get("languages", "Original Audio")
    size = item.get("size", "N/A")
    seeds = item.get("seeds", 0)
    seed_badge = item.get("seed_badge", f"{seeds} Seeds")
    magnet = item.get("magnet", "")

    detail_lines = [
        f"🎬 **Release Details & Leech Gateway**\n",
        f"📽️ **Title:** `{title}`",
        f"📦 **Size:** `{size}` • 🌱 **Seeds:** {seed_badge}",
        f"🔊 **Audio:** `{languages}` • `{quality}`\n",
        f"📋 **Magnet Link (Tap below to copy for external apps):**",
        f"`{magnet}`\n",
        f"⚡ **Choose Leech Engine (0 MB Mobile Hotspot Data):**",
        f"• **Oracle VM:** High-speed P2P, unblocked ports, direct Indian swarms.",
        f"• **GitHub Actions:** Microsoft Azure gigabit datacenter runner."
    ]

    action_buttons = [
        [
            InlineKeyboardButton("⚡ Leech (Oracle VM)", callback_data=f"leech_vm_{info_hash}"),
            InlineKeyboardButton("☁️ Leech (GitHub)", callback_data=f"leech_gh_{info_hash}")
        ]
    ]

    if qid:
        action_buttons.append([
            InlineKeyboardButton("◀️ Back to Search Results", callback_data=f"pt_{page}_{qid}")
        ])

    await callback.message.edit_text(
        "\n".join(detail_lines),
        reply_markup=InlineKeyboardMarkup(action_buttons),
        disable_web_page_preview=True
    )

@Client.on_callback_query(filters.regex(r"^sw_tor_"))
async def switch_to_torrents_callback(client: Client, callback: CallbackQuery):
    """Switches view to the Cloud Torrents Tab"""
    qid = callback.data.replace("sw_tor_", "")
    data = SEARCH_CACHE.get(qid)
    if not data:
        await callback.answer("Session expired.", show_alert=True)
        return

    await callback.answer("Opening Cloud Torrents...")
    if not data.get("torrent_results"):
        await callback.message.edit_text(f"⚡ Fetching 30+ cloud torrent releases for `{data['clean_title']}`...")
        data["torrent_results"] = search_torrents(data["query"], limit=35)

    text, markup = render_torrent_view(qid, page=data.get("torrent_page", 0))
    await callback.message.edit_text(text, reply_markup=markup)

@Client.on_callback_query(filters.regex(r"^sw_vlt_"))
async def switch_to_vault_callback(client: Client, callback: CallbackQuery):
    """Switches view to the Vault Tab"""
    qid = callback.data.replace("sw_vlt_", "")
    await callback.answer("Opening Vault Files...")
    data = SEARCH_CACHE.get(qid)
    if not data:
        await callback.answer("Session expired.", show_alert=True)
        return
    text, markup = render_vault_view(qid, page=data.get("vault_page", 0))
    await callback.message.edit_text(text, reply_markup=markup)

@Client.on_callback_query(filters.regex(r"^noop_"))
async def noop_callback(client: Client, callback: CallbackQuery):
    """No-op handler for non-clickable page number buttons"""
    await callback.answer()

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
