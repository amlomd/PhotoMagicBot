import os
import logging
import replicate
import tempfile
import requests
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")

replicate_client = replicate.Client(api_token=REPLICATE_API_TOKEN)

logging.basicConfig(level=logging.INFO)
user_prompts = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ברוך הבא! כתוב הוראה כלשהי (כמו 'שנה את הצבע לכחול'), ואז שלח לי תמונה.")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_prompts[user_id] = update.message.text
    await update.message.reply_text("מעולה! עכשיו שלח לי את התמונה שלך.")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    prompt = user_prompts.get(user_id)

    if not prompt:
        await update.message.reply_text("אנא שלח קודם הוראה טקסטואלית מה תרצה שאעשה בתמונה.")
        return

    photo_file = await update.message.photo[-1].get_file()
    photo_url = photo_file.file_path
    logging.info(f"Downloading photo from {photo_url}")

    progress_msg = await update.message.reply_text("🔧 מתחיל לעבוד על התמונה... [0%]")
    for percent in [20, 40, 70, 100]:
        await asyncio.sleep(3)
        await progress_msg.edit_text(f"🔧 עובד על התמונה... [{percent}%]")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tf:
        response = requests.get(photo_url)
        tf.write(response.content)
        tf_path = tf.name

    try:
        output_url = replicate_client.run(
            "timbrooks/instruct-pix2pix:9c0cfdf1c6e06c9691cc8896e72c3cfcdf1a351c",
            input={
                "image": open(tf_path, "rb"),
                "prompt": prompt,
                "num_inference_steps": 20,
                "guidance_scale": 7.5,
            }
        )
        await progress_msg.delete()
        await update.message.reply_photo(photo=output_url)
    except Exception as e:
        logging.error(f"שגיאה: {e}")
        await progress_msg.edit_text("❌ שגיאה בעיבוד התמונה. נסה שוב עם תמונה אחרת או הוראה פשוטה יותר.")
    finally:
        user_prompts.pop(user_id, None)

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    logging.info("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
