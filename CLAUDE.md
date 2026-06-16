# CLAUDE.md

This file is the standing context for the project. Read it in full at the start of **every** session before writing or changing any code. The live progress tracker AND the full feature specification both live in `build_plan.md` (progress at the top, spec in the "Specification reference" section at the bottom).

## Session protocol (do this first, every time)

1. Read this file (`CLAUDE.md`).
2. Read `build_plan.md` and find the **Current status** block — this tells you which phase and step you are on.
3. Do the work for the current step only. Do not skip ahead.
4. When a checkbox is finished, tick it in `build_plan.md` and update the **Current status** block.
5. If you make an architectural decision, record it in the **Decision log** in `build_plan.md`.
6. Keep changes scoped to the current phase so the project stays runnable at every step.

## What we are building

A **two-hub web application** for stock/ETF portfolio analysis and equity research, deployed on **Streamlit Cloud** (publicly accessible, no local install required). The target feel is a professional tool in the spirit of Bloomberg / Morningstar Direct / Portfolio Visualizer / FactSet.

### Portfolio Hub
Users build a portfolio of tickers and run risk, return and optimisation analyses on historical market data from Yahoo Finance. The dashboard shows metrics, charts, optimisation and scenario analysis in one scrollable page that refreshes on "Analyse Portfolio".

### Research Hub
Stock screener (4 universes), company fundamentals, valuation engine, insider activity tracker, sector intelligence, investment thesis generator, and ETF deep-dive — all in one tab-based workspace. Automatically routes ETF tickers to the ETF analysis page and stocks to the company analysis flow.

## Technology stack (locked — do not substitute)

| Layer | Technology |
|-------|-----------|
| UI framework | **Streamlit ≥ 1.35** |
| Charts | **Plotly** (`plotly.graph_objects`) via `st.plotly_chart` |
| Data | **yfinance**, **pandas**, **numpy** |
| Analytics | **scipy**, **statsmodels**, **PyPortfolioOpt** |
| Deployment | **Streamlit Cloud** (GitHub auto-deploy) |
| Python | 3.12 |

**No PySide6, no matplotlib/seaborn in the UI, no Qt, no local-only desktop app.**

## Repository structure

```
project/
├── streamlit_app/
│   ├── app.py                    # entry point: two-hub navigation (Portfolio / Research)
│   ├── pages/
│   │   ├── dashboard.py          # Portfolio metrics, charts, optimisation, scenario
│   │   ├── asset_analysis.py     # Per-asset breakdown
│   │   ├── monte_carlo.py        # Monte Carlo simulation
│   │   ├── research_hub.py       # Research Hub shell (4 tabs)
│   │   ├── screener.py           # Stock screener with universe selector
│   │   ├── fundamentals.py       # Company fundamentals detail page
│   │   ├── valuation.py          # Valuation engine (DCF, multiples, historical)
│   │   ├── insider.py            # Insider activity with time-decay scoring
│   │   ├── sector_intel.py       # Sector Intelligence page
│   │   ├── research_report.py    # Unified Investment Thesis / Research Report tab
│   │   └── etf_analysis.py       # ETF deep-dive (Overview / Holdings / Exposure / Performance / Score)
│   ├── components/
│   │   ├── analysis_runner.py    # Fetch prices + compute all portfolio analytics
│   │   ├── portfolio_builder.py  # Sidebar: ticker input, weight sliders, settings
│   │   └── export_panel.py       # CSV / Excel / PDF export UI
│   ├── styles/
│   │   └── theme.py              # Shared colour constants (ACCENT, BG_*, BORDER, etc.)
│   └── state/
│       └── session.py            # st.session_state wrappers (portfolio, result, settings)
│
├── analytics/                    # Pure functions — NO Streamlit, NO network, NO disk
│   ├── returns.py                # CAGR, annualised return, CAPM
│   ├── risk.py                   # Volatility, Sharpe, Sortino, beta, drawdown, VaR, CVaR
│   ├── diversification.py        # Avg correlation, diversification score, risk contributions
│   ├── scenario.py               # Historical stress tests
│   ├── monte_carlo.py            # Simulation engine
│   └── health_score.py           # 0–100 composite portfolio health score
│
├── optimization/                 # PyPortfolioOpt wrappers — pure, no I/O
│   ├── optimizers.py             # Max Sharpe, Min Variance, Black-Litterman
│   └── efficient_frontier.py     # Frontier sampling
│
├── research/
│   ├── data/
│   │   ├── fundamentals_fetcher.py   # yfinance + SEC EDGAR fetch → FundamentalData
│   │   ├── insider_fetcher.py        # SEC EDGAR Form 4 insider trades
│   │   ├── sector_fetcher.py         # Sector aggregation (yfinance)
│   │   ├── etf_fetcher.py            # ETF profile (holdings, sectors, countries, AUM)
│   │   ├── universe.py               # AEX / Nasdaq100 / S&P500 / STOXX600 ticker lists
│   │   └── watchlist_store.py        # JSON watchlist persistence
│   ├── analytics/
│   │   ├── fundamental_scorer.py     # 0–100 fundamental quality score
│   │   ├── valuation_engine.py       # DCF, P/E multiples, historical valuation
│   │   ├── insider_scorer.py         # Insider pressure score with 45-day time decay
│   │   ├── screener.py               # ScreenerRow + composite score_from_info()
│   │   ├── technical_scorer.py       # RSI-14, MA50/200, MACD, momentum, 52-week range
│   │   ├── thesis_generator.py       # Rule-based investment thesis (no LLM)
│   │   └── etf_scorer.py             # ETF composite score (cost / diversification / performance / risk)
│   ├── cache/
│   │   └── screener_cache.py         # Daily JSON cache per universe; invalidates on ticker-list change
│   └── models/
│       └── fundamentals.py           # FundamentalData, Watchlist, ValuationResult, etc.
│
├── services/
│   ├── data_service.py           # yfinance fetch, cache, retry, error mapping
│   ├── cache.py                  # On-disk price-history cache (key: ticker + period)
│   └── portfolio_io.py           # JSON save/load for portfolios
│
├── models/                       # Dataclasses shared across analytics & UI
│   ├── asset.py                  # Asset(ticker, weight)
│   ├── portfolio.py              # Portfolio(assets, benchmark, period)
│   ├── settings.py               # AnalysisSettings(risk_free_rate, market_return, …)
│   └── results.py                # AnalysisResult, AssetMetrics, OptimizationResult
│
├── utils/
│   ├── constants.py              # TRADING_DAYS_PER_YEAR=252, GROWTH_START_VALUE=10000, …
│   ├── logging.py                # Configured logger
│   └── formatting.py             # _pct(), _num(), _bn() helpers
│
├── tests/                        # pytest — mirrors analytics/ and optimization/
├── requirements.txt
└── README.md
```

