# build_plan.md — Build Roadmap & Progress Tracker

> **How to use this file (read every session):**
> 1. Check **Current status** below to see where you left off.
> 2. Work only on the current step. Keep the app runnable after each step.
> 3. Tick a checkbox `[x]` the moment a task is genuinely done (code written *and* sanity-checked).
> 4. After finishing a step, update **Current status** and add a line to the **Decision log** / **Session log** if anything noteworthy happened.
> 5. Honour the layering and domain conventions in `CLAUDE.md`. The full feature spec is the **Specification reference** section at the bottom of this file.

---

## Current status

- **Phase:** 10 — complete
- **Next step:** All phases done — project meets Definition of Done
- **Last updated:** 2026-06-08
- **Notes:** 311 tests passing. Added test_scenario.py (18 tests), test_monte_carlo.py (16 tests), test_exports.py (21 tests), test_health_score.py (32 tests). README.md with installation guide written. Portfolio Health Score (0–100) added as analytics/health_score.py and wired into the dashboard Diversification section.

---

## Phase 1 — Architecture & project scaffold
*Goal: an empty but importable, runnable skeleton.*

- [x] Create the full folder structure from `CLAUDE.md` with `__init__.py` files
- [x] Write `requirements.txt` (pin the locked stack)
- [x] Set up `utils/logging.py` (configured logger) and `utils/constants.py` (252 trading days, benchmarks, periods, default RF rate)
- [x] Stub `main.py` so it opens an empty dark-themed `MainWindow` with 5 empty tabs
- [x] Add `ui/theme.py` dark stylesheet + matplotlib dark style
- [x] Confirm `python main.py` launches and `pytest` runs (even with zero tests)

**Done when:** the app opens, shows 5 empty tabs in dark mode, and imports cleanly.

## Phase 2 — Models
*Goal: the data contracts the whole app passes around.*

- [x] `models/`: `Asset`, `Portfolio`, `AnalysisSettings`, `AnalysisResult` as dataclasses with type hints
- [x] Validators in `utils/` (weights sum, valid ticker format, period enum)
- [x] Unit tests for model construction and validators

**Done when:** models are importable, validated, and tested.

## Phase 3 — Data layer
*Goal: reliable price history in, regardless of network/ticker problems.*

- [x] `services/cache.py` — on-disk cache keyed by ticker + period
- [x] `services/data_service.py` — yfinance fetch (Adjusted Close), retry with backoff, common-date alignment, friendly error mapping (not found / insufficient / no internet)
- [x] `services/portfolio_io.py` — save/load JSON (tickers, weights, benchmark, settings)
- [x] Tests with mocked/synthetic data (no live network calls)

**Done when:** given tickers + period, the service returns a clean aligned price frame or a clear, typed error.

## Phase 4 — Analytics engine
*Goal: every metric in the spec, as pure functions.*

- [x] `analytics/returns.py` — daily returns, CAGR, annualized return, CAPM expected return
- [x] `analytics/risk.py` — volatility, Sharpe, Sortino, beta, max drawdown, VaR 95/99, CVaR
- [x] `analytics/diversification.py` — avg correlation, diversification score, risk & return contribution per asset
- [x] Portfolio-level aggregation (weighted return series, portfolio vol via covariance)
- [x] Unit tests for each, incl. edge cases (single asset, zero variance, missing data)

**Done when:** all Tab-1 metrics can be computed from a price frame + weights, and tests pass.

## Phase 5 — Optimization engine
*Goal: the three optimizers + frontier data.*

- [x] `optimization/optimizers.py` — Max Sharpe, Min Variance, Black-Litterman (PyPortfolioOpt)
- [x] `optimization/efficient_frontier.py` — sample frontier points for the chart
- [x] Make the expected-return input configurable (default: historical average annualized)
- [x] Tests verifying weights sum to 1, respect bounds, and behave sensibly on toy inputs

**Done when:** each optimizer returns valid weights and the frontier can be sampled.

## Phase 6 — Charts (pure draw functions)
*Goal: matplotlib/seaborn figures, no data fetching inside.*

- [x] `charts/growth.py` — portfolio vs benchmark from €10,000
- [x] `charts/frontier.py` — efficient frontier marking current / max-Sharpe / min-var / Black-Litterman
- [x] `charts/drawdown.py` — drawdowns, largest drawdown, duration, recovery
- [x] `charts/rolling_vol.py` — 12-month rolling volatility
- [x] `charts/risk_contribution.py` — bar charts of risk & return contribution
- [x] Correlation/covariance heatmaps + clustering (seaborn) for Tab 3

