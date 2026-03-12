import os, logging, json, io
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, ConversationHandler, filters
)
from pw_api import PhysicsWallahAPI
from database import Database

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
BASE_URL  = os.environ.get("BASE_URL", "")

# Conversation states
ENTER_PHONE, ENTER_OTP, ENTER_TOKEN = range(3)

db = Database()

def stream_url(video_url: str, token: str) -> str:
    """For DRM-free M3U8 URLs, return direct. For others proxy via our server."""
    if BASE_URL and not video_url.startswith("http"):
        return f"{BASE_URL}/stream?url={video_url}&token={token}"
    return video_url  # Direct CDN URL

# ── /start ────────────────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"👋 Welcome *{user.first_name}*\\!\n\n"
        "📚 *Physics Wallah Bot*\n\n"
        "Login with:\n"
        "• /login — OTP login \\(phone number\\)\n"
        "• /token — Paste Bearer token directly\n\n"
        "After login: /batches",
        parse_mode="MarkdownV2"
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *Commands*\n\n"
        "/login \\- Login via OTP\n"
        "/token \\- Login with Bearer token\n"
        "/batches \\- Browse your batches\n"
        "/me \\- Account info\n"
        "/logout \\- Logout\n"
        "/help \\- This message",
        parse_mode="MarkdownV2"
    )

# ── /token — Direct token login ───────────────────────────────────────────────

async def token_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🔑 *Paste your PW Bearer token*\n\n"
        "To get your token:\n"
        "1\\. Open PW app → Login\n"
        "2\\. Use an HTTP interceptor \\(like PCAPdroid\\) to capture the `authorization` header\n"
        "3\\. Copy everything *after* `Bearer `\n\n"
        "Paste it now, or /cancel",
        parse_mode="MarkdownV2"
    )
    return ENTER_TOKEN

async def enter_token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    token = update.message.text.strip()
    # Strip "Bearer " prefix if they pasted the full thing
    if token.lower().startswith("bearer "):
        token = token[7:].strip()

    msg = await update.message.reply_text("⏳ Validating token...")
    api = PhysicsWallahAPI(token)
    result = await api.validate_token(token)

    if result.get("success"):
        user_info = result.get("user", {})
        name = user_info.get("name") or user_info.get("username") or "PW User"
        db.save_user(update.effective_user.id, {
            "token": token, "name": name,
            "phone": user_info.get("phone_number", ""),
            "email": user_info.get("email", ""),
        })
        await msg.edit_text(
            f"✅ *Logged in as {name}\\!*\n\nUse /batches to browse content\\.",
            parse_mode="MarkdownV2"
        )
    else:
        await msg.edit_text(
            f"❌ Invalid token\\.\n`{result.get('message', 'Validation failed')[:200]}`\n\nTry again or use /login",
            parse_mode="MarkdownV2"
        )
    return ConversationHandler.END

# ── /login — OTP flow ─────────────────────────────────────────────────────────

async def login_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if db.get_user(update.effective_user.id, {}).get("token"):
        await update.message.reply_text("✅ Already logged in\\! Use /batches or /logout", parse_mode="MarkdownV2")
        return ConversationHandler.END
    await update.message.reply_text(
        "📱 Enter your *10\\-digit PW registered mobile number*:\n\n/cancel to abort",
        parse_mode="MarkdownV2"
    )
    return ENTER_PHONE

async def enter_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from pw_api import clean_phone
    phone = clean_phone(update.message.text.strip())
    if not phone.isdigit() or len(phone) != 10:
        await update.message.reply_text("❌ Invalid\\. Enter 10\\-digit number:", parse_mode="MarkdownV2")
        return ENTER_PHONE
    context.user_data["phone"] = phone
    msg = await update.message.reply_text("⏳ Sending OTP…")
    result = await PhysicsWallahAPI().send_otp(phone)
    if result.get("success"):
        context.user_data["client_id"] = result.get("clientId", "")
        await msg.edit_text(
            f"✅ OTP sent to *\\+91\\-{phone}*\n\nEnter the 6\\-digit OTP:\n/cancel to abort",
            parse_mode="MarkdownV2"
        )
        return ENTER_OTP
    else:
        await msg.edit_text(
            f"❌ Failed to send OTP:\n`{result.get('message', 'Unknown')[:300]}`\n\n"
            "Try /login again or use /token to paste Bearer token directly\\.",
            parse_mode="MarkdownV2"
        )
        return ConversationHandler.END

