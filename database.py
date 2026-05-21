import sqlite3
import os
import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "stocks.db")
DEFAULT_TAB_NAME = "My Stocks"

TABLE_RECOMMENDATIONS = "recommendations"
TABLE_STOCK_TABS = "stock_tabs"


CREATE_STOCK_TABS_SQL = f"""
CREATE TABLE IF NOT EXISTS {TABLE_STOCK_TABS} (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,
    created_at  TEXT DEFAULT (datetime('now')),
    updated_at  TEXT DEFAULT (datetime('now'))
);
"""

CREATE_RECOMMENDATIONS_SQL = f"""
CREATE TABLE IF NOT EXISTS {TABLE_RECOMMENDATIONS} (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_name  TEXT NOT NULL,
    ticker      TEXT NOT NULL,
    exchange    TEXT NOT NULL,
    yf_symbol   TEXT NOT NULL,
    watchlist_id INTEGER,
    rec_date    TEXT,
    entry_price REAL NOT NULL,
    target1     REAL,
    target2     REAL,
    target3     REAL,
    stop_loss   REAL,
    notes       TEXT,
    status      TEXT DEFAULT 'Active',
    created_at  TEXT DEFAULT (datetime('now')),
    updated_at  TEXT DEFAULT (datetime('now')),
    FOREIGN KEY(watchlist_id) REFERENCES stock_tabs(id) ON DELETE CASCADE
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
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(seed_if_empty: bool = True):
    conn = get_connection()
    try:
        conn.execute(CREATE_STOCK_TABS_SQL)
        conn.execute(CREATE_RECOMMENDATIONS_SQL)
        _ensure_recommendations_schema(conn)

        default_tab_id = _ensure_default_tab(conn)
        _backfill_recommendations_watchlist(conn, default_tab_id)

        conn.commit()
        if seed_if_empty:
            row = conn.execute(f"SELECT COUNT(*) as cnt FROM {TABLE_RECOMMENDATIONS}").fetchone()
            if row["cnt"] == 0:
                _seed(conn, default_tab_id)
    finally:
        conn.close()


def _ensure_recommendations_schema(conn):
    cols = {
        row["name"]
        for row in conn.execute(f"PRAGMA table_info({TABLE_RECOMMENDATIONS})").fetchall()
    }
    if "watchlist_id" not in cols:
        conn.execute(f"ALTER TABLE {TABLE_RECOMMENDATIONS} ADD COLUMN watchlist_id INTEGER")


def _ensure_default_tab(conn) -> int:
    row = conn.execute(
        f"SELECT id FROM {TABLE_STOCK_TABS} WHERE lower(name) = lower(?) LIMIT 1",
        (DEFAULT_TAB_NAME,),
    ).fetchone()
    if row:
        return row["id"]

    fallback = conn.execute(
        f"SELECT id FROM {TABLE_STOCK_TABS} ORDER BY id ASC LIMIT 1"
    ).fetchone()
    if fallback:
        return fallback["id"]

    cur = conn.execute(
        f"INSERT INTO {TABLE_STOCK_TABS} (name) VALUES (?)",
        (DEFAULT_TAB_NAME,),
    )
    return cur.lastrowid


def _backfill_recommendations_watchlist(conn, default_tab_id: int):
    conn.execute(
        f"""
        UPDATE {TABLE_RECOMMENDATIONS}
        SET watchlist_id = ?
        WHERE watchlist_id IS NULL
           OR watchlist_id NOT IN (SELECT id FROM {TABLE_STOCK_TABS})
        """,
        (default_tab_id,),
    )


def _seed(conn, default_tab_id: int):
    sql = """
    INSERT INTO recommendations
        (stock_name, ticker, exchange, yf_symbol, watchlist_id, rec_date, entry_price,
         target1, target2, target3, stop_loss, notes, status)
    VALUES
        (:stock_name, :ticker, :exchange, :yf_symbol, :watchlist_id, :rec_date, :entry_price,
         :target1, :target2, :target3, :stop_loss, :notes, :status)
    """
    for row in SEED_DATA:
        row = dict(row)
        row["watchlist_id"] = default_tab_id
        conn.execute(sql, row)
    conn.commit()


def row_to_dict(row):
    return dict(row)


def get_all(watchlist_id: int = None):
    conn = get_connection()
    try:
        params = []
        where = ""
        if watchlist_id is not None:
            where = "WHERE r.watchlist_id = ?"
            params.append(watchlist_id)
        rows = conn.execute(
            f"""
            SELECT r.*, t.name AS watchlist_name
            FROM {TABLE_RECOMMENDATIONS} r
            LEFT JOIN {TABLE_STOCK_TABS} t ON t.id = r.watchlist_id
            {where}
            ORDER BY CASE r.status WHEN 'Active' THEN 0 ELSE 1 END, r.rec_date DESC
            """,
            params,
        ).fetchall()
        return [row_to_dict(r) for r in rows]
    finally:
        conn.close()


def get_by_id(rec_id):
    conn = get_connection()
    try:
        row = conn.execute(
            f"""
            SELECT r.*, t.name AS watchlist_name
            FROM {TABLE_RECOMMENDATIONS} r
            LEFT JOIN {TABLE_STOCK_TABS} t ON t.id = r.watchlist_id
            WHERE r.id = ?
            """,
            (rec_id,),
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
                (stock_name, ticker, exchange, yf_symbol, watchlist_id, rec_date, entry_price,
                 target1, target2, target3, stop_loss, notes, status)
            VALUES
                (:stock_name, :ticker, :exchange, :yf_symbol, :watchlist_id, :rec_date, :entry_price,
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
            "notes", "status", "watchlist_id",
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
        conn.execute(f"DELETE FROM {TABLE_RECOMMENDATIONS} WHERE id = ?", (rec_id,))
        conn.commit()
        return True
    finally:
        conn.close()


def get_tabs():
    conn = get_connection()
    try:
        rows = conn.execute(
            f"""
            SELECT
                t.id,
                t.name,
                t.created_at,
                t.updated_at,
                COUNT(r.id) AS stock_count
            FROM {TABLE_STOCK_TABS} t
            LEFT JOIN {TABLE_RECOMMENDATIONS} r ON r.watchlist_id = t.id
            GROUP BY t.id, t.name, t.created_at, t.updated_at
            ORDER BY t.created_at ASC, t.id ASC
            """
        ).fetchall()
        return [row_to_dict(r) for r in rows]
    finally:
        conn.close()


def get_tab(tab_id: int):
    conn = get_connection()
    try:
        row = conn.execute(
            f"SELECT * FROM {TABLE_STOCK_TABS} WHERE id = ?",
            (tab_id,),
        ).fetchone()
        return row_to_dict(row) if row else None
    finally:
        conn.close()


def create_tab(name: str):
    conn = get_connection()
    try:
        cur = conn.execute(
            f"INSERT INTO {TABLE_STOCK_TABS} (name) VALUES (?)",
            (name.strip(),),
        )
        conn.commit()
        return get_tab(cur.lastrowid)
    finally:
        conn.close()


def rename_tab(tab_id: int, new_name: str):
    conn = get_connection()
    try:
        conn.execute(
            f"""
            UPDATE {TABLE_STOCK_TABS}
            SET name = ?, updated_at = ?
            WHERE id = ?
            """,
            (new_name.strip(), datetime.datetime.utcnow().isoformat(), tab_id),
        )
        conn.commit()
        return get_tab(tab_id)
    finally:
        conn.close()


def delete_tab(tab_id: int):
    conn = get_connection()
    try:
        tab_count = conn.execute(
            f"SELECT COUNT(*) AS cnt FROM {TABLE_STOCK_TABS}"
        ).fetchone()["cnt"]
        if tab_count <= 1:
            raise ValueError("Cannot delete the last remaining tab")

        fallback = conn.execute(
            f"SELECT id FROM {TABLE_STOCK_TABS} WHERE id != ? ORDER BY id ASC LIMIT 1",
            (tab_id,),
        ).fetchone()
        if not fallback:
            raise ValueError("No fallback tab found")

        conn.execute(
            f"DELETE FROM {TABLE_RECOMMENDATIONS} WHERE watchlist_id = ?",
            (tab_id,),
        )
        conn.execute(f"DELETE FROM {TABLE_STOCK_TABS} WHERE id = ?", (tab_id,))
        conn.commit()
        return fallback["id"]
    finally:
        conn.close()


def find_tab_by_name(name: str):
    conn = get_connection()
    try:
        row = conn.execute(
            f"SELECT * FROM {TABLE_STOCK_TABS} WHERE lower(name) = lower(?) LIMIT 1",
            (name.strip(),),
        ).fetchone()
        return row_to_dict(row) if row else None
    finally:
        conn.close()


def stock_exists_in_tab(tab_id: int, ticker: str, exchange: str, exclude_rec_id: int = None):
    conn = get_connection()
    try:
        sql = f"""
        SELECT id FROM {TABLE_RECOMMENDATIONS}
        WHERE watchlist_id = ?
          AND upper(ticker) = upper(?)
          AND upper(exchange) = upper(?)
        """
        params = [tab_id, ticker, exchange]
        if exclude_rec_id is not None:
            sql += " AND id != ?"
            params.append(exclude_rec_id)
        row = conn.execute(sql, params).fetchone()
        return row is not None
    finally:
        conn.close()
