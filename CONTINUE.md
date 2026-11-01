# StreamVault: Development Status & Continuation Guide

This document provides complete operational context, verified environment configurations, and instructions to maintain or extend **stream-vault** on any machine.

---

## 🟢 Current System Status: ONLINE & VERIFIED

The core engine is fully implemented, verified, and operational:

* **Telegram Bot:** `@perso_streamvault_bot` (Layer 181 MTProto connection active)
* **Database:** MongoDB Atlas M0 Cluster (`stream-vault` database on AWS Mumbai)
* **HTTP Web Streamer:** Asynchronous `aiohttp` Range-Request server running on port `7860`
* **Access Control:** Whitelist security active (`ALLOWED_USERS` filter on all handlers)
* **Mobile Data Impact:** **~0 MB** consumed from your phone hotspot (Telegram cloud-to-cloud file transfers)

---

## 🚀 How to Run the Bot Locally

Whenever you reboot your PC or resume work:

1. Open PowerShell in `d:\Direct_Link`.
2. Activate your Python environment or ensure dependencies are installed:
   ```powershell
   pip install -r requirements.txt
   ```
3. Start the engine:
   ```powershell
   python main.py
   ```
4. Output should display:
   ```text
   [+] Database: Connected successfully to MongoDB Atlas.
   [+] Web Streamer: Online on http://localhost:7860 (Port 7860)
   Telegram Bot Online: @perso_streamvault_bot (ID: 9008960250)
   StreamVault Engine is fully operational! Listening for requests...
   ```

---

## 📱 Bot Usage & Commands Reference

| Action | How to Trigger | What Happens |
| :--- | :--- | :--- |
| **Start / Help** | Send `/start` to `@perso_streamvault_bot` | Greets user, verifies whitelist authorization, and displays indexed database stats. |
| **Search Movies** | Send any title (e.g. `Inception` or `/search Avatar`) | Queries MongoDB Atlas via regex and returns interactive inline buttons with file sizes and resolutions. |
| **Instant Delivery** | Tap any search result button | Sends the native Telegram video file with the **Direct Stream Link (VLC/browser)** in the caption. |
| **1-Click Auto-Save** | Forward any video/movie to the bot | Copies file to private storage vault, records `file_id` in MongoDB, and replies with permanent stream link. |
| **Bulk Channel Index** | Send `/index @channel_username` | Crawls historical channel posts, extracts all media, saves to vault, and indexes into database. |

---

## 📂 Project Architecture & Documentation

- [docs/architecture-plan.md](docs/architecture-plan.md): Full technical architecture, component flowcharts, and module breakdown.
- [docs/setup-guide.md](docs/setup-guide.md): Credentials walkthrough for BotFather, Telegram MTProto API, and MongoDB Atlas.
- [docs/huggingface-deploy.md](docs/huggingface-deploy.md): Docker deployment documentation.
- [conversations/README.md](conversations/README.md): Complete archive of historical Antigravity design sessions (`session_01` & `session_02`).

---

## 🔮 Phase 2 Roadmap (Pending Enhancements)

- [ ] **Google Colab Torrent Leech Notebook:** Create `notebooks/leech_colab.ipynb` to download heavy 4K / >2GB torrents in Google's cloud and auto-upload to your vault with 0 hotspot data.
- [ ] **Cloudflare Tunnel (`cloudflared`):** One-command public HTTPS proxy for external VLC streaming when away from home.
- [ ] **Multi-Channel Auto-Listener:** Background task listening to live posts in whitelisted public channels and auto-indexing them without manual `/index` commands.

---

## 🤖 Prompt to Resume in Antigravity or Any Agent

When continuing on another machine or beginning a new turn, paste this prompt:

```text
I am continuing development on stream-vault (d:\Direct_Link). 
Please read CONTINUE.md and docs/architecture-plan.md to understand the current operational state. 
The core bot (@perso_streamvault_bot) and MongoDB Atlas integration are already running. 
Let's proceed with Phase 2:
1. Build the Google Colab Torrent Leech Notebook (notebooks/leech_colab.ipynb).
2. Configure Cloudflare Tunnel integration for public streaming links.
```
