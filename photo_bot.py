import logging
import replicate
import tempfile
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes

import os

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
REPLICATE_API_TOKEN = os.getenv("REPLICATE_API_TOKEN")


replicate_client = replicate.Client(api_token=REPLICATE_API_TOKEN)
logging.basicConfig(level=logging.INFO)
user_prompts = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("היי! שלח הוראה ואז תמונה.")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_prompts[update.message.from_user.id] = update.message.text
    await update.message.reply_text("מעולה, עכשיו תשלח את התמונה.")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.message.from_user.id
    if uid not in user_prompts:
        await update.message.reply_text("כתבת לי שום הוראה – אנא שלח טקסט קודם.")
        return
    photo = await update.message.photo[-1].get_file()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tf:
        tf.write(requests.get(photo.file_path).content)
        path = tf.name
    await update.message.reply_text("עובד על זה 🛠️")
    try:
        out = replicate_client.run(
            "timbrooks/instruct-pix2pix:9c0cfdf1c6e06c9691cc8896e72c3cfcdf1a351c",
            input={"image": open(path, "rb"), "prompt": user_prompts[uid], "num_inference_steps":20, "guidance_scale":7.5}
        )
        await update.message.reply_photo(photo=out)
    except Exception as e:
        await update.message.reply_text(f"שגיאה: {e}")
    finally:
        user_prompts.pop(uid, None)

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    print("Running...")
    app.run_polling()

if __name__ == "__main__":
    main()
