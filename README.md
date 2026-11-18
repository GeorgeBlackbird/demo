# Demonstration exam: shop management app

My solution for the college demonstration exam. I received the maximum score for it. I am keeping the project as a record of that work; no further updates are planned.

The assignment was a desktop application for a shoe shop, called «ООО Обувь» in the exam materials. It uses Python, PyQt5, SQLite and Excel imports. The interface and supporting documents are in Russian.

## What it includes

- A product catalogue with images, prices, discounts and stock quantities.
- Login and guest access, with different controls for each role.
- Search, supplier filtering and stock sorting for managers and administrators.
- Order management and administrator controls for adding, editing and deleting products.
- Import of products, users, orders and pickup points from Excel files.

## Run locally

Use Python 3.10 or later. From the repository root, with your Python environment activated:

```sh
git clone https://github.com/GeorgeBlackbird/demo.git
cd demo
python -m pip install -r requirements.txt
python main.py
```

On startup, the application creates or initialises `obuv_store.db` using `schema.sql`, then runs the Excel importer. The import runs on subsequent launches too, not just when the database is first created.

Keep the `import/` directory and its images in place. The importer expects these spreadsheets:

```text
Tovar.xlsx
user_import.xlsx
Заказ_import.xlsx
Пункты выдачи_import.xlsx
```

## Roles

| Role | Available interface |
| --- | --- |
| Guest (`Гость`) | Browse the catalogue |
| Client (`Клиент`) | Browse the catalogue after logging in |
| Manager (`Менеджер`) | Search, filter and sort the catalogue; work with orders |
| Administrator (`Администратор`) | Manager controls plus product creation, editing and deletion |

## Windows executable

The existing packaging script uses PyInstaller:

```bat
build_exe.bat
```

Run it from the repository root in an environment where the required Python tools are available. The script installs `requirements.txt` before building and writes `dist/OOO_Obuv_App.exe`.

The current PyInstaller command does not bundle `schema.sql` or the `import/` directory. Keep both beside the executable when distributing it. The application creates its database beside the executable when running as a packaged app.

## Source and exam materials

| File | Purpose |
| --- | --- |
| [`main.py`](main.py) | Startup, data import and window lifecycle |
| [`app_ui.py`](app_ui.py) | Login, role controls, catalogue and order windows |
| [`db.py`](db.py) | SQLite connections, schema initialisation and database helpers |
| [`schema.sql`](schema.sql) | Tables, relationships and constraints |
| [`import_excel.py`](import_excel.py) | Import of the supplied Excel data |
| [Exam brief](<ТЗ ДЭ.md>) | Original task requirements in Russian |

This is a completed exam submission, not an actively maintained shop-management product. The repository has no configured typecheck, lint command or automated test suite. The packaged Windows executable has not been reverified as part of this documentation update.
