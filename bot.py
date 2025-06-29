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

# --- Load & validate tokens ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    logger.error("❌ TELEGRAM_BOT_TOKEN is not set in the environment!")
    sys.exit("Missing TELEGRAM_BOT_TOKEN")

COMICVINE_API_KEY = os.getenv("COMICVINE_API_KEY")
if not COMICVINE_API_KEY:
    logger.error("❌ COMICVINE_API_KEY is not set in the environment!")
    sys.exit("Missing COMICVINE_API_KEY")

SUPERHERO_API_TOKEN = os.getenv("SUPERHERO_API_TOKEN")
if not SUPERHERO_API_TOKEN:
    logger.error("❌ SUPERHERO_API_TOKEN is not set in the environment!")
    sys.exit("Missing SUPERHERO_API_TOKEN")

# API endpoints
COMICVINE_BASE = "https://comicvine.gamespot.com/api"
OLD_API_BASE   = f"https://superheroapi.com/api/{SUPERHERO_API_TOKEN}"
JIKAN_ANIME_ENDPOINT = "https://api.jikan.moe/v4/anime"

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
        "🦸 Welcome to the Superhero & Anime Bot! 🦹\n\n"
        "Commands:\n"
        "/search <name> - Search for superheroes\n"
        "/hero <name>   - Alias for /search\n"
        "/anime <title> - Search for anime titles\n"
        "/addhero Name|Description|Image_URL - Add a custom superhero\n"
        "/searchcustom <name> - Search your custom heroes\n"
        "/listcustom            - List all your added custom heroes"
    )
    await update.message.reply_text(msg)

async def searchcustom(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /searchcustom to find a custom hero by name."""
    if not context.args:
        await update.message.reply_text("Usage: /searchcustom <hero name>")
        return

    query = " ".join(context.args).lower()
    heroes = load_custom_heroes()
    matches = [h for h in heroes if query in h["name"].lower()]

    if not matches:
        return await update.message.reply_text(f"No custom heroes found matching “{query}.”")

    for hero in matches:
        caption = f"*{hero['name']}*\n{hero['description']}"
        await update.message.reply_photo(
            photo=hero["image"],
            caption=caption,
            parse_mode="Markdown"
        )


async def search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /search (or /hero) command with Comic Vine primary and fallback."""
    if not context.args:
        await update.message.reply_text("Usage: /search <hero name>")
        return

    query = " ".join(context.args)

    # Comic Vine lookup
    params = {
        "api_key": COMICVINE_API_KEY,
        "format":  "json",
        "filter":  f"name:{query}",
        "field_list": "name,aliases,gender,deck,image,site_detail_url"
    }
    try:
        cv_resp = requests.get(f"{COMICVINE_BASE}/characters/", params=params).json()
        cv_results = cv_resp.get("results") or []
    except Exception as e:
        logger.warning(f"Comic Vine API request failed: {e}")
        cv_results = []

    if cv_results:
        hero = cv_results[0]
        caption = (
            f"*{hero['name']}*\n"
            f"🔗 More: {hero['site_detail_url']}\n"
            f"📝 Aliases: {', '.join(hero.get('aliases', [])) or 'None'}\n"
            f"👤 Gender: {hero.get('gender', 'Unknown')}\n\n"
            f"{hero.get('deck', 'No description available')}"
        )
        return await update.message.reply_photo(
            photo=hero['image']['original_url'],
            caption=caption,
            parse_mode="Markdown"
        )

    # SuperheroAPI fallback
    encoded = urllib.parse.quote_plus(query)
    try:
        data = requests.get(f"{OLD_API_BASE}/search/{encoded}").json()
    except Exception as e:
        logger.error(f"SuperheroAPI request failed: {e}")
        return await update.message.reply_text("Sorry, both APIs are unreachable.")

    if data.get("response") != "success" or "results" not in data:
        return await update.message.reply_text("Hero not found.")

    results = data.get("results", [])
    exact = [h for h in results if h.get("name", "").lower() == query.lower()]
    to_show = exact or results[:3]

    for hero in to_show:
        bio   = hero.get("biography", {})
        stats = hero.get("powerstats", {})
        app_  = hero.get("appearance", {})
        caption = (
            f"*{hero.get('name','Unknown')}*\n"
            f"🏷️ Full Name: {bio.get('full-name','N/A')}\n"
            f"⚖️ Alignment: {bio.get('alignment','N/A')}\n"
            f"🌍 First Appearance: {bio.get('first-appearance','N/A')}\n\n"
            f"*Power Stats:*\n"
            f"- Intelligence: {stats.get('intelligence','N/A')}\n"
            f"- Strength:     {stats.get('strength','N/A')}\n"
            f"- Speed:        {stats.get('speed','N/A')}\n"
            f"- Durability:   {stats.get('durability','N/A')}\n"
            f"- Power:        {stats.get('power','N/A')}\n"
            f"- Combat:       {stats.get('combat','N/A')}\n\n"
            f"*Appearance:*\n"
            f"- Gender: {app_.get('gender','N/A')}\n"
            f"- Race:   {app_.get('race','N/A')}\n"
            f"- Height: {', '.join(app_.get('height', [])) or 'N/A'}\n"
            f"- Weight: {', '.join(app_.get('weight', [])) or 'N/A'}"
        )
        await update.message.reply_photo(
            photo=hero.get('image', {}).get('url'),
            caption=caption,
            parse_mode="Markdown"
        )


async def anime(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /anime command to search anime titles using Jikan API."""
    if not context.args:
        await update.message.reply_text("Usage: /anime <anime title>")
        return

    query = " ".join(context.args)
    params = {
        "q": query,
        "limit": 3
    }
    try:
        resp = requests.get(JIKAN_ANIME_ENDPOINT, params=params).json()
        anime_list = resp.get('data', [])
    except Exception as e:
        logger.error(f"Jikan API request failed: {e}")
        return await update.message.reply_text("Sorry, could not reach the Anime API.")

    if not anime_list:
        return await update.message.reply_text("No anime found with that title.")

    for anime in anime_list:
        title = anime.get('title')
        url   = anime.get('url')
        synopsis = anime.get('synopsis', 'No synopsis available.')
        image_url = anime.get('images', {}).get('jpg', {}).get('image_url')
        caption = (
            f"*{title}*\n"
            f"🔗 More: {url}\n\n"
            f"{synopsis[:500]}{'...' if len(synopsis)>500 else ''}"
        )
        await update.message.reply_photo(
            photo=image_url,
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
    app.add_handler(CommandHandler("hero", search))   # alias for /search
    app.add_handler(CommandHandler("anime", anime))
    app.add_handler(CommandHandler("addhero", addhero))
    app.add_handler(CommandHandler("listcustom", listcustom))
    app.add_handler(CommandHandler("searchcustom", searchcustom))


    app.run_polling()


if __name__ == "__main__":
    main()
