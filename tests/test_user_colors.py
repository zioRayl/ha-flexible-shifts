import sqlite3
import tempfile
import unittest
from pathlib import Path
import sys

APP_DIR = Path(__file__).resolve().parents[1] / "flexible_shifts" / "app"
sys.path.insert(0, str(APP_DIR))

import db  # noqa: E402


class UserColorTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        db.DB_PATH = str(Path(self.tempdir.name) / "colors.db")

    def tearDown(self):
        self.tempdir.cleanup()

    def test_legacy_users_receive_distinct_colors(self):
        conn = sqlite3.connect(db.DB_PATH)
        conn.executescript(
            """
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                slug TEXT NOT NULL UNIQUE,
                employment_type TEXT NOT NULL,
                target_basis TEXT NOT NULL,
                target_hours REAL NOT NULL,
                monthly_from_weekly_mode TEXT NOT NULL DEFAULT 'x4',
                overtime_min REAL NOT NULL DEFAULT 0,
                overtime_max REAL NOT NULL DEFAULT 12,
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            INSERT INTO users (name, slug, employment_type, target_basis, target_hours, created_at, updated_at)
            VALUES ('Uno', 'uno', 'part_time', 'weekly', 20, '2026-01-01', '2026-01-01');
            INSERT INTO users (name, slug, employment_type, target_basis, target_hours, created_at, updated_at)
            VALUES ('Due', 'due', 'part_time', 'weekly', 20, '2026-01-01', '2026-01-01');
            """
        )
        conn.commit()
        conn.close()

        db.init_db()
        users = db.list_users()
        self.assertRegex(users[0]["color"], r"^#[0-9A-F]{6}$")
        self.assertRegex(users[1]["color"], r"^#[0-9A-F]{6}$")
        self.assertNotEqual(users[0]["color"], users[1]["color"])

    def test_create_and_update_user_color(self):
        db.init_db()
        user = db.create_user(
            {
                "name": "Colorato",
                "employment_type": "part_time",
                "target_basis": "weekly",
                "target_hours": 30.5,
                "monthly_from_weekly_mode": "x4",
                "overtime_min": 0,
                "overtime_max": 12,
                "color": "#16a34a",
                "active": True,
            }
        )
        self.assertEqual(user["color"], "#16A34A")
        updated = db.update_user(user["id"], {"color": "#9333ea"})
        self.assertEqual(updated["color"], "#9333EA")


if __name__ == "__main__":
    unittest.main()
