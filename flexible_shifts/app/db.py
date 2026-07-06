from __future__ import annotations

import json
import os
import re
import sqlite3
import unicodedata
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterator

DB_PATH = os.environ.get("SHIFT_MANAGER_DB", "/data/flexible_shifts.db")


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    normalized = re.sub(r"[^a-zA-Z0-9]+", "_", normalized).strip("_").lower()
    return normalized or "utente"


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                slug TEXT NOT NULL UNIQUE,
                employment_type TEXT NOT NULL CHECK (employment_type IN ('full_time', 'part_time')),
                target_basis TEXT NOT NULL CHECK (target_basis IN ('weekly', 'monthly')),
                target_hours REAL NOT NULL CHECK (target_hours >= 0),
                monthly_from_weekly_mode TEXT NOT NULL DEFAULT 'x4'
                    CHECK (monthly_from_weekly_mode IN ('x4', 'annualized')),
                overtime_min REAL NOT NULL DEFAULT 0,
                overtime_max REAL NOT NULL DEFAULT 12,
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS shifts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                shift_date TEXT NOT NULL,
                work_segments TEXT NOT NULL,
                break_segments TEXT NOT NULL DEFAULT '[]',
                note TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(user_id, shift_date)
            );

            CREATE TABLE IF NOT EXISTS vacations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                credited_hours REAL NOT NULL,
                note TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                UNIQUE(user_id, start_date)
            );

            CREATE INDEX IF NOT EXISTS idx_shifts_user_date ON shifts(user_id, shift_date);
            CREATE INDEX IF NOT EXISTS idx_vacations_user_date ON vacations(user_id, start_date, end_date);
            """
        )


def row_to_user(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "name": row["name"],
        "slug": row["slug"],
        "employment_type": row["employment_type"],
        "target_basis": row["target_basis"],
        "target_hours": row["target_hours"],
        "monthly_from_weekly_mode": row["monthly_from_weekly_mode"],
        "overtime_min": row["overtime_min"],
        "overtime_max": row["overtime_max"],
        "active": bool(row["active"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def row_to_shift(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "date": row["shift_date"],
        "work_segments": json.loads(row["work_segments"]),
        "break_segments": json.loads(row["break_segments"]),
        "note": row["note"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def row_to_vacation(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "user_id": row["user_id"],
        "start_date": row["start_date"],
        "end_date": row["end_date"],
        "credited_hours": row["credited_hours"],
        "note": row["note"],
        "created_at": row["created_at"],
    }


def list_users(active_only: bool = False) -> list[dict[str, Any]]:
    query = "SELECT * FROM users"
    params: tuple[Any, ...] = ()
    if active_only:
        query += " WHERE active = 1"
    query += " ORDER BY active DESC, name COLLATE NOCASE"
    with connect() as conn:
        return [row_to_user(r) for r in conn.execute(query, params).fetchall()]


def get_user(user_id: int) -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return row_to_user(row) if row else None


def create_user(data: dict[str, Any]) -> dict[str, Any]:
    base_slug = slugify(data["name"])
    slug = base_slug
    with connect() as conn:
        suffix = 2
        while conn.execute("SELECT 1 FROM users WHERE slug = ?", (slug,)).fetchone():
            slug = f"{base_slug}_{suffix}"
            suffix += 1
        now = _now()
        cur = conn.execute(
            """
            INSERT INTO users (
                name, slug, employment_type, target_basis, target_hours,
                monthly_from_weekly_mode, overtime_min, overtime_max,
                active, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["name"].strip(),
                slug,
                data["employment_type"],
                data["target_basis"],
                float(data["target_hours"]),
                data.get("monthly_from_weekly_mode", "x4"),
                float(data.get("overtime_min", 0)),
                float(data.get("overtime_max", 12)),
                1 if data.get("active", True) else 0,
                now,
                now,
            ),
        )
        row = conn.execute("SELECT * FROM users WHERE id = ?", (cur.lastrowid,)).fetchone()
        assert row
        return row_to_user(row)


