from __future__ import annotations

from datetime import date

from PyQt5.QtCore import QSize, Qt
from PyQt5.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QFrame,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from models import Order, OrderProduct, Product, Pvz, User
from ui_common import SessionUser, show_error, show_info, split_full_name


class OrderDialog(QDialog):
    def __init__(self, parent: QWidget, order: Order | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Заказ")
        self.order = order

        self.user_name = QLineEdit()
        self.point = QComboBox()
        self.status = QComboBox()
        self.status.setEditable(True)
        self.number = QSpinBox()
        self.number.setRange(1, 999999)
        self.code = QLineEdit()
        self.created = QDateEdit()
        self.created.setCalendarPopup(True)
        self.created.setDate(date.today())
        self.delivery = QDateEdit()
        self.delivery.setCalendarPopup(True)
        self.delivery.setDate(date.today())
        self.items = QLineEdit()
        self.items.setPlaceholderText("Артикул1, 2, Артикул2, 1")

        for pvz in Pvz.select().order_by(Pvz.city, Pvz.street, Pvz.building):
            self.point.addItem(self._format_pvz(pvz), int(pvz.id))

        known_statuses = {"Новый", "В обработке", "Готов к выдаче", "Выдан", "Отменен"}
        for row in Order.select(Order.status).distinct():
            if row.status:
                known_statuses.add(str(row.status))
        self.status.addItems(sorted(known_statuses))

        form = QFormLayout()
        form.addRow("Номер заказа", self.number)
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

        self._set_default_order_number()
        if order is not None:
            self._load()

    def _set_default_order_number(self) -> None:
        max_number = Order.select(Order.number).order_by(Order.number.desc()).first()
        next_number = int(max_number.number) + 1 if max_number else 1
        self.number.setValue(next_number)

    def _load(self) -> None:
        if self.order is None:
            return
        self.number.setValue(int(self.order.number))
        full_name = " ".join(
            [
                str(self.order.client.first_name or "").strip(),
                str(self.order.client.last_name or "").strip(),
                str(self.order.client.middle_name or "").strip(),
            ]
        ).strip()
        self.user_name.setText(full_name)
        self.code.setText(str(self.order.code or ""))

        for i in range(self.point.count()):
            if self.point.itemData(i) == int(self.order.pvz_id):
                self.point.setCurrentIndex(i)
                break
        status_index = self.status.findText(str(self.order.status))
        if status_index >= 0:
            self.status.setCurrentIndex(status_index)
        else:
            self.status.setEditText(str(self.order.status))

        self.created.setDate(self.order.order_date)
        self.delivery.setDate(self.order.delivery_date)

        items = (
            OrderProduct.select(OrderProduct, Product)
            .join(Product)
            .where(OrderProduct.order == self.order)
            .order_by(OrderProduct.id)
        )
        item_str = ", ".join(f"{it.product.articul}, {int(it.quantity)}" for it in items)
        self.items.setText(item_str)

    @staticmethod
    def _format_pvz(pvz: Pvz) -> str:
        return f"{pvz.idx}, {pvz.city}, {pvz.street}, {pvz.building}"


class OrdersPanel(QWidget):
    def __init__(self, session: SessionUser) -> None:
        super().__init__()
        self.session = session

        layout = QVBoxLayout()
        self.orders_cards = QListWidget()
        self.orders_cards.setSpacing(5)
        self.orders_cards.setSelectionMode(QListWidget.SingleSelection)
        self.orders_cards.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self.orders_cards.setStyleSheet(
            """
            QListWidget {
                background-color: #FFFFFF;
                border: none;
                outline: none;
            }
            QListWidget::item {
                border: 2px solid #000000;
                margin: 4px;
                padding: 2px;
                background: transparent;
            }
            QListWidget::item:selected {
                border: 2px solid #00FA9A;
                background: transparent;
            }
            """
        )
        layout.addWidget(self.orders_cards)

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

        self.setLayout(layout)
        self.refresh()

    def refresh(self) -> None:
        orders = (
            Order.select(Order, Pvz, User)
            .join(Pvz)
            .switch(Order)
            .join(User)
            .order_by(Order.id)
        )
        self.orders_cards.clear()
        for order in orders:
            items = (
                OrderProduct.select(OrderProduct, Product)
                .join(Product)
                .where(OrderProduct.order == order)
                .order_by(OrderProduct.id)
            )
            text_items = ", ".join(f"{x.product.articul} x{x.quantity}" for x in items)
            full_name = " ".join(
                [
                    str(order.client.first_name or "").strip(),
                    str(order.client.last_name or "").strip(),
                    str(order.client.middle_name or "").strip(),
                ]
            ).strip()
            list_item = QListWidgetItem()
            list_item.setData(Qt.UserRole, int(order.id))
            list_item.setSizeHint(QSize(0, 165))
            self.orders_cards.addItem(list_item)
            card = self._build_order_card_widget(
                number=int(order.number),
                customer=full_name or "Не указан",
                point=OrderDialog._format_pvz(order.pvz),
                status=str(order.status),
                order_date=str(order.order_date),
                delivery_date=str(order.delivery_date),
                code=str(order.code or ""),
                items=text_items,
            )
            self.orders_cards.setItemWidget(list_item, card)

        if self.orders_cards.count() > 0:
            self.orders_cards.setCurrentRow(0)

    def _selected_order(self) -> Order | None:
        item = self.orders_cards.currentItem()
        if item is None:
            return None
        value = item.data(Qt.UserRole)
        if value is None:
            return None
        return Order.get_or_none(Order.id == int(value))

    def _add_order(self) -> None:
        dialog = OrderDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            self._save_order(dialog, order=None)

    def _edit_order(self) -> None:
        order = self._selected_order()
        if order is None:
            show_error(self, "Выберите заказ.")
            return
        dialog = OrderDialog(self, order=order)
        if dialog.exec_() == QDialog.Accepted:
            self._save_order(dialog, order=order)

    def _save_order(self, dialog: OrderDialog, order: Order | None) -> None:
        full_name = dialog.user_name.text().strip()
        if not full_name:
            show_error(self, "Введите ФИО клиента.")
            return

        status_value = dialog.status.currentText().strip()
        if not status_value:
            show_error(self, "Введите статус заказа.")
            return

        parsed_items = self._parse_items(dialog.items.text().strip())
        if not parsed_items:
            show_error(self, "Добавьте хотя бы одну позицию в заказ.")
            return

        product_qty_list: list[tuple[Product, int]] = []
        for article, qty in parsed_items:
            product = Product.get_or_none(Product.articul == article)
            if product is None:
                show_error(self, f"Товар с артикулом '{article}' не найден.")
                return
            product_qty_list.append((product, qty))

        first_name, last_name, middle_name = split_full_name(full_name)
        login = self._safe_login(full_name)
        client = User.get_or_none(User.login == login)
        if client is None:
            client = User.create(
                first_name=first_name or "Клиент",
                last_name=last_name or "",
                middle_name=middle_name or "",
                login=login,
                password="123456",
                role="Клиент",
            )

        pvz_id = int(dialog.point.currentData())
        pvz = Pvz.get_by_id(pvz_id)
        data = {
            "number": int(dialog.number.value()),
            "order_date": dialog.created.date().toPyDate(),
            "delivery_date": dialog.delivery.date().toPyDate(),
            "code": dialog.code.text().strip(),
            "status": status_value,
            "pvz": pvz,
            "client": client,
        }

        if order is None:
            order = Order.create(**data)
        else:
            Order.update(**data).where(Order.id == order.id).execute()
            OrderProduct.delete().where(OrderProduct.order == order).execute()
            order = Order.get_by_id(order.id)

        for product, qty in product_qty_list:
            OrderProduct.create(order=order, product=product, quantity=qty)

        self.refresh()
        show_info(self, "Заказ сохранен.")

    def _delete_order(self) -> None:
        order = self._selected_order()
        if order is None:
            show_error(self, "Выберите заказ.")
            return
        OrderProduct.delete().where(OrderProduct.order == order).execute()
        order.delete_instance()
        self.refresh()
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

    def _build_order_card_widget(
        self,
        number: int,
        customer: str,
        point: str,
        status: str,
        order_date: str,
        delivery_date: str,
        code: str,
        items: str,
    ) -> QWidget:
        card = QFrame()
        card.setObjectName("orderCard")
        card.setFrameShape(QFrame.NoFrame)
        card_bg = self._status_color(status)
        card.setStyleSheet(
            f"""
            QFrame#orderCard {{
                background-color: {card_bg};
                border: 2px solid #000000;
            }}
            QFrame#orderCard QWidget {{
                background-color: transparent;
            }}
            QFrame#orderCard QLabel {{
                background-color: transparent;
            }}
            QWidget#orderStatusStrip {{
                background-color: transparent;
                border-left: 1px solid #000000;
            }}
            """
        )

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        info_widget = QWidget()
        info_layout = QVBoxLayout()
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(3)

        title = QLabel(f"Заказ №{number} | {status}")
        title.setStyleSheet("font-weight: bold; background: transparent;")
        title.setWordWrap(True)
        info_layout.addWidget(title)
        info_layout.addWidget(QLabel(f"Клиент: {customer}"))
        info_layout.addWidget(QLabel(f"Пункт выдачи: {point}"))
        info_layout.addWidget(QLabel(f"Дата заказа: {order_date}"))
        info_layout.addWidget(QLabel(f"Дата доставки: {delivery_date}"))
        info_layout.addWidget(QLabel(f"Код получения: {code or '-'}"))
        info_layout.addWidget(QLabel(f"Позиции: {items or '-'}"))
        info_widget.setLayout(info_layout)

        status_widget = QWidget()
        status_layout = QVBoxLayout()
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.addStretch()
        status_text = QLabel(f"Статус\n{status}")
        status_text.setAlignment(Qt.AlignCenter)
        status_text.setStyleSheet("font-weight: bold; background: transparent;")
        status_layout.addWidget(status_text)
        status_layout.addStretch()
        status_widget.setObjectName("orderStatusStrip")
        status_widget.setLayout(status_layout)
        status_widget.setMinimumWidth(150)

        layout.addWidget(info_widget, 6)
        layout.addWidget(status_widget, 1)
        card.setLayout(layout)
        return card

    @staticmethod
    def _status_color(status: str) -> str:
        normalized = status.strip().lower()
        if normalized in {"выдан"}:
            return "#EAFCEB"
        if normalized in {"отменен"}:
            return "#FFECEC"
        if normalized in {"готов к выдаче"}:
            return "#E9FFF8"
        if normalized in {"в обработке"}:
            return "#FFFBEA"
        return "#FFFFFF"
