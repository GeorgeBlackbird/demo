import sys

from PyQt5.QtWidgets import QApplication

from app_ui import LoginWindow, MainWindow, apply_global_style


def main() -> int:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    apply_global_style(app)

    login_window = LoginWindow()
    main_window: MainWindow | None = None

    def show_main() -> None:
        nonlocal main_window
        user = login_window.authenticated_user
        if user is None:
            return
        login_window.hide()
        main_window = MainWindow(user)
        main_window.logout_requested.connect(on_logout)
        main_window.show()

    def on_logout() -> None:
        nonlocal main_window
        main_window = None
        login_window.authenticated_user = None
        login_window.login_input.clear()
        login_window.password_input.clear()
        login_window.show()

    login_window.login_completed.connect(show_main)
    login_window.show()
    return app.exec_()


if __name__ == "__main__":
    raise SystemExit(main())