async def enter_otp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    otp = update.message.text.strip()
    if not otp.isdigit() or len(otp) != 6:
        await update.message.reply_text("❌ Enter 6\\-digit OTP:", parse_mode="MarkdownV2")
        return ENTER_OTP
    phone = context.user_data.get("phone")
    client_id = context.user_data.get("client_id", "")
    msg = await update.message.reply_text("⏳ Verifying…")
    result = await PhysicsWallahAPI().verify_otp(phone, otp, client_id)
    if result.get("success"):
        token = result.get("token", "")
        user_info = result.get("user", {})
        name = user_info.get("name") or user_info.get("username") or "PW User"
        db.save_user(update.effective_user.id, {
            "token": token, "name": name,
            "phone": phone, "email": user_info.get("email", ""),
        })
        await msg.edit_text(
            f"🎉 *Logged in as {name}\\!*\n\nUse /batches to browse\\.",
            parse_mode="MarkdownV2"
        )
        context.user_data.clear()
        return ConversationHandler.END
    else:
        await msg.edit_text(
            f"❌ OTP failed:\n`{result.get('message', 'Invalid OTP')[:300]}`\n\nTry /login again\\.",
            parse_mode="MarkdownV2"
        )
        return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ Cancelled\\.", parse_mode="MarkdownV2")
    return ConversationHandler.END

# ── /me & /logout ─────────────────────────────────────────────────────────────

