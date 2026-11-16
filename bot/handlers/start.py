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
        "🎬 **How to Search:**\n"
        "Just type any movie or series name directly in this chat! (e.g. `Interstellar`, `Mirzapur`, `Leo`)\n\n"
        "⚡ **Available Commands:**\n"
        "• `/start` — Show this help menu & system status\n"
        "• `/index @channel` — Index files from a public Telegram channel\n"
        "• `/logs` — View recent system activity logs\n"
        "• `/errors` — View recent system error logs\n\n"
        "💡 **Direct Streaming:**\n"
        "Forward any video to get an instant direct stream link.\n\n"
        f"📊 **Database Stats:** `{total_files}` indexed files currently in vault."
    )
    
    buttons = [
        [
            InlineKeyboardButton("📖 GitHub Repo", url="https://github.com/Aswin-2266/stream-vault")
        ]
    ]

    # Only add Web Gateway button if STREAM_URL is a valid public web URL (Telegram rejects localhost in buttons)
    if config.STREAM_URL.startswith("https://") and "localhost" not in config.STREAM_URL and "127.0.0.1" not in config.STREAM_URL:
        buttons[0].insert(0, InlineKeyboardButton("🌐 Web Gateway", url=config.STREAM_URL))

    keyboard = InlineKeyboardMarkup(buttons)

    await message.reply_text(text, reply_markup=keyboard, disable_web_page_preview=True)
