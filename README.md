# Portfolio Analyser

A professional portfolio analysis tool for stocks and ETFs. Runs **fully locally** — no backend, no subscriptions.

Two interfaces ship from the same codebase:

| Interface | Technology | Access |
|-----------|-----------|--------|
| **Web app** (primary) | Streamlit + Plotly | Browser on any device · iPhone / Android home screen |
| **Desktop app** | PySide6 (Qt 6) | Windows / macOS / Linux native window |

---

## Features

### Dashboard
- Build a portfolio from any ticker on Yahoo Finance
- **7 KPI cards**: CAGR · Ann. Return · Volatility · Sharpe · Sortino · Max Drawdown · Health Score
- **Portfolio Health Score** (0–100) based on Sharpe, drawdown, volatility, diversification and concentration
- **Period selector**: 1M · 3M · 6M · YTD · 1Y · All — growth chart and risk charts follow the selection
- **Allocation view**: Portfolio-weight donut + Sector-allocation donut (yfinance data)
- **Full metric set**: Expected Return · CAGR · CAPM Return · Volatility · Sharpe · Sortino · Beta · Max DD · VaR 95% · VaR 99% · CVaR · Diversification Score · Health Score
- **Correlation matrix**: interactive Plotly heatmap with value annotations

### Optimisation Panel
- **3 optimizers**: Maximum Sharpe · Minimum Variance · Black-Litterman
- Side-by-side weight and metric comparison table for all methods
- **Apply weights** — one click rewrites the portfolio and re-runs all analytics
- **Efficient Frontier** chart with all four portfolio points marked

### Scenario Analysis
- Stress-test: Bull (+15 %) · Mild Recession (−10 %) · Recession (−20 %) · Severe Crash (−35 %)
- Beta-weighted portfolio impact with correlation-stressed volatility estimates
- Bar chart + impact table shown together

### Asset Analysis Page
- **Sortable table** — 16 columns: Ticker · Weight · Price · CAGR · Return · Volatility · Sharpe · Sortino · Beta · Corr. Benchmark · Max DD · VaR 95% · CVaR · Dividend Yield · Risk Contrib. · Return Contrib.
- **Normalised performance chart**: all assets vs benchmark indexed to 100
- **Risk/Return scatter**: bubble size = portfolio weight
- **Sharpe & Sortino bars** with colour thresholds
- **Per-asset expandable detail**: 12 metric cards + mini price chart

### Monte Carlo Page
- Configurable: 100–5 000 simulations, 1–30 year horizon
- **6 KPI cards**: Median · Mean · 5th pct · 95th pct · Prob. of Loss · Median Gain
- **Paths chart**: fan of sample paths with 5th–95th pct confidence band fill
- **Ending-value histogram**: loss-zone shading, percentile markers, statistics table

### Export
| Format | Contents |
|--------|----------|
| **CSV** | Metadata · Portfolio metrics · Per-asset table · Optimisation weights & metrics |
| **Excel** | 4 styled sheets: Summary · Assets · Optimisation · Scenarios |
| **PDF** | 7-section professional report with embedded charts |
| **JSON** | Portfolio save/load (tickers, weights, benchmark, period) |

---

## Quick start — Web app (recommended)

### Step 1 — Clone and install

```bash
git clone https://github.com/sgieles/portfolio-analyse.git
cd portfolio-analyse
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### Step 2 — Run Streamlit

```bash
streamlit run streamlit_app/app.py
```

Open **http://localhost:8501** in your browser.

> **iPhone / Android**: open `http://<your-local-ip>:8501` in Safari or Chrome,
> then use **Add to Home Screen** to install it as a PWA-style icon.

---

## Quick start — Desktop app (PySide6)

```bash
python main.py
```

Requires the same virtual environment. Launches a native dark-themed window with 5 tabs.

---

## Running the tests

```bash
pytest
```

311 tests covering analytics, optimisation, charts, data service, models, validators and exporters. The test suite is fully offline — no network calls.

```bash
pytest -v                           # verbose output
pytest --cov=. --cov-report=term-missing   # coverage
```

---

## Project structure

