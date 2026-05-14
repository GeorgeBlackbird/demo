from __future__ import annotations

from dataclasses import dataclass

from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QMessageBox, QWidget


@dataclass
class SessionUser:
    user_id: int | None
    full_name: str
    role_name: str


def show_error(parent: QWidget, message: str) -> None:
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Critical)
    box.setWindowTitle("Ошибка")
    box.setText(message)
    box.exec_()


def show_info(parent: QWidget, message: str) -> None:
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Information)
    box.setWindowTitle("Информация")
    box.setText(message)
    box.exec_()


def apply_global_style(app) -> None:
    app.setFont(QFont("Times New Roman", 10))
    app.setStyleSheet(
        """
        QWidget {
            background-color: #FFFFFF;
        }
        QLineEdit, QComboBox, QDateEdit, QTableWidget {
            background-color: #FFFFFF;
        }
        QPushButton {
            background-color: #00FA9A;
            padding: 6px 10px;
        }
        QTabWidget::pane {
            border: 1px solid #7FFF00;
        }
        """
    )


def format_user_full_name(user) -> str:
    return " ".join(
        [
            str(user.first_name or "").strip(),
            str(user.last_name or "").strip(),
            str(user.middle_name or "").strip(),
        ]
    ).strip()


def split_full_name(full_name: str) -> tuple[str, str, str]:
    parts = [part for part in full_name.split(" ") if part]
    first_name = parts[0] if len(parts) > 0 else ""
    last_name = parts[1] if len(parts) > 1 else ""
    middle_name = parts[2] if len(parts) > 2 else ""
    return first_name, last_name, middle_name
