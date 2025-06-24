import os
import json
import requests
import openai
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
API_TOKEN = os.getenv("SUPERHERO_API_TOKEN")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
API_BASE = f"https://superheroapi.com/api/{API_TOKEN}"
openai.api_key = OPENAI_KEY

HERO_DB_FILE = "heroes.json"

def load_custom_heroes():
    if not os.path.exists(HERO_DB_FILE):
        return {}
    with open(HERO_DB_FILE, "r") as f:
        return json.load(f)

def save_hero(hero_obj):
    db = load_custom_heroes()
    key = hero_obj["name"].lower()
    db[key] = hero_obj
    with open(HERO_DB_FILE, "w") as f:
        json.dump(db, f, indent=2)

def search_custom(name):
    db = load_custom_heroes()
    return db.get(name.lower())

def search_api(name):
    res = requests.get(f"{API_BASE}/search/{name}")
    if res.status_code == 200:
        data = res.json()
        if data["response"] == "success":
            return data["results"][0]
    return None

async def generate_openai_lore(name):
    prompt = f"Create a superhero profile for {name}. Include powers, backstory, and uniqueness."
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=250
    )
    return response.choices[0].message.content.strip()

def format_api_hero(hero):
    bio = hero["biography"]
    power = hero["powerstats"]
    appearance = hero["appearance"]
    return f"""🦸 *{hero['name']}*

🏷️ *Full Name:* {bio.get("full-name", "Unknown")}
🧬 *Alignment:* {bio.get("alignment", "Unknown")}
🌍 *First Appearance:* {bio.get("first-appearance", "Unknown")}

💥 *Power Stats:*
- Intelligence: {power.get("intelligence")}
- Strength: {power.get("strength")}
- Speed: {power.get("speed")}
- Power: {power.get("power")}
- Combat: {power.get("combat")}

🎭 *Appearance:*
- Gender: {appearance.get("gender")}
- Height: {appearance.get("height")[0]}
- Race: {appearance.get("race")}
"""

async def hero_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Use `/hero Batman` to search.", parse_mode="Markdown")
        return

    name = " ".join(context.args).strip()
    print(f"Received command: {update.message.text}")
    await update.message.reply_text("🔍 Processing your hero search…")

    custom = search_custom(name)
    if custom:
        keyboard = [[InlineKeyboardButton("📸 Image", url=custom["image"])] if "image" in custom else []]
        keyboard.append([InlineKeyboardButton("🔍 Google", url=f"https://www.google.com/search?q={name}+superhero")])
        msg = f"🦸 *{custom['name']}*\n\n{custom['summary']}\n\n🌟 Powers: `{custom.get('powers', 'Unknown')}`"
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    hero = search_api(name)
    if hero:
        msg = format_api_hero(hero)
        keyboard = [
            [InlineKeyboardButton("📸 Image", url=hero["image"]["url"])],
            [InlineKeyboardButton("🔍 Google", url=f"https://www.google.com/search?q={name}+superhero")]
        ]
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    msg = await generate_openai_lore(name)
    await update.message.reply_text(f"🦸 *{name}*\n\n{msg}", parse_mode="Markdown")

async def add_hero(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if str(user_id) != "6876497893":
        await update.message.reply_text("❌ You are not authorized to use this command.")
        return
    try:
        data = json.loads(" ".join(context.args))
        if "name" not in data or "summary" not in data:
            raise ValueError
        save_hero(data)
        await update.message.reply_text(f"✅ Hero '{data['name']}' added.")
    except:
        await update.message.reply_text("❌ Failed to parse hero. Send as JSON with at least 'name' and 'summary'.")

# 🔁 Start the bot using polling (not webhook)
if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("hero", hero_handler))
    app.add_handler(CommandHandler("addhero", add_hero))
    print("🤖 Bot is running...")
    app.run_polling()