**Done when:** each function takes data + an Axes/Figure and renders correctly in isolation.

## Phase 7 — GUI: Tab 1 Portfolio Dashboard
*Goal: the primary workspace, fully wired.*

- [x] Section A — Portfolio Builder: add/remove asset, edit weight, Equal Weight, Normalize, Save/Load, benchmark selector, period selector, **Analyze Portfolio**
- [x] Section B — Metric cards (return/risk/diversification) with color coding
- [x] Section C — Optimization: run the 3 optimizers, current-vs-optimized weight table, current-vs-optimized metric table, **Preview** + **Apply Optimized Weights**
- [x] Section D — All 5 visualizations embedded on the same tab
- [x] **Auto-refresh:** any weight/portfolio change re-runs metrics + charts without a tab switch
- [x] Keep recalculation fast (cache prices; recompute only what changed)

**Done when:** changing an allocation visibly updates both numbers and charts on the same screen.

## Phase 8 — GUI: remaining tabs
- [x] Tab 2 Asset Analysis — sortable table (Ticker, Weight, CAGR, Return, Vol, Sharpe, Beta, MaxDD, VaR95) + latest price, risk/return contribution
- [x] Tab 3 Correlation Analysis — correlation heatmap, covariance heatmap, correlation clustering
- [x] Tab 4 Scenario Analysis — Bull +15% / Mild −10% / Recession −20% / Severe −35% using historical betas & stressed correlations; impact on value, return, volatility; table + chart
- [x] Tab 5 Monte Carlo — configurable sims (100–10 000) & horizon (1–30y); median/mean/5th/95th/prob-of-loss; spaghetti paths + ending-value histogram; MCWorker QThread

**Done when:** all five tabs are functional and read from the shared analysis results.

## Phase 9 — Export & persistence
- [x] `reports/csv_exporter.py` — multi-section CSV (metadata, metrics, assets, optimization)
- [x] `reports/excel_exporter.py` — 4-sheet styled workbook (Summary, Assets, Optimization, Scenarios)
- [x] `reports/pdf_report.py` — 7-section PDF with embedded matplotlib/seaborn charts, professional layout
- [x] Export menu in MainWindow (File: Save/Load; Export: CSV/Excel/PDF), enabled after analysis
- [x] JSON save/load confirmed through dashboard UI buttons + File menu

**Done when:** a user can export a complete, professional PDF plus CSV/Excel.

## Phase 10 — Tests, docs, polish, bonus
- [x] Fill out the pytest suite to cover analytics + optimization thoroughly
- [x] `README.md` + installation guide
- [x] Logging & user-friendly error messages reviewed across the app
- [x] **Bonus:** Portfolio Health Score (0–100) — analytics/health_score.py + dashboard card
- [x] Final pass: PEP8, type hints, docstrings, dead-code removal

**Done when:** the Definition of Done in `CLAUDE.md` is fully met.

---

## Specification reference (full feature spec)

*This is the complete, authoritative feature specification. Phases above implement it; consult this section for exact requirements per tab, metric and behaviour.*

Build a professional desktop application in Python for portfolio analysis of stocks and ETFs.

### Goal

The application must let users assemble a portfolio from stock and ETF tickers and then run risk, return and optimization analyses based on historical market data.

Use Yahoo Finance as the data source via the `yfinance` library.

The application must run fully locally, with no backend.

---

### Core Design: Dashboard First

Design the application as a dashboard-first investment analysis tool.

The main **Portfolio Dashboard** tab must contain:

- Portfolio construction
- Portfolio statistics
- Portfolio optimization
- All primary visualizations

Users should immediately see how changes in allocations affect both numerical metrics and graphical risk/return visualizations without switching tabs.

The Portfolio Dashboard is the primary workspace of the application.

The application should feel similar to professional portfolio analysis tools such as Bloomberg, Morningstar Direct, Portfolio Visualizer or FactSet.

---

### Technology Stack

Use exclusively:

- Python 3.12
- PySide6
- pandas
- numpy
- scipy
- statsmodels
- yfinance
- matplotlib
- seaborn
- PyPortfolioOpt

Use a clear modular architecture:

```
project/
├── main.py
├── ui/
├── services/
├── analytics/
├── charts/
├── models/
├── utils/
├── reports/
└── tests/
```

---

### General Design Principles

