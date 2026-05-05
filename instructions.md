# Pokémon Champions VGC Dashboard — Learning Guide

A step-by-step path from "empty repo" to "interactive Streamlit dashboard."

> **How to use this guide**
> Each task gives you the goal first, then a generic approach with no code.
> If you get stuck, click the 💡 **Hint** disclosure for a nudge.
> If you really want to peek, click the ✅ **Solution** disclosure for a worked answer.
> Try to write each task yourself before opening either disclosure — that's where the learning happens.

---

## Chapter 1 — Gather data

The dashboard needs two kinds of data:
1. **Pokémon metadata** (sprites, types, base stats, movepool) — comes from the
   public **PokéAPI**.
2. **Champions VGC stats** (usage %, top teams, movesets) — only available as
   HTML on sites like **Pikalytics**, so we'll *scrape* them.

### Task 1.1 — Project hygiene: store secrets in `.env`

Before writing any networking code, you need a place to keep configurable
values like a User-Agent string or a delay. These go in a `.env` file at the
project root, which is never committed to git.

**Generic approach:**
- Create a `.env` file at the project root (the template is `.env.example`).
- Add it to `.gitignore` (already done).
- Load values in Python with `python-dotenv` so you can read them via
  `os.environ` like any environment variable.

<details>
<summary>💡 Hint</summary>

The `python-dotenv` package gives you a one-liner: `from dotenv import load_dotenv; load_dotenv()`. After calling it once at the top of a script, every key in `.env` is accessible via `os.getenv("KEY_NAME")`. The `.env.example` file in your repo shows you which variables to set.

</details>

<details>
<summary>✅ Solution</summary>

```python
# src/config.py
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()  # reads .env from the project root

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_RAW = PROJECT_ROOT / "data" / "raw"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
CACHE_DIR = PROJECT_ROOT / os.getenv("SCRAPER_CACHE_DIR", ".cache/scrape")

USER_AGENT = os.getenv(
    "SCRAPER_USER_AGENT",
    "champions-dashboard/0.1 (anonymous)",
)
SCRAPE_DELAY_SECONDS = float(os.getenv("SCRAPER_DELAY_SECONDS", "1.5"))
```

Now `from src.config import USER_AGENT` works anywhere in the project.

</details>

---

### Task 1.2 — Your first API call: fetch one Pokémon from PokéAPI

PokéAPI is a free public REST API. Try calling it for a single Pokémon
(e.g. `garchomp`) and printing its types and base stats.

**Generic approach:**
- The base URL is `https://pokeapi.co/api/v2/`.
- The endpoint for one Pokémon is `pokemon/<name-or-id>`.
- Use the `requests` library to send an HTTP GET.
- The response is JSON — call `.json()` on the response object.

<details>
<summary>💡 Hint</summary>

`requests.get(url)` returns a `Response` object. Always check `response.status_code == 200` before parsing. The PokéAPI JSON has a `types` list of `{slot, type: {name}}` objects and a `stats` list of `{base_stat, stat: {name}}` objects. Try `response.json().keys()` first to see the shape.

</details>

<details>
<summary>✅ Solution</summary>

```python
# src/fetch/pokeapi.py
import requests

BASE = "https://pokeapi.co/api/v2"


def get_pokemon(name_or_id: str | int) -> dict:
    """Fetch one Pokémon's full record from PokéAPI."""
    response = requests.get(f"{BASE}/pokemon/{name_or_id}", timeout=10)
    response.raise_for_status()
    return response.json()


if __name__ == "__main__":
    data = get_pokemon("garchomp")
    types = [t["type"]["name"] for t in data["types"]]
    stats = {s["stat"]["name"]: s["base_stat"] for s in data["stats"]}
    print(f"{data['name']} — types: {types}")
    print("Base stats:", stats)
```

</details>

---

### Task 1.3 — Fetch many: paginate the full Pokémon list and save to disk

Now scale up. Get the names of all Pokémon currently in PokéAPI, then save
them to `data/raw/pokemon_index.json` so you don't have to refetch.

**Generic approach:**
- The list endpoint `pokemon?limit=N&offset=M` returns `{count, next, previous, results}`.
- Either pass a big `limit` once, or follow `next` links until null.
- Save the resulting list to JSON. Use `json.dumps(..., indent=2)` for readability.

<details>
<summary>💡 Hint</summary>

