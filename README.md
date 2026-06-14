# Portfolio Analyser

A professional desktop application for stock and ETF portfolio analysis. Fully local, no backend, no subscriptions.

![Dashboard](docs/screenshot_placeholder.png)

---

## Features

### Portfolio Dashboard (Tab 1)
- Build a portfolio from any stock or ETF ticker available on Yahoo Finance
- Adjust weights; all metrics and charts refresh automatically in under one second
- **14 metric cards** — return, risk and diversification in one glance
- **Portfolio Health Score** (0–100) based on Sharpe, drawdown, volatility, diversification and concentration
- **5 embedded charts**: Growth from €10 000 vs benchmark · Efficient Frontier · Drawdown · Rolling Volatility · Risk Contribution
- **3 portfolio optimizers**: Maximum Sharpe · Minimum Variance · Black-Litterman
- Preview optimized weights before applying; one click to apply and re-run

### Asset Analysis (Tab 2)
- Sortable table with 15 per-asset columns: CAGR, Return, Volatility, Sharpe, Sortino, Beta, Max Drawdown, VaR 95/99, CVaR, Risk Contribution, Return Contribution

### Correlation Analysis (Tab 3)
- Correlation heatmap · Covariance heatmap · Hierarchical correlation clustering

### Scenario Analysis (Tab 4)
- Stress test against Bull Market (+15 %) · Mild Recession (−10 %) · Recession (−20 %) · Severe Crash (−35 %)
- Beta-weighted portfolio impact with correlation-stressed volatility estimates

### Monte Carlo (Tab 5)
- Configurable: 100–10 000 simulations, 1–30 year horizon
- Outputs: median · mean · 5th/95th percentile · probability of loss
- Spaghetti paths chart + ending-value histogram with confidence band

### Export
| Format | Contents |
|--------|----------|
| **CSV** | Metadata · Portfolio metrics · Per-asset table · Optimization weights & metrics |
| **Excel** | 4 styled sheets: Summary · Assets · Optimization · Scenarios |
| **PDF** | 7-section professional report with embedded charts |

### Save & Load
JSON portfolio files store tickers, weights, benchmark and analysis period.

---

## Installation

### Prerequisites

- **Python 3.12 or later** — download from [python.org](https://www.python.org/downloads/)
- **Git** (optional, to clone the repo)

### Step 1 — Get the source

```bash
git clone <repo-url>
cd portfolio-analyse
```

Or download and unzip the archive.

### Step 2 — Create a virtual environment

**Windows (PowerShell)**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

**macOS / Linux**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Step 3 — Install dependencies

```bash
pip install -r requirements.txt
```

This installs approximately 20 packages including PySide6, pandas, numpy, matplotlib, seaborn, PyPortfolioOpt, yfinance, reportlab and openpyxl.

### Step 4 — Launch

```bash
python main.py
```

---

## Running the tests

```bash
pytest
```

279 tests covering analytics, optimization, charts, data service, models, validators and exporters. The test suite is fully offline — no network calls.

To see per-test output:

```bash
pytest -v
```

To measure coverage:

```bash
pytest --cov=. --cov-report=term-missing
```

---

## Quick start

1. Launch the app with `python main.py`.
2. In the **Portfolio Builder** (left panel), type a ticker (e.g. `AAPL`) and press **Add** or Enter.
3. Add several more tickers. Weights default to equal weighting.
4. Choose a **Benchmark** (SPY / VTI / ACWI) and **Period** (1y / 3y / 5y / 10y / Max).
5. Click **Analyze Portfolio**. A progress message appears in the status bar while data is fetched and metrics are computed.
6. Adjust any weight in the table — charts and metrics refresh automatically.
7. In Section C, select an optimizer, then click **Apply** to switch to optimized weights.
8. Export a PDF via **Export → Export PDF Report…**.

---

## Project structure

```
portfolio-analyse/
├── main.py                    # Entry point
├── requirements.txt
├── README.md
├── ui/                        # PySide6 widgets (no calculations)
│   ├── main_window.py
│   ├── dashboard_tab.py       # Primary workspace
│   ├── asset_analysis_tab.py
│   ├── correlation_tab.py
│   ├── scenario_tab.py
│   ├── monte_carlo_tab.py
│   ├── theme.py               # Dark stylesheet + matplotlib theme
│   └── widgets/
│       ├── metric_card.py
│       └── chart_canvas.py
├── analytics/                 # Pure functions (no Qt, no I/O)
│   ├── returns.py             # CAGR, annualized return, CAPM
│   ├── risk.py                # Volatility, Sharpe, Sortino, VaR, CVaR, Beta
│   ├── diversification.py     # Correlation, diversification score, contributions
│   ├── scenario.py            # Stress-test analytics
│   ├── monte_carlo.py         # GBM simulation via Cholesky decomposition
│   └── health_score.py        # 0–100 composite health score
├── optimization/
│   ├── optimizers.py          # Max Sharpe, Min Variance, Black-Litterman
│   └── efficient_frontier.py  # Frontier sampling
├── charts/                    # Draw functions (take data + Axes, return nothing)
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
├── reports/                   # Export
│   ├── csv_exporter.py
│   ├── excel_exporter.py
│   └── pdf_report.py
├── utils/
│   ├── constants.py
│   ├── logging.py
│   └── validators.py
└── tests/                     # pytest suite (279 tests)
```

---

## Architecture rules

The codebase enforces strict layering:

| Layer | May import | May NOT import |
|-------|-----------|----------------|
| `ui` | analytics, services, charts, models | — |
| `analytics`, `optimization`, `charts` | models, utils, numpy/pandas | Qt, network, disk |
| `services` | models, utils | Qt |

This means every calculation in `analytics/` is a pure function that can be unit-tested without launching the UI.

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
| Benchmarks | SPY, VTI, ACWI |
| Periods | 1y, 3y, 5y, 10y, max |

---

## Technology stack

| Package | Purpose |
|---------|---------|
| Python 3.12+ | Runtime |
| PySide6 | GUI framework (Qt 6) |
| pandas | Price/return DataFrames |
| numpy | Numerical computation |
| scipy | Downside deviation, optimisation helpers |
| statsmodels | Statistical helpers |
| yfinance | Yahoo Finance price data |
| matplotlib + seaborn | Embedded charts |
| PyPortfolioOpt | Max Sharpe, Min Variance, Black-Litterman |
| reportlab | PDF generation |
| openpyxl | Excel workbook generation |

---

## Troubleshooting

**The app opens but tickers show "not found"**
Make sure you have an active internet connection for the first fetch. After that, prices are cached locally.

**`pip install -r requirements.txt` fails on PySide6**
PySide6 requires Python 3.9–3.13. Check your Python version with `python --version`.

**PDF export is slow**
Generating the PDF renders all five charts into memory via matplotlib. On a slow machine a 5-page PDF may take 5–10 seconds; this is normal.

**Tests fail with import errors**
Make sure the virtual environment is activated before running `pytest`.
