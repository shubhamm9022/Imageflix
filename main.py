import os
import re
import requests
from io import BytesIO
from PIL import Image
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

BOT_TOKEN = os.getenv("BOT_TOKEN")

# Store user data temporarily (basic memory cache)
user_links = {}

def detect_platform_and_clean(url):
    if "amazon" in url:
        match = re.search(r'/pv-target-images/([a-f0-9]+)', url)
        if match:
            base = match.group(1)
            return f"https://m.media-amazon.com/images/S/pv-target-images/{base}._UR1920,1080_.jpg"
    elif "mzstatic.com" in url:
        return re.sub(r'\._[^.]+', '', url.split(",")[0])
    elif "nflx" in url:
        return url.split("?")[0]
    elif any(p in url for p in ["hotstar", "disney", "hbo", "hulu", "paramount", "zee5", "sonyliv", "mxplayer"]):
        return url.split("?")[0]
    return url

def download_and_resize(url, fmt):
    r = requests.get(url)
    img = Image.open(BytesIO(r.content)).convert("RGB")
    img = img.resize((1920, 1080))
    output = BytesIO()
    img.save(output, format=fmt.upper(), quality=95)
    output.seek(0)
    return output

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message.text.strip()
    if not message.startswith("http"):
        await update.message.reply_text("❌ Please send a valid OTT image URL.")
        return

    cleaned = detect_platform_and_clean(message)
    user_id = str(update.message.from_user.id)
    user_links[user_id] = cleaned

    # Format selection buttons
    buttons = [
        [
            InlineKeyboardButton("JPG", callback_data=f"{user_id}|JPG"),
            InlineKeyboardButton("PNG", callback_data=f"{user_id}|PNG"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(buttons)
    await update.message.reply_text("🎨 Choose output format:", reply_markup=reply_markup)

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data.split("|")
    user_id, fmt = data[0], data[1]

    url = user_links.get(user_id)
    if not url:
        await query.edit_message_text("❌ No image found. Please send the link again.")
        return

    try:
        img = download_and_resize(url, fmt)
        await query.edit_message_text(f"✅ Sending {fmt} image...")
        await query.message.reply_document(document=img, filename=f"cleaned.{fmt.lower()}")
    except Exception as e:
        await query.edit_message_text(f"❌ Failed to process image: {str(e)}")

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(handle_button))
    app.run_polling()