The `count` in the first response tells you how many Pokémon exist total. Calling `pokemon?limit={count}` gives you the entire list in one shot. For a more idiomatic "follow the links" version, loop while `data["next"]` is truthy.

</details>

<details>
<summary>✅ Solution</summary>

```python
# src/fetch/pokeapi.py (continued)
import json
from pathlib import Path

from src.config import DATA_RAW


def list_all_pokemon() -> list[dict]:
    """Return [{name, url}, ...] for every Pokémon in PokéAPI."""
    first = requests.get(f"{BASE}/pokemon?limit=1", timeout=10).json()
    total = first["count"]
    page = requests.get(f"{BASE}/pokemon?limit={total}", timeout=30).json()
    return page["results"]


def save_pokemon_index(path: Path = DATA_RAW / "pokemon_index.json") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    pokemon = list_all_pokemon()
    path.write_text(json.dumps(pokemon, indent=2), encoding="utf-8")
    return path
```

</details>

---

### Task 1.4 — HTTP literacy: status codes, retries, and timeouts

Real networks fail. Make your fetcher robust to flaky requests by retrying
with exponential backoff on transient errors (5xx, timeouts) and giving up
loudly on permanent ones (4xx).

**Generic approach:**
- Wrap the request in a retry decorator from `tenacity`.
- Retry only on transient failures: `requests.Timeout`, `ConnectionError`, 5xx responses.
- Don't retry on 404 — that means the Pokémon doesn't exist; failing is correct.
- Always set `timeout=` on the request itself so it can't hang forever.

<details>
<summary>💡 Hint</summary>

`tenacity` gives you `@retry(stop=stop_after_attempt(3), wait=wait_exponential())`. To inspect *why* a request failed before retrying, look at `response.status_code` and raise a custom exception only on conditions you want to retry.

</details>

<details>
<summary>✅ Solution</summary>

```python
# src/fetch/http.py
import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from src.config import USER_AGENT


class TransientHTTPError(Exception):
    """Raised on 5xx so tenacity will retry."""


@retry(
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((TransientHTTPError, requests.Timeout, requests.ConnectionError)),
)
def get(url: str, **kwargs) -> requests.Response:
    headers = kwargs.pop("headers", {}) | {"User-Agent": USER_AGENT}
    response = requests.get(url, headers=headers, timeout=10, **kwargs)
    if 500 <= response.status_code < 600:
        raise TransientHTTPError(f"{response.status_code} from {url}")
    response.raise_for_status()  # 4xx fails immediately, no retry
    return response
```

</details>

---

### Task 1.5 — Your first scrape: fetch Pikalytics's Champions page

The Champions usage page (`https://www.pikalytics.com/champions`) renders its
data as plain HTML. Fetch the page and have a look at the raw structure in
your browser's **Inspect Element** before parsing.

**Generic approach:**
- Use the polite `get()` helper from Task 1.4 — User-Agent header + retries.
- Save the HTML to `data/raw/pikalytics_champions.html` so you can re-parse
  offline without re-hitting the site.
- Open the file and search for the visible numbers (e.g. `Sneasler`, `43.80`)
  to find which HTML tags hold the data.

<details>
<summary>💡 Hint</summary>

After saving the HTML, open it in a browser locally — it'll render the same as the live page. Then right-click on a usage % → Inspect → look at the parent element's class. That class is your hook for the next task.

</details>

<details>
<summary>✅ Solution</summary>

```python
# src/fetch/pikalytics.py
from pathlib import Path

from src.config import DATA_RAW
from src.fetch.http import get

CHAMPIONS_URL = "https://www.pikalytics.com/champions"


def fetch_champions_html(path: Path = DATA_RAW / "pikalytics_champions.html") -> Path:
    response = get(CHAMPIONS_URL)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(response.text, encoding="utf-8")
    return path


if __name__ == "__main__":
    print("Saved to:", fetch_champions_html())
```

</details>

---

### Task 1.6 — Parse the HTML with BeautifulSoup into a DataFrame

Now turn that raw HTML into a tidy `pandas.DataFrame` with columns like
`name`, `usage_pct`, and `rank`.

**Generic approach:**
- Load the saved HTML from disk (faster than refetching every iteration).
- Construct a `BeautifulSoup(html, "lxml")` object.
- Use `soup.select(".css-class")` (CSS selectors) or `soup.find_all("div", class_="...")` to grab the rows you identified.
- For each row, extract the Pokémon name and usage %.
- Build a list of dicts, then `pd.DataFrame(rows)`.

