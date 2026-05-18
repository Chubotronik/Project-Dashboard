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

# %%
def check_directories(create_if_missing: bool = True) -> None:
    """
    Print environment directories and create them if they don't exist.
    """
    
    print(f"Base directory: {BASE_DIR}")
    print(f"Raw data directory: {DATA_RAW_DIR}")
    print(f"Processed data directory: {DATA_PROCESSED_DIR}")
    print(f"Cache directory: {CACHE_DIR}")
    print(f"Scraper cache directory: {SCRAPER_CACHE}")
    print(f"Scraper user agent: {SCRAPER_USER_AGENT}")
    print(f"Delay time: {DELAY_TIME}")

    scraper_cache_raw = os.getenv("SCRAPER_CACHE_DIR")
    scraper_cache_resolved = Path(scraper_cache_raw) if scraper_cache_raw else BASE_DIR / "cache" / "scraper"
    print(f"SCRAPER_CACHE_DIR raw value: {scraper_cache_raw!r}")
    print(f"SCRAPER_CACHE_DIR resolved: {scraper_cache_resolved.resolve()}")
    print(f"Current working directory: {Path.cwd()}")

    if create_if_missing:
        for directory in [DATA_RAW_DIR, DATA_PROCESSED_DIR, CACHE_DIR, scraper_cache_resolved]:
            if not directory.exists():
                print(f"Directory {directory} does not exist. Creating it.")
                directory.mkdir(parents=True, exist_ok=True)

# %%
