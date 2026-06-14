"""MetricCard — compact label + value display with a colored accent bar."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame, QLabel, QVBoxLayout, QWidget,
)

from ui.theme import ACCENT, BG_SECONDARY, BORDER, TEXT_PRIMARY, TEXT_SECONDARY


class MetricCard(QFrame):
    """Framed card showing a metric name and its formatted value.

    Visual layout::

        ┌──────────────────────┐
        │▌ (accent bar)        │
        │  Label               │
        │             VALUE    │
        └──────────────────────┘

    The accent bar and value colour are updated together via ``set_value``.
    """

    def __init__(self, label: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("MetricCard")
        self.setStyleSheet(
            f"QFrame#MetricCard {{"
            f"  background-color: {BG_SECONDARY};"
            f"  border: 1px solid {BORDER};"
            f"  border-radius: 8px;"
            f"}}"
        )
        self.setMinimumHeight(78)
        self.setMinimumWidth(130)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Coloured accent bar at the top
        self._bar = QFrame()
        self._bar.setFixedHeight(4)
        self._bar.setObjectName("AccentBar")
        self._bar.setStyleSheet(
            f"QFrame#AccentBar {{ background: {ACCENT};"
            f" border-top-left-radius: 8px;"
            f" border-top-right-radius: 8px; }}"
        )
        outer.addWidget(self._bar)

        # Content area
        content = QWidget()
        content.setStyleSheet("background: transparent;")
        inner = QVBoxLayout(content)
        inner.setContentsMargins(12, 6, 12, 10)
        inner.setSpacing(2)

        self._lbl = QLabel(label)
        self._lbl.setStyleSheet(
            f"font-size: 10px; color: {TEXT_SECONDARY};"
            f" background: transparent; font-weight: normal;"
        )
        self._lbl.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self._val = QLabel("—")
        self._val.setStyleSheet(
            f"font-size: 18px; font-weight: bold;"
            f" color: {TEXT_PRIMARY}; background: transparent;"
        )
        self._val.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )

        inner.addWidget(self._lbl)
        inner.addWidget(self._val)
        outer.addWidget(content)

    def set_value(self, text: str, color: str | None = None) -> None:
        """Update the displayed value, its colour, and the accent bar colour."""
        c = color or TEXT_PRIMARY
        self._val.setText(text)
        self._val.setStyleSheet(
            f"font-size: 18px; font-weight: bold;"
            f" color: {c}; background: transparent;"
        )
        self._bar.setStyleSheet(
            f"QFrame#AccentBar {{ background: {c};"
            f" border-top-left-radius: 8px;"
            f" border-top-right-radius: 8px; }}"
        )

    def reset(self) -> None:
        """Reset value to placeholder and restore accent colour."""
        self._val.setText("—")
        self._val.setStyleSheet(
            f"font-size: 18px; font-weight: bold;"
            f" color: {TEXT_PRIMARY}; background: transparent;"
        )
        self._bar.setStyleSheet(
            f"QFrame#AccentBar {{ background: {ACCENT};"
            f" border-top-left-radius: 8px;"
            f" border-top-right-radius: 8px; }}"
        )
