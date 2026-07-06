import tempfile
import unittest
from pathlib import Path
import sys

APP_DIR = Path(__file__).resolve().parents[1] / "flexible_shifts" / "app"
sys.path.insert(0, str(APP_DIR))

import db  # noqa: E402
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

    def test_semicolon_decimal_and_vacation(self):
        content = (
            "data;tipo;start_1;end_1;start_2;end_2;pause_start;pause_end;ore_accreditate;note\n"
            "05/01/2026;work;8,5;14,5;15;19,5;;;;Spezzato\n"
            "12/01/2026;ferie;;;;;;;30,5;Ferie\n"
        ).encode("utf-8")
        result = import_csv(content, self.user["id"])
        self.assertEqual(result["imported"], 1)
        self.assertEqual(result["vacations"], 1)
        self.assertEqual(result["total_errors"], 0)
        shift = db.get_shift_for_day(self.user["id"], "2026-01-05")
        self.assertEqual(shift["work_segments"][0]["start"], "08:30")
        vacations = db.list_vacations([self.user["id"]], "2026-01-01", "2026-01-31")
        self.assertEqual(vacations[0]["credited_hours"], 30.5)


if __name__ == "__main__":
    unittest.main()
