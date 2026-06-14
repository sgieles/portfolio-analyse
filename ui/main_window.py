"""MainWindow — QTabWidget host + menu bar with File/Export actions."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QFileDialog, QMainWindow, QMessageBox,
    QStatusBar, QTabWidget,
)

from ui.asset_analysis_tab import AssetAnalysisTab
from ui.correlation_tab import CorrelationTab
from ui.dashboard_tab import DashboardTab
from ui.monte_carlo_tab import MonteCarloTab
from ui.scenario_tab import ScenarioTab
from models.results import AnalysisResult
from utils.logging import get_logger

log = get_logger(__name__)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Portfolio Analyser")
        self.resize(1_400, 900)
        self.setMinimumSize(1_100, 700)
        self._last_result: AnalysisResult | None = None

        self._build_status_bar()
        self._build_tabs()
        self._build_menu()

    # ── Layout ─────────────────────────────────────────────────────────────────

    def _build_tabs(self) -> None:
        tabs = QTabWidget()
        tabs.setDocumentMode(True)

        self._dashboard     = DashboardTab(tabs)
        self._asset_tab     = AssetAnalysisTab(tabs)
        self._corr_tab      = CorrelationTab(tabs)
        self._scenario_tab  = ScenarioTab(tabs)
        self._mc_tab        = MonteCarloTab(tabs)

        self._dashboard.status_message.connect(self._status_bar.showMessage)
        self._dashboard.analysis_ready.connect(self._on_result_updated)
        self._dashboard.analysis_ready.connect(self._asset_tab.set_result)
        self._dashboard.analysis_ready.connect(self._corr_tab.set_result)
        self._dashboard.analysis_ready.connect(self._scenario_tab.set_result)
        self._dashboard.analysis_ready.connect(self._mc_tab.set_result)

        tabs.addTab(self._dashboard,    "Portfolio Dashboard")
        tabs.addTab(self._asset_tab,    "Asset Analysis")
        tabs.addTab(self._corr_tab,     "Correlation Analysis")
        tabs.addTab(self._scenario_tab, "Scenario Analysis")
        tabs.addTab(self._mc_tab,       "Monte Carlo")
        self.setCentralWidget(tabs)
        self._tabs = tabs

    def _build_status_bar(self) -> None:
        self._status_bar = QStatusBar()
        self._status_bar.showMessage(
            "Ready — add tickers and click Analyze Portfolio."
        )
        self.setStatusBar(self._status_bar)

    def _build_menu(self) -> None:
        mb = self.menuBar()

        # ── File menu ─────────────────────────────────────────────────────────
        file_menu = mb.addMenu("File")

        act_save = QAction("Save Portfolio…", self)
        act_save.setShortcut(QKeySequence.StandardKey.Save)
        act_save.triggered.connect(self._dashboard._on_save_portfolio)
        file_menu.addAction(act_save)

        act_load = QAction("Load Portfolio…", self)
        act_load.setShortcut(QKeySequence.StandardKey.Open)
        act_load.triggered.connect(self._dashboard._on_load_portfolio)
        file_menu.addAction(act_load)

        file_menu.addSeparator()

        act_quit = QAction("Quit", self)
        act_quit.setShortcut(QKeySequence.StandardKey.Quit)
        act_quit.triggered.connect(self.close)
        file_menu.addAction(act_quit)

        # ── Export menu ───────────────────────────────────────────────────────
        export_menu = mb.addMenu("Export")

        self._act_csv   = QAction("Export CSV…",   self)
        self._act_excel = QAction("Export Excel…", self)
        self._act_pdf   = QAction("Export PDF Report…", self)

        self._act_csv.triggered.connect(self._export_csv)
        self._act_excel.triggered.connect(self._export_excel)
        self._act_pdf.triggered.connect(self._export_pdf)

        for act in (self._act_csv, self._act_excel, self._act_pdf):
            act.setEnabled(False)          # enabled after first analysis
            export_menu.addAction(act)

    # ── Slots ──────────────────────────────────────────────────────────────────

    def _on_result_updated(self, result: AnalysisResult) -> None:
        self._last_result = result
        for act in (self._act_csv, self._act_excel, self._act_pdf):
            act.setEnabled(True)

    def _export_csv(self) -> None:
        if not self._last_result:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export CSV", str(Path.home()), "CSV files (*.csv)"
        )
        if not path:
            return
        try:
            from reports.csv_exporter import export_portfolio_csv
            export_portfolio_csv(self._last_result, Path(path))
            self._status_bar.showMessage(f"CSV exported → {path}")
        except Exception as exc:
            log.error("CSV export failed: %s", exc)
            QMessageBox.critical(self, "Export failed", str(exc))

    def _export_excel(self) -> None:
        if not self._last_result:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Excel", str(Path.home()), "Excel files (*.xlsx)"
        )
        if not path:
            return
        try:
            from reports.excel_exporter import export_portfolio_excel
            export_portfolio_excel(self._last_result, Path(path))
            self._status_bar.showMessage(f"Excel exported → {path}")
        except Exception as exc:
            log.error("Excel export failed: %s", exc)
            QMessageBox.critical(self, "Export failed", str(exc))

    def _export_pdf(self) -> None:
        if not self._last_result:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export PDF Report", str(Path.home()), "PDF files (*.pdf)"
        )
        if not path:
            return
        self._status_bar.showMessage("Generating PDF report…")
        try:
            from reports.pdf_report import export_portfolio_pdf
            export_portfolio_pdf(self._last_result, Path(path))
            self._status_bar.showMessage(f"PDF exported → {path}")
        except Exception as exc:
            log.error("PDF export failed: %s", exc)
            QMessageBox.critical(self, "Export failed", str(exc))
