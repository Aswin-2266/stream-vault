import math
import html
import hashlib
import logging
from hydrogram import Client, filters
from hydrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
import config
from bot.utils.database import db
from bot.utils.torrent import search_torrents, extract_language_and_title, get_imdb_suggestion, get_cached_torrent, LANGUAGE_MAP
from bot.utils.userbot import userbot_harvester
from bot.handlers.start import is_authorized
from bot.handlers.indexer import format_size

logger = logging.getLogger("SearchHandler")

# In-memory search session cache: qid -> search metadata & results
SEARCH_CACHE: dict[str, dict] = {}

def get_query_id(query: str) -> str:
    """Generates a compact 8-character hash for Telegram callback buttons"""
    return hashlib.md5(query.lower().strip().encode()).hexdigest()[:8]

def render_vault_view(qid: str, page: int = 0) -> tuple[str, InlineKeyboardMarkup | None]:
    data = SEARCH_CACHE.get(qid)
    if not data:
        return "❌ Search session expired. Please type the movie title again.", None

    vault_list = data.get("vault_results", [])
    channel_list = data.get("channel_results", [])
    tor_list = data.get("torrent_results", [])
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

    # Tab Switcher to Cloud Torrents
    tor_text = f"⚡ Cloud Torrents ({len(tor_list)})" if tor_list else "⚡ Search Torrents"
    buttons.append([InlineKeyboardButton(tor_text, callback_data=f"sw_tor_{qid}")])

    # Optional "Did you mean?" suggestion
    if suggested:
        lines.append(f"\n💡 *Did you mean:* **{suggested}**?")
        buttons.append([InlineKeyboardButton(f"💡 Search '{suggested[:22]}'", callback_data=f"sug_{qid}")])

    return "\n".join(lines), InlineKeyboardMarkup(buttons)

def render_channel_view(qid: str, page: int = 0) -> tuple[str, InlineKeyboardMarkup | None]:
    data = SEARCH_CACHE.get(qid)
    if not data:
        return "❌ Search session expired. Please type the movie title again.", None

    channel_list = data.get("channel_results", [])
    vault_list = data.get("vault_results", [])
    tor_list = data.get("torrent_results", [])
    title = data["clean_title"]
    suggested = data.get("suggested_title")

    total_items = len(channel_list)
    total_pages = max(1, math.ceil(total_items / 5))
    page = max(0, min(page, total_pages - 1))
    data["channel_page"] = page

    start_idx = page * 5
    page_items = channel_list[start_idx:start_idx + 5]

    lines = [
        f"📡 **Telegram Movie Channels for:** `{title}`",
        f"📄 *Page {page + 1} of {total_pages} • {total_items} releases • ⚡ Instant 2s Cloud Copy*\n"
    ]

    buttons = []
    button_row = []

    for i, item in enumerate(page_items, start=1):
        file_name = item.get("file_name", "Unknown Release")
        quality = item.get("quality", "HD")
        languages = item.get("languages", "Original Audio")
        size = item.get("size", "N/A")
        chat_title = item.get("source_chat_title", "Movie Channel")
        hid = item.get("harvest_id")

        lines.append(
            f"{i}️⃣ **{file_name[:65]}**\n"
            f"   📺 **Source:** `{chat_title[:30]}`\n"
            f"   🔊 **Audio:** `{languages}`\n"
            f"   📦 **Specs:** `{quality}` • `{size}` • ⚡ 0 MB Hotspot Data\n"
        )

        btn_label = f"🎬 #{i} ({quality})"
        button_row.append(InlineKeyboardButton(btn_label, callback_data=f"sel_chn_{hid}_{qid}_{page}"))
        if len(button_row) == 2:
            buttons.append(button_row)
            button_row = []

    if button_row:
        buttons.append(button_row)

    # Navigation Row (if multiple pages)
    if total_pages > 1:
        nav_row = []
        if page > 0:
            nav_row.append(InlineKeyboardButton("◀️ Prev", callback_data=f"pc_{page - 1}_{qid}"))
        nav_row.append(InlineKeyboardButton(f"{page + 1}/{total_pages}", callback_data=f"noop_{qid}"))
        if page < total_pages - 1:
            nav_row.append(InlineKeyboardButton("Next ▶️", callback_data=f"pc_{page + 1}_{qid}"))
        buttons.append(nav_row)

    # Tab Switcher Row (Vault & Torrents)
    tab_row = []
    vlt_text = f"📁 Vault ({len(vault_list)})" if vault_list else "📁 Vault (0)"
    tab_row.append(InlineKeyboardButton(vlt_text, callback_data=f"sw_vlt_{qid}" if vault_list else f"noop_{qid}"))
    tor_text = f"⚡ Torrents ({len(tor_list)})" if tor_list else "⚡ Search Torrents"
    tab_row.append(InlineKeyboardButton(tor_text, callback_data=f"sw_tor_{qid}"))
    buttons.append(tab_row)

    # Optional suggestion
    if suggested:
        lines.append(f"\n💡 *Did you mean:* **{suggested}**?")
        buttons.append([InlineKeyboardButton(f"💡 Search '{suggested[:22]}'", callback_data=f"sug_{qid}")])

    return "\n".join(lines), InlineKeyboardMarkup(buttons)

