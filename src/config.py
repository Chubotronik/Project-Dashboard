#%%
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Paths
BASE_DIR = Path(__file__).parent.parent
DATA_RAW_DIR = BASE_DIR / "data" / "raw"
DATA_PROCESSED_DIR = BASE_DIR / "data" / "processed"
CACHE_DIR = BASE_DIR / "cache"

# Scraper settings
SCRAPER_CACHE = os.getenv("SCRAPER_CACHE_DIR", BASE_DIR / "cache" / "scraper")
SCRAPER_USER_AGENT = os.getenv("SCRAPER_USER_AGENT", "champions-dashboard/0.1 (anonymous)")
DELAY_TIME = float(os.getenv("SCRAPER_DELAY_SECONDS", 1.5))
