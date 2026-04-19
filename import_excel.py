from __future__ import annotations

import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Iterable

from openpyxl import load_workbook

from db import BASE_DIR, get_connection, init_db, upsert_user


def resolve_import_dir() -> Path:
    candidates = [
        BASE_DIR / "import",
        BASE_DIR.parent / "import",
        Path.cwd() / "import",
    ]
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(Path(meipass) / "import")

    for path in candidates:
        if path.exists() and path.is_dir():
            return path
    return BASE_DIR / "import"


def _read_rows(path: Path) -> list[tuple]:
    wb = load_workbook(path, data_only=True)
    ws = wb.worksheets[0]
    return [tuple(cell for cell in row) for row in ws.iter_rows(values_only=True)]


def _coerce_float(value: object, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def _coerce_int(value: object, default: int = 0) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def _coerce_date(value: object) -> str:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if value is None:
        return datetime.now().date().isoformat()
    as_text = str(value).strip()
    if not as_text:
        return datetime.now().date().isoformat()
    return as_text


def _normalize_role(role: str) -> str:
    lowered = role.strip().lower()
    if lowered == "администратор":
        return "Администратор"
    if lowered == "менеджер":
        return "Менеджер"
    if lowered == "клиент":
        return "Клиент"
    return "Клиент"


def _safe_login_from_fio(full_name: str) -> str:
    base = re.sub(r"\s+", ".", full_name.strip().lower())
    base = re.sub(r"[^a-zа-я0-9._-]+", "", base)
    return base or f"user_{abs(hash(full_name)) % 100000}"


def _get_or_create_id(
    conn: sqlite3.Connection, table: str, pk_column: str, column: str, value: str
) -> int:
    row = conn.execute(
        f"SELECT {pk_column} AS id FROM {table} WHERE {column} = ?",
        (value,),
    ).fetchone()
    if row:
        return int(row["id"])

    conn.execute(f"INSERT INTO {table}({column}) VALUES (?)", (value,))
    row = conn.execute(
        f"SELECT {pk_column} AS id FROM {table} WHERE {column} = ?",
        (value,),
    ).fetchone()
    return int(row["id"])


def _parse_order_items(raw: object) -> Iterable[tuple[str, int]]:
    if raw is None:
        return []
    parts = [chunk.strip() for chunk in str(raw).split(",") if chunk.strip()]
    result: list[tuple[str, int]] = []
    for idx in range(0, len(parts), 2):
        article = parts[idx]
        qty = 1
        if idx + 1 < len(parts):
            qty = _coerce_int(parts[idx + 1], 1)
            if qty <= 0:
                qty = 1
        result.append((article, qty))
    return result


def import_all(import_dir: Path | None = None) -> dict[str, int]:
    if import_dir is None:
        import_dir = resolve_import_dir()

    init_db()
    product_file = import_dir / "Tovar.xlsx"
    users_file = import_dir / "user_import.xlsx"
    orders_file = import_dir / "Заказ_import.xlsx"
    pickup_file = import_dir / "Пункты выдачи_import.xlsx"

    if not product_file.exists() or not users_file.exists() or not orders_file.exists() or not pickup_file.exists():
        raise FileNotFoundError("В папке import не хватает обязательных Excel-файлов.")

    rows_products = _read_rows(product_file)
    rows_users = _read_rows(users_file)
    rows_orders = _read_rows(orders_file)
    rows_pickups = _read_rows(pickup_file)

    imported_products = 0
    imported_users = 0
    imported_orders = 0
    imported_items = 0

    with get_connection() as conn:
        for row in rows_pickups:
            if not row or not row[0]:
                continue
            conn.execute(
                "INSERT OR IGNORE INTO pickup_points(point_address) VALUES (?)",
                (str(row[0]).strip(),),
            )

        for row in rows_users[1:]:
            if not row or not row[2]:
                continue
            role_name = _normalize_role(str(row[0] or "Клиент"))
            full_name = str(row[1] or "").strip()
            login = str(row[2]).strip()
            password = str(row[3] or "123456").strip()
            upsert_user(conn, role_name, full_name, login, password)
            imported_users += 1

        for row in rows_products[1:]:
            if not row or not row[0]:
                continue
            article = str(row[0]).strip()
            name = str(row[1] or "").strip()
            unit = str(row[2] or "шт.").strip()
            price = _coerce_float(row[3], 0.0)
            supplier_name = str(row[4] or "Не указан").strip()
            manufacturer_name = str(row[5] or "Не указан").strip()
            category_name = str(row[6] or "Без категории").strip()
            discount = _coerce_float(row[7], 0.0)
            stock_qty = _coerce_int(row[8], 0)
            description = str(row[9] or "").strip()
            image_path = str(row[10] or "").strip()

            supplier_id = _get_or_create_id(
                conn, "suppliers", "supplier_id", "supplier_name", supplier_name
            )
            manufacturer_id = _get_or_create_id(
                conn, "manufacturers", "manufacturer_id", "manufacturer_name", manufacturer_name
            )
            category_id = _get_or_create_id(
                conn, "categories", "category_id", "category_name", category_name
            )

            conn.execute(
                """
                INSERT INTO products(
                    article, name, description, unit, category_id, manufacturer_id,
                    supplier_id, price, discount_percent, stock_qty, image_path
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(article) DO UPDATE SET
                    name = excluded.name,
                    description = excluded.description,
                    unit = excluded.unit,
                    category_id = excluded.category_id,
                    manufacturer_id = excluded.manufacturer_id,
                    supplier_id = excluded.supplier_id,
                    price = excluded.price,
                    discount_percent = excluded.discount_percent,
                    stock_qty = excluded.stock_qty,
                    image_path = excluded.image_path
                """,
                (
                    article,
                    name,
                    description,
                    unit,
                    category_id,
                    manufacturer_id,
                    supplier_id,
                    max(price, 0.0),
                    min(max(discount, 0.0), 100.0),
                    max(stock_qty, 0),
                    image_path,
                ),
            )
            imported_products += 1

        for row in rows_orders[1:]:
            if not row or not row[0]:
                continue
            order_id = _coerce_int(row[0], 0)
            if order_id <= 0:
                continue
            article_list_raw = row[1]
            created_at = _coerce_date(row[2])
            delivery_date = _coerce_date(row[3])
            point_id = _coerce_int(row[4], 1)
            customer_name = str(row[5] or "").strip()
            pickup_code = _coerce_int(row[6], 0)
            status_name = str(row[7] or "Новый").strip()

            if customer_name:
                synthetic_login = _safe_login_from_fio(customer_name)
                upsert_user(conn, "Клиент", customer_name, synthetic_login, "123456")
                user_row = conn.execute(
                    "SELECT user_id FROM users WHERE login = ?",
                    (synthetic_login,),
                ).fetchone()
                user_id = int(user_row["user_id"]) if user_row else None
            else:
                user_id = None

            point_row = conn.execute(
                "SELECT point_id FROM pickup_points WHERE point_id = ?",
                (point_id,),
            ).fetchone()
            if point_row is None:
                fallback = conn.execute(
                    "SELECT point_id FROM pickup_points ORDER BY point_id LIMIT 1"
                ).fetchone()
                point_id = int(fallback["point_id"]) if fallback else 1

            status_id = _get_or_create_id(
                conn, "order_statuses", "status_id", "status_name", status_name
            )

            conn.execute(
                """
                INSERT INTO orders(order_id, user_id, point_id, status_id, pickup_code, created_at, delivery_date)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(order_id) DO UPDATE SET
                    user_id = excluded.user_id,
                    point_id = excluded.point_id,
                    status_id = excluded.status_id,
                    pickup_code = excluded.pickup_code,
                    created_at = excluded.created_at,
                    delivery_date = excluded.delivery_date
                """,
                (order_id, user_id, point_id, status_id, pickup_code, created_at, delivery_date),
            )
            imported_orders += 1

            conn.execute("DELETE FROM order_items WHERE order_id = ?", (order_id,))
            for article, qty in _parse_order_items(article_list_raw):
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
                    (
                        order_id,
                        int(product["product_id"]),
                        qty,
                        float(product["price"]),
                        float(product["discount_percent"]),
                    ),
                )
                imported_items += 1

    return {
        "products": imported_products,
        "users": imported_users,
        "orders": imported_orders,
        "order_items": imported_items,
    }


if __name__ == "__main__":
    stats = import_all()
    print("Импорт завершен:", stats)