def render_torrent_view(qid: str, page: int = 0) -> tuple[str, InlineKeyboardMarkup | None]:
    data = SEARCH_CACHE.get(qid)
    if not data:
        return "❌ Search session expired. Please type the movie title again.", None

    tor_list = data.get("torrent_results", [])
    vault_list = data.get("vault_results", [])
    channel_list = data.get("channel_results", [])
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

    # Tab Switcher to Instant Vault
    vlt_text = f"📁 Instant Vault ({len(vault_list)})" if vault_list else "📁 Search Vault"
    buttons.append([InlineKeyboardButton(vlt_text, callback_data=f"sw_vlt_{qid}" if vault_list else f"noop_{qid}")])

    # Optional "Did you mean?" suggestion
    if suggested:
        lines.append(f"\n💡 *Did you mean:* **{suggested}**?")
        buttons.append([InlineKeyboardButton(f"💡 Search '{suggested[:22]}'", callback_data=f"sug_{qid}")])

    return "\n".join(lines), InlineKeyboardMarkup(buttons)

@Client.on_message(filters.text & filters.private)
async def search_handler(client: Client, message: Message):
    """
    Handles user movie searches with Multi-Tab Paginated Gateway:
    1. Instant Vault Search (0ms local/cloud library).
    2. Telegram Movie Channel Harvester (1-2s cloud-to-cloud copy).
    3. Multi-Engine Cloud Torrents (Oracle VM & GitHub Actions).
    """
    if not is_authorized(message.from_user.id):
        return

    text = (message.text or "").strip()
    if text.startswith("/") and not text.lower().startswith("/search"):
        return

    query = text.replace("/search", "", 1).strip()
    if len(query) < 2:
        if text.lower().startswith("/search"):
            await message.reply_text("ℹ️ Please enter at least 2 characters to search.\nUsage: `/search <title>`")
        return

    clean_title, detected_lang = extract_language_and_title(query)
    search_term = clean_title if clean_title else query
    qid = get_query_id(query)

    suggested = get_imdb_suggestion(search_term)

    status_msg = await message.reply_text(f"🔍 Searching library for `{search_term}`...")
    vault_results = await db.search_files(search_term, limit=50)

    # Prioritize vault files matching requested language
    if detected_lang and vault_results:
        aliases = LANGUAGE_MAP.get(detected_lang, [detected_lang])
        def vault_lang_score(doc):
            fn = (doc.get("file_name", "") + " " + doc.get("caption", "")).lower()
            return any(a in fn for a in aliases) or "multi" in fn or "dual" in fn
        vault_results.sort(key=vault_lang_score, reverse=True)

    # Fast direct dual-source search: Instant Vault & 30+ Cloud Torrent indexers
    channel_results = []
    torrent_results = []

    # Scenario 1: Vault has existing files (fastest, 0ms latency)
    if vault_results:
        SEARCH_CACHE[qid] = {
            "query": query,
            "clean_title": search_term,
            "suggested_title": suggested,
            "vault_results": vault_results,
            "channel_results": [],
            "torrent_results": torrent_results,
            "vault_page": 0,
            "channel_page": 0,
            "torrent_page": 0
        }
        text, markup = render_vault_view(qid, page=0)
        await status_msg.edit_text(text, reply_markup=markup)

    # Scenario 2: Vault empty -> search 30+ online cloud torrents immediately
    else:
        await status_msg.edit_text(f"⚡ Searching 30+ online cloud releases for `{search_term}`...")
        torrent_results = search_torrents(query, limit=35)

        SEARCH_CACHE[qid] = {
            "query": query,
            "clean_title": search_term,
            "suggested_title": suggested,
            "vault_results": [],
            "channel_results": [],
            "torrent_results": torrent_results,
            "vault_page": 0,
            "channel_page": 0,
            "torrent_page": 0
        }

        if torrent_results:
            text, markup = render_torrent_view(qid, page=0)
            await status_msg.edit_text(text, reply_markup=markup)
        else:
            total_vault = await db.count_files()
            sug_text = f"\n\n💡 *Did you mean:* **{suggested}**?" if suggested else ""
            help_text = (
                f"❌ No releases found for **{search_term}** in Vault or Torrent Indexers.{sug_text}\n\n"
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
    if detected_lang and vault_results:
        aliases = LANGUAGE_MAP.get(detected_lang, [detected_lang])
        def vault_lang_score(doc):
            fn = (doc.get("file_name", "") + " " + doc.get("caption", "")).lower()
            return any(a in fn for a in aliases) or "multi" in fn or "dual" in fn
        vault_results.sort(key=vault_lang_score, reverse=True)

    channel_results = []
    if userbot_harvester.is_available():
        try:
            channel_results = await userbot_harvester.search_channels(search_term, limit=20)
        except Exception:
            pass

    torrent_results = search_torrents(new_query, limit=35)

    SEARCH_CACHE[new_qid] = {
        "query": new_query,
        "clean_title": search_term,
        "suggested_title": None,
        "vault_results": vault_results,
        "channel_results": channel_results,
        "torrent_results": torrent_results,
        "vault_page": 0,
        "channel_page": 0,
        "torrent_page": 0
    }

    if vault_results:
        text, markup = render_vault_view(new_qid, page=0)
    elif channel_results:
        text, markup = render_channel_view(new_qid, page=0)
    elif torrent_results:
        text, markup = render_torrent_view(new_qid, page=0)
    else:
        text = f"❌ No releases found for **{search_term}**."
        markup = None

    await callback.message.edit_text(text, reply_markup=markup)

@Client.on_callback_query(filters.regex(r"^pv_"))
async def paginate_vault_callback(client: Client, callback: CallbackQuery):
    parts = callback.data.split("_")
    page = int(parts[1])
    qid = parts[2]
    await callback.answer()
    text, markup = render_vault_view(qid, page=page)
    await callback.message.edit_text(text, reply_markup=markup)

@Client.on_callback_query(filters.regex(r"^srch_chn_"))
async def search_channels_from_torrent_callback(client: Client, callback: CallbackQuery):
    await callback.answer("Channel search is disabled.", show_alert=True)

@Client.on_callback_query(filters.regex(r"^sw_chn_"))
async def switch_to_channels_callback(client: Client, callback: CallbackQuery):
    await callback.answer("Channel search is disabled.", show_alert=True)

@Client.on_callback_query(filters.regex(r"^pc_"))
async def paginate_channel_callback(client: Client, callback: CallbackQuery):
    await callback.answer("Channel search is disabled.", show_alert=True)

@Client.on_callback_query(filters.regex(r"^sel_chn_"))
async def select_channel_callback(client: Client, callback: CallbackQuery):
    await callback.answer("Channel search is disabled.", show_alert=True)

@Client.on_callback_query(filters.regex(r"^harv_"))
async def harvest_channel_file_callback(client: Client, callback: CallbackQuery):
    await callback.answer("Channel harvesting is disabled.", show_alert=True)

@Client.on_callback_query(filters.regex(r"^pt_"))
async def paginate_torrents_callback(client: Client, callback: CallbackQuery):
    parts = callback.data.split("_")
    page = int(parts[1])
    qid = parts[2]
    await callback.answer()
    text, markup = render_torrent_view(qid, page=page)
    await callback.message.edit_text(text, reply_markup=markup)

@Client.on_callback_query(filters.regex(r"^sel_tor_"))
async def select_torrent_callback(client: Client, callback: CallbackQuery):
    """
    Renders In-Place Details & Gateway for Torrents.
    """
    parts = callback.data.split("_")
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
        await callback.answer("Invalid selection.", show_alert=True)
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

    detail_lines = [
        f"🎬 **Release Details & Leech Gateway**\n",
        f"📽️ **Title:** `{title}`",
        f"📦 **Size:** `{size}` • 🌱 **Seeds:** {seed_badge}",
        f"🔊 **Audio:** `{languages}` • `{quality}`\n",
        f"⚡ **Choose Leech Engine (0 MB Mobile Hotspot Data):**",
        f"• **Oracle VM:** High-speed P2P, unblocked ports, direct Indian swarms.",
        f"• **GitHub Actions:** Microsoft Azure gigabit datacenter runner."
    ]

    action_buttons = [
        [
            InlineKeyboardButton("⚡ Leech (Oracle VM)", callback_data=f"leech_vm_{info_hash}"),
            InlineKeyboardButton("☁️ Leech (GitHub)", callback_data=f"leech_gh_{info_hash}")
        ],
        [
            InlineKeyboardButton("📋 Copy Magnet Link", callback_data=f"copy_mag_{info_hash}")
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

@Client.on_callback_query(filters.regex(r"^copy_mag_"))
async def copy_magnet_callback(client: Client, callback: CallbackQuery):
    """Sends the 1-tap copyable magnet link as a clean standalone message."""
    info_hash = callback.data.replace("copy_mag_", "")
    item = get_cached_torrent(info_hash)
    if not item:
        await callback.answer("Magnet link expired. Please search again.", show_alert=True)
        return

    await callback.answer("Magnet link sent below!")
    magnet = item.get("magnet", "")

    msg_text = (
        f"📋 **Tap below to copy Magnet Link:**\n"
        f"`{magnet}`\n\n"
        f"💡 *Tap the code box above to copy instantly to clipboard for 1DM, Flud, or qBittorrent.*"
    )
    await callback.message.reply_text(msg_text, disable_web_page_preview=True)

@Client.on_callback_query(filters.regex(r"^noop_"))
async def noop_callback(client: Client, callback: CallbackQuery):
    """No-op handler for non-clickable page number buttons"""
    await callback.answer()

@Client.on_callback_query(filters.regex(r"^get_"))
async def deliver_file_callback(client: Client, callback: CallbackQuery):
    """Delivers the requested file from the vault along with Direct Stream Link."""
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