def update_user(user_id: int, data: dict[str, Any]) -> dict[str, Any] | None:
    existing = get_user(user_id)
    if not existing:
        return None
    merged = {**existing, **data}
    with connect() as conn:
        conn.execute(
            """
            UPDATE users SET
                name = ?, employment_type = ?, target_basis = ?, target_hours = ?,
                monthly_from_weekly_mode = ?, overtime_min = ?, overtime_max = ?,
                active = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                merged["name"].strip(),
                merged["employment_type"],
                merged["target_basis"],
                float(merged["target_hours"]),
                merged.get("monthly_from_weekly_mode", "x4"),
                float(merged.get("overtime_min", 0)),
                float(merged.get("overtime_max", 12)),
                1 if merged.get("active", True) else 0,
                _now(),
                user_id,
            ),
        )
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return row_to_user(row) if row else None


def delete_user(user_id: int) -> bool:
    with connect() as conn:
        cur = conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        return cur.rowcount > 0


def list_shifts(user_ids: list[int], start: str, end: str) -> list[dict[str, Any]]:
    if not user_ids:
        return []
    placeholders = ",".join("?" for _ in user_ids)
    params: list[Any] = [*user_ids, start, end]
    with connect() as conn:
        rows = conn.execute(
            f"""
            SELECT * FROM shifts
            WHERE user_id IN ({placeholders}) AND shift_date BETWEEN ? AND ?
            ORDER BY shift_date, user_id
            """,
            params,
        ).fetchall()
        return [row_to_shift(r) for r in rows]


def get_shift(shift_id: int) -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM shifts WHERE id = ?", (shift_id,)).fetchone()
        return row_to_shift(row) if row else None


def get_shift_for_day(user_id: int, shift_date: str) -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute(
            "SELECT * FROM shifts WHERE user_id = ? AND shift_date = ?",
            (user_id, shift_date),
        ).fetchone()
        return row_to_shift(row) if row else None


def upsert_shift(data: dict[str, Any], shift_id: int | None = None) -> dict[str, Any]:
    work_json = json.dumps(data["work_segments"], separators=(",", ":"))
    break_json = json.dumps(data.get("break_segments", []), separators=(",", ":"))
    now = _now()
    with connect() as conn:
        if shift_id is not None:
            conn.execute(
                """
                UPDATE shifts SET user_id = ?, shift_date = ?, work_segments = ?,
                    break_segments = ?, note = ?, updated_at = ?
                WHERE id = ?
                """,
                (
                    data["user_id"], data["date"], work_json, break_json,
                    data.get("note", ""), now, shift_id,
                ),
            )
            row = conn.execute("SELECT * FROM shifts WHERE id = ?", (shift_id,)).fetchone()
        else:
            conn.execute(
                """
                INSERT INTO shifts (
                    user_id, shift_date, work_segments, break_segments, note, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, shift_date) DO UPDATE SET
                    work_segments = excluded.work_segments,
                    break_segments = excluded.break_segments,
                    note = excluded.note,
                    updated_at = excluded.updated_at
                """,
                (
                    data["user_id"], data["date"], work_json, break_json,
                    data.get("note", ""), now, now,
                ),
            )
            row = conn.execute(
                "SELECT * FROM shifts WHERE user_id = ? AND shift_date = ?",
                (data["user_id"], data["date"]),
            ).fetchone()
        if not row:
            raise ValueError("Turno non trovato dopo il salvataggio")
        return row_to_shift(row)


def delete_shift(shift_id: int) -> bool:
    with connect() as conn:
        cur = conn.execute("DELETE FROM shifts WHERE id = ?", (shift_id,))
        return cur.rowcount > 0


def list_vacations(user_ids: list[int], start: str, end: str) -> list[dict[str, Any]]:
    if not user_ids:
        return []
    placeholders = ",".join("?" for _ in user_ids)
    params: list[Any] = [*user_ids, end, start]
    with connect() as conn:
        rows = conn.execute(
            f"""
            SELECT * FROM vacations
            WHERE user_id IN ({placeholders}) AND start_date <= ? AND end_date >= ?
            ORDER BY start_date, user_id
            """,
            params,
        ).fetchall()
        return [row_to_vacation(r) for r in rows]


def create_vacation(data: dict[str, Any]) -> dict[str, Any]:
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO vacations (user_id, start_date, end_date, credited_hours, note, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, start_date) DO UPDATE SET
                end_date = excluded.end_date,
                credited_hours = excluded.credited_hours,
                note = excluded.note
            """,
            (
                data["user_id"], data["start_date"], data["end_date"],
                float(data["credited_hours"]), data.get("note", ""), _now(),
            ),
        )
        row = conn.execute(
            "SELECT * FROM vacations WHERE user_id = ? AND start_date = ?",
            (data["user_id"], data["start_date"]),
        ).fetchone()
        assert row
        return row_to_vacation(row)


def delete_vacation(vacation_id: int) -> bool:
    with connect() as conn:
        cur = conn.execute("DELETE FROM vacations WHERE id = ?", (vacation_id,))
        return cur.rowcount > 0


def raw_month_data(user_id: int, year: int, month: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    start = date(year, month, 1)
    if month == 12:
        end = date(year + 1, 1, 1)
    else:
        end = date(year, month + 1, 1)
    end_inclusive = date.fromordinal(end.toordinal() - 1)
    return (
        list_shifts([user_id], start.isoformat(), end_inclusive.isoformat()),
        list_vacations([user_id], start.isoformat(), end_inclusive.isoformat()),
    )
