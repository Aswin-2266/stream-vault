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
   - **Network Access (IP Access List):** Click **Allow Access from Anywhere** (`0.0.0.0/0`). This allows your bot to connect from your PC or any cloud server.
6. **Get Connection String:**
   - Go to your Database Cluster overview and click **Connect**.
   - Choose **Drivers** (Python).
   - Copy the connection URI string. It looks like:
     ```text
     mongodb+srv://moviebot:<password>@cluster0.abcde.mongodb.net/?retryWrites=true&w=majority
     ```
   - Replace `<password>` with the database password you created in step 5.
7. **Save this connection string** as your `MONGO_URI`.

---

## Summary of Credentials Needed in `.env`

Once you have completed these steps, your project configuration file (`.env`) will contain:

```env
API_ID=12345678
API_HASH=abcdef1234567890abcdef1234567890
BOT_TOKEN=1234567890:ABCdefGhIJKlmNoPQRsTUVwxyZ
LOG_CHANNEL_ID=-1001987654321
MONGO_URI=mongodb+srv://moviebot:password@cluster0.abcde.mongodb.net/?retryWrites=true&w=majority
```
