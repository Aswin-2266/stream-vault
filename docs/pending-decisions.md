# StreamVault: Architectural Decisions & Roadmap

## Pending Decision: Overcoming Telegram's 2 GB File Upload Limit

### Context & Problem Statement
Telegram Bot API enforces a hard ceiling of **2,000 MB (2.0 GB)** per file for bot uploads. 
Currently, StreamVault uses lossless FFmpeg splitting (`split_video`) to divide files exceeding 1.95 GB into `.part01`, `.part02`, etc. While this preserves 100% video and audio bitstream quality without re-encoding, multi-part video playback can be annoying for users who prefer watching a continuous file without switching parts or manually merging them.

---

### Option Evaluation Matrix

| Metric | Option 1: Oracle Direct Stream Gateway | Option 2: Telegram Premium Userbot | Option 3: Real-Debrid / TorBox Bridge | Option 4: Cloud HEVC Transcoding |
| :--- | :--- | :--- | :--- | :--- |
| **Max File Size** | **Unlimited** (Up to VM disk) | **4.0 GB** | **Unlimited** (Up to 100 GB+) | **Single file (<2 GB)** |
| **Cost** | **100% Free Forever** | ₹150–180/month ($3–4) | ₹250/month ($3) | **100% Free Forever** |
| **Hotspot Data** | **0 MB** | **0 MB** | **0 MB** | **0 MB** |
| **Playback Experience** | 1-Tap Single Stream Link (VLC, MX, Browser) | Native Telegram Video | Instant Direct Web Link (No Leech Wait) | Native Telegram Video |
| **Storage / Retention** | 70 GB rolling buffer (Auto-purged after 7 days) | Permanent Telegram Cloud | Permanent Cloud Debrid Cache | Permanent Telegram Cloud |
| **Setup Complexity** | Low (Already running on Oracle VM) | Medium (Requires phone session string) | Low (Single API Key) | Low (GitHub Actions FFmpeg pipeline) |

---

### Detailed Architecture Analysis

#### Option 1: Oracle Always Free Direct Storage & Stream Gateway (Recommended Free Path)
- **How it works:**
  - StreamVault already has an Oracle Cloud Always Free Ubuntu VM (`140.245.193.224`) with a 100 GB NVMe volume and **10 TB of free outbound network bandwidth each month**.
  - When a release exceeds 1.95 GB, the GitHub Actions cloud runner (or Oracle VM directly) downloads the file and saves it in `/var/streamvault/media/`.
  - The StreamVault server exposes a single, unsplit HTTP streaming URL: `http://140.245.193.224:7860/stream/<unique_id>`.
  - An automated cron job purges media files older than 5 days or when available disk space drops below 15 GB.
- **Verdict:** Best free option. Zero cost, no splitting, instant playback on mobile/TV via VLC or MX Player.

#### Option 2: Telegram Premium Userbot Upload (4 GB Limit)
- **How it works:**
  - Telegram Premium doubles the upload limit from 2 GB to **4 GB** per file.
  - StreamVault would use a Telegram user session (`hydrogram.Client(session_string=...)`) powered by an active Telegram Premium account.
  - Files between 2 GB and 4 GB are uploaded as a single unified `.mkv` or `.mp4` into the private vault channel.
- **Verdict:** Cleanest Telegram-native experience if you already have Telegram Premium.

#### Option 3: Real-Debrid / TorBox Instant Cloud Bridge
- **How it works:**
  - Real-Debrid and TorBox maintain massive cloud caches of nearly all popular torrents.
  - Instead of downloading via aria2c, the bot sends the magnet to Real-Debrid API. If already cached (95% of movies), Real-Debrid generates an unrestricted 1 Gbps direct HTTPS download/stream link in **2 seconds** without any download waiting.
- **Verdict:** Highest speed and zero disk constraint, but requires an active Real-Debrid subscription (~$3/mo).

#### Option 4: Adaptive Cloud HEVC (H.265) Transcoding
- **How it works:**
  - If a 1080p release is 3.5 GB in older H.264 codec, GitHub Actions runs FFmpeg with `libx265 -crf 22 -preset veryfast`.
  - The file size compresses to ~1.2–1.6 GB with zero noticeable visual quality loss, fitting completely inside the free 2 GB Telegram upload limit.
- **Verdict:** Excellent fallback for movies between 2 GB and 4 GB to keep them under 2 GB inside Telegram without parts.

---

### Recommended Hybrid Strategy
1. **Short Term (Immediate):**
   - For files `<= 1.95 GB`: Upload directly to Telegram as single file (Current behavior).
   - For files `> 1.95 GB`: Provide the user with two options:
     1. Direct Magnet Link (for local app download in 1DM / Flud / qBittorrent).
     2. Cloud Leech with current lossless multi-part split for permanent Telegram storage.
2. **Medium Term (Next Phase):**
   - Enable Option 1 (Oracle Direct Stream Gateway) so files >2 GB stream directly from the Oracle VM as a single video link without splitting.
