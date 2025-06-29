import os
import requests
import urllib.parse
from telegram import Update
from telegram.ext import ContextTypes

COMICVINE_API_KEY = os.getenv("COMICVINE_API_KEY")
COMICVINE_BASE     = "https://comicvine.gamespot.com/api"
OLD_API_BASE       = f"https://superheroapi.com/api/{SUPERHERO_API_TOKEN}"

async def search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        return await update.message.reply_text("Usage: /search <hero name>")

    query = " ".join(context.args)
    # 1) Try Comic Vine
    params = {
        "api_key": COMICVINE_API_KEY,
        "format":  "json",
        "filter":  f"name:{query}",
        "field_list": "name,aliases,gender,deck,image,site_detail_url"
    }
    cv_resp = requests.get(f"{COMICVINE_BASE}/characters/", params=params).json()
    cv_results = cv_resp.get("results") or []

    if cv_results:
        hero = cv_results[0]
        caption = (
            f"*{hero['name']}*\n"
            f"🔗 More: {hero['site_detail_url']}\n"
            f"📝 Aliases: {', '.join(hero.get('aliases',[])) or 'None'}\n"
            f"👤 Gender: {hero.get('gender','Unknown')}\n\n"
            f"{hero.get('deck','No description available')}"
        )
        return await update.message.reply_photo(
            photo=hero["image"]["original_url"], caption=caption, parse_mode="Markdown"
        )

    # 2) Fallback to old SuperheroAPI
    encoded = urllib.parse.quote_plus(query)
    data = requests.get(f"{OLD_API_BASE}/search/{encoded}").json()
    if data.get("response") != "success":
        return await update.message.reply_text("Hero not found.")

    results = data["results"]
    exact = [h for h in results if h["name"].lower() == query.lower()]
    to_show = exact or results[:3]

    for hero in to_show:
        bio   = hero["biography"]
        stats = hero["powerstats"]
        app_  = hero["appearance"]
        caption = (
            f"*{hero['name']}*\n"
            f"🏷️ Full Name: {bio.get('full-name','N/A')}\n"
            f"⚖️ Alignment: {bio.get('alignment','N/A')}\n"
            f"🌍 First Appearance: {bio.get('first-appearance','N/A')}\n\n"
            f"*Power Stats:*\n"
            + "\n".join(f"- {k.capitalize()}: {v}" for k,v in stats.items()) +
            "\n\n*Appearance:*\n"
            + "\n".join(f"- {k.capitalize()}: {', '.join(app_.get(k,[])) or 'N/A'}"
                        for k in ("height","weight"))
        )
        await update.message.reply_photo(
            photo=hero["image"]["url"], caption=caption, parse_mode="Markdown"
        )
