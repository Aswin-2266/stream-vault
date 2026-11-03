#!/usr/bin/env python3
"""
StreamVault - Telegram Userbot StringSession Generator
Generates an MTProto StringSession for the Telegram Userbot Movie Harvester.

Usage:
    python scripts/generate_string_session.py
"""

import os
import asyncio
from dotenv import load_dotenv

load_dotenv()

async def main():
    print("=" * 60)
    print("⚡ StreamVault Telegram Userbot StringSession Generator")
    print("=" * 60)
    print("This script generates a session string for the Userbot Harvester.")
    print("Recommendation: Use a secondary/spare phone number for safety.\n")

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

    print("\nConnecting to Telegram MTProto...")
    async with Client(
        name="stream_vault_temp_session",
        api_id=api_id,
        api_hash=api_hash_input,
        in_memory=True
    ) as client:
        session_str = await client.export_session_string()
        me = await client.get_me()

        print("\n" + "=" * 60)
        print("✅ StringSession Generated Successfully!")
        print(f"👤 Account: {me.first_name} (@{me.username or 'No Username'}, ID: {me.id})")
        print("=" * 60)
        print("\nCopy the line below and add it to your .env file on the Oracle VM:\n")
        print(f"TELEGRAM_SESSION_STRING={session_str}\n")
        print("=" * 60)
        print("⚠️ Important: Keep this string secret! Treat it like your Telegram password.")
        print("💡 Step 2: Add this account as a member or Admin in your LOG_CHANNEL_ID.")
        print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