> ⚠️ The exact CSS classes change as Pikalytics redesigns. The solution
> below shows one snapshot; you may need to update the selector. That's a
> normal scraping reality.

<details>
<summary>💡 Hint</summary>

Once you have a `BeautifulSoup` object, `soup.select(".pokemon-row")` returns a list of matching elements, and `el.get_text(strip=True)` gives the visible text inside any element. Use a regex (`re.search(r"([\d.]+)%", text)`) to pull a number out of strings like "43.80% usage".

</details>

<details>
<summary>✅ Solution</summary>

```python
# src/transform/pikalytics.py
import re
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup

from src.config import DATA_RAW

USAGE_RE = re.compile(r"([\d.]+)\s*%")


def parse_champions_usage(html_path: Path = DATA_RAW / "pikalytics_champions.html") -> pd.DataFrame:
    html = html_path.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "lxml")

    # Adjust this selector to whatever Pikalytics uses today.
    rows = soup.select("a[href*='/pokedex/champions/']")

    records = []
    for rank, row in enumerate(rows, start=1):
        name_el = row.select_one(".pokemon-name") or row
        usage_el = row.select_one(".usage") or row
        text = row.get_text(" ", strip=True)
        match = USAGE_RE.search(text)
        if not match:
            continue
        records.append({
            "rank": rank,
            "name": name_el.get_text(strip=True).split()[0].lower(),
            "usage_pct": float(match.group(1)),
        })

    return pd.DataFrame(records).drop_duplicates("name").reset_index(drop=True)
```

</details>

---

### Task 1.7 — Be a polite scraper: cache, throttle, identify yourself

Wrap your fetcher in a "polite" layer so you (a) don't get rate-limited, and
(b) don't refetch pages you already have.

**Generic approach:**
- Cache responses on disk keyed by URL (e.g. SHA-256 of the URL → filename).
- Before fetching, check the cache; if the file exists and is fresh, load it.
- After fetching, save the response.
- Sleep `SCRAPE_DELAY_SECONDS` between *uncached* network calls.
- Keep your custom `User-Agent` from Task 1.4 — that's already politeness.

<details>
<summary>💡 Hint</summary>

`hashlib.sha256(url.encode()).hexdigest()[:16]` gives a short, filesystem-safe key. To define "fresh", use file modification time: `time.time() - path.stat().st_mtime < ttl_seconds`. The cache function returns `(html, was_cached)` so callers can choose whether to sleep.

</details>

<details>
<summary>✅ Solution</summary>

```python
# src/fetch/scrape.py
import hashlib
import time
from pathlib import Path

from src.config import CACHE_DIR, SCRAPE_DELAY_SECONDS
from src.fetch.http import get


def _cache_path(url: str) -> Path:
    key = hashlib.sha256(url.encode()).hexdigest()[:16]
    return CACHE_DIR / f"{key}.html"


def fetch_html(url: str, ttl_seconds: int = 60 * 60 * 24) -> str:
    """Fetch a URL through a 24-hour disk cache. Sleeps after live fetches."""
    cache = _cache_path(url)
    if cache.exists() and (time.time() - cache.stat().st_mtime) < ttl_seconds:
        return cache.read_text(encoding="utf-8")

    response = get(url)
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(response.text, encoding="utf-8")
    time.sleep(SCRAPE_DELAY_SECONDS)
    return response.text
```

Bonus: also write a `respects_robots_txt(url)` helper using `urllib.robotparser` to confirm scraping is allowed before you fetch.

</details>

---

### Task 1.8 — Build the unified data layer

Combine PokéAPI metadata with scraped Pikalytics usage stats into a single
`champions.parquet` file under `data/processed/`. This is what the dashboard
will read.

**Generic approach:**
- Run both fetchers; you have two DataFrames keyed by Pokémon name.
- Normalize names (lowercase, strip dashes/spaces) so they match.
- `df.merge(...)` on the name column.
- Save with `df.to_parquet(path)` — Parquet is faster and smaller than CSV
  for analytical workloads.

<details>
<summary>💡 Hint</summary>

