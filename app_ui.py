from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from PyQt5.QtCore import QSize, Qt
from PyQt5.QtGui import QColor, QFont, QPixmap
from PyQt5.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QFrame,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from db import BASE_DIR, execute, fetch_all, fetch_one, get_connection, normalize_password
from import_excel import resolve_import_dir


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


class LoginWindow(QWidget):
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

    def _do_login(self) -> None:
        login = self.login_input.text().strip()
        password = self.password_input.text()
        if not login or not password:
            show_error(self, "Введите логин и пароль.")
            return

        user = fetch_one(
            """
            SELECT u.user_id, u.full_name, r.role_name, u.password_hash
            FROM users u
            JOIN roles r ON r.role_id = u.role_id
            WHERE LOWER(u.login) = LOWER(?)
            """,
            (login,),
        )
        if user is None:
            show_error(self, "Пользователь не найден.")
            return

        if normalize_password(password) != str(user["password_hash"] or ""):
            show_error(self, "Неверный пароль.")
            return

        self.authenticated_user = SessionUser(
            user_id=int(user["user_id"]),
            full_name=str(user["full_name"]),
            role_name=str(user["role_name"]),
        )
        self.close()

    def _login_guest(self) -> None:
        self.authenticated_user = SessionUser(
            user_id=None,
            full_name="Гость",
            role_name="Гость",
        )
        self.close()


class ProductDialog(QDialog):
    def __init__(self, parent: QWidget, product_id: int | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Товар")
        self.product_id = product_id

        self.article = QLineEdit()
        self.name = QLineEdit()
        self.description = QLineEdit()
        self.unit = QLineEdit("шт.")
        self.category = QLineEdit()
        self.manufacturer = QLineEdit()
        self.supplier = QLineEdit()
        self.price = QLineEdit("0")
        self.discount = QSpinBox()
        self.discount.setRange(0, 100)
        self.stock_qty = QSpinBox()
        self.stock_qty.setRange(0, 99999)
        self.image_path = QLineEdit()

        form = QFormLayout()
        form.addRow("Артикул", self.article)
        form.addRow("Название", self.name)
        form.addRow("Описание", self.description)
        form.addRow("Ед. изм.", self.unit)
        form.addRow("Категория", self.category)
        form.addRow("Производитель", self.manufacturer)
        form.addRow("Поставщик", self.supplier)
        form.addRow("Цена", self.price)
        form.addRow("Скидка (%)", self.discount)
        form.addRow("Кол-во", self.stock_qty)
        form.addRow("Путь к фото", self.image_path)

        save_btn = QPushButton("Сохранить")
        save_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject)
        row = QHBoxLayout()
        row.addWidget(save_btn)
        row.addWidget(cancel_btn)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addLayout(row)
        self.setLayout(layout)

        if product_id is not None:
            self._load()

    def _load(self) -> None:
        row = fetch_one(
            """
            SELECT p.*, c.category_name, m.manufacturer_name, s.supplier_name
            FROM products p
            JOIN categories c ON c.category_id = p.category_id
            JOIN manufacturers m ON m.manufacturer_id = p.manufacturer_id
            JOIN suppliers s ON s.supplier_id = p.supplier_id
            WHERE p.product_id = ?
            """,
            (self.product_id,),
        )
        if row is None:
            return
        self.article.setText(str(row["article"]))
        self.name.setText(str(row["name"]))
        self.description.setText(str(row["description"] or ""))
        self.unit.setText(str(row["unit"]))
        self.category.setText(str(row["category_name"]))
        self.manufacturer.setText(str(row["manufacturer_name"]))
        self.supplier.setText(str(row["supplier_name"]))
        self.price.setText(str(row["price"]))
        self.discount.setValue(int(row["discount_percent"]))
        self.stock_qty.setValue(int(row["stock_qty"]))
        self.image_path.setText(str(row["image_path"] or ""))


