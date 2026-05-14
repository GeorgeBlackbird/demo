from __future__ import annotations

from decimal import Decimal, InvalidOperation
from pathlib import Path

from PyQt5.QtCore import QSize, Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
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

from models import OrderProduct, Product
from ui_common import SessionUser, show_error, show_info


class ProductDialog(QDialog):
    def __init__(self, parent: QWidget, product: Product | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Товар")
        self.product = product

        self.articul = QLineEdit()
        self.name = QLineEdit()
        self.description = QLineEdit()
        self.ed_izm = QLineEdit("шт.")
        self.category = QLineEdit()
        self.creator = QLineEdit()
        self.supplier = QLineEdit()
        self.price = QLineEdit("0")
        self.discount = QSpinBox()
        self.discount.setRange(0, 100)
        self.quantity = QSpinBox()
        self.quantity.setRange(0, 99999)
        self.photo = QLineEdit()

        form = QFormLayout()
        form.addRow("Артикул", self.articul)
        form.addRow("Название", self.name)
        form.addRow("Описание", self.description)
        form.addRow("Ед. изм.", self.ed_izm)
        form.addRow("Категория", self.category)
        form.addRow("Производитель", self.creator)
        form.addRow("Поставщик", self.supplier)
        form.addRow("Цена", self.price)
        form.addRow("Скидка (%)", self.discount)
        form.addRow("Кол-во", self.quantity)
        form.addRow("Путь к фото", self.photo)

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

        if product is not None:
            self._load()

    def _load(self) -> None:
        if self.product is None:
            return
        self.articul.setText(str(self.product.articul))
        self.name.setText(str(self.product.name))
        self.description.setText(str(self.product.description or ""))
        self.ed_izm.setText(str(self.product.ed_izm))
        self.category.setText(str(self.product.category))
        self.creator.setText(str(self.product.creator))
        self.supplier.setText(str(self.product.supplier))
        self.price.setText(str(self.product.price))
        self.discount.setValue(int(self.product.discount or 0))
        self.quantity.setValue(int(self.product.quantity or 0))
        self.photo.setText(str(self.product.photo or ""))


class CatalogPanel(QWidget):
    def __init__(self, session: SessionUser) -> None:
        super().__init__()
        self.session = session

        layout = QVBoxLayout()

        controls = QGridLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск по артикулу / названию / описанию")
        self.search_input.textChanged.connect(self.refresh)

        self.supplier_filter = QComboBox()
        self.supplier_filter.currentIndexChanged.connect(self.refresh)

        self.sort_stock = QComboBox()
        self.sort_stock.addItems(["Без сортировки", "Остаток по возрастанию", "Остаток по убыванию"])
        self.sort_stock.currentIndexChanged.connect(self.refresh)

        controls.addWidget(QLabel("Поиск"), 0, 0)
        controls.addWidget(self.search_input, 0, 1)
        controls.addWidget(QLabel("Поставщик"), 1, 0)
        controls.addWidget(self.supplier_filter, 1, 1)
        controls.addWidget(QLabel("Сортировка"), 2, 0)
        controls.addWidget(self.sort_stock, 2, 1)
        layout.addLayout(controls)

        self.catalog_cards = QListWidget()
        self.catalog_cards.setSpacing(5)
        self.catalog_cards.setSelectionMode(QListWidget.SingleSelection)
        self.catalog_cards.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self.catalog_cards.setStyleSheet(
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

        self.setLayout(layout)
        self._configure_access()
        self._load_supplier_filter()
        self.refresh()

    def _configure_access(self) -> None:
        is_manager_or_admin = self.session.role_name in ("Менеджер", "Администратор")
        is_admin = self.session.role_name == "Администратор"
        self.search_input.setEnabled(is_manager_or_admin)
        self.supplier_filter.setEnabled(is_manager_or_admin)
        self.sort_stock.setEnabled(is_manager_or_admin)
        self.add_product_btn.setVisible(is_admin)
        self.edit_product_btn.setVisible(is_admin)
        self.delete_product_btn.setVisible(is_admin)

    def _load_supplier_filter(self) -> None:
        self.supplier_filter.blockSignals(True)
        current = self.supplier_filter.currentText()
        self.supplier_filter.clear()
        self.supplier_filter.addItem("Все поставщики")
        query = Product.select(Product.supplier).distinct().order_by(Product.supplier)
        for row in query:
            if row.supplier:
                self.supplier_filter.addItem(str(row.supplier))
        idx = self.supplier_filter.findText(current)
        if idx >= 0:
            self.supplier_filter.setCurrentIndex(idx)
        self.supplier_filter.blockSignals(False)

    def refresh(self) -> None:
        query = Product.select()
        text = self.search_input.text().strip()
        if text and self.search_input.isEnabled():
            query = query.where(
                (Product.articul.icontains(text))
                | (Product.name.icontains(text))
                | (Product.description.icontains(text))
            )

        supplier = self.supplier_filter.currentText().strip()
        if supplier and supplier != "Все поставщики" and self.supplier_filter.isEnabled():
            query = query.where(Product.supplier == supplier)

        if self.sort_stock.isEnabled():
            sort_mode = self.sort_stock.currentText()
            if sort_mode == "Остаток по возрастанию":
                query = query.order_by(Product.quantity.asc())
            elif sort_mode == "Остаток по убыванию":
                query = query.order_by(Product.quantity.desc())

        self.catalog_cards.clear()
        for product in query:
            discount = float(product.discount or 0)
            price = float(product.price or 0)
            discounted = price * (1.0 - discount / 100.0)

            list_item = QListWidgetItem()
            list_item.setData(Qt.UserRole, int(product.id))
            list_item.setSizeHint(QSize(0, 170))
            self.catalog_cards.addItem(list_item)
            card = self._build_product_card_widget(product, price, discounted, discount)
            self.catalog_cards.setItemWidget(list_item, card)

        self._load_supplier_filter()
        if self.catalog_cards.count() > 0:
            self.catalog_cards.setCurrentRow(0)

    def _selected_product(self) -> Product | None:
        item = self.catalog_cards.currentItem()
        if item is None:
            return None
        value = item.data(Qt.UserRole)
        if value is None:
            return None
        return Product.get_or_none(Product.id == int(value))

    def _add_product(self) -> None:
        dialog = ProductDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            self._save_product(dialog, product=None)

    def _edit_product(self) -> None:
        product = self._selected_product()
        if product is None:
            show_error(self, "Выберите товар.")
            return
        dialog = ProductDialog(self, product=product)
        if dialog.exec_() == QDialog.Accepted:
            self._save_product(dialog, product=product)

    def _save_product(self, dialog: ProductDialog, product: Product | None) -> None:
        try:
            articul = dialog.articul.text().strip()
            name = dialog.name.text().strip()
            category = dialog.category.text().strip()
            creator = dialog.creator.text().strip()
            supplier = dialog.supplier.text().strip()
            ed_izm = dialog.ed_izm.text().strip() or "шт."
            description = dialog.description.text().strip()
            photo = dialog.photo.text().strip()
            price = Decimal(dialog.price.text().replace(",", "."))
            quantity = int(dialog.quantity.value())
            discount = int(dialog.discount.value())

            if not articul or not name or not category or not creator or not supplier:
                raise ValueError("Заполните обязательные поля товара.")
            if price < 0 or quantity < 0:
                raise ValueError("Цена и количество не могут быть отрицательными.")
        except (InvalidOperation, ValueError) as exc:
            show_error(self, str(exc))
            return

        data = {
            "articul": articul,
            "name": name,
            "ed_izm": ed_izm,
            "price": price,
            "supplier": supplier,
            "creator": creator,
            "category": category,
            "discount": discount,
            "quantity": quantity,
            "description": description,
            "photo": photo,
        }
        if product is None:
            Product.create(**data)
        else:
            Product.update(**data).where(Product.id == product.id).execute()

        self.refresh()
        show_info(self, "Товар сохранен.")

    def _delete_product(self) -> None:
        product = self._selected_product()
        if product is None:
            show_error(self, "Выберите товар.")
            return
        if OrderProduct.select().where(OrderProduct.product == product).exists():
            show_error(self, "Нельзя удалить товар: он присутствует в заказах.")
            return
        product.delete_instance()
        self.refresh()
        show_info(self, "Товар удален.")

    def _build_product_card_widget(
        self,
        product: Product,
        price: float,
        discounted: float,
        discount: float,
    ) -> QWidget:
        card = QFrame()
        card.setObjectName("productCard")
        card.setFrameShape(QFrame.NoFrame)

        if int(product.quantity or 0) == 0:
            card_bg = "#87CEFA"
        elif discount > 15:
            card_bg = "#2E8B57"
        else:
            card_bg = "#FFFFFF"
        card.setStyleSheet(
            f"""
            QFrame#productCard {{
                background-color: {card_bg};
                border: 2px solid #000000;
            }}
            QFrame#productCard QWidget {{
                background-color: transparent;
            }}
            QFrame#productCard QLabel {{
                background-color: transparent;
            }}
            QLabel#productPhoto {{
                background-color: #FFFFFF;
                border: 1px solid #000000;
            }}
            QWidget#productDiscountStrip {{
                background-color: transparent;
                border-left: 1px solid #000000;
            }}
            """
        )

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        image_label = QLabel("Фото")
        image_label.setObjectName("productPhoto")
        image_label.setAlignment(Qt.AlignCenter)
        image_label.setMinimumSize(160, 130)

        image_path = self._resolve_image_path(str(product.photo or ""))
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
        name_label = QLabel(f"{product.category} | {product.name}")
        name_label.setStyleSheet("font-weight: bold; background: transparent;")
        name_label.setWordWrap(True)
        info_layout.addWidget(name_label)
        info_layout.addWidget(QLabel(f"Описание товара: {str(product.description or '-') }"))
        info_layout.addWidget(QLabel(f"Поставщик: {product.supplier}"))
        info_layout.addWidget(QLabel(f"Артикул: {product.articul}"))

        price_row = QHBoxLayout()
        old_price = QLabel(f"{price:.2f}")
        old_price.setStyleSheet("color: #FF0000; text-decoration: line-through; background: transparent;")
        new_price = QLabel(f"{discounted:.2f}")
        new_price.setStyleSheet("color: #000000; font-weight: bold; background: transparent;")
        price_row.addWidget(QLabel("Цена:"))
        price_row.addWidget(old_price)
        price_row.addWidget(new_price)
        price_row.addStretch()
        info_layout.addLayout(price_row)

        info_layout.addWidget(QLabel(f"Единица измерения: {product.ed_izm}"))
        info_layout.addWidget(QLabel(f"Количество на складе: {int(product.quantity or 0)}"))
        info_widget.setLayout(info_layout)

        discount_widget = QWidget()
        discount_layout = QVBoxLayout()
        discount_layout.setContentsMargins(0, 0, 0, 0)
        discount_layout.addStretch()
        discount_text = QLabel(f"Действующая\nскидка\n{discount:.0f}%")
        discount_text.setAlignment(Qt.AlignCenter)
        discount_text.setStyleSheet("font-weight: bold; background: transparent;")
        discount_layout.addWidget(discount_text)
        discount_layout.addStretch()
        discount_widget.setObjectName("productDiscountStrip")
        discount_widget.setLayout(discount_layout)
        discount_widget.setMinimumWidth(120)

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
        base = Path(__file__).resolve().parent
        candidates.extend(
            [
                base / image_name,
                base / "import" / image_name,
                Path.cwd() / image_name,
                Path.cwd() / "import" / image_name,
            ]
        )
        for candidate in candidates:
            if candidate.exists() and candidate.is_file():
                return candidate.resolve()
        return None