Name normalization is the part that bites first. PokéAPI uses `mr-mime`, `ho-oh`. Pikalytics may show `Mr. Mime`, `Ho-Oh`. Build a `normalize(name)` function that lowercases, strips spaces and dots, and replaces "é" with "e".

</details>

<details>
<summary>✅ Solution</summary>

```python
# src/transform/build_dataset.py
import pandas as pd

from src.config import DATA_PROCESSED
from src.fetch.pokeapi import list_all_pokemon
from src.transform.pikalytics import parse_champions_usage


def normalize(name: str) -> str:
    return (
        name.lower()
        .replace(".", "")
        .replace(" ", "-")
        .replace("é", "e")
    )


def build_champions_dataset() -> pd.DataFrame:
    metadata = pd.DataFrame(list_all_pokemon())
    metadata["name"] = metadata["name"].map(normalize)

    usage = parse_champions_usage()
    usage["name"] = usage["name"].map(normalize)

    df = usage.merge(metadata[["name"]], on="name", how="left")

    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    out = DATA_PROCESSED / "champions.parquet"
    df.to_parquet(out, index=False)
    return df
```

</details>

---

## Chapter 2 — Analyze data

Now that `data/processed/champions.parquet` exists, you can interrogate it
with pandas. Treat this chapter as exploratory — work in a notebook
(`notebooks/01_explore.ipynb`) until your queries feel solid, then port them
into clean functions in `src/transform/`.

### Task 2.1 — Load and inspect

Read the parquet and answer: how many Pokémon are in the dataset? What columns? What's the distribution of `usage_pct`?

**Generic approach:**
- `pd.read_parquet(path)`
- `.info()`, `.describe()`, `.head()`
- A quick `.hist()` on `usage_pct` is informative.

<details>
<summary>💡 Hint</summary>

`df.describe()` only summarizes numeric columns by default; pass `include="all"` to see object/string columns too. For a quick visual, `df["usage_pct"].plot(kind="hist", bins=20)` is one line.

</details>

<details>
<summary>✅ Solution</summary>

```python
import pandas as pd
from src.config import DATA_PROCESSED

df = pd.read_parquet(DATA_PROCESSED / "champions.parquet")
print(df.info())
print(df.describe(include="all"))
print(df.head(10))
```

</details>

---

### Task 2.2 — Filter and rank: top-N usage

Write a function `top_n(df, n=20)` that returns the top-N most-used Pokémon
sorted by usage descending.

**Generic approach:**
- `df.sort_values("usage_pct", ascending=False)`
- `.head(n)`
- Reset the index for a clean output.

<details>
<summary>💡 Hint</summary>

Chain it: `df.sort_values(...).head(n).reset_index(drop=True)`. The `drop=True` keeps the old index from sneaking back as a column.

</details>

<details>
<summary>✅ Solution</summary>

```python
# src/transform/queries.py
import pandas as pd


def top_n(df: pd.DataFrame, n: int = 20) -> pd.DataFrame:
    return (
        df.sort_values("usage_pct", ascending=False)
        .head(n)
        .reset_index(drop=True)
    )
```

</details>

---

### Task 2.3 — Joins: enrich usage with PokéAPI metadata

So far, your processed dataset only has the names from PokéAPI's index. Now
fetch *full* PokéAPI records for the top-50 Pokémon (types, base stat total,
sprite URL) and join those onto the usage table.

**Generic approach:**
- For each top-50 name, call `get_pokemon(name)` from Task 1.2.
- Extract the fields you want (types, BST, sprite).
- Build a metadata DataFrame and `merge` on `name`.

<details>
<summary>💡 Hint</summary>

Don't fetch all ~1000 Pokémon — that's wasteful for a dashboard. Just the relevant subset. Use the disk cache from Task 1.7 around the API call too — PokéAPI is generous, but caching keeps your dev loop fast.

</details>

<details>
<summary>✅ Solution</summary>

```python
# src/transform/enrich.py
import pandas as pd
from src.fetch.pokeapi import get_pokemon


def enrich_with_metadata(usage_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for name in usage_df["name"]:
        try:
            data = get_pokemon(name)
        except Exception:
            continue
        rows.append({
            "name": name,
            "types": [t["type"]["name"] for t in data["types"]],
            "bst": sum(s["base_stat"] for s in data["stats"]),
            "sprite": data["sprites"]["front_default"],
        })
    meta = pd.DataFrame(rows)
    return usage_df.merge(meta, on="name", how="left")
```

