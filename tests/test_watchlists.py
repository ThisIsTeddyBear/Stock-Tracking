import os
import sqlite3
import tempfile
import unittest

import database as db
from app import app


class WatchlistApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        db.DB_PATH = os.path.join(self.temp_dir.name, "stocks_test.db")
        db.init_db(seed_if_empty=False)
        app.config["TESTING"] = True
        self.client = app.test_client()
        self.default_tab_id = self.client.get("/api/watchlists").get_json()[0]["id"]

    def tearDown(self):
        self.temp_dir.cleanup()

    def _create_tab(self, name: str) -> int:
        res = self.client.post("/api/watchlists", json={"name": name})
        self.assertEqual(res.status_code, 201, res.get_json())
        return res.get_json()["id"]

    def _create_stock(self, watchlist_id: int, ticker: str, stock_name: str = None):
        payload = {
            "stock_name": stock_name or ticker,
            "ticker": ticker,
            "exchange": "NSE",
            "entry_price": 100.0,
            "status": "Active",
            "watchlist_id": watchlist_id,
        }
        return self.client.post("/api/recommendations", json=payload)

    def test_create_tab_works(self):
        tab_id = self._create_tab("Swing Trades")
        tabs = self.client.get("/api/watchlists").get_json()
        self.assertTrue(any(t["id"] == tab_id and t["name"] == "Swing Trades" for t in tabs))

    def test_switching_tabs_filters_recommendations(self):
        second_tab_id = self._create_tab("Long Term Portfolio")
        first_rec = self._create_stock(self.default_tab_id, "RELIANCE", "Reliance Industries")
        second_rec = self._create_stock(second_tab_id, "TCS", "Tata Consultancy Services")
        self.assertEqual(first_rec.status_code, 201, first_rec.get_json())
        self.assertEqual(second_rec.status_code, 201, second_rec.get_json())

        default_rows = self.client.get(
            f"/api/recommendations?watchlist_id={self.default_tab_id}"
        ).get_json()
        second_rows = self.client.get(
            f"/api/recommendations?watchlist_id={second_tab_id}"
        ).get_json()

        self.assertEqual(len(default_rows), 1)
        self.assertEqual(default_rows[0]["ticker"], "RELIANCE")
        self.assertEqual(len(second_rows), 1)
        self.assertEqual(second_rows[0]["ticker"], "TCS")

    def test_add_stock_goes_to_requested_tab_only(self):
        second_tab_id = self._create_tab("Broker A Ideas")
        created = self._create_stock(second_tab_id, "INFY", "Infosys")
        self.assertEqual(created.status_code, 201, created.get_json())

        default_rows = self.client.get(
            f"/api/recommendations?watchlist_id={self.default_tab_id}"
        ).get_json()
        second_rows = self.client.get(
            f"/api/recommendations?watchlist_id={second_tab_id}"
        ).get_json()
        self.assertEqual(len(default_rows), 0)
        self.assertEqual(len(second_rows), 1)
        self.assertEqual(second_rows[0]["ticker"], "INFY")

    def test_same_stock_can_exist_in_two_tabs(self):
        second_tab_id = self._create_tab("Zerodha Picks")
        one = self._create_stock(self.default_tab_id, "HDFCBANK", "HDFC Bank")
        two = self._create_stock(second_tab_id, "HDFCBANK", "HDFC Bank")
        self.assertEqual(one.status_code, 201, one.get_json())
        self.assertEqual(two.status_code, 201, two.get_json())

        all_rows = self.client.get("/api/recommendations").get_json()
        matches = [r for r in all_rows if r["ticker"] == "HDFCBANK"]
        self.assertEqual(len(matches), 2)
        self.assertNotEqual(matches[0]["watchlist_id"], matches[1]["watchlist_id"])

    def test_delete_tab_does_not_delete_unrelated_tabs_or_stocks(self):
        second_tab_id = self._create_tab("Groww Watchlist")
        default_rec = self._create_stock(self.default_tab_id, "SBIN", "State Bank of India")
        second_rec = self._create_stock(second_tab_id, "ITC", "ITC Ltd")
        self.assertEqual(default_rec.status_code, 201, default_rec.get_json())
        self.assertEqual(second_rec.status_code, 201, second_rec.get_json())

        delete_res = self.client.delete(f"/api/watchlists/{second_tab_id}")
        self.assertEqual(delete_res.status_code, 200, delete_res.get_json())

        tabs = self.client.get("/api/watchlists").get_json()
        self.assertTrue(any(t["id"] == self.default_tab_id for t in tabs))
        self.assertFalse(any(t["id"] == second_tab_id for t in tabs))

        default_rows = self.client.get(
            f"/api/recommendations?watchlist_id={self.default_tab_id}"
        ).get_json()
        self.assertEqual(len(default_rows), 1)
        self.assertEqual(default_rows[0]["ticker"], "SBIN")


class LegacyMigrationTests(unittest.TestCase):
    def test_old_recommendations_table_backfills_default_tab(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db.DB_PATH = os.path.join(temp_dir, "legacy.db")
            conn = sqlite3.connect(db.DB_PATH)
            conn.execute(
                """
                CREATE TABLE recommendations (
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
            )
            conn.execute(
                """
                INSERT INTO recommendations
                (stock_name, ticker, exchange, yf_symbol, rec_date, entry_price, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                ("Legacy Stock", "LEGACY", "NSE", "LEGACY.NS", "2024-01-01", 123.45, "Active"),
            )
            conn.commit()
            conn.close()

            db.init_db(seed_if_empty=False)

            tabs = db.get_tabs()
            recs = db.get_all()
            self.assertGreaterEqual(len(tabs), 1)
            self.assertEqual(len(recs), 1)
            self.assertIsNotNone(recs[0]["watchlist_id"])
            self.assertTrue(any(t["id"] == recs[0]["watchlist_id"] for t in tabs))


if __name__ == "__main__":
    unittest.main()
