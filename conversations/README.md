# Conversations & Brain Archive

This directory stores the complete conversational records, transcripts, steps, user-uploaded screenshots, and planning artifacts from the Antigravity sessions that created **stream-vault**.

Keeping this in a dedicated subfolder ensures that the core codebase remains clean and completely decoupled from conversational history.

---

## 🗂️ Archived Sessions

### 1. [Session 01: Telegram Direct Download Link Generator](session_01_direct_download_link_generator)
* **Conversation ID:** `9ac080ce-5d94-4794-aef0-ea7155b769ff`
* **Topic:** Technical investigation into how Telegram direct download link bots and stream engines operate.
* **Key Findings:**
  - Analysis of open-source architectures (`FileToLink`, `HydroStreamerBot`, `TG-FileStreamBot`).
  - Mechanics of MTProto client libraries (`Hydrogram`, `Pyrogram`) vs standard Bot API limits.
  - Byte-range HTTP proxying (`aiohttp`) allowing instant VLC/browser streaming without local file caching.
* **Contains:** Full step-by-step reasoning, web search summaries, and raw JSONL transcript logs.

### 2. [Session 02: Telegram Movie Bot Architecture & Implementation](session_02_movie_bot_architecture_explained)
* **Conversation ID:** `a01f3378-859c-4460-83c1-fd265a9ee6b1`
* **Topic:** Deep-dive `/grill-me` design interview, architecture finalization, credential acquisition, and live deployment.
* **Milestones Covered:**
  - **Sourcing Strategy:** Designed a zero-hotspot-data model using Telegram cloud-to-cloud channel scraping and MongoDB indexing.
  - **Overcoming Limitations:** Handled the 2GB free Telegram upload limit via `ffmpeg` stream copying; marked heavy torrent leeching for Google Colab offloading.
  - **Infrastructure:** Evaluated cloud options (Oracle, Hugging Face Docker paywall, Render resource constraints) and settled on a local/hybrid setup with 0 mobile data usage.
  - **Security & Fixes:** Addressed GitHub Secret Scanning alert by sanitizing placeholder URIs; implemented whitelist authorization (`ALLOWED_USERS`).
  - **Live Launch:** Successfully created `@perso_streamvault_bot`, connected to MongoDB Atlas Mumbai cluster, and started the engine.
* **Key Artifacts Included:**
  - `hybrid-movie-bot-plan.md`: The complete technical specification and roadmap.
  - `credentials-setup-guide.md`: Step-by-step credentials walkthrough.
  - Full transcript logs (`transcript.jsonl`, `transcript_full.jsonl`), step outputs, and all user screenshots.

---

## 💡 How to Resume Development
If you are an AI assistant (Antigravity, Cursor, etc.) or a developer picking up this project:
1. Refer to [CONTINUE.md](../CONTINUE.md) in the project root for the immediate continuation instructions and project status.
2. Read the transcript in `session_02_movie_bot_architecture_explained/.system_generated/logs/transcript.jsonl` if you need the exact historical conversation context or previous prompt decisions.