</details>

---

### Task 2.4 — Team cores: which Pokémon appear together?

Pikalytics's individual Pokémon pages list "common teammates." Scrape those,
then build a *co-occurrence matrix*: for every (A, B) pair, how often does
B appear on a team using A?

**Generic approach:**
- For each top-50 Pokémon, fetch its `/pokedex/champions/<name>` page.
- Parse out the teammates and their co-occurrence percentages.
- Build a DataFrame with columns `[anchor, teammate, co_pct]`.
- Optionally pivot it into a square matrix with `df.pivot(index, columns, values)`.

<details>
<summary>💡 Hint</summary>

Co-occurrence isn't symmetric in scraped data because Pikalytics shows %
relative to the *anchor* Pokémon. Keep it as a long-format DataFrame
(`anchor, teammate, co_pct`) — it's both honest about the asymmetry and
easier to filter.

</details>

<details>
<summary>✅ Solution</summary>

```python
# src/transform/cores.py
import pandas as pd
from bs4 import BeautifulSoup

from src.fetch.scrape import fetch_html


def fetch_teammates(name: str) -> pd.DataFrame:
    url = f"https://www.pikalytics.com/pokedex/champions/{name}"
    soup = BeautifulSoup(fetch_html(url), "lxml")
    # Selector to be adjusted to current Pikalytics markup.
    rows = soup.select(".teammates .teammate")
    records = []
    for row in rows:
        teammate = row.select_one(".name").get_text(strip=True).lower()
        pct_text = row.select_one(".pct").get_text(strip=True).rstrip("%")
        records.append({"anchor": name, "teammate": teammate, "co_pct": float(pct_text)})
    return pd.DataFrame(records)


def build_cores(top_names: list[str]) -> pd.DataFrame:
    return pd.concat([fetch_teammates(n) for n in top_names], ignore_index=True)
```

</details>

---

### Task 2.5 — Movesheets: most common moves, items, abilities

For each Pokémon, build a "movesheet" — the most common moves, item, and
ability with their usage % within games featuring that Pokémon.

**Generic approach:**
- Same kind of scrape as teammates — different selectors on the same per-Pokémon page.
- Output a long-format DataFrame: `[name, category, value, pct]` where `category ∈ {move, item, ability}`.

<details>
<summary>💡 Hint</summary>

Long-format here is gold for plotting later. A single bar chart with `category` on the facet axis covers all three (moves / items / abilities) without writing three separate functions.

</details>

<details>
<summary>✅ Solution</summary>

```python
# src/transform/movesets.py
import pandas as pd
from bs4 import BeautifulSoup

from src.fetch.scrape import fetch_html


def fetch_movesheet(name: str) -> pd.DataFrame:
    url = f"https://www.pikalytics.com/pokedex/champions/{name}"
    soup = BeautifulSoup(fetch_html(url), "lxml")

    records = []
    for category, css in [("move", ".moves .row"), ("item", ".items .row"), ("ability", ".abilities .row")]:
        for row in soup.select(css):
            value = row.select_one(".value").get_text(strip=True).lower()
            pct = float(row.select_one(".pct").get_text(strip=True).rstrip("%"))
            records.append({"name": name, "category": category, "value": value, "pct": pct})
    return pd.DataFrame(records)
```

</details>

---

### Task 2.6 — Sanity checks

Before plotting anything, validate the data. Flag obvious errors with assertions.

**Generic approach:**
- No duplicate Pokémon names per dataset.
- `usage_pct` is between 0 and 100.
- No nulls in key columns.
- For movesets: per-Pokémon sums should be roughly ≤ 100 per category (multiple
  moves are allowed per set, so it can exceed 100 — but not 600).

<details>
<summary>💡 Hint</summary>

Wrap each check in an `assert` with a useful message: `assert df["name"].is_unique, df[df["name"].duplicated()]`. When it fails, the duplicates print right next to the error.

</details>

<details>
<summary>✅ Solution</summary>

```python
# tests/test_data_invariants.py
import pandas as pd
import pytest
from src.config import DATA_PROCESSED


@pytest.fixture
def usage():
    return pd.read_parquet(DATA_PROCESSED / "champions.parquet")


def test_names_unique(usage):
    assert usage["name"].is_unique


def test_usage_in_range(usage):
    assert ((usage["usage_pct"] >= 0) & (usage["usage_pct"] <= 100)).all()


def test_no_nulls(usage):
    assert usage[["name", "usage_pct"]].notna().all().all()
```

