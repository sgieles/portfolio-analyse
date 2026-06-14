# build_plan.md — Build Roadmap & Progress Tracker

> **How to use this file (read every session):**
> 1. Check **Current status** below to see where you left off.
> 2. Work only on the current step. Keep the app runnable after each step.
> 3. Tick a checkbox `[x]` the moment a task is genuinely done (code written *and* sanity-checked).
> 4. After finishing a step, update **Current status** and add a line to the **Decision log** / **Session log** if anything noteworthy happened.
> 5. Honour the layering and domain conventions in `CLAUDE.md`. The full feature spec is the **Specification reference** section at the bottom of this file.

---

## Current status

- **Phase:** 12 — Dashboard UI Migration ✅ Complete
- **Next step:** Phase 12B — Asset Analysis page (sortable table, all per-asset metrics)
- **Last updated:** 2026-06-14
- **Notes:** All Phase 12 sections shipped: KPI strip (7 metrics), growth chart with 1M/3M/6M/YTD/1Y/All period filter, weight donut + sector donut (yfinance info, cached 1h), full metrics detail (all 13 metrics across Return/Risk/Diversification), correlation heatmap (Plotly, hover values), optimization panel (weights table + metrics table + apply-weights buttons for 3 methods), scenario analysis, drawdown + rolling vol, risk/return contribution charts.

---

## Phase index

| # | Phase | Status |
|---|-------|--------|
| 1 | Architecture & project scaffold | ✅ Done |
| 2 | Models | ✅ Done |
| 3 | Data layer | ✅ Done |
| 4 | Analytics engine | ✅ Done |
| 5 | Optimization engine | ✅ Done |
| 6 | Charts (pure draw functions) | ✅ Done |
| 7 | GUI: Tab 1 Portfolio Dashboard | ✅ Done |
| 8 | GUI: remaining tabs | ✅ Done |
| 9 | Export & persistence | ✅ Done |
| 10 | Tests, docs, polish, bonus | ✅ Done |
| 11 | Streamlit Architecture & Integration | ✅ Done |
| 12 | Dashboard UI Migration | ✅ Done |
| 12B | Asset Analysis Page | ⬜ |
| 13 | Monte Carlo Page Migration | ⬜ |
| 14 | Streamlit Production Readiness | ⬜ |
| 15 | Mobile Deployment & Hosting | ⬜ |
| 16 | Research Foundation & Data Layer | ⬜ |
| 17 | Research Hub & Stock Screener | ⬜ |
| 18 | Stock Fundamentals Engine | ⬜ |
| 19 | Valuation Engine | ⬜ |
| 20 | Insider Activity & Sector Intelligence | ⬜ |
| 21 | Research Dashboard & Investment Thesis | ⬜ |
| 22 | ETF Research Module | ⬜ |
| 23 | Commodities Research Module | ⬜ |

---

## Open questions / decisions to make

> *Resolve these before starting the relevant phase, then move the resolution to the Decision log.*

_All currently-known open questions have been resolved (see Decision log, 2026-06-14). Add new items here as they surface._

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

## Phase 11 — Streamlit Architecture & Integration

*Goal: replace the PySide6 presentation layer with a modern Streamlit frontend while preserving all existing analytics, optimization, export and test functionality.*

- [x] Create new folder structure: streamlit_app/ with app.py, pages/, components/, state/, styles/, assets/
- [x] Add Streamlit + Plotly dependencies
- [x] Create Streamlit application shell (streamlit_app/app.py)
- [x] Create dark theme (streamlit_app/styles/theme.py)
- [x] Integrate existing modules: services, analytics, optimization
- [x] Implement Streamlit Session State management (streamlit_app/state/session.py)
- [x] Create navigation: Dashboard, Asset Analysis, Monte Carlo

**Done when:** Streamlit launches successfully and can load an existing portfolio while reusing the current analytics engine.

## Phase 12 — Dashboard UI Migration
*Goal: rebuild the Portfolio Dashboard using the uploaded dashboard mockup as the visual reference.*

### Section A — Portfolio Construction

- [x] Portfolio Builder sidebar
- [x] Add ticker
- [x] Remove ticker
- [x] Weight sliders
- [x] Normalize weights
- [x] Equal Weight
- [x] Save Portfolio
- [x] Load Portfolio
- [x] Benchmark selector
- [x] Analysis period selector

**Visual target:** Construction panel from mockup.

**Done when:** allocation changes immediately refresh portfolio analytics.

### Section B — Portfolio Statistics

- [x] Expected Return
- [x] CAGR
- [x] Annualized Return
- [x] Volatility
- [x] Sharpe Ratio
- [x] Sortino Ratio
- [x] Beta
- [x] Maximum Drawdown
- [x] VaR 95%
- [x] VaR 99%
- [x] CVaR
- [x] Diversification Score
- [x] Portfolio Health Score

