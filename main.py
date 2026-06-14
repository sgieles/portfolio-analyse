"""Application entry point."""

import sys

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from utils.logging import setup_logging, get_logger
from ui.theme import DARK_STYLESHEET, apply_matplotlib_dark_style
from ui.main_window import MainWindow

setup_logging()
log = get_logger(__name__)


def main() -> None:
    log.info("Starting Portfolio Analyser")

    app = QApplication(sys.argv)
    app.setApplicationName("Portfolio Analyser")
    app.setOrganizationName("PortfolioAnalyser")
    app.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps)

    app.setStyleSheet(DARK_STYLESHEET)
    apply_matplotlib_dark_style()

    window = MainWindow()
    window.show()

    log.info("MainWindow displayed")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