</details>

---

## Chapter 3 — Visualize & interact

Now we paint the picture. Streamlit gives you a Python-only way to build a
web UI; Plotly does the charts.

### Task 3.1 — Your first Plotly chart

Plot a horizontal bar chart of the top-20 Pokémon by usage. Save it as a
function in `src/viz/usage.py` so the Streamlit app can import it.

**Generic approach:**
- `plotly.express.bar(df, x="usage_pct", y="name", orientation="h")`
- Sort the y-axis so the highest bar is on top.
- Return the `Figure` object — never `fig.show()` inside a viz function.

<details>
<summary>💡 Hint</summary>

`fig.update_layout(yaxis={"categoryorder": "total ascending"})` is the
incantation to sort horizontal bars correctly. And keep viz functions pure:
`(df) -> Figure`. No I/O, no Streamlit calls.

</details>

<details>
<summary>✅ Solution</summary>

```python
# src/viz/usage.py
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def usage_bar(df: pd.DataFrame, n: int = 20) -> go.Figure:
    top = df.nlargest(n, "usage_pct")
    fig = px.bar(
        top,
        x="usage_pct",
        y="name",
        orientation="h",
        labels={"usage_pct": "Usage %", "name": ""},
        title=f"Top {n} Pokémon — Champions Usage",
    )
    fig.update_layout(yaxis={"categoryorder": "total ascending"}, height=600)
    return fig
```

</details>

---

### Task 3.2 — Streamlit basics: render the chart

Create `app.py` at the project root that loads the data and renders the
chart from Task 3.1.

**Generic approach:**
- `st.set_page_config(...)` first — title, icon, layout.
- `st.title(...)` for the header.
- Load the parquet into a DataFrame.
- `st.plotly_chart(fig, use_container_width=True)`.

<details>
<summary>💡 Hint</summary>

Run with `streamlit run app.py`. The browser opens to localhost. Saving the file hot-reloads the page — keep the editor and the browser side by side.

</details>

<details>
<summary>✅ Solution</summary>

```python
# app.py
import pandas as pd
import streamlit as st

from src.config import DATA_PROCESSED
from src.viz.usage import usage_bar

st.set_page_config(page_title="Champions VGC", page_icon="⚔️", layout="wide")
st.title("Pokémon Champions — VGC Dashboard")

df = pd.read_parquet(DATA_PROCESSED / "champions.parquet")

st.subheader("Top usage")
st.plotly_chart(usage_bar(df, n=20), use_container_width=True)
```

</details>

---

### Task 3.3 — Layout: sidebar, tabs, columns

Organize the dashboard into tabs (`Overview`, `Pokémon detail`, `Team builder`)
and put global filters (regulation set, top-N slider) in the sidebar.

**Generic approach:**
- `st.sidebar` is a context: anything written inside it lands on the side.
- `st.tabs([...])` returns one context per tab.
- `st.columns(n)` returns column contexts for side-by-side layout.

<details>
<summary>💡 Hint</summary>

`with tab1:` / `with sidebar:` / `with col1:` are all standard `with` blocks. Keeps the indentation visually mirror what the user will see.

</details>

<details>
<summary>✅ Solution</summary>

```python
# app.py (extended)
with st.sidebar:
    st.header("Filters")
    n = st.slider("Top N", min_value=5, max_value=50, value=20, step=5)

overview, detail, builder = st.tabs(["Overview", "Pokémon detail", "Team builder"])

with overview:
    st.plotly_chart(usage_bar(df, n=n), use_container_width=True)

with detail:
    st.write("Coming up in Task 3.4 ⤵️")

with builder:
    st.write("Future work — possibly the deep-learning phase.")
```

</details>

---

### Task 3.4 — Interactivity: pick a Pokémon, see its movesheet

Inside the **Pokémon detail** tab, add a `selectbox` to pick a Pokémon and
render its movesheet (Task 2.5) and teammates (Task 2.4) below.

**Generic approach:**
- `name = st.selectbox("Pokémon", df["name"])`
- Filter the movesheet/teammate DataFrames for that name.
- Render two charts side-by-side using `st.columns(2)`.

<details>
<summary>💡 Hint</summary>

