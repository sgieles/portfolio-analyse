# build_plan.md — Build Roadmap & Progress Tracker

## Current status

- **Phase:** 22 — ETF Research Module ✅ Complete
- **Next step:** Phase 23 — Commodities Research Module
- **Last updated:** 2026-06-16

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
| 23 | Commodities Research Module | ⬜ Next |

---

## Open questions

*None currently open. Add items here before starting the relevant phase.*

---

## Phase 23 — Commodities Research Module

*Goal: extend the research workflow to commodities after stock and ETF research are complete.*

- [ ] Commodity universe (gold, oil, gas, copper, silver, wheat, etc. — yfinance tickers like GC=F, CL=F)
- [ ] Commodity profile fetcher (`research/data/commodity_fetcher.py`)
- [ ] Commodity scorer (`research/analytics/commodity_scorer.py`) — momentum, inflation sensitivity, supply/demand signals
- [ ] Commodity analysis page (`streamlit_app/pages/commodity_analysis.py`)
- [ ] Auto-routing in Research Hub (detect commodity ticker, route to commodity page)
- [ ] Relative strength vs broad market (1/3/6/12m momentum)
- [ ] Inflation & interest rate sensitivity metrics
- [ ] Supply & demand signal indicators

**Done when:** commodity tickers are auto-detected in the Research Hub and route to a dedicated commodity analysis page with scoring, momentum and macro-sensitivity signals.

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
- Metric cards: `st.container(border=True)` + `st.popover` inside the container — the only reliable approach; injected `<style>` blocks are stripped by Streamlit Cloud's HTML sanitiser.
- Beta calculation: rename both series to `_a`/`_b` before `pd.concat` to prevent duplicate-column ValueError when asset ticker == benchmark ticker.
- Timezone: strip tz-info from yfinance DatetimeIndex before `concat`/`reindex` — newer yfinance returns tz-aware index for some exchanges (fix in `data_service._download()` + `analysis_runner.py`).
- Research implementation order: Stocks → ETFs → Commodities.

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
