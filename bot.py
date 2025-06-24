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
    if not os.path.exi
