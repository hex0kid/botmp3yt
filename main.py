import os
import random
from datetime import datetime
from collections import defaultdict

import yt_dlp
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, MessageHandler, CommandHandler, ContextTypes, filters
from telegram.request import HTTPXRequest
from telegram.constants import ChatAction


# =========================
# НАСТРОЙКИ
# =========================
TOKEN = os.environ.get("BOT_TOKEN", "").strip() or "8330678502:AAGd0sPQk0YbvVHyrQGNCUCRHu1ZE9b6n2w"
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

request = HTTPXRequest(
    connect_timeout=30,
    read_timeout=300,
    write_timeout=300,
    pool_timeout=30,
)

keyboard = ReplyKeyboardMarkup(
    [["🎧 Скачать бит (просто пришли ссылку)", "ℹ️ Что умеет бот"]],
    resize_keyboard=True
)

user_stats = defaultdict(int)


# =========================
# МОТИВАЦИЯ
# =========================
STARTS = ["{name}, брат", "{name}, время пришло", "{name}, ща будет жара", "{name}, соберись"]
VERBS = ["разъеби", "уничтожь", "разнеси", "разорви", "забери"]
TARGETS = ["этот бит", "этот инструментал", "эту минусовку"]
STYLE = ["без жалости", "на максималках", "как будто это последний шанс"]
PUNCH = ["пусть это станет хитом", "пусть конкуренты молчат", "пусть это будет легенда"]
EMOJI = ["🔥", "💣", "🎧", "🚀", "😈"]

def generate_hype(name: str, count: int) -> str:
    line1 = f"{random.choice(STARTS).format(name=name)} — {random.choice(VERBS)} {random.choice(TARGETS)} {random.choice(STYLE)} {random.choice(EMOJI)}"
    line2 = f"И да: {random.choice(PUNCH)} {random.choice(EMOJI)}"
    stat = f"\n💿 Ты уже забрал {count} бит(ов). Машина."
    return line1 + "\n" + line2 + stat


# =========================
# КОМАНДЫ
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет!\n\nЯ качаю биты с YouTube и отдаю MP3 320kbps.\nПросто пришли ссылку.",
        reply_markup=keyboard
    )

async def info_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ℹ️ Я скачиваю аудио с YouTube и отправляю MP3 320 kbps.\nПосле — даю мотивацию 😈"
    )

def looks_like_youtube(url: str) -> bool:
    u = url.lower()
    return ("youtube.com/" in u) or ("youtu.be/" in u)


# =========================
# СКАЧИВАНИЕ
# =========================
async def convert_and_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()

    if text == "ℹ️ Что умеет бот":
        await info_cmd(update, context)
        return

    if not looks_like_youtube(text):
        await update.message.reply_text("❌ Это не ссылка на YouTube.")
        return

    url = text
    await update.message.reply_text("🎵 Скачиваю и конвертирую в MP3 320kbps...")

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": f"{DOWNLOAD_DIR}/%(id)s.%(ext)s",
        "noplaylist": True,
        "extractor_args": {
            "youtube": {
                "player_client": ["android", "web"],
            }
        },
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "320",
        }],
        "http_headers": {
            "User-Agent": "Mozilla/5.0",
            "Accept-Language": "ru-RU,ru;q=0.9",
            "Referer": "https://www.youtube.com/",
        },
        "retries": 5,
        "fragment_retries": 5,
        "socket_timeout": 30,
        "concurrent_fragment_downloads": 2,
        "quiet": True,
    }

    mp3_file = None
    title = "audio"

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            vid = info.get("id")
            title = info.get("title", "audio")

            if not vid:
                await update.message.reply_text("❌ Не удалось получить данные видео.")
                return

            mp3_file = f"{DOWNLOAD_DIR}/{vid}.mp3"

        await context.bot.send_chat_action(update.effective_chat.id, ChatAction.UPLOAD_DOCUMENT)

        if not os.path.exists(mp3_file):
            await update.message.reply_text("❌ MP3 не найден. Проверь установлен ли ffmpeg.")
            return

        safe_name = "".join(c for c in title if c not in '\\/:*?"<>|').strip()[:80] or "audio"

        with open(mp3_file, "rb") as f:
            await update.message.reply_document(
                document=f,
                filename=f"{safe_name}.mp3",
                read_timeout=300,
                write_timeout=300,
            )

        user = update.effective_user
        user_stats[user.id] += 1
        await update.message.reply_text(generate_hype(user.first_name or "Брат", user_stats[user.id]))

    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

    finally:
        if mp3_file and os.path.exists(mp3_file):
            os.remove(mp3_file)


# =========================
# ЗАПУСК
# =========================
def main():
    print("BOT STARTED ✅")
    app = Application.builder().token(TOKEN).request(request).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("info", info_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, convert_and_send))
    app.run_polling()


if __name__ == "__main__":
    main()