## Layering rules (strict)

| Layer | May import from | Forbidden |
|-------|----------------|-----------|
| `streamlit_app/` | everything | — |
| `analytics/`, `optimization/` | `models/`, `utils/`, scientific stack | Streamlit, network, disk |
| `research/analytics/` | `research/models/`, `utils/`, scientific stack | Streamlit, network, disk |
| `research/data/` | `research/models/`, `utils/`, yfinance | Streamlit |
| `services/` | `models/`, `utils/`, yfinance | Streamlit |

## Domain conventions (apply consistently everywhere)

- **Returns:** daily returns from **Adjusted Close** (`auto_adjust=True`). Annualise with **252** trading days.
- **Volatility:** `std(daily returns) × √252`.
- **Annualised return:** `mean(daily returns) × 252`.
- **Sharpe:** `(ann_return − rf) / ann_volatility`. Risk-free rate configurable (default 2.5 %).
- **Sortino:** same numerator, denominator = annualised **downside** deviation.
- **Beta:** `cov(asset, benchmark) / var(benchmark)` on daily returns. Use fixed internal column names to avoid duplicate-column bugs when asset == benchmark ticker.
- **Max Drawdown:** `max((peak − trough) / peak)` over the full analysis period.
- **VaR (95 %, 99 %):** historical method on daily returns. **CVaR:** mean of losses beyond VaR threshold.
- **Expected Return:** three methods — historical CAGR, historical mean annualised, CAPM. Default for optimisation = historical mean annualised.
- **Currency:** display in EUR; growth charts start at €10,000.
- **Benchmarks:** SPY, VTI, ACWI. **Periods:** 1y, 3y, 5y, 10y, Max.
- **Timezone:** always strip timezone from yfinance DatetimeIndex before `concat` / `reindex` (newer yfinance returns tz-aware indices for some exchanges).

## Data layer rules

- Source: `yfinance`, Adjusted Close.
- **Cache** price history locally (key: ticker + period) so repeated analyses are fast.
- **Retry** transient network failures with exponential back-off (3 attempts).
- Handle gracefully: ticker not found, insufficient data, missing data, mismatched start dates (inner join), no internet connection.
- Never crash the whole analysis on a single bad ticker — report it and continue.
- **Screener cache:** daily JSON per universe; also keyed by MD5 hash of sorted ticker list so cache invalidates if the universe changes.

## Key design decisions already made

- Streamlit Cloud deployment (not local desktop). GitHub push → auto-redeploy.
- Charts: Plotly only (not matplotlib). `st.plotly_chart(fig, use_container_width=True)`.
- Metric cards: `st.container(border=True)` + `st.popover` inside — the only reliable way to place the info icon inside the card on Streamlit Cloud (injected `<style>` blocks are sanitised).
- Insider scoring uses **exponential time decay** with half-life 45 days: `decay = exp(−ln2 × days_ago / 45)`.
- Investment thesis is **rule-based** (no LLM). Overall score = Fundamentals 30 % + Valuation 25 % + Technical 20 % + Sector 15 % + Insider 10 %.
- ETF detection via `quoteType` / `legalType` in yfinance info; auto-routes to ETF analysis page.
- Research Hub uses `st.tabs` inside the Company Look-up tab; ETF tickers bypass those tabs.

## How to run

```bash
# Local development
pip install -r requirements.txt
streamlit run streamlit_app/app.py

# Tests (must not hit network)
pytest

# Production
git push origin master   # Streamlit Cloud auto-deploys from GitHub
```

## Definition of done (whole project)

All phases 1–22 complete. A fully deployed Streamlit Cloud app with:
- **Portfolio Hub:** metrics dashboard, performance chart, allocation donuts, correlation matrix, drawdown/rolling-vol charts, efficient frontier, optimisation panel, scenario analysis, risk/return contribution charts, export (CSV/Excel/PDF), JSON save/load.
- **Research Hub:** stock screener (4 universes, composite scoring, daily cache), company fundamentals, valuation engine, insider activity with time-decay, sector intelligence, investment thesis / research report, ETF analysis.
- All analytics tests passing (pytest, no network calls).