async def me(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = db.get_user(update.effective_user.id)
    if not data or not data.get("token"):
        await update.message.reply_text("❌ Not logged in\\. Use /login or /token", parse_mode="MarkdownV2")
        return
    await update.message.reply_text(
        f"👤 *{data.get('name', 'N/A')}*\n"
        f"📱 `{data.get('phone', 'N/A')}`\n"
        f"📧 `{data.get('email', 'N/A')}`\n\n"
        f"🔑 Token: `{data['token'][:30]}…`",
        parse_mode="MarkdownV2"
    )

async def logout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db.delete_user(update.effective_user.id)
    await update.message.reply_text("✅ Logged out\\!", parse_mode="MarkdownV2")

# ── /batches ──────────────────────────────────────────────────────────────────

async def list_batches(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = db.get_user(user_id)
    if not data or not data.get("token"):
        await update.message.reply_text("❌ Not logged in\\. Use /login or /token", parse_mode="MarkdownV2")
        return
    msg = await update.message.reply_text("⏳ Fetching batches…")
    api = PhysicsWallahAPI(data["token"])
    result = await api.get_batches()
    if not result.get("success"):
        await msg.edit_text(f"❌ `{result.get('message', 'Error')[:300]}`", parse_mode="MarkdownV2")
        return
    batches = result.get("batches", [])
    if not batches:
        await msg.edit_text("📭 No batches found\\.", parse_mode="MarkdownV2")
        return
    db.save_batches(user_id, batches)
    keyboard = [[InlineKeyboardButton(f"📦 {b['name']}", callback_data=f"batch_{b['id']}")] for b in batches[:20]]
    keyboard.append([InlineKeyboardButton("📥 Export All JSON", callback_data="export_all")])
    await msg.edit_text(
        f"📚 *{len(batches)} Batches found* — select one:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="MarkdownV2"
    )

# ── Callbacks ─────────────────────────────────────────────────────────────────

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = db.get_user(user_id)
    if not data or not data.get("token"):
        await query.edit_message_text("❌ Session expired\\. Use /login", parse_mode="MarkdownV2")
        return

    cb = query.data
    api = PhysicsWallahAPI(data["token"])
    token = data["token"]

    # Export all
    if cb == "export_all":
        await query.edit_message_text("⏳ Building full JSON export \\(may take a minute\\)…", parse_mode="MarkdownV2")
        batches = db.get_batches(user_id)
        result = await api.get_all_content(batches)
        json_str = json.dumps(result, indent=2, ensure_ascii=False)
        bio = io.BytesIO(json_str.encode())
        bio.name = "pw_content.json"
        await query.message.reply_document(bio, caption="📦 Full PW content exported!")
        await query.edit_message_text("✅ JSON sent above ☝️")
        return

    # Back to batches
    if cb == "back_batches":
        batches = db.get_batches(user_id)
        keyboard = [[InlineKeyboardButton(f"📦 {b['name']}", callback_data=f"batch_{b['id']}")] for b in batches[:20]]
        keyboard.append([InlineKeyboardButton("📥 Export All JSON", callback_data="export_all")])
        await query.edit_message_text(
            f"📚 *{len(batches)} Batches* — select one:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="MarkdownV2"
        )
        return

    # Batch selected → show subjects
    if cb.startswith("batch_"):
        batch_id = cb[6:]
        batches = db.get_batches(user_id)
        batch = next((b for b in batches if b["id"] == batch_id), {"name": batch_id})
        await query.edit_message_text(f"⏳ Loading *{batch['name']}*…", parse_mode="MarkdownV2")
        result = await api.get_batch_subjects(batch_id)
        if not result.get("success"):
            await query.edit_message_text(f"❌ `{result.get('message','Error')[:200]}`", parse_mode="MarkdownV2")
            return
        subjects = result.get("subjects", [])
        keyboard = [[InlineKeyboardButton(f"📖 {s['name']}", callback_data=f"subj_{batch_id}_{s['id']}")] for s in subjects]
        keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="back_batches")])
        await query.edit_message_text(
            f"📦 *{batch['name']}* — {len(subjects)} subjects:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="MarkdownV2"
        )
        return

    # Subject selected → show videos
    if cb.startswith("subj_"):
        _, batch_id, subj_id = cb.split("_", 2)
        await query.edit_message_text("⏳ Loading content…")
        result = await api.get_subject_contents(batch_id, subj_id)
        if not result.get("success"):
            await query.edit_message_text(f"❌ `{result.get('message','Error')[:200]}`", parse_mode="MarkdownV2")
            return
        videos = result.get("videos", [])
        notes  = result.get("notes", [])

        if not videos and not notes:
            await query.edit_message_text("📭 No content found in this subject\\.", parse_mode="MarkdownV2")
            return

        keyboard = []
        for v in videos[:15]:
            keyboard.append([InlineKeyboardButton(f"▶️ {v['name'][:50]}", callback_data=f"vid_{v['id']}")])
            # Store video URL
            db.save_video(v["id"], v)

        for n in notes[:5]:
            keyboard.append([InlineKeyboardButton(f"📄 {n['name'][:50]}", callback_data=f"note_{n['id']}")])
            db.save_video(n["id"], n)

        keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data=f"batch_{batch_id}")])
        await query.edit_message_text(
            f"🎬 *{len(videos)} videos*, 📄 *{len(notes)} notes*\n\nSelect:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="MarkdownV2"
        )
        return

    # Video
    if cb.startswith("vid_"):
        vid_id = cb[4:]
        video = db.get_video(vid_id)
        if video:
            url = video.get("url", "")
            name = video.get("name", "Video")
            drm = video.get("drm", False)
            if drm:
                await query.edit_message_text(
                    f"🔒 *DRM Protected*\n\n`{name}`\n\nMPD URL:\n`{url}`\n\n_Use VLC or ExoPlayer_",
                    parse_mode="MarkdownV2"
                )
            else:
                await query.edit_message_text(
                    f"▶️ *{name}*\n\n🔗 [Stream in Browser]({url})\n\n`{url}`",
                    parse_mode="MarkdownV2",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("▶️ Open Stream", url=url)]])
                )
        return

    # Note
    if cb.startswith("note_"):
        note_id = cb[5:]
        note = db.get_video(note_id)
        if note:
            url = note.get("url", "")
            name = note.get("name", "Notes")
            await query.edit_message_text(
                f"📄 *{name}*\n\n🔗 [Download PDF]({url})",
                parse_mode="MarkdownV2",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📄 Open PDF", url=url)]])
            )
        return

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    login_conv = ConversationHandler(
        entry_points=[CommandHandler("login", login_start)],
        states={
            ENTER_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_phone)],
            ENTER_OTP:   [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_otp)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    token_conv = ConversationHandler(
        entry_points=[CommandHandler("token", token_start)],
        states={
            ENTER_TOKEN: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_token)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("me", me))
    app.add_handler(CommandHandler("logout", logout))
    app.add_handler(CommandHandler("batches", list_batches))
    app.add_handler(login_conv)
    app.add_handler(token_conv)
    app.add_handler(CallbackQueryHandler(button_handler))

    async def error_handler(update, context):
        from telegram.error import Conflict, NetworkError
        if isinstance(context.error, (Conflict, NetworkError)):
            return
        logger.error(f"Error: {context.error}", exc_info=context.error)

    app.add_error_handler(error_handler)
    logger.info("🤖 Bot starting...")
    app.run_polling(drop_pending_updates=True, allowed_updates=["message", "callback_query"])

if __name__ == "__main__":
    main()
