import logging
import sqlite3
import os
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ChatMemberHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 8520572898
ASK_POST = 1

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN topilmadi!")

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

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


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("⛔ Ruxsat yo'q.")
        return ConversationHandler.END

    cursor.execute("SELECT COUNT(*) FROM chats")
    total = cursor.fetchone()[0]

    keyboard = [["📢 Post yuborish"], ["📊 Statistika"]]

    await update.message.reply_text(
        f"🔐 Admin panel\n\n📌 Ulangan chatlar: {total}",
        reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
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

    elif member.status in ["left", "kicked"]:
        cursor.execute("DELETE FROM chats WHERE chat_id=?", (chat.id,))
        conn.commit()


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
        except:
            failed += 1

    await update.message.reply_text(
        f"✅ Yuborildi: {sent}\n❌ Xatolik: {failed}"
    )

    return await start(update, context)


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    cursor.execute("SELECT COUNT(*) FROM chats")
    total = cursor.fetchone()[0]

    await update.message.reply_text(
        f"📊 Statistika\n\n🔹 Jami chatlar: {total}"
    )


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^📢 Post yuborish$"), post_start)],
        states={ASK_POST: [MessageHandler(filters.ALL & ~filters.COMMAND, send_post)]},
        fallbacks=[],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv)
    app.add_handler(MessageHandler(filters.Regex("^📊 Statistika$"), stats))
    app.add_handler(ChatMemberHandler(track_bot, ChatMemberHandler.MY_CHAT_MEMBER))

    app.run_polling()


if __name__ == "__main__":
    main()
