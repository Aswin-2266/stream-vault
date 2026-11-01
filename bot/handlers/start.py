from hydrogram import Client, filters
from hydrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
import config
from bot.utils.database import db

def is_authorized(user_id: int) -> bool:
    """Checks if a user is allowed to access the bot (Whitelist security)"""
    if not config.ALLOWED_USERS:
        # If no whitelist is defined, allow (can be set to restricted in production)
        return True
    return user_id in config.ALLOWED_USERS

@Client.on_message(filters.command(["start", "help"]) & filters.private)
async def start_handler(client: Client, message: Message):
    user_id = message.from_user.id
    if not is_authorized(user_id):
        await message.reply_text(
            "⛔ **Access Denied**\n\n"
            "This is a private StreamVault instance. Your Telegram ID is not on the whitelist.\n\n"
            f"Your Telegram ID: `{user_id}`"
        )
        return

    total_files = await db.count_files()
    text = (
        f"👋 **Welcome to StreamVault, {message.from_user.first_name}!**\n\n"
        "⚡ **Capabilities:**\n"
        "• **Search Movies:** Send any movie name or `/search <title>`\n"
        "• **Direct Downloads:** Get files with VLC/browser streaming links in caption\n"
        "• **Channel Indexer:** Send `/index @channel_username` to import files\n"
        "• **Auto-Saver:** Forward any media file to this chat to index it permanently\n"
        "• **Torrent Leech:** Automatic fallback to high-seed cloud torrents\n\n"
        f"📊 **Database Stats:** `{total_files}` indexed files currently in vault."
    )
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🌐 Web Gateway", url=config.STREAM_URL),
            InlineKeyboardButton("📖 Documentation", url="https://github.com/Aswin-2266/stream-vault")
        ]
    ])

    await message.reply_text(text, reply_markup=keyboard, disable_web_page_preview=True)
