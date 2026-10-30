"""Headless tests for selection persistence and readable recovery reports."""
from pathlib import Path
import unittest

from xusguard_gui_helpers import (
    clean_terminal_output,
    selected_keys,
    summarize_recovery_drill,
)

ROOT = Path(__file__).resolve().parents[1]


class SelectionTests(unittest.TestCase):
    def test_multiple_clicked_rows_are_independent(self):
        keys = ["1", "2", "3", "4"]
        self.assertEqual(selected_keys(keys, (0, 2, 3)), ["1", "3", "4"])
        # Clicking the same selected row again removes only that row.
        self.assertEqual(selected_keys(keys, (0, 3)), ["1", "4"])

    def test_selection_uses_stable_keys_after_reordering(self):
        chosen = set(selected_keys(["a", "b", "c"], (0, 2)))
        self.assertEqual(chosen, {"a", "c"})
        reordered = ["c", "b", "a"]
        selected_rows = [i for i, key in enumerate(reordered) if key in chosen]
        self.assertEqual(selected_rows, [0, 2])

    def test_listbox_configuration_keeps_multi_selection_and_focus(self):
        gui = (ROOT / "xusguard_gui.py").read_text(encoding="utf-8")
        self.assertIn("selectmode=tk.MULTIPLE if multiple else tk.BROWSE", gui)
        self.assertIn("exportselection=False", gui)
        self.assertGreaterEqual(gui.count("self.listbox(self.area, multiple=True)"), 2)
        self.assertIn("self.selected_source_ids", gui)
        self.assertIn("self.selected_service_ids", gui)


class DiagnosticsTests(unittest.TestCase):
    @staticmethod
    def fake_log():
        stdout = (
            "\x1b[92m✓ Verified backup created: C:\\Temp\\tmp123\\backups\x1b[0m\n"
            "\x1b[91m✗ Backup failed; refusing to modify hosts file: disk write failed\x1b[0m\n"
        )
        stderr = (
            "test_backup_failure (test_recovery.RecoveryDrill.test_backup_failure) ... ok\n"
            "test_restore (test_recovery.RecoveryDrill.test_restore) ... ok\n"
            "test_symlink (test_recovery.RecoveryDrill.test_symlink) ... "
            "skipped 'Symlinks denied on runner'\n"
            "----------------------------------------------------------------------\n"
            "Ran 3 tests in 0.334s\n\nOK (skipped=1)\n"
        )
        return stdout, stderr

    def test_full_output_removes_ansi_escape_sequences(self):
        stdout, stderr = self.fake_log()
        cleaned = clean_terminal_output(stdout + stderr)
        self.assertNotIn("\x1b", cleaned)
        self.assertIn("Verified backup created", cleaned)

    def test_success_summary_does_not_show_expected_failure_log(self):
        stdout, stderr = self.fake_log()
        result = summarize_recovery_drill(stdout, stderr, 0)
        self.assertTrue(result["passed"])
        self.assertEqual((result["total"], result["passed_count"], result["skipped"]),
                         (3, 2, 1))
        self.assertIn("RECOVERY DRILL PASSED", result["summary"])
        self.assertNotIn("disk write failed", result["summary"])
        self.assertNotIn("C:\\Temp", result["summary"])
        self.assertIn("disk write failed", result["details"])
        self.assertNotIn("\x1b", result["details"])

    def test_failing_test_run_is_never_reported_as_success(self):
        stdout, _ = self.fake_log()
        stderr = ("test_restore (test_recovery.RecoveryDrill.test_restore) ... FAIL\n"
                  "Ran 1 test in 0.001s\n\nFAILED (failures=1)\n")
        result = summarize_recovery_drill(stdout, stderr, 1)
        self.assertFalse(result["passed"])
        self.assertIn("RECOVERY DRILL FAILED", result["summary"])

    def test_truncated_runner_output_is_not_success(self):
        result = summarize_recovery_drill("", "OK", 0)
        self.assertFalse(result["passed"])


if __name__ == "__main__":
    unittest.main()
