# Conversations & Brain Archive

This directory stores the complete conversational records, transcripts, steps, and planning artifacts from the Antigravity sessions that created **stream-vault**. 

Keeping this in a dedicated subfolder ensures that project source code remains clean and isolated from conversation metadata.

---

## 🗂️ Archived Sessions

### 1. [Session 01: Telegram Direct Download Link Generator](session_01_direct_download_link_generator)
* **Conversation ID:** `9ac080ce-5d94-4794-aef0-ea7155b769ff`
* **Topic:** Research on how Telegram file-to-link generators work, high-speed download options, open-source bot architectures (FileToLink, HydroStreamerBot, TG-FileStreamBot), and MTProto streaming protocols.
* **Contains:** Full step-by-step reasoning, web search summaries, and raw JSONL transcript logs.

### 2. [Session 02: Telegram Movie Bot Architecture Explained](session_02_movie_bot_architecture_explained)
* **Conversation ID:** `a01f3378-859c-4460-83c1-fd265a9ee6b1`
* **Topic:** Deep-dive `/grill-me` design interview, resolving trade-offs (Torrent Leech vs. Channel Scraper, 2GB upload limit auto-splitting, whitelist authorization, free Hugging Face Docker deployment without credit cards), and codebase generation.
* **Key Artifacts Included:**
  - `hybrid-movie-bot-plan.md`: The complete technical specification and roadmap.
  - `credentials-setup-guide.md`: Step-by-step walkthrough for Telegram API and MongoDB Atlas.
  - Full transcript logs and step outputs.

---

## 💡 How to Use These Logs
If you are an AI assistant (Antigravity, Cursor, etc.) or developer picking up this project:
1. Refer to [CONTINUE.md](../CONTINUE.md) in the project root for the immediate continuation prompt and next tasks.
2. Read the transcript in `session_02_movie_bot_architecture_explained/.system_generated/logs/transcript.jsonl` if you need the exact historical conversation context or previous prompt decisions.
