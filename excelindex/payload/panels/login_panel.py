from __future__ import annotations

from peewee import fn
from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QApplication, QFormLayout, QLineEdit, QPushButton, QVBoxLayout, QWidget

from models import User
from ui_common import SessionUser, format_user_full_name, show_error


class LoginWindow(QWidget):
    login_completed = pyqtSignal()

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("ООО Обувь - Авторизация")
        self.resize(450, 220)

        self.login_input = QLineEdit()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)

        login_btn = QPushButton("Войти")
        login_btn.clicked.connect(self._do_login)
        guest_btn = QPushButton("Войти как гость")
        guest_btn.clicked.connect(self._login_guest)

        layout = QVBoxLayout()
        form = QFormLayout()
        form.addRow("Логин:", self.login_input)
        form.addRow("Пароль:", self.password_input)
        layout.addLayout(form)
        layout.addWidget(login_btn)
        layout.addWidget(guest_btn)
        self.setLayout(layout)

        self.authenticated_user: SessionUser | None = None

    def closeEvent(self, event) -> None:  # type: ignore[override]
        if self.authenticated_user is None:
            QApplication.instance().quit()
        super().closeEvent(event)

    def _do_login(self) -> None:
        login = self.login_input.text().strip()
        password = self.password_input.text()
        if not login or not password:
            show_error(self, "Введите логин и пароль.")
            return

        user = User.select().where(fn.LOWER(User.login) == login.lower()).first()
        if user is None:
            show_error(self, "Пользователь не найден.")
            return
        if str(user.password) != password:
            show_error(self, "Неверный пароль.")
            return

        self.authenticated_user = SessionUser(
            user_id=int(user.id),
            full_name=format_user_full_name(user),
            role_name=str(user.role),
        )
        self.hide()
        self.login_completed.emit()

    def _login_guest(self) -> None:
        self.authenticated_user = SessionUser(
            user_id=None,
            full_name="Гость",
            role_name="Гость",
        )
        self.hide()
        self.login_completed.emit()
