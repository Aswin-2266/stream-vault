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

---

## Pending Decision 2: Cloud Leech Reliability & P2P Architecture

### Context & Problem Statement
During initial testing of the GitHub Actions cloud runner, torrent downloads for regional Indian releases (TamilBlasters, TamilMV) stalled and timed out after 122 seconds with:
`RuntimeError: Torrent download stalled or timed out (no active seeders available)`.

### Root Cause Analysis
1. **Aggressive Timeout:** aria2c was configured with `--bt-stop-timeout=120`. When resolving magnet links, downloading metadata from the DHT swarm often takes 2–5 minutes at 0 B/s file transfer speed, causing aria2c to terminate prematurely before reaching the actual download stage.
2. **Datacenter Firewall & CGNAT Mismatch:** Microsoft Azure (where GitHub Actions runs) filters inbound UDP traffic on standard BitTorrent ports (6881). Meanwhile, residential seeders in India (JioFiber, Airtel Xstream) are behind Carrier-Grade NAT (CGNAT). When both peers are behind NAT with no open inbound ports, they cannot establish direct P2P connections unless a peer with a dedicated public IP / Seedbox is present in the swarm.

---

### Implementation Status of Evaluated Options

#### Option 1: Optimized GitHub Actions Runner (APPLIED & ACTIVE)
- **Status:** **Implemented & Deployed.**
- **Changes applied in `scripts/cloud_leech.py`:**
  - Extended `--bt-stop-timeout` from 120s to **600s (10 minutes)** to grant ample time for metadata discovery and handshaking.
  - Added global DHT bootstrap router: `--dht-entry-point=router.bittorrent.com:6881`.
  - Shifted ports to `--dht-listen-port=50101-50109` and `--listen-port=50101-50109` to circumvent common datacenter blocks on port 6881.
  - Enabled `--file-allocation=none` to eliminate multi-minute zero-allocation stalls.
  - Increased tracker connection timeouts to 30s and enabled Local Peer Discovery (`--bt-enable-lpd=true`).
  - Added Telegram progress update during metadata resolution: `🔍 Connecting to BitTorrent swarm & discovering peer metadata...`.

---

#### Option 2: Native Oracle Cloud VM Leeching Worker (PENDING DECISION - PLANNED)
- **Status:** **Architected for future activation.**
- **Why it solves the problem permanently:**
  - The Oracle Always Free VM (`140.245.193.224`) possesses a **static, dedicated public IPv4 address**.
  - Inbound ports `6881-6889` (or `50000-50100`) can be opened directly in the OCI Security List and Ubuntu `iptables`.
  - Because the Oracle VM has an open public listening port, **any seeder (even home users on Jio/Airtel CGNAT) can initiate inbound connections directly to your VM**.
  - 100 GB NVMe disk and 10 TB free monthly egress bandwidth allow 24/7 background leeching without runner time limits.
- **Implementation Blueprint:**
  - Deploy a lightweight systemd daemon `streamvault-leech.service` on the Oracle VM.
  - The daemon monitors MongoDB Atlas `leech_queue` for new tasks submitted via the bot.
  - Once downloaded, it either copies directly to `/var/streamvault/media/` for 0-wait local streaming or uploads to Telegram Vault.

---

#### Option 3: Debrid Cloud Integration (PENDING DECISION - IN-DEPTH ANALYSIS)
- **Status:** **Evaluated with real-world 2025/2026 internet data.**
- **Comparison of Free vs. Paid Debrid Services:**

| Provider | Tier | Storage / Task Limits | Rate Limits & Cooldowns | API Usability for Bot | Real-World Verdict |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **TorBox** | **Free** | 10 GB max per torrent | **1 download per 24 hours**;<br>Max **10 downloads/month** | Official REST API | ❌ **Too restrictive for automated bots.** The 1-per-day cooldown blocks consecutive searches/downloads. |
| **Seedr.cc** | **Free** | **2.0 GB** baseline storage (expandable to ~4 GB via social tasks) | 1 parallel download slot | Unofficial / REST API | ❌ **Incompatible with 1080p movies.** Nearly all 1080p Indian releases are 2.2–4.5 GB, triggering immediate "Storage full" errors. |
| **PikPak** | **Free** | **6.0 GB** total storage | 3–5 cloud download tasks/day | Reverse-engineered API only | ⚠️ **Good size limit, poor bot API.** Fits 1080p releases, but lacks an open developer API and requires account rotation. |
| **Real-Debrid** | **Paid** (~₹250/mo or $3/mo) | **Unlimited** (100 GB+ files) | **Unlimited** high-speed caching | Official, robust REST API | ✅ **Gold standard.** Un-restricts torrents in 2 seconds from 10 Gbps CDN caches. Zero P2P seeding issues, 100% reliable. |

- **Conclusion for Option 3:**
  - **Free debrid tiers** (TorBox, Seedr, PikPak) enforce heavy rate limits (1 per day on TorBox) or small storage ceilings (2 GB on Seedr) that make them impractical as an automated bot backend.
  - If third-party cloud caching is desired in the future, **Real-Debrid** (~₹250/month) is the only provider that provides instant 2-second caching and reliable automation without maintenance headaches.

---

#### Option 4: Instant Torrent Finder with Mobile Local Download (ACTIVE)
- **Status:** **Implemented & Fully Operational.**
- Tapping any release in search options displays the full release details and a 1-tap copyable `magnet:?xt=...` code block.
- Users can copy the magnet with a single tap and download directly via **1DM+ or Flud** on Android (or qBittorrent on PC).
- Mobile cellular networks (Jio 5G / Airtel 5G) route peer-to-peer traffic directly between domestic peers, bypassing datacenter firewall limitations.

