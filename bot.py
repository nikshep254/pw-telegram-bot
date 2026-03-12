import os
import logging
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, ConversationHandler, filters
)
from pw_api import PhysicsWallahAPI
from database import Database

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
BASE_URL = os.environ.get("BASE_URL", "")  # Railway URL for video streaming

# Conversation states
ENTER_PHONE, ENTER_OTP = range(2)

db = Database()

# ─── HELPERS ────────────────────────────────────────────────────────────────

def get_video_url(video_id: str, token: str) -> str:
    return f"{BASE_URL}/stream/{video_id}?token={token}"

# ─── COMMAND HANDLERS ───────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    text = (
        f"👋 Welcome *{user.first_name}*!\n\n"
        "📚 *Physics Wallah Video Bot*\n\n"
        "This bot lets you:\n"
        "• 🔑 Login with your PW account\n"
        "• 📦 Browse all your batches\n"
        "• 🎬 Stream videos directly\n\n"
        "Use /login to get started!"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📖 *Available Commands*\n\n"
        "/start - Welcome message\n"
        "/login - Login with phone number\n"
        "/batches - View all your batches\n"
        "/logout - Logout from your account\n"
        "/me - View your account info\n"
        "/help - Show this help message\n\n"
        "After login, use /batches to explore your content!"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

# ─── LOGIN FLOW ─────────────────────────────────────────────────────────────

async def login_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    existing = db.get_user(user_id)
    if existing and existing.get("token"):
        await update.message.reply_text(
            "✅ You're already logged in!\nUse /batches to explore or /logout to switch accounts."
        )
        return ConversationHandler.END

    await update.message.reply_text(
        "📱 *Login to Physics Wallah*\n\n"
        "Please enter your *registered mobile number*:\n"
        "(Format: 10-digit number, e.g. 9876543210)\n\n"
        "Type /cancel to abort.",
        parse_mode="Markdown"
    )
    return ENTER_PHONE

async def enter_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.text.strip()
    if not phone.isdigit() or len(phone) != 10:
        await update.message.reply_text("❌ Invalid number. Enter a 10-digit mobile number:")
        return ENTER_PHONE

    phone = phone.strip()
    # Strip country code just in case user typed it
    if phone.startswith("+91"): phone = phone[3:]
    elif phone.startswith("91") and len(phone) == 12: phone = phone[2:]
    context.user_data["phone"] = phone
    msg = await update.message.reply_text("⏳ Sending OTP...")

    api = PhysicsWallahAPI()
    result = await api.send_otp(phone)

    if result.get("success"):
        context.user_data["client_id"] = result.get("clientId", "")
        await msg.edit_text(
            f"✅ OTP sent to *+91-{phone}*\n\n"
            "Please enter the *6-digit OTP* you received:\n\n"
            "Type /cancel to abort.",
            parse_mode="Markdown"
        )
        return ENTER_OTP
    else:
        await msg.edit_text(
            f"❌ Failed to send OTP: {result.get('message', 'Unknown error')}\n"
            "Try /login again."
        )
        return ConversationHandler.END

async def enter_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    otp = update.message.text.strip()
    if not otp.isdigit() or len(otp) != 6:
        await update.message.reply_text("❌ Invalid OTP. Enter the 6-digit OTP:")
        return ENTER_OTP

    phone = context.user_data.get("phone")
    client_id = context.user_data.get("client_id", "")
    msg = await update.message.reply_text("⏳ Verifying OTP...")

    api = PhysicsWallahAPI()
    result = await api.verify_otp(phone, otp, client_id)

    if result.get("success"):
        token = result.get("token")
        refresh_token = result.get("refreshToken", "")
        user_info = result.get("user", {})

        user_id = update.effective_user.id
        db.save_user(user_id, {
            "phone": phone,
            "token": token,
            "refresh_token": refresh_token,
            "name": user_info.get("name", "User"),
            "email": user_info.get("email", ""),
        })

        await msg.edit_text(
            f"🎉 *Login Successful!*\n\n"
            f"👤 Name: {user_info.get('name', 'N/A')}\n"
            f"📱 Phone: +91-{phone}\n\n"
            "Use /batches to explore your content!",
            parse_mode="Markdown"
        )
        context.user_data.clear()
        return ConversationHandler.END
    else:
        await msg.edit_text(
            f"❌ OTP verification failed: {result.get('message', 'Invalid OTP')}\n"
            "Try /login again."
        )
        return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ Login cancelled.")
    return ConversationHandler.END

