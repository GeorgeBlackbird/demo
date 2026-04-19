import sys

from PyQt5.QtWidgets import QApplication

from app_ui import LoginWindow, MainWindow, apply_global_style, show_error
from db import init_db
from import_excel import import_all


def bootstrap_data() -> None:
    init_db()
    import_all()


def main() -> int:
    app = QApplication(sys.argv)
    apply_global_style(app)

    try:
        bootstrap_data()
    except Exception as exc:
        temp = LoginWindow()
        show_error(temp, f"Ошибка инициализации данных: {exc}")
        return 1

    login_window = LoginWindow()
    login_window.show()
    app.exec_()

    if login_window.authenticated_user is None:
        return 0

    window = MainWindow(login_window.authenticated_user)
    window.show()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())

