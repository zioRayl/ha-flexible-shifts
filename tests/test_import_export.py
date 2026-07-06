import tempfile
import unittest
from pathlib import Path
import sys

APP_DIR = Path(__file__).resolve().parents[1] / "flexible_shifts" / "app"
sys.path.insert(0, str(APP_DIR))

import db  # noqa: E402
from calculations import shift_total_hours  # noqa: E402
from import_export import import_csv  # noqa: E402


class ImportTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        db.DB_PATH = str(Path(self.tempdir.name) / "import.db")
        db.init_db()
        self.user = db.create_user({
            "name": "Import User",
            "employment_type": "part_time",
            "target_basis": "weekly",
            "target_hours": 30.5,
            "monthly_from_weekly_mode": "x4",
            "overtime_min": 0,
            "overtime_max": 12,
            "active": True,
        })

    def tearDown(self):
        self.tempdir.cleanup()

    def test_legacy_two_pairs_are_converted_to_pause(self):
        content = (
            "data;tipo;start_1;end_1;start_2;end_2;pause_start;pause_end;ore_accreditate;note\n"
            "05/01/2026;work;8,5;14,5;15;19,5;;;;Vecchio formato\n"
            "12/01/2026;ferie;;;;;;;30,5;Ferie\n"
        ).encode("utf-8")
        result = import_csv(content, self.user["id"])
        self.assertEqual(result["imported"], 1)
        self.assertEqual(result["vacations"], 1)
        self.assertEqual(result["total_errors"], 0)
        shift = db.get_shift_for_day(self.user["id"], "2026-01-05")
        self.assertEqual(shift["work_segments"], [{"start": "08:30", "end": "19:30"}])
        self.assertEqual(shift["break_segments"], [{"start": "14:30", "end": "15:00"}])
        self.assertEqual(shift_total_hours(shift), 10.5)
        vacations = db.list_vacations([self.user["id"]], "2026-01-01", "2026-01-31")
        self.assertEqual(vacations[0]["credited_hours"], 30.5)

    def test_single_day_and_range_vacations(self):
        content = (
            "data;data_fine;tipo;inizio_turno;fine_turno;inizio_pausa;fine_pausa;ore_accreditate;note\n"
            "20/01/2026;;ferie;;;;;;;Giorno singolo\n"
            "02/02/2026;04/02/2026;ferie;;;;;;;Tre giorni\n"
        ).encode("utf-8")
        result = import_csv(content, self.user["id"])
        self.assertEqual(result["vacations"], 2)
        self.assertEqual(result["total_errors"], 0)
        vacations = db.list_vacations([self.user["id"]], "2026-01-01", "2026-02-28")
        self.assertEqual(vacations[0]["start_date"], "2026-01-20")
        self.assertEqual(vacations[0]["end_date"], "2026-01-20")
        self.assertAlmostEqual(vacations[0]["credited_hours"], 30.5 / 7, places=5)
        self.assertEqual(vacations[1]["end_date"], "2026-02-04")
        self.assertAlmostEqual(vacations[1]["credited_hours"], 30.5 * 3 / 7, places=5)

    def test_modern_single_shift_format(self):
        content = (
            "data;tipo;inizio_turno;fine_turno;inizio_pausa;fine_pausa;ore_accreditate;note\n"
            "06/01/2026;work;08:00;19:30;11:00;15:00;;Turno con pausa\n"
        ).encode("utf-8")
        result = import_csv(content, self.user["id"])
        self.assertEqual(result["imported"], 1)
        self.assertEqual(result["total_errors"], 0)
        shift = db.get_shift_for_day(self.user["id"], "2026-01-06")
        self.assertEqual(shift["work_segments"], [{"start": "08:00", "end": "19:30"}])
        self.assertEqual(shift["break_segments"], [{"start": "11:00", "end": "15:00"}])
        self.assertEqual(shift_total_hours(shift), 7.5)


if __name__ == "__main__":
    unittest.main()
