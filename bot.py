import os
import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# ============================================
# PUT YOUR BOT TOKEN BELOW (between the quotes)
# ============================================
BOT_TOKEN = "8539560440:AAFU-n-xeBuokRhdFzhhM9BVQdgLDglovzQ"

# Video auto-deletes after 10 minutes (600 seconds)
DELETE_AFTER = 600

# Folder where your videos are stored
VIDEO_FOLDER = "videos"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_video_list():
    if not os.path.exists(VIDEO_FOLDER):
        os.makedirs(VIDEO_FOLDER)
    videos = [
        f for f in os.listdir(VIDEO_FOLDER)
        if f.lower().endswith(('.mp4', '.avi', '.mkv', '.mov'))
    ]
    return sorted(videos)


async def delete_message_later(context: ContextTypes.DEFAULT_TYPE):
    job_data = context.job.data
    chat_id = job_data["chat_id"]
    message_id = job_data["message_id"]
    try:
        await context.bot.delete_message(
            chat_id=chat_id,
            message_id=message_id
        )
        logger.info(f"Deleted message {message_id} in chat {chat_id}")
    except Exception as e:
        logger.error(f"Failed to delete: {e}")


async def send_video_and_schedule_delete(context, chat_id, video_index):
    videos = get_video_list()

    if video_index >= len(videos):
        await context.bot.send_message(chat_id=chat_id, text="Video not found.")
        return

    video_file = videos[video_index]
    video_path = os.path.join(VIDEO_FOLDER, video_file)
    name = os.path.splitext(video_file)[0]

    loading_msg = await context.bot.send_message(
        chat_id=chat_id,
        text="Sending video... please wait."
    )

    try:
        with open(video_path, "rb") as vf:
            video_msg = await context.bot.send_video(
                chat_id=chat_id,
                video=vf,
                caption=(
                    f"  {name}\n\n"
                    f"  This video will be DELETED in 10 minutes!"
                ),
                supports_streaming=True
            )

        await loading_msg.delete()

        # Schedule auto-delete after 10 minutes
        context.job_queue.run_once(
            delete_message_later,
            when=DELETE_AFTER,
            data={"chat_id": chat_id, "message_id": video_msg.message_id}
        )

        warn_msg = await context.bot.send_message(
            chat_id=chat_id,
            text="  Timer started! Video deletes in 10 minutes."
        )

        context.job_queue.run_once(
            delete_message_later,
            when=DELETE_AFTER,
            data={"chat_id": chat_id, "message_id": warn_msg.message_id}
        )

        logger.info(f"Sent video '{video_file}' to {chat_id}")

    except Exception as e:
        await loading_msg.edit_text(f"Error sending video: {e}")
        logger.error(f"Error: {e}")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Check if user clicked a deep link
    if context.args and context.args[0].startswith("video_"):
        video_index = int(context.args[0].split("_")[1])
        await send_video_and_schedule_delete(
            context, update.message.chat_id, video_index
        )
        return

    # Normal /start - show video list
    videos = get_video_list()

    if not videos:
        await update.message.reply_text(
            "No videos found!\n"
            "Add .mp4 files to the 'videos' folder and restart the bot."
        )
        return

    keyboard = []
    for i, video in enumerate(videos):
        name = os.path.splitext(video)[0]
        keyboard.append(
            [InlineKeyboardButton(
                f"  {name}", callback_data=f"video_{i}"
            )]
        )

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "  Welcome to Video Bot!\n\n"
        "Click a button below to watch a video.\n"
        "  Video will auto-delete after 10 minutes!",
        reply_markup=reply_markup
    )


async def list_videos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    videos = get_video_list()

    if not videos:
        await update.message.reply_text("No videos available.")
        return

    keyboard = []
    for i, video in enumerate(videos):
        name = os.path.splitext(video)[0]
        keyboard.append(
            [InlineKeyboardButton(
                f"  {name}", callback_data=f"video_{i}"
            )]
        )

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "  Available Videos:",
        reply_markup=reply_markup
    )


async def get_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    videos = get_video_list()

    if not videos:
        await update.message.reply_text("No videos available.")
        return

    bot_info = await context.bot.get_me()
    bot_username = bot_info.username

    text = "  Shareable Video Links:\n\n"
    for i, video in enumerate(videos):
        name = os.path.splitext(video)[0]
        link = f"https://t.me/{bot_username}?start=video_{i}"
        text += f"  {name}\n   {link}\n\n"

    text += "Share these links with anyone!\n"
    text += "Video plays when they click and deletes after 10 min."

    await update.message.reply_text(text)


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    if not data.startswith("video_"):
        return

    video_index = int(data.split("_")[1])
    chat_id = query.message.chat_id

    await send_video_and_schedule_delete(context, chat_id, video_index)


def main():
    print("========================================")
    print("   Bot is starting...")
    print("========================================")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("list", list_videos))
    app.add_handler(CommandHandler("links", get_links))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("  Bot is running!")
    print("  Press Ctrl+C to stop")
    print("========================================")

    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()