# ─── ACCOUNT ────────────────────────────────────────────────────────────────

async def me(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    if not user_data or not user_data.get("token"):
        await update.message.reply_text("❌ Not logged in. Use /login first.")
        return

    await update.message.reply_text(
        f"👤 *Your Account*\n\n"
        f"Name: {user_data.get('name', 'N/A')}\n"
        f"Phone: +91-{user_data.get('phone', 'N/A')}\n"
        f"Email: {user_data.get('email', 'N/A')}\n\n"
        f"🔑 Token: `{user_data['token'][:20]}...`",
        parse_mode="Markdown"
    )

async def logout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db.delete_user(user_id)
    await update.message.reply_text("✅ Logged out successfully! Use /login to login again.")

# ─── BATCHES ────────────────────────────────────────────────────────────────

async def list_batches(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = db.get_user(user_id)
    if not user_data or not user_data.get("token"):
        await update.message.reply_text("❌ Not logged in. Use /login first.")
        return

    msg = await update.message.reply_text("⏳ Fetching your batches...")
    api = PhysicsWallahAPI(user_data["token"])
    result = await api.get_batches()

    if not result.get("success"):
        await msg.edit_text(f"❌ Failed to fetch batches: {result.get('message', 'Error')}")
        return

    batches = result.get("batches", [])
    if not batches:
        await msg.edit_text("📭 No batches found in your account.")
        return

    # Save batches for later navigation
    db.save_batches(user_id, batches)

    keyboard = []
    for batch in batches[:20]:  # Telegram limit
        keyboard.append([
            InlineKeyboardButton(
                f"📦 {batch.get('name', 'Batch')}",
                callback_data=f"batch_{batch['id']}"
            )
        ])
    keyboard.append([InlineKeyboardButton("📥 Export All as JSON", callback_data="export_all")])

    await msg.edit_text(
        f"📚 *Your Batches* ({len(batches)} found)\n\nSelect a batch to explore:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

# ─── CALLBACK HANDLERS ──────────────────────────────────────────────────────

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user_data = db.get_user(user_id)

    if not user_data or not user_data.get("token"):
        await query.edit_message_text("❌ Session expired. Use /login again.")
        return

    data = query.data
    api = PhysicsWallahAPI(user_data["token"])

    # ── Export all batches as JSON ──────────────────────────────────────────
    if data == "export_all":
        await query.edit_message_text("⏳ Fetching full batch data, this may take a moment...")
        batches = db.get_batches(user_id)
        result = await api.get_all_content(batches)
        json_str = json.dumps(result, indent=2, ensure_ascii=False)

        # Send as file if too large
        if len(json_str) > 4000:
            import io
            bio = io.BytesIO(json_str.encode())
            bio.name = "pw_batches.json"
            await query.message.reply_document(bio, caption="📦 All your PW batches & content exported!")
            await query.edit_message_text("✅ JSON exported above ☝️")
        else:
            await query.edit_message_text(f"```json\n{json_str[:3900]}\n```", parse_mode="Markdown")
        return

    # ── Batch selected ──────────────────────────────────────────────────────
    if data.startswith("batch_"):
        batch_id = data[6:]
        batches = db.get_batches(user_id)
        batch = next((b for b in batches if str(b["id"]) == batch_id), None)
        batch_name = batch.get("name", batch_id) if batch else batch_id

        await query.edit_message_text(f"⏳ Fetching content for *{batch_name}*...", parse_mode="Markdown")
        result = await api.get_batch_subjects(batch_id)

        if not result.get("success"):
            await query.edit_message_text(f"❌ {result.get('message', 'Failed to load batch')}")
            return

        subjects = result.get("subjects", [])
        if not subjects:
            await query.edit_message_text("📭 No subjects found in this batch.")
            return

        keyboard = []
        for subj in subjects:
            keyboard.append([
                InlineKeyboardButton(
                    f"📖 {subj.get('name', 'Subject')}",
                    callback_data=f"subj_{batch_id}_{subj['id']}"
                )
            ])
        keyboard.append([InlineKeyboardButton("⬅️ Back to Batches", callback_data="back_batches")])

        await query.edit_message_text(
            f"📦 *{batch_name}*\n\n📚 Subjects ({len(subjects)}):",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return

    # ── Subject selected ────────────────────────────────────────────────────
    if data.startswith("subj_"):
        parts = data.split("_", 2)
        batch_id, subj_id = parts[1], parts[2]

        await query.edit_message_text("⏳ Fetching topics...")
        result = await api.get_subject_topics(batch_id, subj_id)

        if not result.get("success"):
            await query.edit_message_text(f"❌ {result.get('message', 'Failed to load topics')}")
            return

        topics = result.get("topics", [])
        keyboard = []
        for topic in topics[:15]:
            keyboard.append([
                InlineKeyboardButton(
                    f"📝 {topic.get('name', 'Topic')}",
                    callback_data=f"topic_{batch_id}_{subj_id}_{topic['id']}"
                )
            ])
        keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data=f"batch_{batch_id}")])

        await query.edit_message_text(
            f"📖 Topics ({len(topics)}):",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return

    # ── Topic (video list) ──────────────────────────────────────────────────
    if data.startswith("topic_"):
        parts = data.split("_", 3)
        batch_id, subj_id, topic_id = parts[1], parts[2], parts[3]

        await query.edit_message_text("⏳ Fetching videos...")
        result = await api.get_topic_videos(batch_id, subj_id, topic_id)

        if not result.get("success"):
            await query.edit_message_text(f"❌ {result.get('message', 'Failed to load videos')}")
            return

        videos = result.get("videos", [])
        if not videos:
            await query.edit_message_text("📭 No videos found in this topic.")
            return

        keyboard = []
        for v in videos[:10]:
            keyboard.append([
                InlineKeyboardButton(
                    f"▶️ {v.get('name', 'Video')}",
                    callback_data=f"video_{v['id']}"
                )
            ])
        keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data=f"subj_{batch_id}_{subj_id}")])

        await query.edit_message_text(
            f"🎬 Videos ({len(videos)}):",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return

    # ── Video selected ──────────────────────────────────────────────────────
    if data.startswith("video_"):
        video_id = data[6:]
        token = user_data["token"]
        stream_url = get_video_url(video_id, token)

        await query.edit_message_text(
            f"🎬 *Video Ready!*\n\n"
            f"🔗 [Click to Stream]({stream_url})\n\n"
            f"📋 Video ID: `{video_id}`\n\n"
            f"_Link works in browser or VLC_",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🎬 Open Stream", url=stream_url)
            ]])
        )
        return

    # ── Back to batches ─────────────────────────────────────────────────────
    if data == "back_batches":
        batches = db.get_batches(user_id)
        keyboard = []
        for batch in batches[:20]:
            keyboard.append([
                InlineKeyboardButton(
                    f"📦 {batch.get('name', 'Batch')}",
                    callback_data=f"batch_{batch['id']}"
                )
            ])
        keyboard.append([InlineKeyboardButton("📥 Export All as JSON", callback_data="export_all")])
        await query.edit_message_text(
            f"📚 *Your Batches* ({len(batches)} found)\n\nSelect a batch to explore:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

# ─── MAIN ───────────────────────────────────────────────────────────────────

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    login_handler = ConversationHandler(
        entry_points=[CommandHandler("login", login_start)],
        states={
            ENTER_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_phone)],
            ENTER_OTP:   [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_otp)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("me", me))
    app.add_handler(CommandHandler("logout", logout))
    app.add_handler(CommandHandler("batches", list_batches))
    app.add_handler(login_handler)
    app.add_handler(CallbackQueryHandler(button_handler))

    logger.info("🤖 Bot starting...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
