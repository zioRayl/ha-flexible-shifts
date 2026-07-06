from __future__ import annotations

import csv
import io
from datetime import date, datetime, timedelta
from typing import Any

from calculations import normalize_segments, parse_time_value, vacation_credit_hours, weekly_standard_hours
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
    "end_date": {"end_date", "data_fine", "fine_ferie", "ferie_fino_al"},
    "start_1": {"start_1", "start1", "inizio_1", "inizio1", "entrata_1", "entrata1", "start", "inizio_turno"},
    "end_1": {"end_1", "end1", "stop_1", "stop1", "fine_1", "fine1", "uscita_1", "uscita1", "stop", "fine_turno"},
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

            if row_type in {"vacation", "ferie", "holiday_week", "ferie_settimana", "vacation_day", "ferie_giorno"}:
                raw_credit = row.get(columns.get("credited_hours", ""), "").strip() if columns.get("credited_hours") else ""
                raw_end_date = row.get(columns.get("end_date", ""), "").strip() if columns.get("end_date") else ""

                if raw_end_date:
                    vacation_start = row_date
                    vacation_end = _parse_date(raw_end_date)
                elif row_type in {"holiday_week", "ferie_settimana"}:
                    vacation_start = row_date - timedelta(days=row_date.weekday())
                    vacation_end = vacation_start + timedelta(days=4 if user["employment_type"] == "full_time" else 6)
                else:
                    # New default: a generic "ferie" row is one day. For compatibility
                    # with old exports, a weekly credit with no end date is inferred as a full week.
                    inferred_week = False
                    if raw_credit:
                        try:
                            inferred_week = float(raw_credit.replace(",", ".")) >= weekly_standard_hours(user) * 0.9
                        except ValueError:
                            inferred_week = False
                    if inferred_week and row_type in {"vacation", "ferie"}:
                        vacation_start = row_date - timedelta(days=row_date.weekday())
                        vacation_end = vacation_start + timedelta(days=4 if user["employment_type"] == "full_time" else 6)
                    else:
                        vacation_start = row_date
                        vacation_end = row_date

                if vacation_end < vacation_start:
                    raise ValueError("La data di fine ferie precede quella di inizio")
                credit = (
                    float(raw_credit.replace(",", "."))
                    if raw_credit
                    else vacation_credit_hours(user, vacation_start, vacation_end)
                )
                create_vacation({
                    "user_id": user_id,
                    "start_date": vacation_start.isoformat(),
                    "end_date": vacation_end.isoformat(),
                    "credited_hours": credit,
                    "note": note,
                })
                vacations += 1
                continue

            first_start = row.get(columns.get("start_1", ""), "").strip() if columns.get("start_1") else ""
            first_end = row.get(columns.get("end_1", ""), "").strip() if columns.get("end_1") else ""
            second_start = row.get(columns.get("start_2", ""), "").strip() if columns.get("start_2") else ""
            second_end = row.get(columns.get("end_2", ""), "").strip() if columns.get("end_2") else ""
            pause_start = row.get(columns.get("pause_start", ""), "").strip() if columns.get("pause_start") else ""
            pause_end = row.get(columns.get("pause_end", ""), "").strip() if columns.get("pause_end") else ""

            if not first_start or not first_end:
                raise ValueError("Inizio turno o fine turno mancanti")
            if bool(second_start) != bool(second_end):
                raise ValueError("Seconda coppia Start/Stop incompleta")
            if bool(pause_start) != bool(pause_end):
                raise ValueError("Pausa incompleta")

            # Compatibilità con i vecchi Google Sheet: due coppie Start/Stop
            # significano un unico turno con la pausa compresa tra le due coppie.
            if second_start and second_end:
                if pause_start or pause_end:
                    raise ValueError("Usare la seconda coppia Start/Stop oppure la pausa esplicita, non entrambe")
                work_segments = [{
                    "start": parse_time_value(first_start),
                    "end": parse_time_value(second_end),
                }]
                break_segments = [{
                    "start": parse_time_value(first_end),
                    "end": parse_time_value(second_start),
                }]
            else:
                work_segments = [{
                    "start": parse_time_value(first_start),
                    "end": parse_time_value(first_end),
                }]
                break_segments = []
                if pause_start and pause_end:
                    break_segments.append({
                        "start": parse_time_value(pause_start),
                        "end": parse_time_value(pause_end),
                    })

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


CSV_TEMPLATE = """data;data_fine;tipo;inizio_turno;fine_turno;inizio_pausa;fine_pausa;ore_accreditate;note
2026-01-05;;work;08:30;14:30;;;;Turno mattina
2026-01-06;;work;08:00;19:30;11:00;15:00;;Turno con pausa
2026-01-12;;ferie;;;;;;;Singolo giorno di ferie
2026-02-02;2026-02-08;ferie;;;;;;;Intervallo di ferie
"""
