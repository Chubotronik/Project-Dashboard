# Pokémon Champions VGC Dashboard

A Streamlit + Plotly dashboard for exploring Pokémon Champions VGC data: usage %,
likely teams, matchup stats, and movesheets.

This is a **learning project**. The full step-by-step build guide lives in
[`instructions.md`](./instructions.md). Future-Claude reads [`CLAUDE.md`](./CLAUDE.md)
for context.

## Quick start

```powershell
# Activate the virtual environment (Windows / PowerShell)
.\venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Run the dashboard (once you've built it — see instructions.md)
streamlit run app.py
```

## Layout

```
src/        Python package — fetch / transform / viz modules
data/raw/   Raw scraped & API responses (git-ignored)
data/processed/  Cleaned datasets the dashboard reads from
notebooks/  Exploratory Jupyter notebooks
tests/      Pytest tests
.streamlit/ Streamlit theme/config
```
