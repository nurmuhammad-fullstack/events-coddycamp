import logging
import sqlite3
import os
from datetime import datetime
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ChatMemberHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

# ==============================
# CONFIG
# ==============================

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 1210446923   # <-- o'zingning Telegram ID

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN topilmadi! Railway Variables ga qo'shing.")

ASK_POST = 1

# ==============================
# LOGGING
# ==============================

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

logger = logging.getLogger(__name__)

# ==============================
# DATABASE
# ==============================

conn = sqlite3.connect("database.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS chats (
    chat_id INTEGER PRIMARY KEY,
    chat_type TEXT,
    title TEXT,
    added_date TEXT
)
""")

conn.commit()

# ==============================
# HANDLERS
# ==============================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Ruxsat yo'q.")
        return ConversationHandler.END

    cursor.execute("SELECT COUNT(*) FROM chats")
    total = cursor.fetchone()[0]

    keyboard = [
        ["📢 Post yuborish"],
        ["📊 Statistika"]
    ]
    markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        f"🔐 Admin panel\n\n"
        f"📌 Ulangan chatlar: {total}",
        reply_markup=markup
    )
    return ConversationHandler.END


async def track_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    member = update.my_chat_member.new_chat_member

    if member.status in ["administrator", "member"]:
        cursor.execute("""
        INSERT OR IGNORE INTO chats (chat_id, chat_type, title, added_date)
        VALUES (?, ?, ?, ?)
        """, (
            chat.id,
            chat.type,
            chat.title,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))
        conn.commit()
        logger.info(f"Qo'shildi: {chat.id}")

    elif member.status in ["left", "kicked"]:
        cursor.execute("DELETE FROM chats WHERE chat_id=?", (chat.id,))
        conn.commit()
        logger.info(f"O'chirildi: {chat.id}")


async def post_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return ConversationHandler.END

    await update.message.reply_text(
        "✍ Postni yuboring:",
        reply_markup=ReplyKeyboardRemove()
    )
    return ASK_POST


async def send_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return ConversationHandler.END

    message = update.message

    cursor.execute("SELECT chat_id FROM chats")
    chats = cursor.fetchall()

    sent = 0
    failed = 0

    for (chat_id,) in chats:
        try:
            await message.copy(chat_id=chat_id)
            sent += 1
        except Exception as e:
            failed += 1
            logger.warning(f"Xatolik {chat_id}: {e}")

    await update.message.reply_text(
        f"✅ Yuborildi: {sent}\n"
        f"❌ Xatolik: {failed}"
    )

    return await start(update, context)


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    cursor.execute("SELECT COUNT(*) FROM chats")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM chats WHERE chat_type='channel'")
    channels = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM chats WHERE chat_type='supergroup'")
    groups = cursor.fetchone()[0]

    await update.message.reply_text(
        f"📊 Statistika\n\n"
        f"🔹 Jami: {total}\n"
        f"📢 Kanallar: {channels}\n"
        f"👥 Guruhlar: {groups}"
    )

# ==============================
# MAIN
# ==============================

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("^📢 Post yuborish$"), post_start)
        ],
        states={
            ASK_POST: [
                MessageHandler(filters.ALL & ~filters.COMMAND, send_post)
            ]
        },
        fallbacks=[],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv)
    app.add_handler(MessageHandler(filters.Regex("^📊 Statistika$"), stats))
    app.add_handler(ChatMemberHandler(track_bot, ChatMemberHandler.MY_CHAT_MEMBER))

    logger.info("Bot ishga tushdi...")
    app.run_polling()


if __name__ == "__main__":
    main()