- Professional, modern desktop UI
- Dark mode as the default
- Scalable design
- Fast recalculations
- Clear separation between data, analytics and presentation
- All key insights visible without many clicks
- Suitable for both beginners and advanced investors

---

### TAB 1: PORTFOLIO DASHBOARD

This is the most important screen of the application. All core functionality must be available here. Use a dashboard layout.

#### Section A — Portfolio Builder

Functions:

- Add asset
- Remove asset
- Adjust weight
- Equal Weight
- Normalize Weights
- Save Portfolio
- Load Portfolio

Support: stocks and ETFs.

Show a table:

| Ticker | Asset Name | Weight |
|--------|------------|--------|

Default: equal weighting across all assets.

##### Benchmark Selection

Support: `SPY`, `VTI`, `ACWI`.

The benchmark is used for: Beta, comparison charts, CAPM, relative performance.

##### Analysis Period

Support: 1 year, 3 years, 5 years, 10 years, Max.

Button: **Analyze Portfolio**

#### Section B — Portfolio Metrics

Show metric cards.

**Return**
- Expected Return
- CAGR
- Annualized Return

**Risk**
- Volatility
- Sharpe Ratio
- Sortino Ratio
- Beta
- Maximum Drawdown
- VaR 95%
- VaR 99%
- CVaR

**Diversification**
- Number of assets
- Average correlation
- Diversification score

Use clear color coding.

#### Section C — Portfolio Optimization

Support:

**Maximum Sharpe Portfolio** — maximize `(Expected Return − Risk Free Rate) / Volatility`

**Minimum Variance Portfolio** — minimize portfolio variance

**Black-Litterman Portfolio** — use PyPortfolioOpt; goal is more stable and realistic allocations

##### Optimization Results

Show:

| Asset | Current Weight | Optimized Weight |
|-------|----------------|------------------|

And:

| Metric | Current | Optimized |
|--------|---------|-----------|
| Return | | |
| Volatility | | |
| Sharpe | | |
| Beta | | |
| VaR | | |
| Drawdown | | |

Buttons:
- **Preview Optimized Portfolio**
- **Apply Optimized Weights**

After applying, immediately refresh all statistics and charts.

#### Section D — Dashboard Visualizations

All primary visualizations must be visible directly on the same tab. No separate visualization tab. Visualizations must refresh automatically after portfolio changes.

1. **Portfolio Growth** — historical growth of portfolio and benchmark, starting value €10,000. The user must immediately see whether the portfolio outperformed or underperformed the benchmark.
2. **Efficient Frontier** — visualize current portfolio, Maximum Sharpe, Minimum Variance and Black-Litterman portfolios. X-axis: risk. Y-axis: expected return. This is one of the most important visualizations.
3. **Drawdown Chart** — historical drawdowns; clearly show the largest drawdown, the duration of drawdowns and recovery periods.
4. **Rolling Volatility** — 12-month rolling volatility; the user must see how risk changes over time.
5. **Risk Contribution** — contribution per asset to total risk and total return, using bar charts.

---

### TAB 2: ASSET ANALYSIS

Analysis at the individual asset level.

Show a sortable table:

| Ticker | Weight | CAGR | Return | Volatility | Sharpe | Beta | Max Drawdown | VaR95 |
|--------|--------|------|--------|------------|--------|------|--------------|-------|

Extra: latest price, correlation with benchmark, dividend yield where available.

Support sorting on all columns.

---

### TAB 3: CORRELATION ANALYSIS

Show:

- **Correlation Matrix** — heatmap
- **Covariance Matrix** — heatmap
- **Correlation Clustering** — cluster assets by correlation to give direct insight into hidden concentration risk

Use seaborn.

---

### TAB 4: SCENARIO ANALYSIS

Run stress tests.

Support:

- Bull Market: +15%
- Mild Recession: −10%
- Recession: −20%
- Severe Crash: −35%

Use historical betas and historical correlations.

Compute the impact on: portfolio value, expected return, volatility.

Show tables and charts.

---

### TAB 5: MONTE CARLO SIMULATION

Monte Carlo simulation.

Defaults: 1,000 simulations, 5-year horizon.

Configurable: number of simulations, time horizon.

Show: median ending value, average ending value, 5th percentile, 95th percentile, probability of loss.

Visualizations: simulation paths, distribution of ending values, confidence intervals.

---

### Expected Return

Compute three different return estimates.

1. **Historical CAGR**
2. **Historical average annualized return**
3. **CAPM Expected Return** — `Expected Return = Risk Free Rate + Beta × (Market Return − Risk Free Rate)`, using the chosen benchmark.

