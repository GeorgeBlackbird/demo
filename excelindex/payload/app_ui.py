from __future__ import annotations

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from panels.catalog_panel import CatalogPanel
from panels.login_panel import LoginWindow
from models import Order, OrderProduct, Product, Pvz, User, db
from panels.orders_panel import OrdersPanel
from ui_common import SessionUser, apply_global_style, show_error


def _prepare_database() -> None:
    db.connect(reuse_if_open=True)
    db.create_tables([User, Pvz, Product, Order, OrderProduct], safe=True)


class MainWindow(QMainWindow):
    logout_requested = pyqtSignal()

    def __init__(self, session: SessionUser) -> None:
        super().__init__()
        _prepare_database()
        self.session = session
        self._is_logging_out = False

        self.setWindowTitle("ИС ООО Обувь")
        self.resize(1300, 760)

        root = QWidget()
        outer = QVBoxLayout()
        top_row = QHBoxLayout()
        top_row.addStretch()
        self.user_label = QLabel(f"{session.full_name} | {session.role_name}")
        top_row.addWidget(self.user_label)
        self.logout_btn = QPushButton("Выход")
        self.logout_btn.clicked.connect(self._on_logout_clicked)
        top_row.addWidget(self.logout_btn)
        outer.addLayout(top_row)

        self.tabs = QTabWidget()
        self.catalog_tab = CatalogPanel(session)
        self.tabs.addTab(self.catalog_tab, "Каталог")

        self.orders_tab: OrdersPanel | None = None
        if session.role_name in ("Менеджер", "Администратор"):
            self.orders_tab = OrdersPanel(session)
            self.tabs.addTab(self.orders_tab, "Заказы")

        outer.addWidget(self.tabs)
        root.setLayout(outer)
        self.setCentralWidget(root)

    def _on_logout_clicked(self) -> None:
        self._is_logging_out = True
        self.logout_requested.emit()
        self.close()

    def closeEvent(self, event) -> None:  # type: ignore[override]
        if not self._is_logging_out:
            QApplication.instance().quit()
        super().closeEvent(event)


_prepare_database()

__all__ = [
    "LoginWindow",
    "MainWindow",
    "SessionUser",
    "apply_global_style",
    "show_error",
]
