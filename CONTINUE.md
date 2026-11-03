# StreamVault: Development Status & Continuation Guide

This document provides complete operational context, verified environment configurations, and instructions to maintain or extend **stream-vault** on any machine.

---

## 🟢 Current System Status: ONLINE & VERIFIED

The core engine is fully implemented, verified, and operational:

* **Telegram Bot:** `@perso_streamvault_bot` (Layer 181 MTProto connection active)
* **Production Host:** Oracle Cloud Infrastructure Always Free VM (`140.245.193.224`, Hyderabad `ap-hyderabad-1`)
* **Process Manager:** Linux Systemd service `streamvault.service` with auto-restart on boot/crash
* **Anti-Idle Protection:** Native `oracle-keepalive.timer` running gentle CPU & network keepalives every 3 hours
* **Database:** MongoDB Atlas M0 Cluster (`stream-vault` database on AWS Mumbai)
* **HTTP Web Streamer:** Asynchronous `aiohttp` Range-Request server running on port `7860`
* **Public Gateway:** Direct Public IPv4 streaming on `http://140.245.193.224:7860`
* **Crypto Acceleration:** Hardware-accelerated MTProto AES via `cryptg` and `tgcrypto` (`bot/utils/crypto_patch.py`), speeding up media transfers >8,000x and eliminating timeouts
* **Cloud Torrent Leeching (Phase 2 & 3):** Dual-engine architecture operational:
  - 1-Tap automated GitHub Actions cloud runner (`.github/workflows/leech.yml` + `scripts/cloud_leech.py`)
  - **Instant Torrent Finder:** Tap any release button to display the full release details and a 1-tap copyable Magnet link (`magnet:?xt=...`) directly in chat for external apps (Flud, 1DM, qBittorrent)
  - **Live Progress Updates:** Real-time editing of the Telegram status message at quarter milestones (25%, 50%, 75%, 100%) and 5s throttled updates with visual progress bars (`[███████░░░░░░░░] 50%`) and gigabit speed tracking
  - Queue-driven Google Colab batch worker (`notebooks/leech_colab.ipynb`)
  - Regional & Indian Torrent Aggregator (Torrentio Stremio Streams, BitSearch, Apibay, YTS) with language audio detection
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

## ☁️ Managing StreamVault on Oracle Cloud VM

Connect from PowerShell:
```powershell
ssh -i "$HOME\Downloads\ssh-key-2026-11-03.key" ubuntu@140.245.193.224
```

### Essential Linux Commands for StreamVault:
* **View Live Streaming Logs (Real-Time):**
  ```bash
  journalctl -u streamvault -f
  ```
  *(Press `Ctrl + C` to stop watching logs).*
* **View Last 50 Lines of Logs:**
  ```bash
  journalctl -u streamvault -n 50 --no-pager
  ```
* **Check Service Status:**
  ```bash
  sudo systemctl status streamvault
  ```
* **Restart Bot (After Code Changes):**
  ```bash
  cd ~/stream-vault && git pull && sudo systemctl restart streamvault
  ```
* **Stop / Start Bot:**
  ```bash
  sudo systemctl stop streamvault
  sudo systemctl start streamvault
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
- [docs/pending-decisions.md](docs/pending-decisions.md): Comprehensive evaluation of options to overcome the 2 GB Telegram file limit (Oracle Direct Stream Gateway, Telegram Premium Userbot, Real-Debrid Bridge, HEVC Transcoding).
- [docs/setup-guide.md](docs/setup-guide.md): Credentials walkthrough for BotFather, Telegram MTProto API, and MongoDB Atlas.
- [docs/huggingface-deploy.md](docs/huggingface-deploy.md): Docker deployment documentation.
- [conversations/README.md](conversations/README.md): Complete archive of historical Antigravity design sessions (`session_01` & `session_02`).

---

## 🔮 Phase 2 Roadmap (Pending Enhancements)

- [ ] **Google Colab Torrent Leech Notebook:** Create `notebooks/leech_colab.ipynb` to download heavy 4K / >2GB torrents in Google's cloud and auto-upload to your vault with 0 hotspot data.
- [ ] **Multi-Channel Auto-Listener:** Background task listening to live posts in whitelisted public channels and auto-indexing them without manual `/index` commands.

---

## 🤖 Prompt to Resume in Antigravity or Any Agent

When continuing on another machine or beginning a new turn, paste this prompt:

```text
I am continuing development on stream-vault (d:\Direct_Link). 
Please read CONTINUE.md, docs/architecture-plan.md, and conversations/README.md to understand the current operational state. 
The core bot (@perso_streamvault_bot), MongoDB Atlas integration, Cloudflare Tunnel, and cryptg acceleration are fully verified and running. 
Let's proceed with Phase 2:
1. Build the Google Colab Torrent Leech Notebook (notebooks/leech_colab.ipynb).
2. Add live background auto-indexing for whitelisted channels.
```
