import hashlib
import sqlite3
import sys
from pathlib import Path
from typing import Any


def _runtime_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


BASE_DIR = _runtime_base_dir()
DB_PATH = BASE_DIR / "obuv_store.db"


EMBEDDED_SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS roles (
    role_id INTEGER PRIMARY KEY AUTOINCREMENT,
    role_name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    role_id INTEGER NOT NULL,
    full_name TEXT NOT NULL,
    login TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    FOREIGN KEY (role_id) REFERENCES roles(role_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS categories (
    category_id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS manufacturers (
    manufacturer_id INTEGER PRIMARY KEY AUTOINCREMENT,
    manufacturer_name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS suppliers (
    supplier_id INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS products (
    product_id INTEGER PRIMARY KEY AUTOINCREMENT,
    article TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    description TEXT,
    unit TEXT NOT NULL DEFAULT 'шт.',
    category_id INTEGER NOT NULL,
    manufacturer_id INTEGER NOT NULL,
    supplier_id INTEGER NOT NULL,
    price REAL NOT NULL CHECK (price >= 0),
    discount_percent REAL NOT NULL DEFAULT 0 CHECK (discount_percent BETWEEN 0 AND 100),
    stock_qty INTEGER NOT NULL DEFAULT 0 CHECK (stock_qty >= 0),
    image_path TEXT,
    FOREIGN KEY (category_id) REFERENCES categories(category_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    FOREIGN KEY (manufacturer_id) REFERENCES manufacturers(manufacturer_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    FOREIGN KEY (supplier_id) REFERENCES suppliers(supplier_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS pickup_points (
    point_id INTEGER PRIMARY KEY AUTOINCREMENT,
    point_address TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS order_statuses (
    status_id INTEGER PRIMARY KEY AUTOINCREMENT,
    status_name TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS orders (
    order_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    point_id INTEGER NOT NULL,
    status_id INTEGER NOT NULL,
    pickup_code INTEGER,
    created_at TEXT NOT NULL,
    delivery_date TEXT,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
        ON UPDATE CASCADE
        ON DELETE SET NULL,
    FOREIGN KEY (point_id) REFERENCES pickup_points(point_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,
    FOREIGN KEY (status_id) REFERENCES order_statuses(status_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS order_items (
    order_item_id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    qty INTEGER NOT NULL CHECK (qty > 0),
    price_at_order REAL NOT NULL CHECK (price_at_order >= 0),
    discount_at_order REAL NOT NULL DEFAULT 0 CHECK (discount_at_order BETWEEN 0 AND 100),
    FOREIGN KEY (order_id) REFERENCES orders(order_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(product_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT
);
"""


def _resolve_schema_path() -> Path | None:
    candidates = [
        BASE_DIR / "schema.sql",
        BASE_DIR.parent / "schema.sql",
        Path.cwd() / "schema.sql",
    ]
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        candidates.append(Path(meipass) / "schema.sql")

    for path in candidates:
        if path.exists():
            return path
    return None


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def is_sha256_hash(value: str) -> bool:
    if len(value) != 64:
        return False
    return all(ch in "0123456789abcdef" for ch in value.lower())


def verify_password(input_password: str, stored_password_hash: str) -> bool:
    candidates = [input_password, input_password.strip()]
    if is_sha256_hash(stored_password_hash):
        return any(hash_password(candidate) == stored_password_hash for candidate in candidates)

    # Fallback for legacy/plaintext password records.
    return any(candidate == stored_password_hash for candidate in candidates)


def init_db() -> None:
    schema_path = _resolve_schema_path()
    if schema_path is not None:
        schema = schema_path.read_text(encoding="utf-8")
    else:
        schema = EMBEDDED_SCHEMA

    with get_connection() as conn:
        conn.executescript(schema)
        seed_roles(conn)


def seed_roles(conn: sqlite3.Connection) -> None:
    roles = ["Гость", "Клиент", "Менеджер", "Администратор"]
    for role_name in roles:
        conn.execute(
            "INSERT OR IGNORE INTO roles(role_name) VALUES (?)",
            (role_name,),
        )


def fetch_all(query: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
    with get_connection() as conn:
        return list(conn.execute(query, params).fetchall())


def fetch_one(query: str, params: tuple[Any, ...] = ()) -> sqlite3.Row | None:
    with get_connection() as conn:
        return conn.execute(query, params).fetchone()


def execute(query: str, params: tuple[Any, ...] = ()) -> None:
    with get_connection() as conn:
        conn.execute(query, params)


def execute_many(query: str, items: list[tuple[Any, ...]]) -> None:
    if not items:
        return
    with get_connection() as conn:
        conn.executemany(query, items)


def get_role_id(conn: sqlite3.Connection, role_name: str) -> int:
    row = conn.execute(
        "SELECT role_id FROM roles WHERE role_name = ?",
        (role_name,),
    ).fetchone()
    if row is None:
        conn.execute("INSERT INTO roles(role_name) VALUES (?)", (role_name,))
        row = conn.execute(
            "SELECT role_id FROM roles WHERE role_name = ?",
            (role_name,),
        ).fetchone()
    return int(row["role_id"])


def upsert_user(
    conn: sqlite3.Connection,
    role_name: str,
    full_name: str,
    login: str,
    password: str,
) -> None:
    role_id = get_role_id(conn, role_name)
    conn.execute(
        """
        INSERT INTO users(role_id, full_name, login, password_hash)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(login) DO UPDATE SET
            role_id = excluded.role_id,
            full_name = excluded.full_name,
            password_hash = excluded.password_hash
        """,
        (role_id, full_name, login, hash_password(password)),
    )

