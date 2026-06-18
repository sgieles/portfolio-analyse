# build_plan.md — Build Roadmap & Progress Tracker

## Current status

- **Phase:** 25 — Export & Portfolio Persistence ✅ Complete
- **Next step:** Phase 26 — TBD
- **Last updated:** 2026-06-18

---

## Phase index

| # | Phase | Status |
|---|-------|--------|
| 1–10 | Core analytics, optimisation, PySide6 GUI, exports, tests (311 passing) | ✅ Done |
| 11 | Streamlit architecture & integration | ✅ Done |
| 12 | Dashboard UI (metrics, charts, optimisation, scenario analysis) | ✅ Done |
| 12B | Asset Analysis page | ✅ Done |
| 13 | Monte Carlo page | ✅ Done |
| 14 | Production readiness (caching, error handling, export panel) | ✅ Done |
| 15 | Mobile deployment & Streamlit Cloud hosting | ✅ Done |
| 16 | Research foundation, SEC EDGAR client, watchlists | ✅ Done |
| 17 | Research Hub & Stock Screener (4 universes, composite score, daily cache) | ✅ Done |
| 18 | Stock Fundamentals Engine (score, trends, peer comparison) | ✅ Done |
| 19 | Valuation Engine (DCF, multiples, historical, sector vs market) | ✅ Done |
| 20 | Insider Activity (time-decay score) + Sector Intelligence (SWOT/PESTLE) | ✅ Done |
| 21 | Research Report & Investment Thesis (rule-based, technical scorer) | ✅ Done |
| 22 | ETF Research Module (profile, scorer, analysis page, auto-routing) | ✅ Done |
| 23 | Dash UI Migration (full app rebuild: dark theme, sidebar, Portfolio Hub, Research Hub) | ✅ Done |
| 24 | Commodities Research Module | ✅ Done |
| 25 | Export & Portfolio Persistence | ✅ Done |

---

## Open questions

*None currently open. Add items here before starting the relevant phase.*

---

## Phase 23 — Dash UI Migration ✅

Complete rebuild of the UI layer from Streamlit to Dash:
- `dash_app/app.py` — entry point, routing, stores
- `dash_app/assets/style.css` — full dark Bloomberg theme
- `dash_app/components/theme.py` — colour constants + Plotly layout defaults
- `dash_app/components/analysis_runner.py` — pure analysis runner (no framework coupling)
- `dash_app/layouts/portfolio_hub.py` — Portfolio Hub: sidebar, dashboard, asset analysis, Monte Carlo
- `dash_app/layouts/research_hub.py` — Research Hub: screener, watchlists, company lookup, sector intel

**Run:** `python dash_app/app.py` → `http://localhost:8050`

---

## Phase 24 — Commodities Research Module ✅

- [x] Commodity universe: 15 tickers across Precious Metals, Energy, Base Metals, Agriculture (`research/data/commodity_fetcher.py`)
- [x] `is_commodity(ticker)` — detects `=F` suffix; auto-routes before yfinance info call
- [x] `CommodityProfile` dataclass + `fetch_commodity_history()` (5Y OHLCV)
- [x] `commodity_scorer.py` — momentum (1M/3M/6M/1Y), trend (MA50/MA200/golden cross), volatility, seasonality
- [x] Composite score 0–100: Momentum 40% + Trend 35% + Volatility 25%
- [x] `dash_app/layouts/commodity_analysis.py` — price+MA chart, drawdown, seasonality bar, score cards, signals
- [x] Auto-routing in `research_hub._render_company` — `GC=F` → commodity page
- [x] Fixed `_render_etf` broken import (was importing from deleted `streamlit_app/`) — now uses `etf_fetcher` + `etf_scorer`

---

## Decision log

*Architectural choices and deviations from spec, with reason.*