class OrderDialog(QDialog):
    def __init__(self, parent: QWidget, order_id: int | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Заказ")
        self.order_id = order_id

        self.user_name = QLineEdit()
        self.point = QComboBox()
        self.status = QComboBox()
        self.code = QSpinBox()
        self.code.setRange(0, 999999)
        self.created = QDateEdit()
        self.created.setCalendarPopup(True)
        self.created.setDate(date.today())
        self.delivery = QDateEdit()
        self.delivery.setCalendarPopup(True)
        self.delivery.setDate(date.today())
        self.items = QLineEdit()
        self.items.setPlaceholderText("Артикул1, 2, Артикул2, 1")

        for row in fetch_all("SELECT point_id, point_address FROM pickup_points ORDER BY point_id"):
            self.point.addItem(f"#{row['point_id']} {row['point_address']}", int(row["point_id"]))
        for row in fetch_all("SELECT status_id, status_name FROM order_statuses ORDER BY status_id"):
            self.status.addItem(str(row["status_name"]), int(row["status_id"]))

        form = QFormLayout()
        form.addRow("ФИО клиента", self.user_name)
        form.addRow("Пункт выдачи", self.point)
        form.addRow("Статус", self.status)
        form.addRow("Код получения", self.code)
        form.addRow("Дата заказа", self.created)
        form.addRow("Дата доставки", self.delivery)
        form.addRow("Состав заказа", self.items)

        save_btn = QPushButton("Сохранить")
        save_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject)
        row = QHBoxLayout()
        row.addWidget(save_btn)
        row.addWidget(cancel_btn)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addLayout(row)
        self.setLayout(layout)

        if order_id is not None:
            self._load()

    def _load(self) -> None:
        order = fetch_one(
            """
            SELECT o.order_id, o.point_id, o.status_id, o.pickup_code, o.created_at, o.delivery_date,
                   COALESCE(u.full_name, '') AS full_name
            FROM orders o
            LEFT JOIN users u ON u.user_id = o.user_id
            WHERE o.order_id = ?
            """,
            (self.order_id,),
        )
        if order is None:
            return

        self.user_name.setText(str(order["full_name"]))
        self.code.setValue(int(order["pickup_code"] or 0))
        for i in range(self.point.count()):
            if self.point.itemData(i) == int(order["point_id"]):
                self.point.setCurrentIndex(i)
                break
        for i in range(self.status.count()):
            if self.status.itemData(i) == int(order["status_id"]):
                self.status.setCurrentIndex(i)
                break

        created_at = str(order["created_at"])
        delivery_date = str(order["delivery_date"] or created_at)
        self.created.setDate(date.fromisoformat(created_at[:10]))
        self.delivery.setDate(date.fromisoformat(delivery_date[:10]))

        items = fetch_all(
            """
            SELECT p.article, oi.qty
            FROM order_items oi
            JOIN products p ON p.product_id = oi.product_id
            WHERE oi.order_id = ?
            ORDER BY oi.order_item_id
            """,
            (self.order_id,),
        )
        item_str = ", ".join(f"{it['article']}, {it['qty']}" for it in items)
        self.items.setText(item_str)


