from __future__ import annotations

import os
from datetime import date, datetime, timedelta
from typing import Any

import requests

from calculations import annual_report, is_currently_working, month_report, shift_total_hours
from db import get_shift_for_day, list_shifts, list_users

SUPERVISOR_TOKEN = os.environ.get("SUPERVISOR_TOKEN", "")
HA_SYNC_ENABLED = os.environ.get("SHIFT_MANAGER_HA_SYNC", "true").lower() in {"1", "true", "yes", "on"}
BASE_URL = "http://supervisor/core/api"


def _post_state(entity_id: str, state: Any, attributes: dict[str, Any]) -> None:
    if not SUPERVISOR_TOKEN or not HA_SYNC_ENABLED:
        return
    requests.post(
        f"{BASE_URL}/states/{entity_id}",
        headers={
            "Authorization": f"Bearer {SUPERVISOR_TOKEN}",
            "Content-Type": "application/json",
        },
        json={"state": state, "attributes": attributes},
        timeout=10,
    ).raise_for_status()


def _next_shift(user_id: int) -> dict[str, Any] | None:
    today = date.today()
    shifts = list_shifts([user_id], today.isoformat(), (today + timedelta(days=60)).isoformat())
    now = datetime.now()
    candidates: list[tuple[datetime, dict[str, Any]]] = []
    for shift in shifts:
        for segment in shift.get("work_segments", []):
            start_hour, start_minute = (int(part) for part in segment["start"].split(":"))
            start_dt = datetime.combine(date.fromisoformat(shift["date"]), datetime.min.time()).replace(
                hour=start_hour, minute=start_minute
            )
            if start_dt >= now:
                candidates.append((start_dt, shift))
                break
    if not candidates:
        return None
    return min(candidates, key=lambda item: item[0])[1]


def sync_all_users() -> dict[str, Any]:
    if not HA_SYNC_ENABLED:
        return {"enabled": False, "synced": 0, "errors": []}
    if not SUPERVISOR_TOKEN:
        return {"enabled": True, "synced": 0, "errors": ["SUPERVISOR_TOKEN non disponibile"]}

    synced = 0
    errors: list[str] = []
    today = date.today()

    for user in list_users(active_only=True):
        try:
            slug = user["slug"]
            month = month_report(user, today.year, today.month)
            annual = annual_report(user, today.year)
            today_shift = get_shift_for_day(user["id"], today.isoformat())
            next_shift = _next_shift(user["id"])

            common = {
                "friendly_name": f"{user['name']} - Turni",
                "user_id": user["id"],
                "employment_type": user["employment_type"],
            }
            _post_state(
                f"sensor.turni_{slug}_ore_mese",
                month["total_hours"],
                {**common, "unit_of_measurement": "h", "icon": "mdi:clock-outline", **month},
            )
            _post_state(
                f"sensor.turni_{slug}_straordinari_mese",
                month["overtime_hours"],
                {
                    **common,
                    "unit_of_measurement": "h",
                    "icon": "mdi:clock-alert-outline",
                    "status": month["overtime_status"],
                    "threshold_min": user["overtime_min"],
                    "threshold_max": user["overtime_max"],
                },
            )
            _post_state(
                f"sensor.turni_{slug}_weekend_lavorati_mese",
                month["weekend_days_worked"],
                {
                    **common,
                    "unit_of_measurement": "giorni",
                    "icon": "mdi:calendar-weekend",
                    "available": month["weekend_days_available"],
                    "percentage": month["weekend_percentage"],
                },
            )
            _post_state(
                f"sensor.turni_{slug}_ore_anno",
                annual["summary"]["total_hours"],
                {
                    **common,
                    "unit_of_measurement": "h",
                    "icon": "mdi:calendar-clock",
                    **annual["summary"],
                },
            )
            if next_shift:
                first_segment = next_shift["work_segments"][0]
                next_state = f"{next_shift['date']}T{first_segment['start']}:00"
                next_attrs = {
                    **common,
                    "icon": "mdi:calendar-arrow-right",
                    "date": next_shift["date"],
                    "segments": next_shift["work_segments"],
                    "breaks": next_shift["break_segments"],
                    "duration_hours": shift_total_hours(next_shift),
                    "note": next_shift["note"],
                    "device_class": "timestamp",
                }
            else:
                next_state = "unknown"
                next_attrs = {**common, "icon": "mdi:calendar-remove"}
            _post_state(f"sensor.turni_{slug}_prossimo_turno", next_state, next_attrs)

            working = bool(today_shift and is_currently_working(today_shift))
            _post_state(
                f"binary_sensor.turni_{slug}_al_lavoro",
                "on" if working else "off",
                {
                    **common,
                    "icon": "mdi:store-clock",
                    "device_class": "occupancy",
                    "today_shift": today_shift or {},
                },
            )
            synced += 1
        except Exception as exc:  # noqa: BLE001 - keep other users syncing
            errors.append(f"{user['name']}: {exc}")

    return {"enabled": True, "synced": synced, "errors": errors}
