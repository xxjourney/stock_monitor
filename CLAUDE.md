# Taiwan Stock Monitor

A Line chatbot that monitors Taiwan stocks and sends notifications based on technical indicators and institutional investor data.

## Project Structure

- `stock_data.py` — Core data fetching, caching, and indicator calculation
- `export_report.py` — Batch CSV export of all watchlist stocks with indicators
- `main.py` — Line Bot webhook server (Flask)
- `watchlist.json` — Stock groups (e.g., Group_1 through Group_N)
- `cache/` — Daily cached CSVs per stock

## Key Architecture

### `get_stock_data(stock_id, force_refresh=False)`
- Fetches 730 days of price data + institutional investor data via FinMind API
- **Two cache files per stock per day:**
  - `{stock_id}_{today}.csv` — merged price + institutional + indicators (smart 15:00 cache)
  - `{stock_id}_{today}_inst.csv` — institutional data only (cached all day, no intraday updates)
- **Smart cache logic:** After 15:00 (market close), merged cache is bypassed if it was created before 15:00 (price may be stale). Institutional cache is always reused.
- **Stale fallback:** On API error, returns stale merged cache and bumps its mtime to prevent retry loops.

### FinMind API Rate Limiting
- Limit: 600 requests/hour
- 412 unique stocks × 2 endpoints = 824 calls for a first-ever full scan
- After first run: institutional cache reuse cuts to ~412 calls/scan
- `time.sleep(1.0)` between each API call

### Indicators Calculated
- **KD (Taiwan Standard):** RSV with 9-period rolling window, K/D smoothed via EWM (com=2, alpha=1/3)
- **MACD:** pandas-ta, fast=12, slow=26, signal=9

### Signals in `check_conditions()`
1. **Advanced Filter:** K crosses above 20 AND foreign net buy for 3 consecutive days
2. **MACD Golden Cross:** MACD line crosses above Signal line

## Usage

```bash
# Check a single stock
python stock_data.py 2330

# Export report for a watchlist group
python export_report.py Group_16

# Export report for all stocks
python export_report.py
```

## Environment

- `.env` file with `FINMIND_API_TOKEN` for authenticated API access (higher rate limits)
- Without token: guest mode (lower rate limits)
- `venv/` — Python virtual environment