class MainWindow(QMainWindow):
    def __init__(self, session: SessionUser) -> None:
        super().__init__()
        self.session = session
        self.setWindowTitle("ИС ООО Обувь")
        self.resize(1300, 760)

        root = QWidget()
        outer = QVBoxLayout()
        top_row = QHBoxLayout()
        top_row.addStretch()
        self.user_label = QLabel(f"{session.full_name} | {session.role_name}")
        top_row.addWidget(self.user_label)
        outer.addLayout(top_row)

        self.tabs = QTabWidget()
        self.catalog_tab = self._build_catalog_tab()
        self.orders_tab = self._build_orders_tab()
        self.tabs.addTab(self.catalog_tab, "Каталог")
        if session.role_name in ("Менеджер", "Администратор"):
            self.tabs.addTab(self.orders_tab, "Заказы")
        outer.addWidget(self.tabs)

        root.setLayout(outer)
        self.setCentralWidget(root)
        self._refresh_catalog()
        self._refresh_orders()

    def _build_catalog_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout()

        controls = QGridLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск по артикулу / названию / описанию")
        self.search_input.textChanged.connect(self._refresh_catalog)

        self.supplier_filter = QComboBox()
        self.supplier_filter.currentIndexChanged.connect(self._refresh_catalog)

        self.sort_stock = QComboBox()
        self.sort_stock.addItems(["Без сортировки", "Остаток по возрастанию", "Остаток по убыванию"])
        self.sort_stock.currentIndexChanged.connect(self._refresh_catalog)

        controls.addWidget(QLabel("Поиск"), 0, 0)
        controls.addWidget(self.search_input, 0, 1)
        controls.addWidget(QLabel("Поставщик"), 1, 0)
        controls.addWidget(self.supplier_filter, 1, 1)
        controls.addWidget(QLabel("Сортировка"), 2, 0)
        controls.addWidget(self.sort_stock, 2, 1)
        layout.addLayout(controls)

        self.catalog_cards = QListWidget()
        self.catalog_cards.setSpacing(10)
        self.catalog_cards.setSelectionMode(QListWidget.SingleSelection)
        self.catalog_cards.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self.catalog_cards.setStyleSheet(
            """
            QListWidget::item {
                border: 2px solid #000000;
                margin: 4px;
                padding: 2px;
            }
            QListWidget::item:selected {
                border: 2px solid #00FA9A;
                background: #F4FFFA;
            }
            """
        )
        layout.addWidget(self.catalog_cards)

        btn_row = QHBoxLayout()
        self.add_product_btn = QPushButton("Добавить товар")
        self.edit_product_btn = QPushButton("Редактировать товар")
        self.delete_product_btn = QPushButton("Удалить товар")
        self.add_product_btn.clicked.connect(self._add_product)
        self.edit_product_btn.clicked.connect(self._edit_product)
        self.delete_product_btn.clicked.connect(self._delete_product)
        btn_row.addWidget(self.add_product_btn)
        btn_row.addWidget(self.edit_product_btn)
        btn_row.addWidget(self.delete_product_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        widget.setLayout(layout)
        self._configure_catalog_access()
        self._load_supplier_filter()
        return widget

    def _configure_catalog_access(self) -> None:
        is_manager_or_admin = self.session.role_name in ("Менеджер", "Администратор")
        is_admin = self.session.role_name == "Администратор"
        self.search_input.setEnabled(is_manager_or_admin)
        self.supplier_filter.setEnabled(is_manager_or_admin)
        self.sort_stock.setEnabled(is_manager_or_admin)
        self.add_product_btn.setVisible(is_admin)
        self.edit_product_btn.setVisible(is_admin)
        self.delete_product_btn.setVisible(is_admin)

    def _build_orders_tab(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout()
        self.orders_table = QTableWidget()
        self.orders_table.setColumnCount(8)
        self.orders_table.setHorizontalHeaderLabels(
            ["ID", "Клиент", "Пункт выдачи", "Статус", "Дата заказа", "Дата доставки", "Код", "Позиции"]
        )
        self.orders_table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.orders_table)

        row = QHBoxLayout()
        self.add_order_btn = QPushButton("Добавить заказ")
        self.edit_order_btn = QPushButton("Редактировать заказ")
        self.delete_order_btn = QPushButton("Удалить заказ")
        self.add_order_btn.clicked.connect(self._add_order)
        self.edit_order_btn.clicked.connect(self._edit_order)
        self.delete_order_btn.clicked.connect(self._delete_order)
        row.addWidget(self.add_order_btn)
        row.addWidget(self.edit_order_btn)
        row.addWidget(self.delete_order_btn)
        row.addStretch()
        layout.addLayout(row)

        widget.setLayout(layout)
        return widget

    def _load_supplier_filter(self) -> None:
        self.supplier_filter.blockSignals(True)
        current = self.supplier_filter.currentText()
        self.supplier_filter.clear()
        self.supplier_filter.addItem("Все поставщики")
        for row in fetch_all("SELECT supplier_name FROM suppliers ORDER BY supplier_name"):
            self.supplier_filter.addItem(str(row["supplier_name"]))
        idx = self.supplier_filter.findText(current)
        if idx >= 0:
            self.supplier_filter.setCurrentIndex(idx)
        self.supplier_filter.blockSignals(False)

    def _refresh_catalog(self) -> None:
        params: list[object] = []
        where_parts: list[str] = []

        text = self.search_input.text().strip()
        if text and self.search_input.isEnabled():
            where_parts.append("(p.article LIKE ? OR p.name LIKE ? OR p.description LIKE ?)")
            like = f"%{text}%"
            params.extend([like, like, like])

        supplier = self.supplier_filter.currentText().strip()
        if supplier and supplier != "Все поставщики" and self.supplier_filter.isEnabled():
            where_parts.append("s.supplier_name = ?")
            params.append(supplier)

        where_clause = f"WHERE {' AND '.join(where_parts)}" if where_parts else ""
        order_clause = ""
        sort_mode = self.sort_stock.currentText()
        if self.sort_stock.isEnabled():
            if sort_mode == "Остаток по возрастанию":
                order_clause = "ORDER BY p.stock_qty ASC"
            elif sort_mode == "Остаток по убыванию":
                order_clause = "ORDER BY p.stock_qty DESC"

        rows = fetch_all(
            f"""
            SELECT
                p.product_id, p.article, p.name, c.category_name, s.supplier_name,
                p.price, p.discount_percent, p.stock_qty, p.description, p.image_path
            FROM products p
            JOIN categories c ON c.category_id = p.category_id
            JOIN suppliers s ON s.supplier_id = p.supplier_id
            {where_clause}
            {order_clause}
            """,
            tuple(params),
        )

        self.catalog_cards.clear()
        for row in rows:
            discount = float(row["discount_percent"])
            price = float(row["price"])
            discounted = price * (1.0 - discount / 100.0)

            list_item = QListWidgetItem()
            list_item.setData(Qt.UserRole, int(row["product_id"]))
            list_item.setSizeHint(QSize(0, 170))
            self.catalog_cards.addItem(list_item)
            card = self._build_product_card_widget(
                article=str(row["article"]),
                name=str(row["name"]),
                category=str(row["category_name"]),
                supplier=str(row["supplier_name"]),
                price=price,
                discounted=discounted,
                discount=discount,
                stock_qty=int(row["stock_qty"]),
                description=str(row["description"] or ""),
                image_name=str(row["image_path"] or ""),
            )
            self.catalog_cards.setItemWidget(list_item, card)

        self._load_supplier_filter()
        if rows:
            self.catalog_cards.setCurrentRow(0)

    def _selected_product_id(self) -> int | None:
        item = self.catalog_cards.currentItem()
        if item is None:
            return None
        value = item.data(Qt.UserRole)
        return int(value) if value is not None else None

    def _add_product(self) -> None:
        dialog = ProductDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            self._save_product(dialog, product_id=None)

    def _edit_product(self) -> None:
        product_id = self._selected_product_id()
        if product_id is None:
            show_error(self, "Выберите товар.")
            return
        dialog = ProductDialog(self, product_id=product_id)
        if dialog.exec_() == QDialog.Accepted:
            self._save_product(dialog, product_id=product_id)

    def _save_product(self, dialog: ProductDialog, product_id: int | None) -> None:
        try:
            article = dialog.article.text().strip()
            name = dialog.name.text().strip()
            category = dialog.category.text().strip()
            manufacturer = dialog.manufacturer.text().strip()
            supplier = dialog.supplier.text().strip()
            unit = dialog.unit.text().strip() or "шт."
            description = dialog.description.text().strip()
            image_path = dialog.image_path.text().strip()
            price = float(dialog.price.text().replace(",", "."))
            stock_qty = int(dialog.stock_qty.value())
            discount = int(dialog.discount.value())

            if not article or not name or not category or not manufacturer or not supplier:
                raise ValueError("Заполните обязательные поля товара.")
            if price < 0 or stock_qty < 0:
                raise ValueError("Цена и количество не могут быть отрицательными.")
        except ValueError as exc:
            show_error(self, str(exc))
            return

        with get_connection() as conn:
            category_id = self._get_or_create(conn, "categories", "category_id", "category_name", category)
            manufacturer_id = self._get_or_create(
                conn, "manufacturers", "manufacturer_id", "manufacturer_name", manufacturer
            )
            supplier_id = self._get_or_create(conn, "suppliers", "supplier_id", "supplier_name", supplier)

            if product_id is None:
                conn.execute(
                    """
                    INSERT INTO products(
                        article, name, description, unit, category_id, manufacturer_id, supplier_id,
                        price, discount_percent, stock_qty, image_path
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        article,
                        name,
                        description,
                        unit,
                        category_id,
                        manufacturer_id,
                        supplier_id,
                        price,
                        discount,
                        stock_qty,
                        image_path,
                    ),
                )
            else:
                conn.execute(
                    """
                    UPDATE products
                    SET article = ?, name = ?, description = ?, unit = ?, category_id = ?,
                        manufacturer_id = ?, supplier_id = ?, price = ?, discount_percent = ?,
                        stock_qty = ?, image_path = ?
                    WHERE product_id = ?
                    """,
                    (
                        article,
                        name,
                        description,
                        unit,
                        category_id,
                        manufacturer_id,
                        supplier_id,
                        price,
                        discount,
                        stock_qty,
                        image_path,
                        product_id,
                    ),
                )

        self._refresh_catalog()
        show_info(self, "Товар сохранен.")

    def _delete_product(self) -> None:
        product_id = self._selected_product_id()
        if product_id is None:
            show_error(self, "Выберите товар.")
            return

        try:
            execute("DELETE FROM products WHERE product_id = ?", (product_id,))
            self._refresh_catalog()
            show_info(self, "Товар удален.")
        except sqlite3.IntegrityError:
            show_error(self, "Нельзя удалить товар: он присутствует в заказах.")

    def _build_product_card_widget(
        self,
        article: str,
        name: str,
        category: str,
        supplier: str,
        price: float,
        discounted: float,
        discount: float,
        stock_qty: int,
        description: str,
        image_name: str,
    ) -> QWidget:
        card = QFrame()
        card.setFrameShape(QFrame.Box)

        if stock_qty == 0:
            card_bg = "#87CEFA"
        elif discount > 15:
            card_bg = "#2E8B57"
        else:
            card_bg = "#FFFFFF"
        card.setStyleSheet(f"QFrame {{ background-color: {card_bg}; }}")

        layout = QHBoxLayout()

        image_label = QLabel("Фото")
        image_label.setAlignment(Qt.AlignCenter)
        image_label.setMinimumSize(160, 130)
        image_label.setStyleSheet("border: 1px solid #000000; background: #FFFFFF;")
        image_path = self._resolve_image_path(image_name)
        if image_path is not None:
            pixmap = QPixmap(str(image_path))
            if not pixmap.isNull():
                image_label.setText("")
                image_label.setPixmap(
                    pixmap.scaled(
                        150,
                        120,
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation,
                    )
                )

        info_widget = QWidget()
        info_layout = QVBoxLayout()
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(3)

        name_label = QLabel(f"{category} | {name}")
        name_label.setStyleSheet("font-weight: bold;")
        name_label.setWordWrap(True)
        info_layout.addWidget(name_label)

        desc_text = description if description else "-"
        info_layout.addWidget(QLabel(f"Описание товара: {desc_text}"))
        info_layout.addWidget(QLabel(f"Поставщик: {supplier}"))
        info_layout.addWidget(QLabel(f"Артикул: {article}"))

        price_row = QHBoxLayout()
        old_price = QLabel(f"{price:.2f}")
        old_price.setStyleSheet("color: #FF0000; text-decoration: line-through;")
        new_price = QLabel(f"{discounted:.2f}")
        new_price.setStyleSheet("color: #000000; font-weight: bold;")
        price_row.addWidget(QLabel("Цена:"))
        price_row.addWidget(old_price)
        price_row.addWidget(new_price)
        price_row.addStretch()
        info_layout.addLayout(price_row)

        info_layout.addWidget(QLabel("Единица измерения: шт."))
        info_layout.addWidget(QLabel(f"Количество на складе: {stock_qty}"))
        info_widget.setLayout(info_layout)

        discount_widget = QWidget()
        discount_layout = QVBoxLayout()
        discount_layout.setContentsMargins(0, 0, 0, 0)
        discount_layout.addStretch()
        discount_text = QLabel(f"Действующая\nскидка\n{discount:.0f}%")
        discount_text.setAlignment(Qt.AlignCenter)
        discount_text.setStyleSheet("font-weight: bold;")
        discount_layout.addWidget(discount_text)
        discount_layout.addStretch()
        discount_widget.setLayout(discount_layout)
        discount_widget.setMinimumWidth(120)
        discount_widget.setStyleSheet("border-left: 1px solid #000000;")

        layout.addWidget(image_label, 2)
        layout.addWidget(info_widget, 5)
        layout.addWidget(discount_widget, 1)
        card.setLayout(layout)
        return card

    @staticmethod
    def _resolve_image_path(image_name: str) -> Path | None:
        if not image_name:
            return None

        source = Path(image_name)
        candidates: list[Path] = []
        if source.is_absolute():
            candidates.append(source)

        import_dir = resolve_import_dir()
        candidates.extend(
            [
                import_dir / image_name,
                BASE_DIR / image_name,
                BASE_DIR / "import" / image_name,
                Path.cwd() / image_name,
                Path.cwd() / "import" / image_name,
            ]
        )

        for candidate in candidates:
            if candidate.exists() and candidate.is_file():
                return candidate.resolve()
        return None

    def _refresh_orders(self) -> None:
        if not hasattr(self, "orders_table"):
            return

        rows = fetch_all(
            """
            SELECT
                o.order_id,
                COALESCE(u.full_name, 'Не указан') AS customer,
                pp.point_address,
                os.status_name,
                o.created_at,
                o.delivery_date,
                o.pickup_code
            FROM orders o
            LEFT JOIN users u ON u.user_id = o.user_id
            JOIN pickup_points pp ON pp.point_id = o.point_id
            JOIN order_statuses os ON os.status_id = o.status_id
            ORDER BY o.order_id
            """
        )
        self.orders_table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            items = fetch_all(
                """
                SELECT p.article, oi.qty
                FROM order_items oi
                JOIN products p ON p.product_id = oi.product_id
                WHERE oi.order_id = ?
                ORDER BY oi.order_item_id
                """,
                (row["order_id"],),
            )
            text_items = ", ".join(f"{x['article']} x{x['qty']}" for x in items)
            values = [
                str(row["order_id"]),
                str(row["customer"]),
                str(row["point_address"]),
                str(row["status_name"]),
                str(row["created_at"]),
                str(row["delivery_date"] or ""),
                str(row["pickup_code"] or ""),
                text_items,
            ]
            for col, value in enumerate(values):
                self.orders_table.setItem(i, col, QTableWidgetItem(value))
        self.orders_table.resizeColumnsToContents()

    def _selected_order_id(self) -> int | None:
        if not hasattr(self, "orders_table"):
            return None
        row = self.orders_table.currentRow()
        if row < 0:
            return None
        return int(self.orders_table.item(row, 0).text())

    def _add_order(self) -> None:
        dialog = OrderDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            self._save_order(dialog, None)

    def _edit_order(self) -> None:
        order_id = self._selected_order_id()
        if order_id is None:
            show_error(self, "Выберите заказ.")
            return
        dialog = OrderDialog(self, order_id=order_id)
        if dialog.exec_() == QDialog.Accepted:
            self._save_order(dialog, order_id)

    def _save_order(self, dialog: OrderDialog, order_id: int | None) -> None:
        full_name = dialog.user_name.text().strip()
        point_id = int(dialog.point.currentData())
        status_id = int(dialog.status.currentData())
        pickup_code = int(dialog.code.value())
        created_at = dialog.created.date().toString("yyyy-MM-dd")
        delivery_date = dialog.delivery.date().toString("yyyy-MM-dd")
        items_text = dialog.items.text().strip()
        parsed_items = self._parse_items(items_text)

        with get_connection() as conn:
            user_id = None
            if full_name:
                login = self._safe_login(full_name)
                conn.execute(
                    """
                    INSERT OR IGNORE INTO users(role_id, full_name, login, password_hash)
                    VALUES (
                        (SELECT role_id FROM roles WHERE role_name = 'Клиент'),
                        ?, ?, ?
                    )
                    """,
                    (full_name, login, "123456"),
                )
                user_row = conn.execute("SELECT user_id FROM users WHERE login = ?", (login,)).fetchone()
                user_id = int(user_row["user_id"]) if user_row else None

            if order_id is None:
                cur = conn.execute(
                    """
                    INSERT INTO orders(user_id, point_id, status_id, pickup_code, created_at, delivery_date)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (user_id, point_id, status_id, pickup_code, created_at, delivery_date),
                )
                order_id = int(cur.lastrowid)
            else:
                conn.execute(
                    """
                    UPDATE orders
                    SET user_id = ?, point_id = ?, status_id = ?, pickup_code = ?, created_at = ?, delivery_date = ?
                    WHERE order_id = ?
                    """,
                    (user_id, point_id, status_id, pickup_code, created_at, delivery_date, order_id),
                )
                conn.execute("DELETE FROM order_items WHERE order_id = ?", (order_id,))

            for article, qty in parsed_items:
                product = conn.execute(
                    "SELECT product_id, price, discount_percent FROM products WHERE article = ?",
                    (article,),
                ).fetchone()
                if product is None:
                    continue
                conn.execute(
                    """
                    INSERT INTO order_items(order_id, product_id, qty, price_at_order, discount_at_order)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (order_id, product["product_id"], qty, product["price"], product["discount_percent"]),
                )

        self._refresh_orders()
        show_info(self, "Заказ сохранен.")

    def _delete_order(self) -> None:
        order_id = self._selected_order_id()
        if order_id is None:
            show_error(self, "Выберите заказ.")
            return
        execute("DELETE FROM orders WHERE order_id = ?", (order_id,))
        self._refresh_orders()
        show_info(self, "Заказ удален.")

    @staticmethod
    def _safe_login(full_name: str) -> str:
        return (
            full_name.strip()
            .lower()
            .replace(" ", ".")
            .replace(",", "")
            .replace(";", "")
            .replace(":", "")
        )

    @staticmethod
    def _parse_items(items_text: str) -> list[tuple[str, int]]:
        if not items_text:
            return []
        parts = [x.strip() for x in items_text.split(",") if x.strip()]
        result: list[tuple[str, int]] = []
        idx = 0
        while idx < len(parts):
            article = parts[idx]
            qty = 1
            if idx + 1 < len(parts):
                try:
                    qty = max(1, int(parts[idx + 1]))
                except ValueError:
                    qty = 1
            result.append((article, qty))
            idx += 2
        return result

    @staticmethod
    def _get_or_create(
        conn: sqlite3.Connection, table: str, pk: str, field: str, value: str
    ) -> int:
        row = conn.execute(f"SELECT {pk} AS id FROM {table} WHERE {field} = ?", (value,)).fetchone()
        if row:
            return int(row["id"])
        conn.execute(f"INSERT INTO {table}({field}) VALUES (?)", (value,))
        row = conn.execute(f"SELECT {pk} AS id FROM {table} WHERE {field} = ?", (value,)).fetchone()
        return int(row["id"])


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

