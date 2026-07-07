from __future__ import annotations

import csv
from contextlib import asynccontextmanager
import io
import os
import sqlite3
import threading
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Literal

import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator, model_validator

import db
from calculations import (
    annual_report,
    normalize_segments,
    parse_time_value,
    shift_total_hours,
    vacation_allocation_for_period,
    vacation_credit_hours,
)
from ha_sync import sync_all_users
from import_export import CSV_TEMPLATE, import_csv

APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = APP_DIR / "static"
DB_PATH = Path(os.environ.get("SHIFT_MANAGER_DB", "/data/flexible_shifts.db"))
SYNC_INTERVAL = int(os.environ.get("SHIFT_MANAGER_SYNC_INTERVAL", "60"))

@asynccontextmanager
async def lifespan(_: FastAPI):
    db.init_db()
    threading.Thread(target=_background_sync, daemon=True).start()
    yield


app = FastAPI(title="Flexible Shifts", version="0.4.0", lifespan=lifespan)


@app.middleware("http")
async def ingress_only(request: Request, call_next):
    """Reject direct container-network access when running as a Home Assistant app."""
    restricted = os.environ.get("SHIFT_MANAGER_INGRESS_ONLY", "false").lower() in {"1", "true", "yes", "on"}
    client_host = request.client.host if request.client else ""
    if restricted and client_host not in {"172.30.32.2", "127.0.0.1", "::1"}:
        return JSONResponse(status_code=403, content={"detail": "Accesso consentito solo tramite Home Assistant Ingress"})
    return await call_next(request)


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class TimeRange(BaseModel):
    start: str
    end: str


class UserPayload(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    employment_type: Literal["full_time", "part_time"] = "part_time"
    target_basis: Literal["weekly", "monthly"] = "weekly"
    target_hours: float = Field(ge=0, le=744)
    monthly_from_weekly_mode: Literal["x4", "annualized"] = "x4"
    overtime_min: float = Field(default=0, ge=0, le=744)
    overtime_max: float = Field(default=12, ge=0, le=744)
    color: str = Field(default="#2563EB", pattern=r"^#[0-9A-Fa-f]{6}$")
    active: bool = True

    @model_validator(mode="after")
    def validate_thresholds(self) -> "UserPayload":
        if self.overtime_max < self.overtime_min:
            raise ValueError("La soglia massima deve essere maggiore o uguale alla minima")
        return self


def _time_minutes(value: str) -> int:
    hours, minutes = value.split(":")
    return int(hours) * 60 + int(minutes)


def _validate_shift_window(start: str, end: str, pause_start: str | None = None, pause_end: str | None = None) -> None:
    if start == end:
        raise ValueError("Inizio e fine turno non possono coincidere")
    start_minutes = _time_minutes(start)
    end_minutes = _time_minutes(end)
    if end_minutes <= start_minutes:
        end_minutes += 1440
    if pause_start is None and pause_end is None:
        return
    if not pause_start or not pause_end:
        raise ValueError("Compilare sia l’inizio sia la fine della pausa")
    pause_start_minutes = _time_minutes(pause_start)
    pause_end_minutes = _time_minutes(pause_end)
    if pause_start_minutes < start_minutes:
        pause_start_minutes += 1440
    if pause_end_minutes <= start_minutes:
        pause_end_minutes += 1440
    if pause_end_minutes <= pause_start_minutes:
        pause_end_minutes += 1440
    if not (start_minutes <= pause_start_minutes < pause_end_minutes <= end_minutes):
        raise ValueError("La pausa deve essere compresa nell’orario del turno")


class ShiftPayload(BaseModel):
    user_id: int
    date: date
    work_segments: list[TimeRange] = Field(min_length=1, max_length=1)
    break_segments: list[TimeRange] = Field(default_factory=list, max_length=1)
    note: str = Field(default="", max_length=1000)

    @field_validator("work_segments", "break_segments")
    @classmethod
    def normalize_time_ranges(cls, value: list[TimeRange]) -> list[TimeRange]:
        normalized = normalize_segments([item.model_dump() for item in value])
        return [TimeRange(**item) for item in normalized]

    @model_validator(mode="after")
    def validate_single_shift(self) -> "ShiftPayload":
        work = self.work_segments[0]
        pause = self.break_segments[0] if self.break_segments else None
        _validate_shift_window(
            work.start, work.end, pause.start if pause else None, pause.end if pause else None
        )
        return self


class PresetPayload(BaseModel):
    user_id: int
    name: str = Field(min_length=1, max_length=100)
    start_time: str
    end_time: str
    pause_start: str | None = None
    pause_end: str | None = None

    @field_validator("start_time", "end_time", "pause_start", "pause_end", mode="before")
    @classmethod
    def normalize_time(cls, value: Any) -> str | None:
        if value is None or str(value).strip() == "":
            return None
        return parse_time_value(str(value))

    @model_validator(mode="after")
    def validate_preset(self) -> "PresetPayload":
        _validate_shift_window(self.start_time, self.end_time, self.pause_start, self.pause_end)
        return self


class VacationPayload(BaseModel):
    user_id: int
    start_date: date | None = None
    end_date: date | None = None
    # Legacy field kept so clients from 0.2.x can still create a full vacation week.
    date_in_week: date | None = None
    note: str = Field(default="", max_length=1000)
    credited_hours: float | None = Field(default=None, ge=0, le=744)

    @model_validator(mode="after")
    def validate_dates(self) -> "VacationPayload":
        if self.date_in_week and not self.start_date and not self.end_date:
            return self
        if not self.start_date:
            raise ValueError("La data di inizio ferie è obbligatoria")
        if self.end_date is None:
            self.end_date = self.start_date
        if self.end_date < self.start_date:
            raise ValueError("La data di fine ferie non può precedere quella di inizio")
        return self


def _require_user(user_id: int) -> dict[str, Any]:
    user = db.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Utente non trovato")
    return user


def _sync_soon() -> None:
    threading.Thread(target=sync_all_users, daemon=True).start()


def _background_sync() -> None:
    while True:
        try:
            sync_all_users()
        except Exception as exc:  # noqa: BLE001
            print(f"[Flexible Shifts] Errore sincronizzazione Home Assistant: {exc}", flush=True)
        time.sleep(max(30, SYNC_INTERVAL))


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "version": "0.4.0", "time": datetime.now().isoformat()}


