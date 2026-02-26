"""
資料庫模組 - 使用 SQLite 儲存股票追蹤資料
"""
import sqlite3
import os
from datetime import datetime

DB_PATH = os.environ.get("DB_PATH", os.path.join(os.path.dirname(__file__), "data", "stocks.db"))


def get_db():
    """取得資料庫連線"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """初始化資料表"""
    conn = get_db()
    cursor = conn.cursor()

    # 1. 建立資料表（不含可能缺少的欄位）
    cursor.executescript("""
        CREATE TABLE IF NOT EXISTS config (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            initial_capital REAL NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        );

        CREATE TABLE IF NOT EXISTS batch (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            start_date TEXT NOT NULL,
            allocated_capital REAL NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        );

        CREATE TABLE IF NOT EXISTS stock_record (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            batch_id INTEGER NOT NULL,
            stock_code TEXT NOT NULL,
            stock_name TEXT NOT NULL DEFAULT '未知',
            buy_price REAL NOT NULL DEFAULT 0,
            shares INTEGER NOT NULL DEFAULT 0,
            current_price REAL DEFAULT 0,
            price_updated_at TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (batch_id) REFERENCES batch(id) ON DELETE CASCADE
        );
    """)

    # 2. 升級：若舊資料庫缺少欄位，自動新增
    migrations = [
        "ALTER TABLE config ADD COLUMN fee_discount REAL NOT NULL DEFAULT 0.28",
        "ALTER TABLE stock_record ADD COLUMN is_sold INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE stock_record ADD COLUMN sell_price REAL DEFAULT 0",
        "ALTER TABLE stock_record ADD COLUMN sell_date TEXT",
    ]
    for sql in migrations:
        try:
            cursor.execute(sql)
        except sqlite3.OperationalError:
            pass  # 欄位已存在

    # 3. 確保 config 只有一筆
    cursor.execute("INSERT OR IGNORE INTO config (id, initial_capital, fee_discount) VALUES (1, 0, 0.28)")

    conn.commit()
    conn.close()


# ============ Config CRUD ============

def get_config():
    conn = get_db()
    row = conn.execute("SELECT * FROM config WHERE id = 1").fetchone()
    conn.close()
    result = dict(row) if row else {"id": 1, "initial_capital": 0, "fee_discount": 0.28}
    # 確保 fee_discount 存在
    if "fee_discount" not in result:
        result["fee_discount"] = 0.28
    return result


def update_config(initial_capital, fee_discount=0.28):
    conn = get_db()
    conn.execute(
        "UPDATE config SET initial_capital = ?, fee_discount = ?, updated_at = datetime('now', 'localtime') WHERE id = 1",
        (initial_capital, fee_discount)
    )
    conn.commit()
    conn.close()


# ============ Batch CRUD ============

def create_batch(name, start_date, allocated_capital):
    conn = get_db()
    cursor = conn.execute(
        "INSERT INTO batch (name, start_date, allocated_capital) VALUES (?, ?, ?)",
        (name, start_date, allocated_capital)
    )
    batch_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return batch_id


def get_all_batches():
    conn = get_db()
    rows = conn.execute("SELECT * FROM batch ORDER BY start_date DESC, id DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_batch(batch_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM batch WHERE id = ?", (batch_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def update_batch(batch_id, name, start_date, allocated_capital):
    conn = get_db()
    conn.execute(
        "UPDATE batch SET name = ?, start_date = ?, allocated_capital = ? WHERE id = ?",
        (name, start_date, allocated_capital, batch_id)
    )
    conn.commit()
    conn.close()


def delete_batch(batch_id):
    conn = get_db()
    conn.execute("DELETE FROM batch WHERE id = ?", (batch_id,))
    conn.commit()
    conn.close()


# ============ StockRecord CRUD ============

def add_stock_record(batch_id, stock_code, stock_name, buy_price, shares):
    conn = get_db()
    cursor = conn.execute(
        "INSERT INTO stock_record (batch_id, stock_code, stock_name, buy_price, shares) VALUES (?, ?, ?, ?, ?)",
        (batch_id, stock_code, stock_name, buy_price, shares)
    )
    record_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return record_id


def get_stocks_by_batch(batch_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM stock_record WHERE batch_id = ? ORDER BY id",
        (batch_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_stock_record(record_id, buy_price, shares):
    conn = get_db()
    conn.execute(
        "UPDATE stock_record SET buy_price = ?, shares = ? WHERE id = ?",
        (buy_price, shares, record_id)
    )
    conn.commit()
    conn.close()


def update_stock_current_price(record_id, current_price):
    conn = get_db()
    conn.execute(
        "UPDATE stock_record SET current_price = ?, price_updated_at = datetime('now', 'localtime') WHERE id = ?",
        (current_price, record_id)
    )
    conn.commit()
    conn.close()


def delete_stock_record(record_id):
    conn = get_db()
    conn.execute("DELETE FROM stock_record WHERE id = ?", (record_id,))
    conn.commit()
    conn.close()


def sell_stock(record_id, sell_price, sell_date):
    """標記股票為已賣出"""
    conn = get_db()
    conn.execute(
        "UPDATE stock_record SET is_sold = 1, sell_price = ?, sell_date = ? WHERE id = ?",
        (sell_price, sell_date, record_id)
    )
    conn.commit()
    conn.close()


def unsell_stock(record_id):
    """取消賣出狀態"""
    conn = get_db()
    conn.execute(
        "UPDATE stock_record SET is_sold = 0, sell_price = 0, sell_date = NULL WHERE id = ?",
        (record_id,)
    )
    conn.commit()
    conn.close()


def get_all_stock_records():
    """取得所有股票紀錄（含批次資訊），用於統計"""
    conn = get_db()
    rows = conn.execute("""
        SELECT sr.*, b.name as batch_name, b.start_date as batch_date
        FROM stock_record sr
        JOIN batch b ON sr.batch_id = b.id
        ORDER BY b.start_date DESC, sr.id
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]
