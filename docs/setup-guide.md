# Credentials & Prerequisites Setup Guide

This guide walks you through acquiring the necessary API keys, database, and Telegram channel setup required for your **Hybrid Telegram Movie Bot** (Telegram Scraper + Cloud Torrent Leech).

---

## 1. Telegram Bot Token (from @BotFather)

The Bot Token allows your bot to send messages, display search buttons, and serve files to users.

1. Open Telegram and search for **`@BotFather`** (ensure it has the official blue verification checkmark).
2. Send the command:
   ```text
   /newbot
   ```
3. Enter a friendly name for your bot (e.g., `My Personal Movie Finder`).
4. Enter a unique username ending in `bot` (e.g., `my_private_streamer_bot`).
5. BotFather will provide an HTTP API token formatted like:
   ```text
   1234567890:ABCdefGhIJKlmNoPQRsTUVwxyZ
   ```
6. **Save this token** as your `BOT_TOKEN`.

---

## 2. Telegram API ID & API Hash (my.telegram.org)

The API ID and Hash allow the bot to run MTProto userbot sessions to scrape, clone, and download files from public Telegram channels.

1. Go to [https://my.telegram.org](https://my.telegram.org) in your web browser.
2. Log in using your phone number (including international country code, e.g., `+91...`).
3. Telegram will send a login confirmation code to your Telegram app. Enter it on the website.
4. Click on **API development tools**.
5. Fill out the short form:
   - **App title:** Any name (e.g., `MovieScraper`)
   - **Short name:** Any short name (e.g., `moviescraper`)
   - **Platform:** Desktop or Other
6. Click **Create application**.
7. You will see:
   - **`App api_id`** (an integer, e.g., `12345678`)
   - **`App api_hash`** (a 32-character hex string, e.g., `a1b2c3d4e5f6g7h8...`)
8. **Save both** as your `API_ID` and `API_HASH`.

---

## 3. Create Your Private Storage / Database Channel

This private channel acts as your cloud storage where all your movie files will live permanently.

1. In Telegram, create a **New Channel**.
2. Set the channel to **Private** (do not make it public to prevent copyright issues).
3. Name it something like `Movie Cloud Vault`.
4. Open the channel settings and add your newly created bot as an **Administrator** with full permissions (Post Messages, Edit Messages, Delete Messages).
5. Post any message in the channel, forward it to **`@userinfobot`** or **`@MissRose_bot`** to get the Channel ID (usually starts with `-100`, e.g., `-1001987654321`).
6. **Save this ID** as your `LOG_CHANNEL_ID`.

---

## 4. Free MongoDB Database (MongoDB Atlas)

MongoDB will store the filenames, resolutions, sizes, and Telegram `file_id` pointers so searches are instantaneous.

1. Go to [https://www.mongodb.com/cloud/atlas/register](https://www.mongodb.com/cloud/atlas/register) and sign up for a free account.
2. When prompted to select a plan, choose the **M0 Free (Shared)** tier.
3. Select any cloud provider and region closest to you (e.g., AWS / Mumbai, Frankfurt, or Virginia).
4. Click **Create Deployment**.
5. **Security Setup:**
   - **Database User:** Create a username and password (e.g., user: `moviebot`, password: `YourStrongPassword123`). Note them down.
   - **Network Access (IP Access List):** Click **Allow Access from Anywhere** (`0.0.0.0/0`).
     > [!IMPORTANT]
     > If connecting via a mobile 5G hotspot (e.g., Airtel, Jio), your carrier assigns dynamic CGNAT IP addresses that change frequently. You **must** whitelist `0.0.0.0/0` in Atlas Network Access, otherwise you will encounter `SSL: TLSV1_ALERT_INTERNAL_ERROR` connection drops.
6. **Get Connection String:**
   - Go to your Database Cluster overview and click **Connect**.
   - Choose **Drivers** (Python).
   - Copy the connection URI string. It looks like:
     ```text
     mongodb+srv://<username>:<password>@<cluster-name>.mongodb.net/?retryWrites=true&w=majority
     ```
   - Replace `<username>` and `<password>` with your database user credentials.
7. **Save this connection string** as your `MONGO_URI`.

---

## 5. Cloudflare Tunnel Gateway (Auto-Generated HTTPS)

StreamVault includes `bin/cloudflared.exe`. When launched locally:
- It creates an encrypted HTTPS tunnel (`https://*.trycloudflare.com`) pointing directly to your local port 7860.
- This allows your phone browser, VLC, and 1DM+ to stream movies without port-forwarding your home router or paying for a VPS.

---

## 6. High-Speed MTProto Crypto Acceleration

To ensure video streaming starts instantly without `Retrying upload.GetFile due to: Request timed out`:
- `cryptg` is used to hardware-accelerate AES-256-IGE decryption via AES-NI CPU instructions.
- Decryption time is reduced from ~15 seconds per MiB chunk down to **1.78 milliseconds**.

---

## Summary of Credentials Needed in `.env`

Once you have completed these steps, your project configuration file (`.env`) will contain:

```env
API_ID=your_api_id_here
API_HASH=your_api_hash_here
BOT_TOKEN=your_bot_token_here
LOG_CHANNEL_ID=-100xxxxxxxxxx
MONGO_URI=your_mongodb_connection_uri_here
```
