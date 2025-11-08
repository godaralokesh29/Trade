import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Google API ---
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# --- MongoDB ---
MONGO_CONNECTION_STRING = os.getenv("MONGO_CONNECTION_STRING")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "tradesage_hackathon_db")

ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")

# --- Application ---
# We can add more settings here later
IS_DEV_MODE = True