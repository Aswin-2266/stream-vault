# Deploying StreamVault to Hugging Face Spaces (100% Free)

This guide shows you how to run **stream-vault** 24/7 in the cloud on **Hugging Face Spaces** for free with **zero credit card required**.

---

## 🎁 What You Get (Free Tier)
- **Cost:** \$0.00 / forever
- **Credit Card:** Not required
- **RAM:** 16 GB
- **CPU:** 2 dedicated vCPUs
- **Disk:** 50 GB storage buffer
- **Public Domain:** Free HTTPS link (`https://<username>-stream-vault.hf.space`) for direct VLC streaming

---

## 3-Minute Deployment Steps

### Step 1: Create a Free Hugging Face Account
1. Visit [huggingface.co/join](https://huggingface.co/join).
2. Sign up using your email or sign in with your GitHub account.

---

### Step 2: Create a New Docker Space
1. Click your profile picture (top right) and select **New Space** (or go to [huggingface.co/new-space](https://huggingface.co/new-space)).
2. Fill out the form:
   - **Space Name:** `stream-vault`
   - **License:** `MIT`
   - **Select the Space SDK:** Choose **Docker** -> **Blank**
   - **Space Hardware:** Select **Free (2 vCPU · 16 GB RAM)**
   - **Visibility:** Public (recommended so the DDL web stream is accessible to VLC/browsers)
3. Click **Create Space**.

---

### Step 3: Add Your Secrets (Environment Variables)
1. In your newly created Space, navigate to the **Settings** tab.
2. Scroll down to **Variables and secrets**.
3. Under **Secrets**, click **New secret** for each required key:

| Secret Name | Value Example | Description |
| :--- | :--- | :--- |
| `API_ID` | `12345678` | From [my.telegram.org](https://my.telegram.org) |
| `API_HASH` | `abcdef123456789...` | From [my.telegram.org](https://my.telegram.org) |
| `BOT_TOKEN` | `1234567890:ABCdef...` | From `@BotFather` |
| `LOG_CHANNEL_ID` | `-1001234567890` | Your private storage channel ID |
| `MONGO_URI` | `mongodb+srv://...` | Free MongoDB Atlas connection string |
| `ALLOWED_USERS` | `123456789` | Your personal Telegram User ID |
| `STREAM_URL` | `https://<username>-stream-vault.hf.space` | Your Space's public HTTPS URL |

---

### Step 4: Push Your Code to Hugging Face
You can connect Hugging Face directly to your existing GitHub repo or push with git:

```powershell
# Add Hugging Face as a git remote (replace <username> with your HF username)
git remote add hf https://huggingface.co/spaces/<your-username>/stream-vault

# Push code to build and launch
git push hf main --force
```

Hugging Face will automatically read the `Dockerfile`, install `ffmpeg`, `aria2c`, and launch your bot 24/7!
