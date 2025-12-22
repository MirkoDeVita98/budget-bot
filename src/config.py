import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
DB_PATH = os.getenv("DB_PATH", "budget_old.db")
BASE_CURRENCY = os.getenv("BASE_CURRENCY", "CHF")