- Streamlit selected over PySide6 for presentation; analytics/optimization/export/tests unchanged.
- Black-Litterman via manual equilibrium π = δΣw (PyPortfolioOpt requires views to differ from BL prior).
- Two-hub navigation: Research Hub (default landing) + Portfolio Hub.
- Research data sources: US fundamentals + insider = SEC EDGAR (XBRL, free, no key); EU fundamentals = yfinance; macro = ECB SDMX. All free, no API key.
- Screener cache: daily JSON per universe + MD5 hash of sorted ticker list → invalidates when universe changes.
- Insider scoring: exponential time decay, half-life 45 days — `decay = exp(−ln2 × days_ago / 45)`. Very recent trades (≤14d) get an alert banner in the UI.
- Investment thesis: rule-based (no LLM). Overall score = Fundamentals 30% + Valuation 25% + Technical 20% + Sector 15% + Insider 10%.
- ETF detection via `quoteType`/`legalType` in yfinance info; auto-routes to ETF analysis page in Research Hub.
- Beta calculation: rename both series to `_a`/`_b` before `pd.concat` to prevent duplicate-column ValueError when asset ticker == benchmark ticker.
- Timezone: strip tz-info from yfinance DatetimeIndex before `concat`/`reindex` — newer yfinance returns tz-aware index for some exchanges (fix in `data_service._download()` + `analysis_runner.py`).
- Research implementation order: Stocks → ETFs → Commodities.
- **UI migration: Streamlit → Dash** (2026-06-16). Full control over CSS/layout. Dark Bloomberg theme. `dcc.Store` for state. `@callback` with `allow_duplicate=True` for multi-writer stores. `dash_app/` is the active UI; `streamlit_app/` kept as legacy reference.

---

## Session log

*One line per session: date · phases touched · outcome.*

- 2026-06-08 · Phases 1–10 · Full PySide6 app, all analytics/optimisation/exports, 311 tests passing.
- 2026-06-16 · Phases 11–15 · Streamlit migration, two-hub shell, Streamlit Cloud deployment.
- 2026-06-16 · Phase 16 · Research foundation: SEC EDGAR client, research cache, watchlists.
- 2026-06-16 · Phase 17 · Stock Screener: 4 universes, composite scoring, daily cache, ticker-hash invalidation.
- 2026-06-16 · Phase 18 · Fundamentals Engine: annual + quarterly trends, peer comparison, score explainability.
- 2026-06-16 · Phase 19 · Valuation Engine: DCF + multiples, historical reconstruction, sector/market comparison.
- 2026-06-16 · Phase 20 · Insider Activity (time-decay scoring, role weights, recent-trade alerts) + Sector Intelligence (SWOT, PESTLE, 11 sectors).
- 2026-06-16 · Phase 21 · Research Report: rule-based thesis generator, technical scorer (RSI/MA/MACD/momentum), unified report page + Research Report tab.
- 2026-06-16 · Phase 22 · ETF Research Module: etf_fetcher, etf_scorer, etf_analysis page (5 tabs), auto-routing in Research Hub.
- 2026-06-16 · Bugfixes · Beta ValueError (duplicate column names when asset==benchmark); timezone ValueError (tz-aware DatetimeIndex); metric card info icon moved inside card via st.container(border=True).
- 2026-06-16 · Phase 23 · Full Dash migration: dark Bloomberg UI, sidebar, Portfolio Hub (dashboard/asset analysis/Monte Carlo), Research Hub (screener/watchlists/company/sector). Entry: python dash_app/app.py.
- 2026-06-16 · Infra · Render.com deployment live (https://portfolio-analyse.onrender.com); iPhone PWA support (meta tags, manifest, touch icon); CLAUDE.md cleanup.
- 2026-06-17 · Phase 24 · Commodities: fetcher (15 tickers), scorer (momentum/trend/volatility/seasonality), commodity_analysis.py page, auto-routing in Research Hub; fixed _render_etf broken streamlit import.
- 2026-06-18 · Phase 25 · Export & Portfolio Persistence: Save JSON (sidebar 💾), Load JSON via dcc.Upload (sidebar 📂), CSV export (metrics + weights), Excel export (3 sheets: Metrics / Weights / Daily Returns).