Selectbox returns the chosen value directly — store it in a variable and use it as a filter. If the movesheet DataFrame is empty for that Pokémon (rare names), use `st.info("No data for this Pokémon yet.")` to fail gracefully.

</details>

<details>
<summary>✅ Solution</summary>

```python
# inside the `with detail:` block
with detail:
    name = st.selectbox("Pick a Pokémon", df["name"].sort_values())
    movesheet = pd.read_parquet(DATA_PROCESSED / "movesheets.parquet")
    teammates = pd.read_parquet(DATA_PROCESSED / "teammates.parquet")

    moves_for = movesheet[movesheet["name"] == name]
    teammates_for = teammates[teammates["anchor"] == name]

    if moves_for.empty:
        st.info("No movesheet data for this Pokémon yet.")
    else:
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Common moves / items / abilities")
            fig = px.bar(moves_for, x="pct", y="value", color="category", orientation="h")
            st.plotly_chart(fig, use_container_width=True)
        with col2:
            st.subheader("Common teammates")
            fig = px.bar(teammates_for.head(10), x="co_pct", y="teammate", orientation="h")
            st.plotly_chart(fig, use_container_width=True)
```

</details>

---

### Task 3.5 — Performance: cache the data loaders

Right now every interaction re-reads parquet from disk. Use `@st.cache_data`
so the DataFrames are loaded once per session.

**Generic approach:**
- Wrap each `pd.read_parquet(...)` call in a function decorated with `@st.cache_data`.
- Streamlit hashes the arguments to know whether to re-run the function.

<details>
<summary>💡 Hint</summary>

`@st.cache_data` for **data** (DataFrames, lists, dicts), `@st.cache_resource` for **shared resources** (database connections, ML models). Don't mix them up — caching a connection with `cache_data` will pickle and break it.

</details>

<details>
<summary>✅ Solution</summary>

```python
# src/data_io.py
import pandas as pd
import streamlit as st

from src.config import DATA_PROCESSED


@st.cache_data
def load_usage() -> pd.DataFrame:
    return pd.read_parquet(DATA_PROCESSED / "champions.parquet")


@st.cache_data
def load_movesheets() -> pd.DataFrame:
    return pd.read_parquet(DATA_PROCESSED / "movesheets.parquet")


@st.cache_data
def load_teammates() -> pd.DataFrame:
    return pd.read_parquet(DATA_PROCESSED / "teammates.parquet")
```

Then in `app.py` replace direct `pd.read_parquet(...)` with `load_usage()` etc.

</details>

---

### Task 3.6 — Polish: theme, empty states, error handling

Final pass. Make the dashboard not feel like a school project:
- Theme set in `.streamlit/config.toml` (already there — tweak colors if you want).
- Every chart has a sensible empty-state message when its DataFrame is empty.
- Wrap data loads in a top-level `try/except` that shows `st.error(...)` instead of crashing.

**Generic approach:**
- Audit each panel: what happens if the underlying DataFrame is empty?
- Replace empty Plotly figures with `st.info(...)`.
- Catch `FileNotFoundError` at the top of the app — direct the user to run the fetch step.

<details>
<summary>💡 Hint</summary>

A nice pattern: `def safe_chart(df, builder):  return builder(df) if not df.empty else None` — then in the app, `fig = safe_chart(...); st.plotly_chart(fig) if fig else st.info("No data")`.

</details>

<details>
<summary>✅ Solution</summary>

```python
# app.py (top of file)
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Champions VGC", page_icon="⚔️", layout="wide")

try:
    from src.data_io import load_usage, load_movesheets, load_teammates
    usage = load_usage()
    movesheets = load_movesheets()
    teammates = load_teammates()
except FileNotFoundError as exc:
    st.error(
        f"Missing data file: `{exc.filename}`.\n\n"
        "Run `python -m src.transform.build_dataset` first to populate `data/processed/`."
    )
    st.stop()
```

</details>

---

## What's next

You now have a working dashboard. Possible next chapters (open them when you're ready):

- **Chapter 4 — Deploy**: Streamlit Community Cloud is free and takes ~5 minutes from a GitHub repo.
- **Chapter 5 — Schedule fresh data**: a GitHub Action that runs the fetcher daily and pushes a new `data/processed/` parquet.
- **Chapter 6 — Deep-learning predictors**: the original stretch goal — recommend teammates given a partial team using collaborative filtering or a small transformer over team-cores.
