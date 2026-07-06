from __future__ import annotations

import csv
import io
from datetime import date, datetime, timedelta
from typing import Any

from calculations import normalize_segments, parse_time_value, vacation_credit_hours
from db import create_vacation, get_shift_for_day, get_user, upsert_shift


def _normalize_header(value: str) -> str:
    return (
        value.strip().lower()
        .replace(" ", "_")
        .replace("-", "_")
        .replace("à", "a")
        .replace("è", "e")
        .replace("ì", "i")
        .replace("ò", "o")
        .replace("ù", "u")
    )


ALIASES = {
    "date": {"date", "data", "giorno"},
    "type": {"type", "tipo", "tipologia"},
    "start_1": {"start_1", "start1", "inizio_1", "inizio1", "entrata_1", "entrata1", "start"},
    "end_1": {"end_1", "end1", "stop_1", "stop1", "fine_1", "fine1", "uscita_1", "uscita1", "stop"},
    "start_2": {"start_2", "start2", "inizio_2", "inizio2", "entrata_2", "entrata2"},
    "end_2": {"end_2", "end2", "stop_2", "stop2", "fine_2", "fine2", "uscita_2", "uscita2"},
    "pause_start": {"pause_start", "pausa_start", "inizio_pausa", "pausa_inizio"},
    "pause_end": {"pause_end", "pausa_end", "fine_pausa", "pausa_fine"},
    "note": {"note", "nota", "descrizione"},
    "credited_hours": {"credited_hours", "ore_accreditate", "ore_ferie"},
}


def _resolve_columns(fieldnames: list[str]) -> dict[str, str]:
    normalized = {_normalize_header(name): name for name in fieldnames}
    resolved: dict[str, str] = {}
    for canonical, aliases in ALIASES.items():
        for alias in aliases:
            if alias in normalized:
                resolved[canonical] = normalized[alias]
                break
    return resolved


def _parse_date(value: str) -> date:
    raw = value.strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Data non valida: {raw}")


def _detect_dialect(text: str) -> csv.Dialect:
    sample = text[:4096]
    first_line = sample.splitlines()[0] if sample.splitlines() else ""
    # Prefer the delimiter visible in the header. Decimal commas in data rows can fool Sniffer.
    counts = {";": first_line.count(";"), ",": first_line.count(","), "\t": first_line.count("\t")}
    delimiter = max(counts, key=counts.get)
    if counts[delimiter] > 0:
        class Detected(csv.excel):
            pass
        Detected.delimiter = delimiter
        return Detected
    try:
        return csv.Sniffer().sniff(sample, delimiters=";,\t")
    except csv.Error:
        return csv.excel


def import_csv(content: bytes, user_id: int) -> dict[str, Any]:
    user = get_user(user_id)
    if not user:
        raise ValueError("Utente non trovato")

    text = content.decode("utf-8-sig")
    dialect = _detect_dialect(text)
    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    if not reader.fieldnames:
        raise ValueError("Il CSV non contiene intestazioni")

    columns = _resolve_columns(reader.fieldnames)
    if "date" not in columns:
        raise ValueError("Colonna data mancante")

    imported = 0
    updated = 0
    vacations = 0
    errors: list[dict[str, Any]] = []

    for line_number, row in enumerate(reader, start=2):
        try:
            row_date = _parse_date(row.get(columns["date"], ""))
            row_type = row.get(columns.get("type", ""), "work").strip().lower() if columns.get("type") else "work"
            note = row.get(columns.get("note", ""), "").strip() if columns.get("note") else ""

            if row_type in {"vacation", "ferie", "holiday_week", "ferie_settimana"}:
                monday = row_date - timedelta(days=row_date.weekday())
                end_date = monday + timedelta(days=4 if user["employment_type"] == "full_time" else 6)
                raw_credit = row.get(columns.get("credited_hours", ""), "").strip() if columns.get("credited_hours") else ""
                credit = float(raw_credit.replace(",", ".")) if raw_credit else vacation_credit_hours(user)
                create_vacation({
                    "user_id": user_id,
                    "start_date": monday.isoformat(),
                    "end_date": end_date.isoformat(),
                    "credited_hours": credit,
                    "note": note,
                })
                vacations += 1
                continue

            work_segments: list[dict[str, str]] = []
            break_segments: list[dict[str, str]] = []
            for start_key, end_key in (("start_1", "end_1"), ("start_2", "end_2")):
                if start_key in columns and end_key in columns:
                    start_raw = row.get(columns[start_key], "").strip()
                    end_raw = row.get(columns[end_key], "").strip()
                    if start_raw or end_raw:
                        if not start_raw or not end_raw:
                            raise ValueError(f"Coppia {start_key}/{end_key} incompleta")
                        work_segments.append({"start": parse_time_value(start_raw), "end": parse_time_value(end_raw)})

            if "pause_start" in columns or "pause_end" in columns:
                pause_start = row.get(columns.get("pause_start", ""), "").strip() if columns.get("pause_start") else ""
                pause_end = row.get(columns.get("pause_end", ""), "").strip() if columns.get("pause_end") else ""
                if pause_start or pause_end:
                    if not pause_start or not pause_end:
                        raise ValueError("Pausa incompleta")
                    break_segments.append({"start": parse_time_value(pause_start), "end": parse_time_value(pause_end)})

            if not work_segments:
                raise ValueError("Nessun intervallo di lavoro presente")

            existed = get_shift_for_day(user_id, row_date.isoformat()) is not None
            upsert_shift({
                "user_id": user_id,
                "date": row_date.isoformat(),
                "work_segments": normalize_segments(work_segments),
                "break_segments": normalize_segments(break_segments),
                "note": note,
            })
            if existed:
                updated += 1
            else:
                imported += 1
        except Exception as exc:  # noqa: BLE001 - line-level import report
            errors.append({"line": line_number, "error": str(exc)})

    return {
        "imported": imported,
        "updated": updated,
        "vacations": vacations,
        "errors": errors,
        "total_errors": len(errors),
    }


CSV_TEMPLATE = """data;tipo;start_1;end_1;start_2;end_2;pause_start;pause_end;ore_accreditate;note
2026-01-05;work;08:30;14:30;;;;;;Turno mattina
2026-01-06;work;08:30;14:30;15:00;19:30;;;;Turno spezzato
2026-01-07;work;08:00;17:00;;;12:30;13:00;;Pausa esplicita
2026-01-12;ferie;;;;;;;30,5;Settimana ferie
"""
