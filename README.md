# 📚 Physics Wallah Telegram Bot

A Telegram bot that lets you login to Physics Wallah, browse all your batches, and stream videos — all from Telegram.

## ✨ Features

- 🔑 **Login via OTP** — Phone number + OTP authentication
- 📦 **Browse Batches** — All your enrolled batches in an interactive menu
- 📖 **Navigate Content** — Batches → Subjects → Topics → Videos
- 🎬 **Stream Videos** — Direct streaming URLs (redirect to CDN)
- 📥 **Export JSON** — Full batch/content tree as downloadable JSON
- 🔒 **Session Storage** — Tokens saved persistently on Railway

---

## 🚀 Deploy to Railway (Free, No Credit Card)

### Step 1: Create Telegram Bot
1. Open Telegram → search `@BotFather`
2. Send `/newbot` → follow prompts → copy your **Bot Token**

### Step 2: Push to GitHub
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/pw-bot.git
git push -u origin main
```

### Step 3: Deploy on Railway
1. Go to [railway.app](https://railway.app) → Sign up with GitHub (free)
2. Click **New Project** → **Deploy from GitHub repo**
3. Select your repo → Railway auto-detects Python

### Step 4: Set Environment Variables
In Railway dashboard → your service → **Variables** tab:

| Variable | Value |
|----------|-------|
| `BOT_TOKEN` | Your Telegram bot token from BotFather |
| `BASE_URL` | Leave blank for now (fill after deploy) |

Click **Deploy**.

### Step 5: Set BASE_URL
1. After deploy → go to **Settings** tab → **Networking**
2. Click **Generate Domain** → copy the URL (e.g. `https://pw-bot-production.up.railway.app`)
3. Go back to **Variables** → set `BASE_URL` to that URL
4. Redeploy (Railway auto-redeploys on env var changes)

### Step 6: Add Persistent Volume (Optional but Recommended)
1. In your Railway project → **New** → **Volume**
2. Mount path: `/data`
3. This ensures user sessions survive restarts

---

## 🤖 Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome message |
| `/login` | Login with PW phone number |
| `/batches` | Browse your batches |
| `/me` | View account info & token |
| `/logout` | Logout |
| `/help` | Show all commands |

---

## 🏗️ Project Structure

```
pw-telegram-bot/
├── main.py          # Entrypoint (starts bot + server)
├── bot.py           # Telegram bot handlers
├── pw_api.py        # Physics Wallah API wrapper
├── server.py        # Flask streaming proxy server
├── database.py      # JSON file-based session storage
├── requirements.txt
├── Procfile         # Railway/Heroku process config
├── railway.toml     # Railway deployment config
└── .env.example     # Environment variables template
```

---

## 🎬 How Video Streaming Works

```
User clicks video in bot
        ↓
Bot sends: BASE_URL/stream/{video_id}?token={auth_token}
        ↓
Flask server calls PW API with the token
        ↓
Gets real CDN video URL
        ↓
302 Redirect → User's browser/VLC streams directly from CDN
```

**DRM Videos**: Some PW videos are DRM-protected (Widevine). For these, the bot returns the MPD manifest URL and DRM license URL. Use a Widevine-capable player.

---

## 📦 JSON Export Format

```json
{
  "batches": [
    {
      "id": "batch_id",
      "name": "JEE Mains 2024",
      "subjects": [
        {
          "id": "subj_id",
          "name": "Physics",
          "topics": [
            {
              "id": "topic_id",
              "name": "Mechanics",
              "videos": [
                {
                  "id": "video_id",
                  "name": "Newton's Laws",
                  "duration": 3600,
                  "url": "https://cdn.../video.mpd",
                  "drm": false
                }
              ]
            }
          ]
        }
      ]
    }
  ]
}
```

---

## ⚠️ Notes

- This bot is for **personal use only** with your own PW account
- DRM-protected videos require a Widevine-capable player (Chrome, ExoPlayer)
- Free Railway tier gives 500 hours/month — more than enough for personal use
- Session tokens are stored locally in JSON files

---

## 🛠️ Local Development

```bash
pip install -r requirements.txt
cp .env.example .env
# Fill in .env with your BOT_TOKEN and BASE_URL=http://localhost:8080
python main.py
```
