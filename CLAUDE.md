# CLAUDE.md — context for future-Claude working in this repo

## Project

A **Streamlit + Plotly dashboard** for **Pokémon Champions VGC** data. The user
(Mario) is using this as a learning project. A possible future phase will add
deep-learning predictors for personalized recommendations, but **that is out of
scope until Mario explicitly opens it**.

The current target dashboard surfaces:
- Pokémon **usage %** in the current Champions ladder/regulation set
- **Win %** where derivable from tournament data
- **Likely teams** (team cores — Pokémon that frequently appear together)
- **Matchup stats** between top Pokémon
- **Movesheets** per Pokémon (most common moves, items, abilities, EV spreads)

## How to behave in this repo

### 🟥 Learning mode is the default — never hand over code unsolicited

Mario stated this in `instructions.txt` and reinforced it in chat: he wants the
**skeleton** of the code, never the full answer up front.

When he asks "how do I do X?" the response shape is:
1. Explain the concept in plain prose.
2. Sketch the generic approach.
3. Offer to reveal hints / a worked solution if he asks.

In **`instructions.md`** every task uses this structure literally:

```
### Task — <short imperative title>

<one-paragraph framing of the task and why it matters>

**Generic approach:** <high-level, language-agnostic recipe — no code>

<details>
<summary>💡 Hint</summary>

<a clickable nudge: which library / which function / which docs page>

</details>

<details>
<summary>✅ Solution</summary>

\`\`\`python
# the actual implementation
\`\`\`

</details>
```

**Both hints and solutions go inside `<details>` blocks.** Mario explicitly
asked for the solutions to also be hidden until clicked.

The exception: if Mario says "just give me the code" / "write it for me" /
"do it" — then provide the implementation directly.

### Project shape

```
app.py                   Streamlit entrypoint (Mario builds this — start as a stub)
src/
├── fetch/               API calls + scraping live here
├── transform/           Pandas cleaning, aggregation, derived metrics
└── viz/                 Plotly chart builders (pure functions: df -> Figure)
data/
├── raw/                 Raw API responses + scraped HTML/JSON dumps. Git-ignored.
└── processed/           Cleaned parquet/CSV the dashboard reads. Tracked in git.
notebooks/               Exploratory Jupyter work
tests/                   Pytest
.streamlit/              Theme + server config
```

Keep the **fetch / transform / viz** separation. Streamlit code in `app.py`
should call into `src.viz.<module>` for chart construction — never build
Plotly figures inline in the UI layer once the project gets past the first
few chapters.

### Data sources

Researched **2026-05-05**:

| Source | Type | Notes |
| --- | --- | --- |
| **PokéAPI** (`https://pokeapi.co/api/v2/`) | Public REST API, no auth | First-class for Pokémon **metadata** — sprites, base stats, types, learnsets |
| **Pikalytics** (`pikalytics.com/champions`) | Scraping only (server-rendered HTML) | Best Champions usage stats, top teams, regulation-set views |
| **MetaVGC** / **Pokémon Zone** / **Champions Lab** | Scraping only | Backup sources if Pikalytics structure changes |
| **Smogon stats** (`smogon.com/stats/YYYY-MM/`) | Public flat files | NOT Champions data — Showdown-side. Useful for comparison only |

**No public API exists for Champions usage data** — scraping is required.
That's not a pivot to Showdown; Champions data IS reachable, just via HTML.

### The polite-scraper checklist (enforce in every fetch task)

1. Custom `User-Agent` header (read from `.env`, see `.env.example`)
2. `time.sleep` between requests — default 1.5s
3. **Disk cache** every response (`.cache/scrape/<url-hash>.html`) — refetch only when stale
4. Respect `robots.txt`
5. No login-walled content
6. Don't redistribute scraped data

### Tech stack pinned for this project

- `streamlit` for the UI
- `plotly` for all charts (no matplotlib/seaborn in the dashboard layer)
- `pandas` + `pyarrow` for data wrangling and parquet I/O
- `requests` + `beautifulsoup4` + `lxml` for scraping
- `python-dotenv` for `.env` loading
- `tenacity` for retry logic on flaky requests

Deferred until later phases: `scikit-learn`, `scipy`, deep-learning frameworks.

### Conventions

- Type hints on all `src/` functions
- Docstrings short, explain the *why* — names should already cover the *what*
- One responsibility per module: a file in `src/fetch/` fetches; a file in `src/transform/` transforms; don't mix
- Save raw responses as JSON or `.html`; save processed data as Parquet
- Streamlit caching: `@st.cache_data` for DataFrames, `@st.cache_resource` for clients/sessions

### Commits

Don't commit on Mario's behalf unless he asks. He runs git himself.
