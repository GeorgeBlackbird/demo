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


def normalize_password(value: str) -> str:
    return value.strip()


def init_db() -> None:
    schema_path = _resolve_schema_path()
    if schema_path is None:
        raise FileNotFoundError("Не найден schema.sql. Положите файл рядом с приложением.")

    schema = schema_path.read_text(encoding="utf-8")

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
        (role_id, full_name, login, normalize_password(password)),
    )