Configurable: Risk Free Rate, Market Expected Return.

Show all three methods. Use the historical average return as the default for optimization, but make this configurable.

---

### Risk Calculations

Use daily returns. Compute:

- **Volatility** — annualized standard deviation
- **Sharpe Ratio** — configurable risk-free rate
- **Sortino Ratio** — using downside deviation
- **Beta** — relative to the chosen benchmark
- **Maximum Drawdown** — full historical drawdown
- **Historical VaR** — 95% and 99%
- **CVaR** — expected shortfall

---

### Data Functionality

Use Yahoo Finance via `yfinance`. Use Adjusted Close and dividend-adjusted returns. Support stocks and ETFs.

Implement: local caching, retry mechanism, error handling.

Account for: missing data, different start dates, unavailable tickers, network problems.

---

### Export Functionality

Support: CSV, Excel, PDF report.

The PDF contains: portfolio overview, statistics, optimization results, efficient frontier, drawdown analysis, correlation matrix, scenario analysis.

Produce a professional report suitable for investors.

---

### Save and Load

Support JSON portfolios. Save: tickers, weights, benchmark, analysis settings.

---

### Logging and Error Handling

Implement logging, exception handling and user-friendly error messages.

Examples: ticker not found, insufficient data, no internet connection.

---

### Bonus Features

If straightforward to implement:

- **Rebalancing Advisor** — advises how to return to target weights
- **Dividend Analysis** — show dividend yield, dividend income, dividend growth
- **Portfolio Health Score** — score from 0–100 based on diversification, risk, concentration, drawdown and Sharpe ratio

---

### Code Quality

Requirements: type hints, dataclasses, PEP8, modular architecture, unit tests, logging, documentation.

Deliver: `requirements.txt`, `README.md`, installation guide.

---

### Expected Output

Deliver a fully working application. Generate: the full project structure, all source code, tests, `requirements.txt`, `README.md`, installation instructions.

Work step by step:

1. Design architecture
2. Create project structure
3. Build data layer
4. Build analytics engine
5. Build optimization engine
6. Build GUI
7. Add visualizations
8. Add export functionality
9. Add tests
10. Deliver complete working application

---

## Decision log
*Record architectural choices and deviations from the spec here, with a one-line reason.*

- Theme file lives at `ui/theme.py` (not `utils/theme.py`) — it imports PySide6 so belongs in the UI layer.
- Black-Litterman implemented via manual equilibrium formula π = δΣw (PyPortfolioOpt 1.6.0 requires views; without views BL = market prior).
- `requirements.txt` uses `>=` minimum bounds instead of exact pins — Python 3.14.5 is newer than the originally planned 3.12, so exact pins for PySide6 6.7.2 etc. were unavailable; installed: PySide6 6.11.1, pandas 3.0.3, numpy 2.4.6.

## Session log
*One short line per working session: date, phase touched, what got finished.*

- 2026-06-08: Phase 1 — full scaffold created, all imports verified, pytest harness working.
- 2026-06-08: Phase 2 — Asset, Portfolio, AnalysisSettings, AnalysisResult dataclasses + validators, 58 tests passing.
- 2026-06-08: Phase 3 — PriceCache, DataService (retry + alignment), portfolio JSON I/O, 91 tests passing.
- 2026-06-08: Phase 4 — returns, risk, diversification analytics (pure functions), conftest fixtures, 166 tests passing.
- 2026-06-08: Phase 5 — Max Sharpe, Min Variance, Black-Litterman optimizers + frontier sampler, 196 tests passing.
- 2026-06-08: Phase 6 — growth, frontier, drawdown, rolling vol, risk contribution, correlation charts; 223 tests passing.
- 2026-06-08: Phase 7 — full Dashboard Tab: AnalysisWorker thread, MetricCard/ChartCanvas widgets, all sections wired, 400 ms auto-refresh; 223 tests passing.
- 2026-06-08: Phase 8 — all 5 tabs functional; analytics/scenario.py + analytics/monte_carlo.py; analysis_ready signal wired to all tabs; 223 tests passing.
- 2026-06-08: Phase 9 — CSV/Excel/PDF exporters + Export menu in MainWindow; all exports smoke-tested; 223 tests passing.
- 2026-06-08: Phase 10 — test_scenario (18), test_monte_carlo (16), test_exports (21), test_health_score (32); analytics/health_score.py; README.md; 311 tests passing.
