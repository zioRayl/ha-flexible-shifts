from __future__ import annotations

import calendar
import re
from datetime import date, datetime, timedelta
from typing import Any

from db import raw_month_data

ITALIAN_MONTHS = [
    "Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno",
    "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre",
]


def parse_time_value(value: str | int | float) -> str:
    """Return HH:MM. Accepts HH:MM, HH.MM, decimal hours and comma decimals."""
    if value is None:
        raise ValueError("Orario mancante")
    raw = str(value).strip()
    if not raw:
        raise ValueError("Orario mancante")

    if re.fullmatch(r"\d{1,2}:\d{2}", raw):
        hour, minute = (int(x) for x in raw.split(":"))
    elif re.fullmatch(r"\d{1,2}[.,]\d{2}", raw):
        # Two digits after the separator are interpreted as minutes (e.g. 13.30).
        left, right = re.split(r"[.,]", raw)
        hour, minute = int(left), int(right)
    else:
        try:
            numeric = float(raw.replace(",", "."))
        except ValueError as exc:
            raise ValueError(f"Formato orario non valido: {raw}") from exc
        hour = int(numeric)
        minute = round((numeric - hour) * 60)

    if minute == 60:
        hour += 1
        minute = 0
    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        raise ValueError(f"Orario fuori intervallo: {raw}")
    return f"{hour:02d}:{minute:02d}"


def time_to_minutes(value: str) -> int:
    normalized = parse_time_value(value)
    hour, minute = (int(x) for x in normalized.split(":"))
    return hour * 60 + minute


def interval_minutes(start: str, end: str) -> int:
    start_min = time_to_minutes(start)
    end_min = time_to_minutes(end)
    if end_min <= start_min:
        end_min += 24 * 60
    return end_min - start_min


def normalize_segments(segments: list[dict[str, Any]]) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    for segment in segments:
        start = parse_time_value(segment.get("start", ""))
        end = parse_time_value(segment.get("end", ""))
        if interval_minutes(start, end) <= 0:
            raise ValueError("Intervallo orario non valido")
        normalized.append({"start": start, "end": end})
    return normalized


def shift_total_hours(shift: dict[str, Any]) -> float:
    work_minutes = sum(interval_minutes(s["start"], s["end"]) for s in shift.get("work_segments", []))
    break_minutes = sum(interval_minutes(s["start"], s["end"]) for s in shift.get("break_segments", []))
    total = work_minutes - break_minutes
    if total < 0:
        raise ValueError("La durata delle pause supera la durata del turno")
    return round(total / 60, 2)


def monthly_standard_hours(user: dict[str, Any]) -> float:
    if user["target_basis"] == "monthly":
        return round(float(user["target_hours"]), 2)
    weekly = float(user["target_hours"])
    if user.get("monthly_from_weekly_mode") == "annualized":
        return round(weekly * 52 / 12, 2)
    return round(weekly * 4, 2)


def weekly_standard_hours(user: dict[str, Any]) -> float:
    if user["target_basis"] == "weekly":
        return round(float(user["target_hours"]), 2)
    return round(float(user["target_hours"]) / 4, 2)


def vacation_credit_hours(user: dict[str, Any]) -> float:
    return weekly_standard_hours(user)


def weekend_days_in_month(year: int, month: int) -> int:
    _, days = calendar.monthrange(year, month)
    return sum(1 for day in range(1, days + 1) if date(year, month, day).weekday() >= 5)