@app.get("/api/users")
def users(active_only: bool = False) -> list[dict[str, Any]]:
    return db.list_users(active_only=active_only)


@app.post("/api/users", status_code=201)
def create_user(payload: UserPayload) -> dict[str, Any]:
    user = db.create_user(payload.model_dump())
    _sync_soon()
    return user


@app.put("/api/users/{user_id}")
def update_user(user_id: int, payload: UserPayload) -> dict[str, Any]:
    user = db.update_user(user_id, payload.model_dump())
    if not user:
        raise HTTPException(status_code=404, detail="Utente non trovato")
    _sync_soon()
    return user


@app.delete("/api/users/{user_id}", status_code=204, response_class=Response)
def delete_user(user_id: int) -> Response:
    if not db.delete_user(user_id):
        raise HTTPException(status_code=404, detail="Utente non trovato")
    _sync_soon()
    return Response(status_code=204)


@app.get("/api/presets")
def presets(user_id: int) -> list[dict[str, Any]]:
    _require_user(user_id)
    return db.list_presets(user_id)


@app.post("/api/presets", status_code=201)
def create_preset(payload: PresetPayload) -> dict[str, Any]:
    _require_user(payload.user_id)
    try:
        return db.create_preset(payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.put("/api/presets/{preset_id}")
def update_preset(preset_id: int, payload: PresetPayload) -> dict[str, Any]:
    existing = db.get_preset(preset_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Preset non trovato")
    _require_user(payload.user_id)
    try:
        preset = db.update_preset(preset_id, payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if not preset:
        raise HTTPException(status_code=404, detail="Preset non trovato")
    return preset


@app.delete("/api/presets/{preset_id}", status_code=204, response_class=Response)
def delete_preset(preset_id: int) -> Response:
    if not db.delete_preset(preset_id):
        raise HTTPException(status_code=404, detail="Preset non trovato")
    return Response(status_code=204)


@app.get("/api/calendar")
def calendar_data(
    user_ids: str = Query(..., description="ID utenti separati da virgola"),
    start: date = Query(...),
    end: date = Query(...),
) -> dict[str, Any]:
    try:
        ids = sorted({int(item) for item in user_ids.split(",") if item.strip()})
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Elenco utenti non valido") from exc
    if end < start:
        raise HTTPException(status_code=400, detail="Intervallo date non valido")

    shifts = db.list_shifts(ids, start.isoformat(), end.isoformat())
    for shift in shifts:
        shift["total_hours"] = shift_total_hours(shift)
    vacations = db.list_vacations(ids, start.isoformat(), end.isoformat())
    users_by_id = {user_id: db.get_user(user_id) for user_id in ids}
    for vacation in vacations:
        user = users_by_id.get(vacation["user_id"])
        if not user:
            continue
        allocation = vacation_allocation_for_period(user, vacation, start, end)
        vacation["credited_hours_in_range"] = round(allocation["credited_hours"], 2)
        vacation["vacation_days_in_range"] = allocation["vacation_days"]
        vacation["equivalent_weeks_in_range"] = round(allocation["equivalent_weeks"], 2)
    return {"shifts": shifts, "vacations": vacations}


@app.post("/api/shifts", status_code=201)
def create_shift(payload: ShiftPayload) -> dict[str, Any]:
    _require_user(payload.user_id)
    data = payload.model_dump(mode="json")
    data["date"] = payload.date.isoformat()
    saved = db.upsert_shift(data)
    saved["total_hours"] = shift_total_hours(saved)
    _sync_soon()
    return saved


@app.put("/api/shifts/{shift_id}")
def update_shift(shift_id: int, payload: ShiftPayload) -> dict[str, Any]:
    if not db.get_shift(shift_id):
        raise HTTPException(status_code=404, detail="Turno non trovato")
    _require_user(payload.user_id)
    data = payload.model_dump(mode="json")
    data["date"] = payload.date.isoformat()
    saved = db.upsert_shift(data, shift_id=shift_id)
    saved["total_hours"] = shift_total_hours(saved)
    _sync_soon()
    return saved


@app.delete("/api/shifts/{shift_id}", status_code=204, response_class=Response)
def delete_shift(shift_id: int) -> Response:
    if not db.delete_shift(shift_id):
        raise HTTPException(status_code=404, detail="Turno non trovato")
    _sync_soon()
    return Response(status_code=204)


@app.post("/api/vacations", status_code=201)
def create_vacation(payload: VacationPayload) -> dict[str, Any]:
    user = _require_user(payload.user_id)

    if payload.date_in_week and not payload.start_date:
        # Backward compatibility with 0.2.x: date_in_week means a complete week.
        start_date = payload.date_in_week - timedelta(days=payload.date_in_week.weekday())
        end_date = start_date + timedelta(days=4 if user["employment_type"] == "full_time" else 6)
    else:
        assert payload.start_date is not None
        start_date = payload.start_date
        end_date = payload.end_date or start_date

    credit = (
        payload.credited_hours
        if payload.credited_hours is not None
        else vacation_credit_hours(user, start_date, end_date)
    )
    vacation = db.create_vacation(
        {
            "user_id": payload.user_id,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "credited_hours": credit,
            "note": payload.note,
        }
    )
    _sync_soon()
    return vacation


@app.delete("/api/vacations/{vacation_id}", status_code=204, response_class=Response)
def delete_vacation(vacation_id: int) -> Response:
    if not db.delete_vacation(vacation_id):
        raise HTTPException(status_code=404, detail="Ferie non trovate")
    _sync_soon()
    return Response(status_code=204)


@app.get("/api/reports/annual")
def report_annual(user_id: int, year: int = Query(ge=2000, le=2100)) -> dict[str, Any]:
    user = _require_user(user_id)
    return annual_report(user, year)


@app.post("/api/import/csv")
async def upload_csv(user_id: int = Form(...), file: UploadFile = File(...)) -> dict[str, Any]:
    if not file.filename or not file.filename.lower().endswith((".csv", ".txt")):
        raise HTTPException(status_code=400, detail="Caricare un file CSV o TXT")
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File troppo grande (massimo 5 MB)")
    try:
        result = import_csv(content, user_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    _sync_soon()
    return result


@app.get("/api/import/template.csv")
def csv_template() -> PlainTextResponse:
    return PlainTextResponse(
        CSV_TEMPLATE,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="template_turni.csv"'},
    )


@app.get("/api/export/csv")
def export_csv(user_id: int, year: int = Query(ge=2000, le=2100)) -> StreamingResponse:
    user = _require_user(user_id)
    start = date(year, 1, 1)
    end = date(year, 12, 31)
    shifts = db.list_shifts([user_id], start.isoformat(), end.isoformat())
    vacations = db.list_vacations([user_id], start.isoformat(), end.isoformat())

    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow([
        "utente", "data", "data_fine", "tipo", "inizio_turno", "fine_turno",
        "inizio_pausa", "fine_pausa", "ore_totali", "ore_accreditate", "note",
    ])
    for shift in shifts:
        work = shift["work_segments"][0]
        pause = shift["break_segments"][0] if shift["break_segments"] else {"start": "", "end": ""}
        writer.writerow([
            user["name"], shift["date"], "", "work", work["start"], work["end"],
            pause["start"], pause["end"],
            str(shift_total_hours(shift)).replace(".", ","), "", shift["note"],
        ])
    for vacation in vacations:
        writer.writerow([
            user["name"], vacation["start_date"], vacation["end_date"], "ferie",
            "", "", "", "", "",
            str(vacation["credited_hours"]).replace(".", ","), vacation["note"],
        ])

    filename = f"turni_{user['slug']}_{year}.csv"
    return StreamingResponse(
        iter([output.getvalue().encode("utf-8-sig")]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/api/backup")
def backup_database() -> FileResponse:
    db.init_db()
    backup_dir = DB_PATH.parent / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    filename = f"flexible_shifts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    destination = backup_dir / filename
    with sqlite3.connect(DB_PATH) as source, sqlite3.connect(destination) as target:
        source.backup(target)
    return FileResponse(destination, filename=filename, media_type="application/octet-stream")


@app.post("/api/sync")
def sync_now() -> dict[str, Any]:
    return sync_all_users()


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8099, log_level="info")
