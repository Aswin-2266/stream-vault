# How to Continue This Project (`stream-vault`)

This document provides instructions, full context, and an exact prompt to resume development of **stream-vault** seamlessly on your PC or in another environment.

---

## 📌 Project Overview
**stream-vault** is a private, self-hosted hybrid media indexing and streaming bot. It eliminates annoying 15-hour token verification systems, ad-shorteners, and local hosting costs by combining:
1. **Telegram Cloud Storage Vault:** Media files are scraped/stored in a private Telegram channel using Telegram's free cloud storage.
2. **Channel Scraper & AutoFilter:** Automatically scrapes and indexes movie files from public Telegram channels into MongoDB Atlas.
3. **On-Demand Torrent Leeching:** When a requested title is not found in Telegram channels, the bot queries torrent indexers (YTS/1337x), downloads the file via `aria2c` at cloud speeds, auto-splits it if it exceeds 2 GB with `ffmpeg`, uploads it to your Telegram storage channel, and caches the `file_id`.
4. **Dual Delivery (Native File + DDL):** Sends the native Telegram video file and embeds a **Direct Download Link (DDL) / Stream Link** in the caption powered by an asynchronous `aiohttp` web server handling HTTP Range requests (for direct playback in VLC/browser).
5. **Access Control:** Strictly whitelisted to the owner and approved Telegram User IDs.

---

## 📂 Repository Context & Reference Files
- [docs/setup-guide.md](docs/setup-guide.md): Step-by-step instructions for getting Telegram API credentials, Bot Token, Private Log Channel, and MongoDB Atlas URI.
- [docs/architecture-plan.md](docs/architecture-plan.md): Full technical architecture, component flowcharts, and module breakdown.
- [docs/huggingface-deploy.md](docs/huggingface-deploy.md): 3-minute 100% free cloud deployment guide (zero credit card).
- [conversations/README.md](conversations/README.md): Dedicated archive holding full conversational logs, transcripts, and artifacts for both Antigravity sessions (`session_01` & `session_02`).

---

## 📋 Confirmed Design Decisions (From `/grill-me` Interview)
- **Primary Source:** Public Telegram channel scraping (bootstraps with a channel list on startup + `/index @channel` command).
- **Secondary Source:** Torrent fallback for unindexed movies with high-seed torrent lookups.
- **File Sizing:** Shows all resolutions (up to 4K). Files exceeding 1.99 GB are automatically split into parts using `ffmpeg` stream copying (no re-encoding) to comply with Telegram's free 2 GB upload limit.
- **User Interface:** Interactive inline button search results. Selecting an item delivers the Telegram video file with the direct streaming link in the caption.
- **Security:** Private whitelist only (`ALLOWED_USERS` in `.env`).
- **Initial Target:** Tested locally on PC first, designed cleanly for future 24/7 cloud deployment (e.g. Oracle Cloud Always-Free or Linux VPS).

---

## 🚀 Exact Prompt to Continue Development

When you open this project in **Antigravity** (or another AI coding agent) on your PC, paste this exact prompt:

```text
I am continuing development on stream-vault (d:\Direct_Link). 
Please read CONTINUE.md, docs/setup-guide.md, and docs/architecture-plan.md to understand the architecture and confirmed requirements. 
Let's proceed with Step 1 of the implementation plan:
1. Create the PowerShell dependency checker (scripts/check_dependencies.ps1) for Python, ffmpeg, and aria2c.
2. Create requirements.txt and .env.example.
3. Build config.py and the asynchronous MongoDB database client in bot/utils/database.py.
```

---

## 🛠️ Next Steps in the Implementation Roadmap
1. **Step 1: Environment & Dependencies** (`scripts/check_dependencies.ps1`, `requirements.txt`, `.env.example`).
2. **Step 2: Database & Configuration** (`config.py`, `bot/utils/database.py`).
3. **Step 3: Dual Client & Security Whitelist** (`bot/client.py`, `bot/handlers/start.py`).
4. **Step 4: Channel Scraper & Indexer** (`bot/handlers/indexer.py`).
5. **Step 5: Torrent Leech & Splitter** (`bot/utils/torrent.py`, `bot/utils/splitter.py`, `bot/handlers/leech.py`).
6. **Step 6: Stream Server & Search Delivery** (`bot/utils/streamer.py`, `bot/handlers/search.py`).
7. **Step 7: Verification & Testing**.
