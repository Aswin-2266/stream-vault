#!/usr/bin/env python3
"""
StreamVault - Telegram Userbot StringSession Generator
Generates an MTProto StringSession for the Telegram Userbot Movie Harvester.

Usage:
    python scripts/generate_string_session.py
"""

import os
import sys
import asyncio
from dotenv import load_dotenv

# Apply cryptg / OpenSSL acceleration before importing Hydrogram
try:
    from bot.utils.crypto_patch import apply_crypto_patch
    apply_crypto_patch()
except Exception:
    pass

load_dotenv()

async def main():
    print("=" * 65)
    print("⚡ StreamVault Telegram Userbot StringSession Generator")
    print("=" * 65)
    print("Recommendation: Use a secondary/spare phone number for safety.")
    print("Make sure you include the country code (e.g. +91 for India).\n")

    # Auto-load existing API_ID and API_HASH from .env if present
    env_api_id = os.getenv("API_ID", "")
    env_api_hash = os.getenv("API_HASH", "")

    api_id_input = input(f"Enter API_ID [{env_api_id}]: ").strip() or env_api_id
    api_hash_input = input(f"Enter API_HASH [{env_api_hash}]: ").strip() or env_api_hash

    if not api_id_input or not api_hash_input:
        print("❌ Error: API_ID and API_HASH are required. Get them from https://my.telegram.org")
        return

    try:
        api_id = int(api_id_input)
    except ValueError:
        print("❌ Error: API_ID must be a numeric integer.")
        return

    from hydrogram import Client
    from hydrogram.errors import PhoneNumberInvalid, PhoneCodeInvalid, PhoneCodeExpired, SessionPasswordNeeded

    print("\nConnecting to Telegram MTProto...")
    print("💡 When prompted, enter your phone number with '+' and country code (e.g. +919876543210)\n")

    try:
        async with Client(
            name="stream_vault_temp_session",
            api_id=api_id,
            api_hash=api_hash_input,
            in_memory=True
        ) as client:
            session_str = await client.export_session_string()
            me = await client.get_me()

            print("\n" + "=" * 65)
            print("✅ StringSession Generated Successfully!")
            print(f"👤 Account: {me.first_name} (@{me.username or 'No Username'}, ID: {me.id})")
            print("=" * 65)
            print("\nCopy the line below and add it to your .env file on the Oracle VM:\n")
            print(f"TELEGRAM_SESSION_STRING={session_str}\n")
            print("=" * 65)
            print("⚠️ Important: Keep this string secret! Treat it like your Telegram password.")
            print("💡 Step 2: Add this account as a member or Admin in your LOG_CHANNEL_ID.")
            print("=" * 65)

    except PhoneNumberInvalid:
        print("\n❌ Error: Invalid phone number.")
        print("👉 You must include your country code starting with '+' (e.g., +91 for India).")
        print("👉 Example: +919876543210 (no spaces, dashes, or leading zeros).")
    except PhoneCodeInvalid:
        print("\n❌ Error: The OTP login code you entered was incorrect. Please run the script again.")
    except PhoneCodeExpired:
        print("\n❌ Error: The OTP login code expired. Please run the script again.")
    except Exception as e:
        print(f"\n❌ Error during session generation: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nSession generation cancelled.")
