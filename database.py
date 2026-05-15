import sqlite3
import os
import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stocks.db")

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS recommendations (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_name  TEXT NOT NULL,
    ticker      TEXT NOT NULL,
    exchange    TEXT NOT NULL,
    yf_symbol   TEXT NOT NULL,
    rec_date    TEXT,
    entry_price REAL NOT NULL,
    target1     REAL,
    target2     REAL,
    target3     REAL,
    stop_loss   REAL,
    notes       TEXT,
    status      TEXT DEFAULT 'Active',
    created_at  TEXT DEFAULT (datetime('now')),
    updated_at  TEXT DEFAULT (datetime('now'))
);
"""

SEED_DATA = [
    {
        "stock_name": "Tata Consultancy Services",
        "ticker": "TCS",
        "exchange": "NSE",
        "yf_symbol": "TCS.NS",
        "rec_date": "2024-01-15",
        "entry_price": 3800,
        "target1": 3950,
        "target2": 4100,
        "target3": 4300,
        "stop_loss": 3650,
        "notes": "Strong IT sector play",
        "status": "Active",
    },
    {
        "stock_name": "HDFC Bank",
        "ticker": "HDFCBANK",
        "exchange": "NSE",
        "yf_symbol": "HDFCBANK.NS",
        "rec_date": "2024-02-10",
        "entry_price": 1650,
        "target1": 1720,
        "target2": 1800,
        "target3": None,
        "stop_loss": 1580,
        "notes": "Banking sector momentum",
        "status": "Active",
    },
    {
        "stock_name": "Infosys",
        "ticker": "INFY",
        "exchange": "NSE",
        "yf_symbol": "INFY.NS",
        "rec_date": "2024-03-05",
        "entry_price": 1400,
        "target1": 1480,
        "target2": 1550,
        "target3": 1650,
        "stop_loss": 1340,
        "notes": "IT recovery trade",
        "status": "Watching",
    },
]


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    try:
        conn.execute(CREATE_TABLE_SQL)
        conn.commit()
        row = conn.execute("SELECT COUNT(*) as cnt FROM recommendations").fetchone()
        if row["cnt"] == 0:
            _seed(conn)
    finally:
        conn.close()


def _seed(conn):
    sql = """
    INSERT INTO recommendations
        (stock_name, ticker, exchange, yf_symbol, rec_date, entry_price,
         target1, target2, target3, stop_loss, notes, status)
    VALUES
        (:stock_name, :ticker, :exchange, :yf_symbol, :rec_date, :entry_price,
         :target1, :target2, :target3, :stop_loss, :notes, :status)
    """
    for row in SEED_DATA:
        conn.execute(sql, row)
    conn.commit()


def row_to_dict(row):
    return dict(row)


def get_all():
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM recommendations ORDER BY CASE status WHEN 'Active' THEN 0 ELSE 1 END, rec_date DESC"
        ).fetchall()
        return [row_to_dict(r) for r in rows]
    finally:
        conn.close()


def get_by_id(rec_id):
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM recommendations WHERE id = ?", (rec_id,)
        ).fetchone()
        return row_to_dict(row) if row else None
    finally:
        conn.close()


def insert(data: dict):
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            INSERT INTO recommendations
                (stock_name, ticker, exchange, yf_symbol, rec_date, entry_price,
                 target1, target2, target3, stop_loss, notes, status)
            VALUES
                (:stock_name, :ticker, :exchange, :yf_symbol, :rec_date, :entry_price,
                 :target1, :target2, :target3, :stop_loss, :notes, :status)
            """,
            data,
        )
        conn.commit()
        return get_by_id(cur.lastrowid)
    finally:
        conn.close()


def update(rec_id: int, data: dict):
    conn = get_connection()
    try:
        allowed = {
            "stock_name", "ticker", "exchange", "yf_symbol", "rec_date",
            "entry_price", "target1", "target2", "target3", "stop_loss",
            "notes", "status",
        }
        fields = {k: v for k, v in data.items() if k in allowed}
        if not fields:
            return get_by_id(rec_id)
        set_clause = ", ".join(f"{k} = :{k}" for k in fields)
        fields["id"] = rec_id
        fields["updated_at"] = datetime.datetime.utcnow().isoformat()
        conn.execute(
            f"UPDATE recommendations SET {set_clause}, updated_at = :updated_at WHERE id = :id",
            fields,
        )
        conn.commit()
        return get_by_id(rec_id)
    finally:
        conn.close()


def delete(rec_id: int):
    conn = get_connection()
    try:
        conn.execute("DELETE FROM recommendations WHERE id = ?", (rec_id,))
        conn.commit()
        return True
    finally:
        conn.close()
