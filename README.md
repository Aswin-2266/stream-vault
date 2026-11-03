# StreamVault ⚡

> A private, self-hosted hybrid media indexing, cloud relay, and HTTP streaming engine.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Telegram](https://img.shields.io/badge/Telegram-MTProto%202.0-2CA5E0.svg)](https://telegram.org)
[![MongoDB Atlas](https://img.shields.io/badge/MongoDB-Atlas%20M0-47A248.svg)](https://www.mongodb.com/cloud/atlas)

---

## 📖 Overview

**StreamVault** is an ad-free, self-hosted Telegram media bot and streaming gateway. It eliminates frustrating 15-hour verification tokens, link shorteners, and third-party hosting dependencies by leveraging Telegram's cloud infrastructure as a permanent, high-speed media vault.

### 🌟 Key Highlights
* **Zero Mobile Data Consumption:** Movie files move **cloud-to-cloud** directly within Telegram's data centers. Indexing 1,000+ movies uses under 5 MB of internet traffic.
* **Instant Telegram Channel Harvester (1–2s Cloud Copy):** Automatically scans public movie channels and global MTProto archives for `.mkv`/`.mp4` media when a torrent stalls or has 0 seeders. Copies files cloud-to-cloud directly into your private Vault in **1–2 seconds** with 0 MB mobile hotspot data and 0 MB server disk consumption.
* **Native Oracle Cloud Leech Engine:** Downloads torrents directly on the Oracle VM (`140.245.193.224`) using an asynchronous `aria2c` worker with unblocked P2P ports (`50101-50109`). Connects directly to Indian home seeders (Jio/Airtel CGNAT) with zero stalls.
* **2-Step Release Details Gateway:** Clean search results (`[🎬 #1 (1080p)]`) edit in-place to display release specs, a 1-tap copyable Magnet code block for 1DM/Flud, and dual leech options (`⚡ Leech (Oracle VM)` vs `☁️ Leech (GitHub)`).
* **Automated Rolling FIFO Cache:** Cached video files stay in `downloads/` for 3 days for zero-latency local HTTP Range-Request streaming on port `7860`. An automated cleaner purges files older than 3 days or when disk $>75\%$, while remaining permanently backed up in your Telegram Vault.
* **Instant AutoFilter Search & Language Priority:** Intelligent 2-tier search ranking: when a language keyword is supplied (e.g. `tamil`, `telugu`, `hindi`), matching language releases are prioritized at the top of both Vault and Cloud Torrent tabs, sorted by seeders descending.
* **Direct Stream Delivery (DDL):** Built-in asynchronous HTTP server handling byte-range requests for seamless streaming in VLC, MX Player, MPV, or web browsers.
* **Lossless Video Splitting:** Automatically slices media files exceeding 1.95 GB using `ffmpeg` stream copying (no re-encoding) to comply with Telegram's free upload limits.
* **Strict Whitelist Security:** Enforces access control via `ALLOWED_USERS` to prevent unauthorized usage and protect server resources.

---

## 🕹️ Bot Commands & Usage

| Command | Usage | Description |
| :--- | :--- | :--- |
| `/start` | `/start` | Welcome banner, whitelist verification, and live vault statistics. |
| `/search` | `/search <title>` *(or send title directly)* | Multi-tab search gateway: Vault Files, Telegram Channels (1-2s copy), & Cloud Torrents. |
| `/index` | `/index @channel_username` | Lightning channel crawler: indexes 2,000+ movies directly into MongoDB in seconds. |
| `/index_batch` | `/index_batch @ch1 @ch2 @ch3` | Bulk crawler: sequentially indexes multiple movie dump channels into your vault. |
| `/errors` | `/errors` | View recent system & cloud leech errors/warnings directly in Telegram with 1-tap clear. |
| `/logs` | `/logs` | View recent operational system events from MongoDB Atlas. |
| **Auto-Save** | Forward any video to the bot | Copies media to your storage channel and provides an instant DDL streaming link. |
| **Cloud Leech** | Tap any torrent search result | Downloads at 100 MB/s in cloud, splits, and uploads to vault (0 MB mobile hotspot data). |
| **Channel Harvester** | Tap `[📡 Telegram Channels]` | Instant 1–2s cloud-to-cloud copy from movie channels directly into your vault. |
| **Dead Swarm Rescue** | Tap `[📡 Search Channels]` | 1-tap fallback when a torrent has 0 seeders or download stalls. |

---

## 🛠️ Quick Start

### 1. Prerequisites
- Python 3.11 or higher
- A Telegram account with API credentials from [my.telegram.org](https://my.telegram.org)
- A Telegram Bot Token from [@BotFather](https://t.me/BotFather)
- A free [MongoDB Atlas](https://www.mongodb.com/cloud/atlas) cluster

### 2. Installation
```powershell
# Clone the repository
git clone https://github.com/Aswin-2266/stream-vault.git
cd stream-vault

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Credentials
Copy the example environment file and fill in your values:
```powershell
cp .env.example .env
```

| Variable | Description |
| :--- | :--- |
| `API_ID` | Telegram API ID from `my.telegram.org` |
| `API_HASH` | Telegram API Hash from `my.telegram.org` |
| `BOT_TOKEN` | Bot API Token from `@BotFather` |
| `LOG_CHANNEL_ID` | Private Telegram Channel ID (e.g. `-100xxxxxxxxxx`) |
| `MONGO_URI` | MongoDB Atlas connection string |
| `ALLOWED_USERS` | Comma-separated Telegram User IDs allowed to access the bot |
| `PORT` | Web streaming server port (default: `7860`) |
| `TELEGRAM_SESSION_STRING` | *(Optional)* MTProto Userbot Session for 2-second cloud channel harvesting |
| `HARVEST_CHANNELS` | *(Optional)* Comma-separated movie channels to search (e.g. `@tamilblasters_official`) |

### 3b. Generate Telegram Userbot StringSession (Optional)
To enable 1–2 second cloud-to-cloud harvesting from movie channels:
```powershell
python scripts/generate_string_session.py
```
*Prompted for your phone number and OTP code; paste the generated `TELEGRAM_SESSION_STRING=...` into your `.env`.*

### 4. Run the Bot
```powershell
python main.py
```

---

## ☁️ 24/7 Cloud Hosting (Oracle Cloud Always Free)

StreamVault runs 24/7 on Oracle Cloud Infrastructure (OCI) Always Free tier:

1. **Systemd Service Management:**
   ```bash
   # View live real-time streaming logs
   journalctl -u streamvault -f

   # Check bot status and memory usage
   sudo systemctl status streamvault

   # Restart after updating code
   sudo systemctl restart streamvault

   # Stop / Start service
   sudo systemctl stop streamvault
   sudo systemctl start streamvault
   ```

2. **Pull Latest Updates on Server:**
   ```bash
   cd ~/stream-vault && git pull && sudo systemctl restart streamvault
   ```

3. **Open BitTorrent & Streaming Ports (In Oracle VM iptables):**
   ```bash
   # Open HTTP streaming gateway (Port 7860) and BitTorrent P2P swarm (Ports 50101-50109)
   sudo iptables -I INPUT 1 -p tcp --dport 7860 -j ACCEPT
   sudo iptables -I INPUT 1 -p tcp --dport 50101:50109 -j ACCEPT
   sudo iptables -I INPUT 1 -p udp --dport 50101:50109 -j ACCEPT
   sudo netfilter-persistent save
   ```
   *(Ensure these ports are also allowed in your Oracle Cloud VCN Security List).*

4. **Anti-Idle Daemon:** Includes `oracle-keepalive.timer` to protect Always Free compute instances from idle reclamation.

---

## 🔍 Search & Language Ranking Hierarchy

When searching for movies with or without language tokens (e.g. `Jailer tamil`, `Interstellar hindi`):

```text
User Search: "<Title> <Language>"
       │
       ▼
1. Language Token Extraction:
   - Isolates audio keywords: tamil, telugu, hindi, malayalam, kannada, english.
   - Preserves exact movie title without forced auto-correction.
       │
       ▼
2. 2-Tier Priority Sorting:
   ┌─────────────────────────────────────────────────────────────┐
   │ Priority 1 (Top): Exact Language & Multi/Dual-Audio Matches │
   │                  Sorted strictly by SEEDERS (High to Low)   │
   ├─────────────────────────────────────────────────────────────┤
   │ Priority 2: Other Language Releases (Original / Global)     │
   │                  Sorted strictly by SEEDERS (High to Low)   │
   └─────────────────────────────────────────────────────────────┘
```

Both the **MongoDB Vault Tab** and the **Cloud Torrents Tab** enforce this hierarchy.

---

## 📂 Documentation & Reference

* [docs/setup-guide.md](docs/setup-guide.md) — Step-by-step credentials acquisition walkthrough.
* [docs/architecture-plan.md](docs/architecture-plan.md) — Technical specifications and component architecture.
* [docs/huggingface-deploy.md](docs/huggingface-deploy.md) — Docker container deployment guide.
* [CONTINUE.md](CONTINUE.md) — Developer continuation prompt and Phase 2 roadmap.
* [conversations/README.md](conversations/README.md) — Historical Antigravity design session archive.

---

## 📄 License
MIT License. Created for personal media archiving, indexing, and private streaming workflows.
