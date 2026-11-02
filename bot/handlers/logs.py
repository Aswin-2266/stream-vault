from hydrogram import Client, filters
from hydrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from bot.utils.database import db
from bot.handlers.start import is_authorized

def format_error_card(errors: list[dict]) -> str:
    if not errors:
        return "✅ **No errors recorded in the past 7 days!**\n\nYour StreamVault engine is healthy and operational."

    lines = [f"🚨 **Recent Error Logs (Showing {len(errors)} latest):**\n"]
    for i, err in enumerate(errors, start=1):
        dt = err.get("created_at")
        dt_str = dt.strftime("%Y-%m-%d %H:%M:%S") if dt else "Unknown Time"
        level = err.get("level", "ERROR")
        source = err.get("source", "main_bot")
        module = err.get("module", "root")
        msg = err.get("message", "No description provided.")
        tb = err.get("traceback")

        badge = "⚠️" if level == "WARNING" else "❌"
        lines.append(
            f"{i}️⃣ {badge} **[{level}]** `{dt_str} UTC`\n"
            f"   📍 **Source:** `{source}` • **Module:** `{module}`\n"
            f"   💬 `{msg[:120]}`"
        )
        if tb:
            # Show last line of traceback for quick diagnosis
            last_line = [l.strip() for l in tb.strip().splitlines() if l.strip()][-1]
            lines.append(f"   🔍 *Detail:* `{last_line[:100]}`\n")
        else:
            lines.append("")

    return "\n".join(lines)

def format_system_card(logs: list[dict]) -> str:
    if not logs:
        return "ℹ️ **No operational system logs recorded yet.**"

    lines = [f"📊 **Recent System Logs (Showing {len(logs)} latest):**\n"]
    for i, item in enumerate(logs, start=1):
        dt = item.get("created_at")
        dt_str = dt.strftime("%Y-%m-%d %H:%M:%S") if dt else "Unknown Time"
        module = item.get("module", "root")
        msg = item.get("message", "")
        source = item.get("source", "main_bot")

        lines.append(
            f"{i}️⃣ ℹ️ **[{module}]** `{dt_str} UTC`\n"
            f"   💬 `{msg[:140]}`\n"
        )

    return "\n".join(lines)

@Client.on_message(filters.command("errors") & filters.private)
async def errors_command_handler(client: Client, message: Message):
    """Displays recent warning and error logs from MongoDB Atlas"""
    if not is_authorized(message.from_user.id):
        await message.reply_text("⛔ Unauthorized.")
        return

    status_msg = await message.reply_text("🔍 Fetching error logs from MongoDB Atlas...")
    errors = await db.get_recent_errors(limit=5)
    text = format_error_card(errors)

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔄 Refresh", callback_data="ref_err"),
            InlineKeyboardButton("🗑️ Clear Errors", callback_data="clr_err")
        ]
    ])
    await status_msg.edit_text(text, reply_markup=buttons)

@Client.on_message(filters.command("logs") & filters.private)
async def logs_command_handler(client: Client, message: Message):
    """Displays recent operational system logs from MongoDB Atlas"""
    if not is_authorized(message.from_user.id):
        await message.reply_text("⛔ Unauthorized.")
        return

    status_msg = await message.reply_text("🔍 Fetching system logs from MongoDB Atlas...")
    logs = await db.get_recent_system_logs(limit=5)
    text = format_system_card(logs)

    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Refresh", callback_data="ref_sys")]
    ])
    await status_msg.edit_text(text, reply_markup=buttons)

@Client.on_callback_query(filters.regex(r"^ref_err$"))
async def refresh_errors_callback(client: Client, callback: CallbackQuery):
    """Refreshes error logs view"""
    if not is_authorized(callback.from_user.id):
        await callback.answer("Unauthorized", show_alert=True)
        return

    await callback.answer("Refreshing errors...")
    errors = await db.get_recent_errors(limit=5)
    text = format_error_card(errors)
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔄 Refresh", callback_data="ref_err"),
            InlineKeyboardButton("🗑️ Clear Errors", callback_data="clr_err")
        ]
    ])
    await callback.message.edit_text(text, reply_markup=buttons)

@Client.on_callback_query(filters.regex(r"^clr_err$"))
async def clear_errors_callback(client: Client, callback: CallbackQuery):
    """Clears error logs from MongoDB Atlas"""
    if not is_authorized(callback.from_user.id):
        await callback.answer("Unauthorized", show_alert=True)
        return

    deleted = await db.clear_error_logs()
    await callback.answer(f"Cleared {deleted} error logs!", show_alert=True)
    text = "🗑️ **Error logs cleared successfully!**\n\nNo active error records in MongoDB Atlas."
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Refresh", callback_data="ref_err")]
    ])
    await callback.message.edit_text(text, reply_markup=buttons)

@Client.on_callback_query(filters.regex(r"^ref_sys$"))
async def refresh_system_logs_callback(client: Client, callback: CallbackQuery):
    """Refreshes system logs view"""
    if not is_authorized(callback.from_user.id):
        await callback.answer("Unauthorized", show_alert=True)
        return

    await callback.answer("Refreshing logs...")
    logs = await db.get_recent_system_logs(limit=5)
    text = format_system_card(logs)
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Refresh", callback_data="ref_sys")]
    ])
    await callback.message.edit_text(text, reply_markup=buttons)