```
portfolio-analyse/
├── main.py                    # Desktop app entry point (PySide6)
├── requirements.txt
├── README.md
│
├── streamlit_app/             # Web app (Streamlit)
│   ├── app.py                 # Entry point — run with: streamlit run streamlit_app/app.py
│   ├── pages/
│   │   ├── dashboard.py       # Main dashboard (all sections)
│   │   ├── asset_analysis.py  # Per-asset table + charts
│   │   └── monte_carlo.py     # MC simulation
│   ├── components/
│   │   ├── portfolio_builder.py  # Sidebar: add/remove tickers, weights
│   │   ├── analysis_runner.py    # Fetch + compute (cached)
│   │   └── export_panel.py       # CSV / Excel / PDF / JSON download buttons
│   ├── state/
│   │   └── session.py         # st.session_state accessors
│   └── styles/
│       └── theme.py           # Warm/light colour palette + Plotly template + CSS
│
├── analytics/                 # Pure functions (no Qt, no I/O)
│   ├── returns.py             # CAGR, annualised return, CAPM
│   ├── risk.py                # Volatility, Sharpe, Sortino, VaR, CVaR, Beta
│   ├── diversification.py     # Correlation, diversification score, contributions
│   ├── scenario.py            # Stress-test analytics
│   ├── monte_carlo.py         # GBM simulation via Cholesky decomposition
│   └── health_score.py        # 0–100 composite health score
├── optimization/
│   ├── optimizers.py          # Max Sharpe, Min Variance, Black-Litterman
│   └── efficient_frontier.py  # Frontier sampling
├── charts/                    # Matplotlib draw functions (desktop app)
│   ├── growth.py
│   ├── frontier.py
│   ├── drawdown.py
│   ├── rolling_vol.py
│   └── risk_contribution.py
├── services/                  # I/O: network + disk
│   ├── data_service.py        # yfinance fetch, retry, error mapping
│   ├── cache.py               # Local price cache keyed by ticker + period
│   └── portfolio_io.py        # JSON save/load
├── models/                    # Dataclasses
│   ├── asset.py
│   ├── portfolio.py
│   ├── settings.py
│   └── results.py
├── reports/                   # Export (shared by both interfaces)
│   ├── csv_exporter.py
│   ├── excel_exporter.py
│   └── pdf_report.py
├── utils/
│   ├── constants.py
│   ├── logging.py
│   └── validators.py
├── ui/                        # PySide6 widgets (desktop only)
└── tests/                     # pytest suite (311 tests)
```

---

## Architecture

The codebase enforces strict layering:

| Layer | May import | May NOT import |
|-------|-----------|----------------|
| `streamlit_app`, `ui` | analytics · services · charts · models | — |
| `analytics` · `optimization` · `charts` | models · utils · scientific stack | Qt · network · disk |
| `services` | models · utils | Qt |

Every calculation in `analytics/` is a pure function testable without any UI.

---

## Domain conventions

| Concept | Method |
|---------|--------|
| Returns | Daily, from Adjusted Close |
| Annualisation | × 252 trading days |
| Volatility | Daily std × √252 |
| Sharpe | (ann. return − rf) / ann. vol |
| Sortino | (ann. return − rf) / annualised downside deviation |
| Beta | cov(asset, benchmark) / var(benchmark) |
| VaR | Historical method, positive loss magnitude |
| CVaR | Mean of losses beyond VaR threshold |
| Growth charts | Start value €10 000 |
| Benchmarks | SPY · VTI · ACWI |
| Periods | 1y · 3y · 5y · 10y · max |

---

## Technology stack

| Package | Purpose |
|---------|---------|
| Python 3.12+ | Runtime |
| Streamlit 1.x | Web interface |
| Plotly | Interactive charts (web) |
| PySide6 | Desktop GUI framework (Qt 6) |
| pandas | Price/return DataFrames |
| numpy | Numerical computation |
| scipy | Downside deviation, optimisation helpers |
| statsmodels | Statistical helpers |
| yfinance | Yahoo Finance price data |
| matplotlib + seaborn | Charts for desktop app and PDF export |
| PyPortfolioOpt | Max Sharpe, Min Variance, Black-Litterman |
| reportlab | PDF generation |
| openpyxl | Excel workbook generation |

---

## Troubleshooting

**Tickers show "not found"**
Make sure you have an active internet connection for the first fetch. After that, prices are cached locally in `.cache/`.

**`pip install` fails on PySide6**
PySide6 requires Python 3.9–3.13. Check with `python --version`. If you only need the web app, PySide6 is optional.

**PDF export is slow**
Generating the PDF renders all charts via matplotlib. On a slow machine it may take 5–10 seconds; this is normal.

**Tests fail with import errors**
Make sure the virtual environment is activated before running `pytest`.

**Streamlit: port 8501 already in use**
Run on a different port: `streamlit run streamlit_app/app.py --server.port 8502`