def month_report(user: dict[str, Any], year: int, month: int) -> dict[str, Any]:
    shifts, vacations = raw_month_data(user["id"], year, month)
    worked_hours = round(sum(shift_total_hours(s) for s in shifts), 2)

    month_start = date(year, month, 1)
    if month == 12:
        month_end = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        month_end = date(year, month + 1, 1) - timedelta(days=1)

    vacation_weeks = 0
    vacation_hours = 0.0
    for vacation in vacations:
        vac_start = date.fromisoformat(vacation["start_date"])
        if month_start <= vac_start <= month_end:
            vacation_weeks += 1
            vacation_hours += float(vacation["credited_hours"])

    total_hours = round(worked_hours + vacation_hours, 2)
    standard = monthly_standard_hours(user)
    balance = round(total_hours - standard, 2)
    overtime = round(max(0.0, balance), 2)

    if user["employment_type"] == "part_time":
        weekend_worked_dates = {
            s["date"]
            for s in shifts
            if date.fromisoformat(s["date"]).weekday() >= 5 and shift_total_hours(s) > 0
        }
        weekends_available = weekend_days_in_month(year, month)
        weekends_worked = len(weekend_worked_dates)
        weekend_percentage = round((weekends_worked / weekends_available * 100), 1) if weekends_available else 0
    else:
        weekends_available = 0
        weekends_worked = 0
        weekend_percentage = 0

    if overtime > float(user["overtime_max"]):
        overtime_status = "excessive"
    elif overtime >= float(user["overtime_min"]):
        overtime_status = "acceptable"
    else:
        overtime_status = "below"

    return {
        "month": month,
        "month_name": ITALIAN_MONTHS[month - 1],
        "worked_hours": worked_hours,
        "vacation_hours": round(vacation_hours, 2),
        "total_hours": total_hours,
        "standard_hours": standard,
        "balance_hours": balance,
        "overtime_hours": overtime,
        "overtime_status": overtime_status,
        "weekend_days_worked": weekends_worked,
        "weekend_days_available": weekends_available,
        "weekend_percentage": weekend_percentage,
        "vacation_weeks": vacation_weeks,
        "has_data": bool(shifts or vacation_weeks),
    }


def annual_report(user: dict[str, Any], year: int, today: date | None = None) -> dict[str, Any]:
    today = today or date.today()
    months = [month_report(user, year, month) for month in range(1, 13)]

    if year < today.year:
        active_months = 12
    elif year == today.year:
        active_months = today.month
    else:
        active_months = 0

    summary_months = months[:active_months]
    total_hours = round(sum(m["total_hours"] for m in summary_months), 2)
    total_worked = round(sum(m["worked_hours"] for m in summary_months), 2)
    total_vacation_hours = round(sum(m["vacation_hours"] for m in summary_months), 2)
    total_overtime = round(sum(m["overtime_hours"] for m in summary_months), 2)
    total_standard = round(sum(m["standard_hours"] for m in summary_months), 2)
    total_weekend_worked = sum(m["weekend_days_worked"] for m in summary_months)
    total_weekend_available = sum(m["weekend_days_available"] for m in summary_months)
    total_vacation_weeks = sum(m["vacation_weeks"] for m in summary_months)
    overall_weekend_percentage = round(
        total_weekend_worked / total_weekend_available * 100, 1
    ) if total_weekend_available else 0

    return {
        "year": year,
        "user": user,
        "months": months,
        "summary": {
            "total_hours": total_hours,
            "worked_hours": total_worked,
            "vacation_hours": total_vacation_hours,
            "overtime_hours": total_overtime,
            "standard_hours": total_standard,
            "balance_hours": round(total_hours - total_standard, 2),
            "weekend_days_worked": total_weekend_worked,
            "weekend_days_available": total_weekend_available,
            "weekend_percentage": overall_weekend_percentage,
            "vacation_weeks": total_vacation_weeks,
            "active_months": active_months,
        },
    }


def is_currently_working(shift: dict[str, Any], now: datetime | None = None) -> bool:
    now = now or datetime.now()
    if shift.get("date") != now.date().isoformat():
        return False
    current = now.hour * 60 + now.minute

    def contains(segment: dict[str, str]) -> bool:
        start = time_to_minutes(segment["start"])
        end = time_to_minutes(segment["end"])
        if end <= start:
            return current >= start or current < end
        return start <= current < end

    in_work = any(contains(s) for s in shift.get("work_segments", []))
    in_break = any(contains(s) for s in shift.get("break_segments", []))
    return in_work and not in_break