**Visual target:** KPI cards from mockup.

**Done when:** all metrics update automatically after portfolio changes.

### Section C — Performance Visualization

Reuse existing analytics and chart logic.

- [x] Portfolio vs Benchmark chart
- [x] Benchmark visibility toggle
- [x] Time period selector:
  - 1M
  - 3M
  - 6M
  - YTD
  - 1Y
  - All

**Visual target:** Performance card from mockup.

**Technology:** Plotly

**Done when:** chart behaves similarly to the uploaded mockup.

### Section D — Allocation Analysis

- [x] Sector allocation view (yfinance info, cached 1h)
- [x] Portfolio weight donut view
- [ ] Region allocation view (deferred — yfinance does not expose region reliably)

**Visual target:** Allocation panel from mockup.

**Done when:** users can inspect portfolio exposure by sector and region.

### Section E — Efficient Frontier

Reuse:

- optimization/efficient_frontier.py

Display:

- [x] Current Portfolio
- [x] Maximum Sharpe Portfolio
- [x] Minimum Variance Portfolio
- [x] Black-Litterman Portfolio

**Visual target:** Efficient Frontier chart from mockup.

**Done when:** users can compare portfolio positioning interactively.

### Section F — Optimization Panel

Reuse:

- optimization/optimizers.py

Display:

- [x] Current vs Optimized Weights
- [x] Current vs Optimized Metrics
- [x] Preview Optimized Portfolio
- [x] Apply Optimized Weights

Optimization methods:

- [x] Maximum Sharpe
- [x] Minimum Variance
- [x] Black-Litterman

**Visual target:** Optimization card from mockup.

**Done when:** optimized allocations can be applied and refresh the dashboard immediately.

### Section G — Correlation Matrix

Reuse:

- correlation analytics
- existing correlation calculations

Display:

- [x] Correlation heatmap
- [x] Hover values
- [x] Color scale legend

**Visual target:** Correlation Matrix card from mockup.

**Done when:** users can easily identify concentration and correlation risk.

### Section H — Drawdown Analysis

Reuse:

- charts/drawdown.py

Display:

- [x] Historical drawdown chart
- [x] Maximum drawdown marker
- [ ] Recovery period visualization (deferred)

**Visual target:** Drawdown chart from mockup.

**Done when:** drawdown history is clearly visible.

### Section I — Rolling Volatility

Reuse:

- charts/rolling_vol.py

Display:

- [x] Rolling volatility chart
- [x] Average volatility marker

**Visual target:** Rolling Volatility chart from mockup.

**Done when:** users can inspect risk changes through time.

### Section J — Scenario Analysis

*Folded into the Dashboard, per decision 2026-06-14.*

Reuse:

- analytics/scenario.py

Display:

- [x] Bull Market +15%
- [x] Mild Recession −10%
- [x] Recession −20%
- [x] Severe Crash −35%
- [x] Impact table: portfolio value, expected return, volatility
- [x] Scenario impact chart

Uses historical betas and stressed correlations.

**Done when:** stress-test scenarios refresh together with the rest of the Dashboard.

## Phase 12B — Asset Analysis Page
*Goal: rebuild the per-asset analysis as its own Streamlit page (per decision 2026-06-14).*

Reuse:

- analytics/* (per-asset metrics)
- existing asset-level calculations

Display a sortable table:

| Ticker | Weight | CAGR | Return | Volatility | Sharpe | Beta | Max Drawdown | VaR95 |
|--------|--------|-----:|-------:|-----------:|-------:|-----:|-------------:|------:|

- [ ] Sortable on all columns
- [ ] Latest price
- [ ] Correlation with benchmark
- [ ] Dividend yield where available
- [ ] Risk contribution per asset
- [ ] Return contribution per asset

**Technology:** Plotly + Streamlit dataframe.

**Done when:** the Asset Analysis page reads from shared analysis results and sorts on every column.

## Phase 13 — Monte Carlo Page Migration

*Goal: replace the existing Monte Carlo tab with a dedicated Streamlit page.*

Reuse:

- analytics/monte_carlo.py

- [ ] Simulation controls
- [ ] Horizon selector
- [ ] Number of simulations selector
- [ ] Confidence interval display
- [ ] Median path
- [ ] Sample simulation paths
- [ ] Ending-value distribution

**Visual target:** Monte Carlo screen from mockup.

**Done when:** Monte Carlo analysis is fully interactive within Streamlit.

## Phase 14 — Streamlit Production Readiness

*Goal: make the Streamlit version the primary application interface.*

> Scope (2026-06-14): Phase 14 covers **desktop/tablet** responsiveness and production polish. All **mobile** layout + hosting lives in Phase 15.

- [ ] Responsive layout (desktop / tablet)
- [ ] Streamlit caching
- [ ] Consistent dashboard styling
- [ ] Loading indicators
- [ ] User-friendly error handling
- [ ] Integrate existing exports:
  - CSV
  - Excel
  - PDF
- [ ] Performance profiling
- [ ] Update README
- [ ] Add Streamlit installation instructions
- [ ] Add migration documentation

**Done when:** the Streamlit dashboard fully replaces the PySide6 interface and all existing functionality remains available.

### Streamlit Migration Decision

#### Preserve Existing Modules

Keep unchanged:

```text
analytics/
optimization/
services/
reports/
models/
tests/
utils/
```

These modules are considered production-ready and remain the single source of truth for all calculations.

#### Replace Presentation Layer

Replace:

```text
ui/
main.py
PySide6 widgets
Qt threading
```

with:

```text
streamlit_app/
Plotly charts
Streamlit Session State
Streamlit caching
```

#### Migration Principles

- Preserve existing analytics logic.
- Preserve existing optimization logic.
- Preserve existing export functionality.
- Preserve existing test coverage.
- Reuse existing portfolio calculations wherever possible.
- Minimize business logic changes.
- Focus migration effort on the presentation layer only.
- Match the uploaded dashboard mockup as closely as possible.
- Prefer Plotly over Matplotlib for interactive dashboard visualizations.
- Maintain fast recalculation performance using Streamlit caching.

## Phase 15 — Mobile Deployment & Hosting

*Goal: make the application accessible from desktop, tablet and mobile devices using a single codebase.*

### Deployment Strategy

Primary deployment target:

```text
GitHub Repository
        ↓
Streamlit Community Cloud
        ↓
https://app.streamlit.app
        ↓
Desktop / Tablet / Mobile
```

The application must remain fully browser-based.

Users can install the application on iPhone and Android using:

- Safari → Add to Home Screen
- Chrome → Add to Home Screen

No native mobile application is required.

### Mobile UI

- [ ] Responsive layout
- [ ] Mobile KPI cards
- [ ] Mobile navigation
- [ ] Mobile-friendly charts
- [ ] Touch-friendly controls
- [ ] Responsive tables

> Note: the screener's mobile/responsive treatment is handled in Phase 17 (where the screener is built), not here.

### Hosting

- [ ] GitHub repository deployment
- [ ] Streamlit Community Cloud deployment
- [ ] Automatic deployment from GitHub
- [ ] Deployment documentation

### Documentation

- [ ] iPhone installation guide
- [ ] Android installation guide
- [ ] Deployment guide

### Done when

The application works comfortably on:

- Desktop
- Tablet
- iPhone
- Android

using a single hosted Streamlit deployment.

## Phase 16 — Research Foundation & Data Layer

*Goal: transform the application from a portfolio analysis tool into a complete investment research platform.*

> **Decision needed before Phase 18:** choose a research data source (see *Open questions*).

### New Application Structure

```text
Application
├── Research Hub      ← start screen
└── Portfolio Hub     (includes Monitoring)
```

Research Hub becomes the primary application entry point. **Two hubs only** — Monitoring lives inside Portfolio Hub (decision 2026-06-14).

**Navigation rollout (interim flat → hub-based):** Phases 11–13 ship a flat Portfolio Hub nav (Dashboard / Asset Analysis / Monte Carlo). The two-hub shell is introduced **here in Phase 16**: a hub-level switcher wrapping the existing Portfolio Hub pages, with the Research Hub added as the second hub. The default landing stays the Dashboard until the Research Hub has content; the entry-point switch to Research Hub happens in **Phase 17**.

- [ ] Two-hub navigation shell (Research Hub / Portfolio Hub switcher)
- [ ] Move existing Streamlit pages under Portfolio Hub

Portfolio Hub remains focused on:

- Portfolio Construction
- Optimization
- Scenario Analysis
- Monte Carlo
- Monitoring

### Research Workflow

```text
Research Hub
    ↓
Asset Analysis
    ↓
Investment Thesis
    ↓
Watchlist
    ↓
Portfolio Construction
    ↓
Optimization
```

### Research Data Source (open-source)

**Primary source: SEC EDGAR** — `https://data.sec.gov` — free, public, **no API key**.

Access rules:
- Mandatory `User-Agent` header, format `"AppName contact@email"` (requests without it return 403).
- Max **10 requests/second** across all `*.sec.gov` domains (target ~8/s); no daily limit.
- Cache `companyfacts.json` ≥ 24h — it only changes when a new filing is submitted (fits the existing research caching layer).

Key endpoints:
- `https://www.sec.gov/files/company_tickers.json` — ticker ⇄ CIK mapping (build once, cache).
- `https://data.sec.gov/api/xbrl/companyfacts/CIK##########.json` — every XBRL-tagged fact a company ever filed (revenue, EPS, assets, margins, debt, shares, etc.) → fundamentals (Phase 18) + relative-valuation inputs (Phase 19).
- `https://data.sec.gov/api/xbrl/companyconcept/CIK##########/us-gaap/<Concept>.json` — single concept across all periods (faster for one metric).
- `https://data.sec.gov/api/xbrl/frames/...` — one concept across all companies for a period (peer comparison).
- `https://data.sec.gov/submissions/CIK##########.json` — filing history incl. Forms 3/4/5 → insider activity (Phase 20).

Implementation notes:
- Call directly via `requests`/`httpx` (no Python-version constraint — works on the current 3.14.x). Avoid the OpenBB aggregator for now: it only supports Python 3.9–3.12.
- Concept names vary per company (us-gaap synonyms); when a tag is missing, fall back to the company's `companyfacts.json` to discover the actual tag used.
- **Refresh strategy:** populate the research caching layer with a **nightly batch job**, never on screener load. Fetching S&P 500 + Nasdaq 100 fundamentals is ~600 unique CompanyFacts calls; at ~8 req/s that is a background job, so the screener always reads from cache and the cache refreshes overnight. Store a per-CIK `last_filed`/`last_refreshed` timestamp so the job can skip unchanged companies.

**Coverage gaps:**
- EDGAR is **US-only**. STOXX Europe 600 / AEX fundamentals come from **yfinance** (`.financials`, `.balance_sheet`, `.cashflow`, `.info`) — free and EU-ticker coverage, but quality is inconsistent and not official; validate/clean on ingest. *(resolved 2026-06-14)*
- ESEF via `filings.xbrl.org` (open, official, IFRS-tagged, annual-only) is kept as a possible future upgrade if yfinance coverage proves too thin.
- **Macro** (Phase 20) is not in EDGAR — use the **ECB Data Portal** (SDMX REST API at `data-api.ecb.europa.eu`, free, no key). *(resolved 2026-06-14)*

### Research Data Layer

- [ ] Financial statement ingestion
- [ ] Quarterly financial storage
- [ ] Annual financial storage
- [ ] Sector mapping
- [ ] Industry mapping
- [ ] Insider transaction ingestion
- [ ] Sector intelligence ingestion
- [ ] Macroeconomic data ingestion
- [ ] Research caching layer (nightly batch refresh — see *Research Data Source* refresh strategy)

### Watchlists

- [ ] Create watchlist
- [ ] Add asset
- [ ] Remove asset
- [ ] Save watchlist
- [ ] Score watchlist

### Done when

Research data is available independently from portfolio analytics.

## Phase 17 — Research Hub & Stock Screener

*Goal: create a screener that identifies attractive investment candidates.*

### Asset Universe

#### Stocks

- [ ] S&P 500
- [ ] Nasdaq 100
- [ ] STOXX Europe 600
- [ ] AEX

### Research Screener

Display:

| Asset | Sector | Overall | Fundamentals | Valuation | Sector Score | Insider | Trend |
|-------|--------|--------:|-------------:|----------:|-------------:|--------:|------:|

### Filters

- [ ] Overall Score
- [ ] Sector
- [ ] Country
- [ ] Market Cap
- [ ] Dividend Yield
- [ ] Growth
- [ ] Valuation
- [ ] Insider Activity

### Navigation

- [ ] Switch the default landing / entry point to the Research Hub (per decision 2026-06-14)
- [ ] Click asset → Asset Detail Page

### Responsive

- [ ] Responsive / mobile-friendly screener table (moved here from Phase 15)

### Done when

Users can quickly discover interesting investment opportunities.

## Phase 18 — Stock Fundamentals Engine

*Goal: evaluate company quality through growth, profitability, balance sheet strength and sector outperformance.*

### Fundamental Score Components

#### Growth

- [ ] Revenue Growth
- [ ] EPS Growth
- [ ] Free Cash Flow Growth

#### Profitability

- [ ] Gross Margin
- [ ] Operating Margin
- [ ] Net Margin

#### Capital Efficiency

- [ ] ROIC
- [ ] ROE
- [ ] ROA

#### Balance Sheet

- [ ] Debt / Equity
- [ ] Interest Coverage
- [ ] Current Ratio

### Long-Term Trend Analysis

#### Annual Trends

- [ ] Revenue
- [ ] EPS
- [ ] Free Cash Flow
- [ ] Margins
- [ ] ROIC
- [ ] Debt

Support:

- [ ] 5 Year View
- [ ] 10 Year View

#### Quarterly Trends

- [ ] Revenue
- [ ] EPS
- [ ] Margins
- [ ] Free Cash Flow

Purpose:

- Detect acceleration
- Detect deceleration
- Detect turnarounds
- Detect margin compression

### Peer Comparison

Compare against:

- [ ] Sector
- [ ] Industry
- [ ] Top Quartile Companies

### Explainability

Display:

Strengths

Weaknesses

Drivers behind the score

### Done when

Users understand both the score and the underlying financial trends.

## Phase 19 — Valuation Engine

*Goal: determine whether a company is undervalued or overvalued.*

### Relative Valuation

- [ ] P/E
- [ ] Forward P/E
- [ ] EV/EBITDA
- [ ] EV/Sales
- [ ] Price/Sales
- [ ] Price/Book
- [ ] Free Cash Flow Yield

Compare against:

- [ ] Historical Average
- [ ] Sector
- [ ] Industry
- [ ] Broad Market

### Intrinsic Valuation

#### DCF

- [ ] Growth assumptions
- [ ] Discount rate
- [ ] Terminal value

Output:

- [ ] Fair Value
- [ ] Current Price
- [ ] Margin of Safety

### Explainability

Display reasons for score.

### Done when

Users understand valuation attractiveness and valuation risks.

## Phase 20 — Insider Activity & Sector Intelligence

*Goal: understand management conviction and sector attractiveness.*

### Insider Activity

#### Buy Side

- [ ] CEO Purchases
- [ ] CFO Purchases
- [ ] Executive Purchases
- [ ] Director Purchases

#### Sell Side

- [ ] CEO Sales
- [ ] CFO Sales
- [ ] Executive Sales
- [ ] Director Sales

#### Time Horizons

- [ ] 3 Months
- [ ] 6 Months
- [ ] 12 Months

#### Weighting

CEO > CFO > Executive > Director

### Sector Intelligence

#### Sector KPI Dashboard

- [ ] Sector Growth
- [ ] Margin Trends
- [ ] ROIC Trends
- [ ] Valuation Trends

#### Sector Momentum

- [ ] 3 Month
- [ ] 6 Month
- [ ] 12 Month

#### Relative Strength

- [ ] vs S&P 500
- [ ] vs World Index

### PESTLE Analysis

Generate concise:

- [ ] Political
- [ ] Economic
- [ ] Social
- [ ] Technological
- [ ] Legal
- [ ] Environmental

### SWOT Analysis

Generate concise:

- [ ] Strengths
- [ ] Weaknesses
- [ ] Opportunities
- [ ] Threats

### Sector Outlook

- [ ] Bullish
- [ ] Neutral
- [ ] Bearish

with supporting rationale.

### Done when

Users understand both company quality and sector attractiveness.

## Phase 21 — Research Dashboard & Investment Thesis

*Goal: create an institutional-quality equity research report.*

### KPI Header

- [ ] Overall Score
- [ ] Fundamental Score
- [ ] Valuation Score
- [ ] Sector Score
- [ ] Insider Score
- [ ] Technical Score

### Research Report Layout

1. Investment Thesis
2. Fundamentals
3. Valuation
4. Insider Activity
5. Sector Intelligence
6. Macro Environment
7. Technical Context
8. Risk Factors
9. Final Assessment

### AI-Assisted Investment Thesis

Generate a concise explanation of:

- Company quality
- Sector attractiveness
- Valuation
- Risks
- Overall conclusion

### Done when

Each stock has a complete research report understandable within five minutes.

## Phase 22 — ETF Research Module

*Goal: extend the research workflow to ETFs after stock research is complete.*

- [ ] Holdings Analysis
- [ ] Sector Exposure
- [ ] Geographic Exposure
- [ ] Expense Ratio
- [ ] Tracking Error
- [ ] Diversification Analysis
- [ ] Concentration Risk
- [ ] Factor Exposure
- [ ] ETF Scoring

### Done when

ETFs can be researched using the same workflow as stocks.

## Phase 23 — Commodities Research Module

*Goal: extend the research workflow to commodities after stock and ETF research are complete.*

- [ ] Commodity Scoring
- [ ] Supply & Demand Analysis
- [ ] Inventory Trends
- [ ] Inflation Sensitivity
- [ ] Interest Rate Sensitivity
- [ ] Economic Growth Sensitivity
- [ ] Currency Sensitivity
- [ ] Relative Strength
- [ ] Momentum

### Done when

Commodities can be analyzed through the same research workflow as stocks and ETFs.

---

## Specification reference v2 (full feature spec)

> **Status note (2026-06-14):** This is the **v2 specification**. It supersedes and retires the original PySide6 v1 desktop spec (preserved in git history). It describes the browser-based Streamlit research + portfolio platform that Phases 11–23 implement. The analytics, risk, optimization, scenario and Monte Carlo requirements are carried over from v1 unchanged — those formulas remain authoritative; only the presentation, architecture, data and deployment layers are new.

*This is the complete, authoritative feature specification. The phases above implement it; consult this section for exact requirements per page, metric and behaviour.*

Build a professional, browser-based investment **research and portfolio analysis platform** in Python. It must let users (1) discover and research individual assets, and (2) assemble, analyse and optimise portfolios — based on historical market data and company fundamentals.

### Goal

The application is split into two top-level hubs:

- **Research Hub** — the start screen. Discover, screen, score and research individual assets (stocks first, then ETFs and commodities). Output an investment thesis and feed candidates into watchlists.
- **Portfolio Hub** — assemble a portfolio from researched assets, then run risk, return, optimisation, scenario and Monte Carlo analyses. Includes monitoring.

The platform runs in the browser, is hosted on Streamlit Community Cloud, and is usable on desktop, tablet and mobile (add-to-home-screen, no native app).

---

### Architecture

- **Presentation:** Streamlit + Plotly. Streamlit Session State for app state; Streamlit caching for fast recalculation.
- **Preserved engines (single source of truth, unchanged):** `analytics/`, `optimization/`, `services/`, `reports/`, `models/`, `utils/`, `tests/`. The migration touches the presentation layer only.
- **Navigation:** two-hub shell (Research Hub / Portfolio Hub switcher). Research Hub is the default landing page once it has content.
- **Retired:** `ui/` (PySide6 widgets), `main.py` (Qt entry point), Qt threading, matplotlib/seaborn for interactive dashboards (matplotlib retained only inside the PDF report).

```
project/
├── streamlit_app/        # app.py, pages/, components/, state/, styles/, assets/
├── services/             # data + research ingestion, caching, IO
├── analytics/            # returns, risk, diversification, scenario, monte_carlo, health_score
├── optimization/         # optimizers, efficient_frontier
├── research/             # fundamentals, valuation, insider, sector intelligence, scoring
├── charts/               # (legacy matplotlib for PDF only)
├── models/
├── utils/
├── reports/              # csv, excel, pdf
└── tests/
```

---

### Data Sources

- **Prices:** Yahoo Finance via `yfinance` — Adjusted Close, dividend-adjusted returns. Stocks and ETFs.
- **US fundamentals + insider:** SEC EDGAR (`data.sec.gov`) — XBRL CompanyFacts for fundamentals, Forms 3/4/5 for insider. Free, no key, 10 req/s, `User-Agent` required.
- **European fundamentals:** `yfinance` (`.financials`, `.balance_sheet`, `.cashflow`, `.info`) for STOXX 600 / AEX — free, inconsistent quality, validated on ingest. (ESEF via `filings.xbrl.org` is a future upgrade.)
- **Macro:** ECB Data Portal (SDMX REST API, `data-api.ecb.europa.eu`) — free, no key.
- **Caching:** all research data is populated by a **nightly batch refresh** into a research caching layer; the UI reads from cache, never live on screener load.

Account for: missing data, different start dates, unavailable tickers, network problems. Implement local caching, retry with backoff, and user-friendly error handling.

---

### General Design Principles

- Professional, modern, dark-mode-default UI matching the dashboard mockup.
- Dashboard-first within each hub: key insights visible without many clicks.
- Fast recalculations via caching.
- Clear separation between data, analytics and presentation.
- Suitable for both beginners and advanced investors.
- Comparable in feel to Bloomberg, Morningstar Direct, Portfolio Visualizer or FactSet.

---

## RESEARCH HUB (start screen)

### Screener

Asset universes: **S&P 500, Nasdaq 100, STOXX Europe 600, AEX**.

Display a scored table:

| Asset | Sector | Overall | Fundamentals | Valuation | Sector Score | Insider | Trend |

Filters: Overall Score, Sector, Country, Market Cap, Dividend Yield, Growth, Valuation, Insider Activity. Clicking an asset opens its Asset Detail page. Screener must be responsive / mobile-friendly.

### Fundamentals Engine

Score company quality across:

- **Growth:** revenue growth, EPS growth, free cash flow growth.
- **Profitability:** gross / operating / net margin.
- **Capital efficiency:** ROIC, ROE, ROA.
- **Balance sheet:** debt/equity, interest coverage, current ratio.

Trend analysis: annual (5y / 10y) and quarterly for revenue, EPS, FCF, margins, ROIC, debt — to detect acceleration, deceleration, turnarounds and margin compression. Peer comparison vs sector, industry and top-quartile companies. Explainability: surface strengths, weaknesses and the drivers behind the score.

### Valuation Engine

- **Relative:** P/E, forward P/E, EV/EBITDA, EV/Sales, P/S, P/B, FCF yield — compared against historical average, sector, industry and the broad market.
- **Intrinsic (DCF):** growth assumptions, discount rate, terminal value → fair value, current price, margin of safety.
- Explainability: reasons behind the valuation score and the valuation risks.

### Insider Activity & Sector Intelligence

- **Insider:** buy/sell by CEO, CFO, executives, directors over 3 / 6 / 12 months, weighted CEO > CFO > Executive > Director.
- **Sector intelligence:** sector KPI dashboard (growth, margins, ROIC, valuation trends), momentum (3/6/12m), relative strength vs S&P 500 and a world index.
- **PESTLE** and **SWOT** summaries, and a sector outlook (bullish / neutral / bearish) with rationale.

### Research Report & Investment Thesis

Per asset, a KPI header (Overall, Fundamental, Valuation, Sector, Insider, Technical scores) and a report: investment thesis, fundamentals, valuation, insider activity, sector intelligence, macro environment, technical context, risk factors, final assessment. An AI-assisted thesis concisely covers company quality, sector attractiveness, valuation, risks and an overall conclusion. Target: understandable within five minutes.

### Watchlists

Create, add/remove assets, save, and score a watchlist. Watchlists feed portfolio construction.

### ETF & Commodity Research (later phases)

ETFs: holdings, sector/geographic exposure, expense ratio, tracking error, diversification, concentration risk, factor exposure, scoring. Commodities: scoring, supply/demand, inventory trends, inflation / rate / growth / currency sensitivity, relative strength, momentum. Same research workflow as stocks.

---

## PORTFOLIO HUB

The Portfolio Dashboard is the primary workspace. It must surface construction, statistics, optimisation and all primary visualisations together, so allocation changes immediately update both numbers and charts.

### Page: Dashboard

#### Construction

Add / remove asset, adjust weight (sliders), Equal Weight, Normalize, Save / Load (JSON). Benchmark selector (`SPY`, `VTI`, `ACWI`). Analysis period (1y, 3y, 5y, 10y, Max). Default: equal weighting.

#### Statistics (KPI cards)

- **Return:** Expected Return, CAGR, Annualized Return.
- **Risk:** Volatility, Sharpe, Sortino, Beta, Maximum Drawdown, VaR 95%, VaR 99%, CVaR.
- **Diversification:** number of assets, average correlation, diversification score.
- **Portfolio Health Score** (0–100).

Clear colour coding.

#### Optimization

- **Maximum Sharpe** — maximise `(Expected Return − Risk Free Rate) / Volatility`.
- **Minimum Variance** — minimise portfolio variance.
- **Black-Litterman** — PyPortfolioOpt, for more stable, realistic allocations.

Show current-vs-optimized weights and current-vs-optimized metrics (Return, Volatility, Sharpe, Beta, VaR, Drawdown). Buttons: Preview Optimized Portfolio, Apply Optimized Weights. Applying refreshes all statistics and charts.

#### Visualizations (Plotly, on the Dashboard)

1. **Portfolio Growth** — portfolio vs benchmark from €10,000; outperformance immediately visible. Time-period selector (1M, 6M, YTD, 1Y, 5Y), benchmark visibility toggle.
2. **Efficient Frontier** — current, Max Sharpe, Min Variance and Black-Litterman portfolios. X = risk, Y = expected return.
3. **Allocation Analysis** — sector and region exposure with a toggle.
4. **Correlation Matrix** — heatmap with hover values and colour legend.
5. **Drawdown** — historical drawdowns with the largest drawdown marker and recovery periods.
6. **Rolling Volatility** — 12-month rolling volatility with an average marker.

#### Scenario Analysis (folded into the Dashboard)

Stress tests: Bull +15%, Mild Recession −10%, Recession −20%, Severe Crash −35%, using historical betas and stressed correlations. Impact on portfolio value, expected return and volatility — table and chart. Refreshes with the rest of the Dashboard.

### Page: Asset Analysis

Sortable per-asset table (sortable on all columns):

| Ticker | Weight | CAGR | Return | Volatility | Sharpe | Beta | Max Drawdown | VaR95 |

Plus latest price, correlation with benchmark, dividend yield where available, and risk/return contribution per asset.

### Page: Monte Carlo

Defaults: 1,000 simulations, 5-year horizon. Configurable simulations (100–10,000) and horizon (1–30y). Show median, mean, 5th and 95th percentile ending values and probability of loss. Visualise sample paths, ending-value distribution and confidence intervals.

### Monitoring

Track an existing portfolio over time (within Portfolio Hub).

---

### Expected Return

Compute three estimates and show all three; use the historical average annualized return as the optimisation default (configurable):

1. Historical CAGR.
2. Historical average annualized return.
3. CAPM: `Risk Free Rate + Beta × (Market Return − Risk Free Rate)`, using the chosen benchmark. Risk Free Rate and Market Expected Return are configurable.

### Risk Calculations

Use daily returns. Volatility = annualized std dev. Sharpe (configurable RF rate). Sortino (downside deviation). Beta vs chosen benchmark. Maximum Drawdown (full history). Historical VaR 95% and 99%. CVaR (expected shortfall).

---

### Export

CSV, Excel and a professional PDF report. The PDF contains: portfolio overview, statistics, optimisation results, efficient frontier, drawdown analysis, correlation matrix and scenario analysis. Reuse the existing `reports/` exporters.

### Save and Load

JSON portfolios storing tickers, weights, benchmark and analysis settings.

### Logging and Error Handling

Logging, exception handling and user-friendly messages (ticker not found, insufficient data, no internet connection, stale/empty research cache).

### Deployment

GitHub repository → Streamlit Community Cloud → single hosted URL. Installable on iPhone (Safari → Add to Home Screen) and Android (Chrome → Add to Home Screen). No native app. Responsive on desktop, tablet and mobile.

### Code Quality

Type hints, dataclasses, PEP8, modular architecture, unit tests, logging, documentation. Deliver `requirements.txt`, `README.md`, installation + deployment guides, and migration documentation.

---

### Bonus Features

If straightforward: Rebalancing Advisor (how to return to target weights), Dividend Analysis (yield, income, growth). Portfolio Health Score is already in scope above.

---

## Decision log
*Record architectural choices and deviations from the spec here, with a one-line reason.*

- Streamlit selected as the new presentation layer; existing analytics, optimization, export and test layers remain unchanged to minimize migration risk and maximize code reuse.
- Black-Litterman implemented via manual equilibrium formula π = δΣw (PyPortfolioOpt 1.6.0 requires views; without views BL = market prior).
- `requirements.txt` uses `>=` minimum bounds instead of exact pins — Python 3.14.5 is newer than the originally planned 3.12, so exact pins for PySide6 6.7.2 etc. were unavailable; installed: PySide6 6.11.1, pandas 3.0.3, numpy 2.4.6.
- Research Hub introduced as the primary application entry point. Portfolio Hub remains focused on portfolio construction, optimization and monitoring.
- Application split into **two top-level hubs** (2026-06-14): Research Hub (start screen) and Portfolio Hub; Monitoring folded into Portfolio Hub rather than a separate hub.
- Hub rollout sequence (2026-06-14): build Portfolio Hub flat first (Phases 11–13), introduce the two-hub navigation shell in Phase 16, and switch the default entry point to the Research Hub in Phase 17 once it has content.
- Research implementation order: Stocks → ETFs → Commodities.
- Fundamental analysis includes annual and quarterly trend analysis, peer comparison, sector comparison and score explainability.
- Sector Intelligence includes KPI analysis, momentum analysis, relative strength, PESTLE analysis and SWOT analysis.
- Primary research data source = **SEC EDGAR** (`data.sec.gov`): open-source, free, no API key, 10 req/s, fundamentals via XBRL CompanyFacts + insider via Forms 3/4/5. Called directly (requests/httpx) rather than via OpenBB, which is capped at Python 3.9–3.12. European fundamentals and macro deferred to a secondary source (FRED/ECB).
- Streamlit page layout (2026-06-14): Asset Analysis = its own page (Phase 12B); Scenario Analysis = folded into the Dashboard (Phase 12, Section J); Monte Carlo = its own page (Phase 13).
- Macro data source = **ECB Data Portal** (SDMX, free, no key) — chosen over FRED to avoid a US-centric macro lens for a partly-European asset universe.
- Mobile deployment strategy selected: GitHub + Streamlit Community Cloud + Add-to-Home-Screen on iOS and Android.
- European fundamentals source = **yfinance** (2026-06-14): free and covers EU tickers; quality is inconsistent so data is validated/cleaned on ingest. ESEF via `filings.xbrl.org` kept as a future upgrade path.
- Phase 14 / 15 boundary (2026-06-14): Phase 14 = responsive desktop/tablet + production polish; Phase 15 = mobile layout + hosting only. Screener responsive treatment moved to Phase 17.
- Specification reference rewritten to **v2** (2026-06-14): describes the Streamlit two-hub research + portfolio platform; the original PySide6 v1 spec is retired (preserved in git history).

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