---

## Pending Decision 3: Alternative Content Sourcing & Streaming Engines (Beyond Torrents)

### Context & Problem Statement
When searching for older movies or regional dubbed content (e.g., *The Shawshank Redemption* in Tamil/Telugu or older 90s/2000s classics), BitTorrent swarms often have **0 active seeders**, causing downloads to stall indefinitely regardless of open ports or timeout settings. 

To eliminate dead-end searches and stalled downloads, alternative acquisition and streaming pipelines were evaluated.

---

### Comparative Evaluation of Content Delivery Methods

| Method | Speed | Availability of Tamil/Telugu Dubs | Reliability | Cost / Requirements |
| :--- | :--- | :--- | :--- | :--- |
| **1. P2P Torrents (Current)** | Fast if $\ge 20$ seeds; Stalls if $<10$ seeds | High (Tamilblasters / TamilMV) | Low on older movies (Dead swarms) | 100% Free |
| **2. Debrid Cloud (TorBox / RD)** | **Instant (0.5s cached)** | **Very High** (almost everything cached) | **Very High** | Free tier limited; Paid ~$3.50/mo |
| **3. Web Scrapers (VidSrc)** | **Instant** | **Low to Medium** (mostly English/Hindi) | **Medium** | **100% Free** |
| **4. Telegram Userbot (Inside TG)** | **Instant (1-2s cloud copy)** | **Highest** (Telegram is king for regional content) | **High** | **100% Free** (Needs phone session) |

---

### Detailed Analysis of Evaluated Options

#### Option 1: Debrid Cloud Integration (TorBox / Real-Debrid)
- **Status:** **Evaluated (Pending Decision for paid vs. limited free integration).**
- **Characteristics:**
  - **Speed:** Instant (0.5s cached response).
  - **Availability:** Very High (almost all popular and regional torrent releases are pre-cached).
  - **Reliability:** Very High (no relying on active seeders or open firewall ports).
  - **Cost / Requirements:** Free tier limited; Paid ~$3.50/month (~₹250/mo).
- **How it works:**
  - Debrid servers (Real-Debrid, TorBox) operate massive petabyte storage clusters. Whenever any user worldwide requests a torrent, it is downloaded once and permanently stored on high-speed cloud CDNs.
  - When our bot checks a torrent magnet against the Debrid API:
    - If already cached (~95% of Tamilblasters/TamilMV releases), it bypasses P2P downloading completely.
    - It immediately returns a direct, unmetered **1 Gbps HTTPS stream / download link** in **0.5 seconds**.
- **Tier Differences:**
  - **TorBox (Free):** 10 GB torrent limit, but restricted to **1 download per 24 hours** (max 10/month), suitable only as an occasional emergency fallback.
  - **Real-Debrid (Paid, ~$3.50/mo):** Unlimited downloads, uncapped multi-gigabit bandwidth, near 100% cache hit rate for regional films.
- **Bot Integration Blueprint:**
  - Add an inline button: `[⚡ Instant Stream via Debrid]`.
  - Bot checks hash cache status; if cached, replies instantly with the direct streaming link without launching any background download runner.

#### Option 2: Free Web Streaming Scrapers (VidSrc / SuperEmbed / HLS)
- **Status:** **Evaluated (Pending Decision for 100% free web streaming fallback).**
- **Characteristics:**
  - **Speed:** Instant (direct video stream).
  - **Availability:** Low to Medium (mostly English and popular Hindi content; regional Tamil/Telugu dubs are rare).
  - **Reliability:** Medium (embed domains frequently rotate or enable anti-bot protections).
  - **Cost / Requirements:** **100% Free Forever**.
- **How it works:**
  - Web scraping engines resolve streaming links from free movie indexers (VidSrc, SuperEmbed, 2Embed) using IMDb or TMDB movie IDs (e.g., `tt0111161`).
  - Scrapes the direct `.m3u8` (HLS adaptive stream) or `.mp4` CDN link.
  - Users can stream immediately in their web browser or open the link directly in VLC Player without downloading any torrent or consuming cloud storage.
- **Key Limitations:**
  - Free web scrapers rarely cater to South Indian regional audio languages (Tamil, Telugu, Malayalam, Kannada), focusing heavily on Hollywood (English) and Bollywood (Hindi).
  - Embed providers regularly change player domain names and iframe obfuscation scripts, requiring occasional maintenance.
- **Bot Integration Blueprint:**
  - When P2P torrent seeders are 0 or user selects instant web view, offer an inline button: `[🌐 Instant Web Stream (VidSrc)]`.
  - Opens direct in-browser player or returns VLC-compatible HLS stream link.

#### Option 3: Telegram Userbot Ingestion (Native TG Cloud Library)
- **Status:** **Evaluated (Highest potential for 100% free regional South Indian content).**
- **Characteristics:**
  - **Speed:** Instant (1–2 second cloud-to-cloud file copy).
  - **Availability:** Highest (Telegram is the largest active library for Tamil, Telugu, and Hindi dubbed movies).
  - **Reliability:** High (files are already hosted on Telegram's high-speed media servers).
  - **Cost / Requirements:** **100% Free** (Requires a Telegram user session string / phone authorization).
- **How it works:**
  - Powered by a secondary Telegram account via Hydrogram `SESSION_STRING`.
  - When a user searches for a movie not yet in the private vault, the userbot executes `client.search_global("Movie Name Tamil")` across public channels.
  - Copies the discovered `.mkv` file directly to the private Vault channel in 1–2 seconds with **0 MB mobile data consumption**.


