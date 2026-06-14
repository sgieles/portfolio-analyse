"""Sidebar export panel — CSV, Excel, PDF and JSON download buttons."""

from __future__ import annotations

import tempfile
from pathlib import Path

import streamlit as st

from streamlit_app.state import session
from streamlit_app.styles.theme import ACCENT, BORDER, BG_SECONDARY, TEXT_PRIMARY, TEXT_SECONDARY


def _bytes_from_path_fn(fn, result, suffix: str) -> bytes:
    """Call fn(result, path), read the written file as bytes, delete it."""
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        fn(result, tmp_path)
        return tmp_path.read_bytes()
    finally:
        tmp_path.unlink(missing_ok=True)


def render() -> None:
    """Render export and save/load controls in the sidebar."""
    result = session.get_result()
    pf     = session.get_portfolio()
    settings = session.get_settings()

    st.sidebar.markdown(
        f"<div style='font-size:12px; font-weight:700; color:{TEXT_PRIMARY}; "
        f"margin-bottom:6px;'>Export Report</div>",
        unsafe_allow_html=True,
    )

    if result is None:
        st.sidebar.caption("Run an analysis first to enable exports.")
    else:
        name = (pf.name or "portfolio").replace(" ", "_")

        # ── CSV ───────────────────────────────────────────────────────────────
        try:
            from reports.csv_exporter import export_portfolio_csv
            csv_bytes = _bytes_from_path_fn(export_portfolio_csv, result, ".csv")
            st.sidebar.download_button(
                label="Download CSV",
                data=csv_bytes,
                file_name=f"{name}_analysis.csv",
                mime="text/csv",
                use_container_width=True,
                key="dl_csv",
            )
        except Exception as exc:
            st.sidebar.caption(f"CSV error: {exc}")

        # ── Excel ─────────────────────────────────────────────────────────────
        try:
            from reports.excel_exporter import export_portfolio_excel
            xl_bytes = _bytes_from_path_fn(export_portfolio_excel, result, ".xlsx")
            st.sidebar.download_button(
                label="Download Excel",
                data=xl_bytes,
                file_name=f"{name}_analysis.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                key="dl_xlsx",
            )
        except Exception as exc:
            st.sidebar.caption(f"Excel error: {exc}")

        # ── PDF ───────────────────────────────────────────────────────────────
        try:
            from reports.pdf_report import export_portfolio_pdf
            pdf_bytes = _bytes_from_path_fn(export_portfolio_pdf, result, ".pdf")
            st.sidebar.download_button(
                label="Download PDF",
                data=pdf_bytes,
                file_name=f"{name}_report.pdf",
                mime="application/pdf",
                use_container_width=True,
                key="dl_pdf",
            )
        except Exception as exc:
            st.sidebar.caption(f"PDF error: {exc}")

    st.sidebar.divider()

    # ── Save portfolio JSON ────────────────────────────────────────────────────
    st.sidebar.markdown(
        f"<div style='font-size:12px; font-weight:700; color:{TEXT_PRIMARY}; "
        f"margin-bottom:6px;'>Save Portfolio</div>",
        unsafe_allow_html=True,
    )
    if pf.assets:
        try:
            from services.portfolio_io import save_portfolio
            json_bytes = _save_portfolio_json(pf, settings)
            name = (pf.name or "portfolio").replace(" ", "_")
            st.sidebar.download_button(
                label="Download Portfolio JSON",
                data=json_bytes,
                file_name=f"{name}.json",
                mime="application/json",
                use_container_width=True,
                key="dl_json",
            )
        except Exception as exc:
            st.sidebar.caption(f"Save error: {exc}")
    else:
        st.sidebar.caption("Add tickers to save a portfolio.")


def _save_portfolio_json(pf, settings) -> bytes:
    from services.portfolio_io import save_portfolio
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        save_portfolio(pf, settings, tmp_path)
        return tmp_path.read_bytes()
    finally:
        tmp_path.unlink(missing_ok=True)
