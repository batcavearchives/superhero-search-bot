import os
import sys
import json
import logging
import requests
import urllib.parse

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load and validate tokens (fail fast if missing)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    logger.error("❌ TELEGRAM_BOT_TOKEN is not set in the environment!")
    sys.exit("Missing TELEGRAM_BOT_TOKEN")

SUPERHERO_API_TOKEN = os.getenv("SUPERHERO_API_TOKEN")
if not SUPERHERO_API_TOKEN:
    logger.error("❌ SUPERHERO_API_TOKEN is not set in the environment!")
    sys.exit("Missing SUPERHERO_API_TOKEN")

SUPERHERO_API_URL = f"https://superheroapi.com/api/{SUPERHERO_API_TOKEN}"

# File to store custom heroes
CUSTOM_DB_FILE = "custom_heroes.json"


def load_custom_heroes() -> list:
    """Load custom heroes from JSON file."""
    if not os.path.exists(CUSTOM_DB_FILE):
        with open(CUSTOM_DB_FILE, "w") as f:
            json.dump([], f)
    with open(CUSTOM_DB_FILE, "r") as f:
        return json.load(f)


def save_custom_heroes(heroes: list):
    """Save custom heroes to JSON file."""
    with open(CUSTOM_DB_FILE, "w") as f:
        json.dump(heroes, f, indent=2)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    msg = (
        "🦸 Welcome to the Superhero Bot! 🦹\n\n"
        "Commands:\n"
        "/search <name> - Search for existing superheroes\n"
        "/hero <name>  - Alias for /search\n"
        "/addhero Name|Description|Image_URL - Add a custom superhero\n"
        "/listcustom - List your added custom heroes"
    )
    await update.message.reply_text(msg)


async def search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /search (or /hero) command with URL-encoding and exact-match."""
    if not context.args:
        await update.message.reply_text("Usage: /search <hero name>")
        return

    query = " ".join(context.args)
    encoded = urllib.parse.quote_plus(query)
    try:
        resp = requests.get(f"{SUPERHERO_API_URL}/search/{encoded}")
        data = resp.json()
    except Exception as e:
        logger.error(f"API request failed: {e}")
        await update.message.reply_text("Sorry, I couldn't reach the Superhero API.")
        return

    if data.get("response") != "success" or "results" not in data:
        await update.message.reply_text("Hero not found.")
        return

    results = data.get("results", [])
    # Prioritize exact name match
    exact = [h for h in results if h.get("name", "").lower() == query.lower()]
    to_show = exact or results[:3]

    for hero in to_show:
        bio = hero.get("biography", {})
        stats = hero.get("powerstats", {})
        app_ = hero.get("appearance", {})
        caption = (
            f"*{hero.get('name','Unknown')}*\n"
            f"🏷️ Full Name: {bio.get('full-name','N/A')}\n"
            f"⚖️ Alignment: {bio.get('alignment','N/A')}\n"
            f"🌍 First Appearance: {bio.get('first-appearance','N/A')}\n\n"
            f"*Power Stats:*\n"
            f"- Intelligence: {stats.get('intelligence','N/A')}\n"
            f"- Strength: {stats.get('strength','N/A')}\n"
            f"- Speed: {stats.get('speed','N/A')}\n"
            f"- Durability: {stats.get('durability','N/A')}\n"
            f"- Power: {stats.get('power','N/A')}\n"
            f"- Combat: {stats.get('combat','N/A')}\n\n"
            f"*Appearance:*\n"
            f"- Gender: {app_.get('gender','N/A')}\n"
            f"- Race: {app_.get('race','N/A')}\n"
            f"- Height: {', '.join(app_.get('height', [])) or 'N/A'}\n"
            f"- Weight: {', '.join(app_.get('weight', [])) or 'N/A'}"
        )
        await update.message.reply_photo(
            photo=hero.get("image", {}).get("url"),
            caption=caption,
            parse_mode="Markdown"
        )


async def addhero(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /addhero command to add a custom hero."""
    text = update.message.text[len("/addhero"):].strip()
    parts = [p.strip() for p in text.split("|")]
    if len(parts) != 3:
        await update.message.reply_text("Usage: /addhero Name|Description|Image_URL")
        return
    name, desc, img = parts

    heroes = load_custom_heroes()
    heroes.append({"name": name, "description": desc, "image": img})
    save_custom_heroes(heroes)
    await update.message.reply_text(f"Custom hero '{name}' added!")


async def listcustom(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /listcustom command to display custom heroes."""
    heroes = load_custom_heroes()
    if not heroes:
        await update.message.reply_text("No custom heroes added yet.")
        return

    for hero in heroes:
        caption = f"*{hero['name']}*\n{hero['description']}"
        await update.message.reply_photo(
            photo=hero["image"],
            caption=caption,
            parse_mode="Markdown"
        )


def main() -> None:
    """Start the Telegram bot."""
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("search", search))
    app.add_handler(CommandHandler("hero", search))  # alias for /search
    app.add_handler(CommandHandler("addhero", addhero))
    app.add_handler(CommandHandler("listcustom", listcustom))

    app.run_polling()


if __name__ == "__main__":
    main()
