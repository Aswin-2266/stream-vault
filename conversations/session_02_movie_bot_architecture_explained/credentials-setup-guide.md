# Telegram & MongoDB Credentials Setup Walkthrough

This guide details how to obtain the necessary credentials to build and run your **Hybrid Telegram Movie Bot**.

---

### 1. Telegram Bot Token (@BotFather)
1. Open Telegram and search for **`@BotFather`**.
2. Send `/newbot`.
3. Provide a display name (e.g., `My Movie Streamer`) and a bot username ending in `bot` (e.g., `my_movie_streamer_bot`).
4. Copy the HTTP API token provided (e.g., `1234567890:ABCdefGhIJKlmNoPQRsTUVwxyZ`).

---

### 2. Telegram API ID & API Hash (my.telegram.org)
1. Navigate to [my.telegram.org](https://my.telegram.org) in a web browser.
2. Sign in with your Telegram phone number and verify via the in-app code.
3. Click on **API development tools**.
4. Fill in an app title and short name (e.g., `MovieScraper`).
5. Copy the generated **`App api_id`** and **`App api_hash`**.

---

### 3. Private Storage / Log Channel
1. In Telegram, create a **New Private Channel** (e.g., `Movie Storage Vault`).
2. Add your newly created bot as an **Administrator** with full permissions.
3. Obtain the Channel ID (starts with `-100`, e.g., `-1001987654321`) by forwarding a channel post to `@userinfobot`.

---

### 4. Free MongoDB Atlas Cluster
1. Sign up at [mongodb.com/cloud/atlas](https://www.mongodb.com/cloud/atlas/register).
2. Create a free deployment (**M0 Free Shared** tier).
3. Under Database Access, create a username and strong password.
4. Under Network Access, add `0.0.0.0/0` (Allow access from anywhere).
5. In Cluster view, click **Connect** → **Drivers** (Python) and copy the connection URI string.

---

### Configuration Reference (`.env`)
```env
API_ID=your_api_id
API_HASH=your_api_hash
BOT_TOKEN=your_bot_token
LOG_CHANNEL_ID=-100xxxxxxxxxx
MONGO_URI=your_mongodb_connection_uri_here
```
