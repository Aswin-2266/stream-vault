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
* **Instant AutoFilter Search:** Fast regex search powered by MongoDB Atlas returns matches with inline resolution and size badges.
* **Direct Stream Delivery (DDL):** Built-in asynchronous HTTP server handling byte-range requests for seamless streaming in VLC, MX Player, MPV, or web browsers.
* **Automated Cloudflare HTTPS Gateway:** Generates an encrypted `*.trycloudflare.com` public URL on startup so mobile devices stream directly without port-forwarding.
* **Dual-Engine Cloud Leeching:** 1-tap automated torrent leeching via GitHub Actions (never leave the bot) + Queue-driven Google Colab worker (`notebooks/leech_colab.ipynb`) for batch series, all with **0 MB mobile hotspot data**.
* **Universal IMDb Auto-Correction:** Typo-tolerant movie title resolution powered by IMDb's open suggestion API (e.g. `openhimer` ➔ `Oppenheimer`, `shashank redemption` ➔ `The Shawshank Redemption`) with smart audio language token isolation (`tamil`, `telugu`, `hindi`).
* **Dual-Index Search Engine:** Aggregates YTS for Hollywood 720p/1080p/4K releases and Open Trackers for Indian regional/dubbed content (Tamil, Telugu, Hindi).
* **Hardware-Accelerated Crypto:** Injects C-optimized `cryptg` AES-NI routines to eliminate MTProto timeouts, achieving <2ms decryption per chunk.
* **Lossless Video Splitting:** Automatically slices media files exceeding 1.95 GB using `ffmpeg` stream copying (no re-encoding) to comply with Telegram's free upload limits.
* **Strict Whitelist Security:** Enforces access control via `ALLOWED_USERS` to prevent unauthorized usage and protect server resources.

---

## 🕹️ Bot Commands & Usage

| Command | Usage | Description |
| :--- | :--- | :--- |
| `/start` | `/start` | Welcome banner, whitelist verification, and live vault statistics. |
| `/search` | `/search <title>` *(or send title directly)* | Tabbed paginated search: Instant Vault playback (Page 1..N) & 30+ Cloud Torrents. |
| `/index` | `/index @channel_username` | Lightning channel crawler: indexes 2,000+ movies directly into MongoDB in seconds. |
| `/index_batch` | `/index_batch @ch1 @ch2 @ch3` | Bulk crawler: sequentially indexes multiple movie dump channels into your vault. |
| `/errors` | `/errors` | View recent system & cloud leech errors/warnings directly in Telegram with 1-tap clear. |
| `/logs` | `/logs` | View recent operational system events from MongoDB Atlas. |
| **Auto-Save** | Forward any video to the bot | Copies media to your storage channel and provides an instant DDL streaming link. |
| **Cloud Leech** | Tap any torrent search result | Downloads at 100 MB/s in cloud, splits, and uploads to vault (0 MB mobile hotspot data). |

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

### 4. Run the Bot
```powershell
python main.py
```

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
