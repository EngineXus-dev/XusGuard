"""Headless regression tests for XusGuard GUI preview and guarded apply."""
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import xusguard as core
from xusguard_preview import apply_preview, build_preview


class GuiPreviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.hosts = self.root / "hosts"
        self.hosts.write_text("127.0.0.1 localhost\n192.0.2.8 work.example\n", encoding="utf-8")
        self.backups = self.root / "backups"
        self.cache = self.root / "cache"
        self.backups.mkdir()
        self.cache.mkdir()
        for name, value in [("get_backup_directory", self.backups),
                            ("get_sources_directory", self.cache)]:
            patcher = mock.patch.object(core, name, return_value=value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.sources = {"1": {"name": "Testing", "url": "https://example.org/hosts", "enabled": True}}
        self.assertIsNotNone(core.save_source_file("1", "Testing", {"ads.example": "0.0.0.0"}))

    def test_preview_is_read_only_and_preserves_user_entries(self):
        before = self.hosts.read_bytes()
        with mock.patch.object(core, "install_hosts_file",
                               side_effect=AssertionError("must not write on preview")):
            preview = build_preview(core, self.hosts, self.sources)
        self.assertEqual(self.hosts.read_bytes(), before)
        self.assertEqual(preview["domains"], 1)
        self.assertIn("192.0.2.8 work.example", preview["content"])
        self.assertIn("ads.example", preview["content"])
        self.assertEqual(list(self.backups.iterdir()), [])

    def test_explicit_apply_creates_rollback_and_updates_only_managed(self):
        preview = build_preview(core, self.hosts, self.sources)
        self.assertTrue(apply_preview(core, preview, self.sources))
        text = self.hosts.read_text()
        self.assertIn("192.0.2.8 work.example", text)
        self.assertIn("0.0.0.0\tads.example", text)
        self.assertEqual(len(list(self.backups.glob("*.adblock_backup"))), 1)

    def test_apply_refuses_changed_hosts_since_preview(self):
        preview = build_preview(core, self.hosts, self.sources)
        self.hosts.write_text(self.hosts.read_text() + "192.0.2.9 changed.example\n")
        with mock.patch.object(core, "install_hosts_file",
                               side_effect=AssertionError("must not write stale preview")):
            with self.assertRaises(ValueError):
                apply_preview(core, preview, self.sources)

    def test_apply_refuses_changed_cache_since_preview(self):
        preview = build_preview(core, self.hosts, self.sources)
        path = core.get_source_file_path("Testing")
        path.write_text("0.0.0.0 different.example\n")
        with mock.patch.object(core, "install_hosts_file",
                               side_effect=AssertionError("must not write stale preview")):
            with self.assertRaises(ValueError):
                apply_preview(core, preview, self.sources)

    def test_missing_cache_refused(self):
        core.get_source_file_path("Testing").unlink()
        with self.assertRaises(ValueError):
            build_preview(core, self.hosts, self.sources)

    def test_non_utf8_user_hosts_never_silently_rewritten(self):
        self.hosts.write_bytes(b"127.0.0.1 localhost\n# old byte \xff\n")
        with self.assertRaises(ValueError):
            build_preview(core, self.hosts, self.sources)

    def test_source_change_after_preview_refused(self):
        preview = build_preview(core, self.hosts, self.sources)
        altered = {k: dict(v) for k, v in self.sources.items()}
        altered["1"]["enabled"] = False
        with self.assertRaises(ValueError):
            apply_preview(core, preview, altered)


if __name__ == "__main__":
    unittest.main()
