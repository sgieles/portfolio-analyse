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

A **dashboard-first** desktop application for stock/ETF portfolio analysis. Users build a portfolio of tickers and run risk, return and optimization analyses on historical market data from Yahoo Finance. Runs **fully locally, no backend**. The target feel is a professional tool in the spirit of Bloomberg / Morningstar Direct / Portfolio Visualizer / FactSet.

The **Portfolio Dashboard** is the primary workspace: portfolio construction, statistics, optimization and all primary charts live on one tab and refresh automatically when allocations change. The user should never have to switch tabs to see how a weight change affects metrics and charts.

## Technology stack (locked — do not substitute)

Python 3.12 · PySide6 · pandas · numpy · scipy · statsmodels · yfinance · matplotlib · seaborn · PyPortfolioOpt

Charts are matplotlib/seaborn figures embedded in PySide6 via `FigureCanvasQTAgg`. No web tech, no Qt Charts, no Plotly.

## Architecture

```
project/
├── main.py            # entry point: builds QApplication, applies dark theme, shows MainWindow
├── ui/                # PySide6 widgets only — NO calculations here
│   ├── main_window.py        # QTabWidget host for the 5 tabs
│   ├── dashboard_tab.py      # Tab 1 (Builder, Metrics, Optimization, Visualizations)
│   ├── asset_analysis_tab.py # Tab 2
│   ├── correlation_tab.py    # Tab 3
│   ├── scenario_tab.py       # Tab 4
│   ├── monte_carlo_tab.py    # Tab 5
│   ├── widgets/              # reusable widgets (metric cards, weight table, chart canvas)
│   └── theme.py              # dark stylesheet + matplotlib dark style
├── services/          # data acquisition & persistence (I/O side effects live here)
│   ├── data_service.py       # yfinance fetch, caching, retry, error mapping
│   ├── cache.py              # local on-disk cache of price history
│   └── portfolio_io.py       # save/load JSON portfolios
├── analytics/         # pure functions on pandas/numpy — NO Qt, NO I/O
│   ├── returns.py            # CAGR, annualized return, CAPM expected return
│   ├── risk.py               # volatility, Sharpe, Sortino, beta, drawdown, VaR, CVaR
│   ├── diversification.py    # avg correlation, diversification score, risk contribution
│   ├── scenario.py           # stress tests via historical betas/correlations
│   ├── monte_carlo.py        # simulation engine
│   └── health_score.py       # 0–100 portfolio health score (bonus)
├── optimization/      # PyPortfolioOpt wrappers (may live under analytics/ if preferred)
│   ├── optimizers.py         # max Sharpe, min variance, Black-Litterman
│   └── efficient_frontier.py # frontier sampling for the chart
├── charts/            # functions that take data + Axes/Figure and draw — NO data fetching
│   ├── growth.py             # portfolio vs benchmark growth from €10,000
│   ├── frontier.py           # efficient frontier with the 4 marked portfolios
│   ├── drawdown.py
│   ├── rolling_vol.py
│   └── risk_contribution.py
├── models/            # dataclasses: Asset, Portfolio, AnalysisSettings, AnalysisResult
├── utils/             # logging config, constants, formatting, validators
├── reports/           # CSV / Excel / PDF export
└── tests/             # pytest unit tests, mirroring the analytics/optimization modules
```

### Layering rule (strict)

`ui` → may call `services`, `analytics`, `optimization`, `charts`, `reports`, `models`.
`analytics`, `optimization`, `charts` → pure: depend only on `models`, `utils`, and the scientific stack. **No Qt imports, no network, no disk.**
`services` → the only layer allowed to touch the network or filesystem.

This separation is the whole point of the design. If a calculation needs Qt or a network call to work, it is in the wrong layer.

## Domain conventions (apply consistently everywhere)

- **Returns:** use **daily** returns from **Adjusted Close** (dividend-adjusted). Annualize with **252** trading days.
- **Volatility:** annualized standard deviation = daily std × √252.
- **Annualized return** from daily mean = daily mean × 252.
- **Sharpe:** `(annualized return − risk-free rate) / annualized volatility`. Risk-free rate is **configurable**.
- **Sortino:** same numerator, denominator = annualized **downside** deviation.
- **Beta:** `cov(asset, benchmark) / var(benchmark)` on daily returns vs the chosen benchmark.
- **Max Drawdown:** computed over the full price history of the chosen analysis period.
- **VaR (95%, 99%):** historical method on daily returns. **CVaR:** mean of losses beyond the VaR threshold (expected shortfall).
- **Expected Return:** offer all three methods — historical CAGR, historical average annualized return, CAPM. **Default used for optimization = historical average annualized return**, but configurable.
- **Currency:** display in EUR; growth charts start at €10,000. (Prices come from Yahoo in their native currency — note this assumption in the data layer; do not silently mix currencies.)
- **Benchmarks:** SPY, VTI, ACWI. **Analysis periods:** 1y, 3y, 5y, 10y, Max.

## Data layer rules

- Source: `yfinance`, Adjusted Close.
- **Cache** price history locally so repeated analyses are fast; key by ticker + period.
- **Retry** transient network failures with backoff.
- Handle gracefully and surface user-friendly messages for: ticker not found, insufficient data, missing data, mismatched start dates (align on common date range), no internet connection.
- Never let a single bad ticker crash the whole analysis — report it and continue where sensible.

## Code quality bar

- Full **type hints**; use **dataclasses** for domain models.
- **PEP8**; keep functions small and pure in the analytics/optimization/charts layers.
- **Docstrings** on public functions/classes, with the formula or method noted for every financial calculation.
- **Logging** via a configured logger (`utils/logging.py`), not `print`.
- **pytest** unit tests for every analytics and optimization function, including edge cases (single asset, missing data, zero variance). Use small synthetic price series or fixtures — tests must not hit the network.
- Deliver `requirements.txt`, `README.md` and an installation guide.

## How to run / test

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python main.py        # launch the app
pytest                # run the test suite
```

## Definition of done (whole project)

A fully working, locally-running application with all 5 tabs functional, automatic dashboard refresh on portfolio changes, the three optimizers, all five dashboard charts, CSV/Excel/PDF export, JSON save/load, tests passing, and the docs delivered. Bonus features (Rebalancing Advisor, Dividend Analysis, Portfolio Health Score) are added only after the core is complete and stable.
