"""End-to-end recovery drills using disposable hosts files only.

Runs on Linux, macOS and Windows in CI. Never modifies a real OS hosts file.
"""
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import xusguard as app
from xusguard_recovery import inspect_backup, list_backups, restore_backup


class RecoveryDrill(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)
        self.hosts = self.folder / "hosts"
        self.backups = self.folder / "backups"
        self.backups.mkdir()
        self.initial = b"127.0.0.1 localhost\r\n# legacy byte: \xff\r\n"
        self.hosts.write_bytes(self.initial)
        patcher = mock.patch.object(app, "get_backup_directory",
                                    return_value=self.backups)
        patcher.start()
        self.addCleanup(patcher.stop)

    def original_backup(self):
        self.assertTrue(app.backup_hosts_file(self.hosts))
        records = list_backups(self.hosts, self.backups)
        self.assertEqual(len(records), 1)
        return records[0]

    def test_full_install_corruption_rollback_roundtrip(self):
        before = self.original_backup()
        self.assertTrue(app.install_hosts_file(
            self.hosts, "127.0.0.1 localhost\n"
            "# BEGIN XUSGUARD MANAGED\n0.0.0.0 ads.example\n"
            "# END XUSGUARD MANAGED\n"))
        self.assertNotEqual(self.hosts.read_bytes(), self.initial)
        self.assertTrue(app.recover_selected_backup(
            self.hosts, before["path"], before["sha256"]))
        self.assertEqual(self.hosts.read_bytes(), self.initial)
        self.assertGreaterEqual(len(list_backups(self.hosts, self.backups)), 3)

    def test_correct_backup_list_scopes_to_hosts_name(self):
        self.original_backup()
        (self.backups / "otherhost_20260201_000000_abc.adblock_backup").write_bytes(
            b"0.0.0.0 malicious.example\n")
        records = list_backups(self.hosts, self.backups)
        self.assertEqual(len(records), 1)
        self.assertTrue(records[0]["path"].endswith(".adblock_backup"))

    def test_hash_mismatch_refuses_restore(self):
        entry = self.original_backup()
        self.assertTrue(app.install_hosts_file(self.hosts, "127.0.0.1 localhost\n"))
        current = self.hosts.read_bytes()
        self.assertFalse(app.recover_selected_backup(
            self.hosts, entry["path"], "0" * 64))
        self.assertEqual(self.hosts.read_bytes(), current)

    def test_tampering_after_preview_refuses_restore(self):
        entry = self.original_backup()
        self.assertTrue(app.install_hosts_file(self.hosts, "0.0.0.0 ads.example\n"))
        current = self.hosts.read_bytes()
        Path(entry["path"]).write_bytes(b"0.0.0.0 switched.example\n")
        self.assertFalse(app.recover_selected_backup(
            self.hosts, entry["path"], entry["sha256"]))
        self.assertEqual(self.hosts.read_bytes(), current)

    def test_symlink_backup_refused(self):
        victim = self.folder / "external.dat"
        victim.write_bytes(self.initial)
        link = self.backups / "hosts_fake.adblock_backup"
        try:
            link.symlink_to(victim)
        except (OSError, NotImplementedError):
            self.skipTest("Symlinks denied on runner")
        self.assertFalse(list_backups(self.hosts, self.backups))
        with self.assertRaises(ValueError):
            inspect_backup(self.hosts, link, [self.backups])

    def test_path_traversal_refused(self):
        outside = self.folder / "hosts_unsafe.adblock_backup"
        outside.write_bytes(self.initial)
        with self.assertRaises(ValueError):
            inspect_backup(self.hosts, outside, [self.backups])

    def test_empty_backup_refused(self):
        (self.backups / "hosts_empty.adblock_backup").write_bytes(b"")
        self.assertEqual(list_backups(self.hosts, self.backups), [])

    def test_backup_failure_preserves_current_hosts(self):
        entry = self.original_backup()
        self.assertTrue(app.install_hosts_file(self.hosts, "0.0.0.0 ads.example\n"))
        current = self.hosts.read_bytes()
        with mock.patch.object(app, "backup_hosts_file", return_value=False):
            self.assertFalse(app.recover_selected_backup(
                self.hosts, entry["path"], entry["sha256"]))
        self.assertEqual(self.hosts.read_bytes(), current)

    def test_atomic_replace_failure_does_not_truncate(self):
        entry = self.original_backup()
        self.assertTrue(app.install_hosts_file(self.hosts, "0.0.0.0 ads.example\n"))
        current = self.hosts.read_bytes()
        with mock.patch.object(app, "replace_preserving_metadata",
                               side_effect=PermissionError("locked")):
            self.assertFalse(app.recover_selected_backup(
                self.hosts, entry["path"], entry["sha256"]))
        self.assertEqual(self.hosts.read_bytes(), current)
        self.assertEqual(list(self.folder.glob(".xusguard-*")), [])

    def test_restore_with_malformed_original_non_utf8_bytes(self):
        entry = self.original_backup()
        self.assertEqual(entry["sha256"], hashlib.sha256(self.initial).hexdigest())
        self.assertTrue(app.install_hosts_file(self.hosts, "0.0.0.0 ads.example\n"))
        self.assertTrue(app.recover_selected_backup(
            self.hosts, entry["path"], entry["sha256"]))
        self.assertEqual(self.hosts.read_bytes(), self.initial)

    def test_interrupted_backup_removes_partial_file(self):
        with mock.patch.object(app.os, "fsync", side_effect=OSError("disk write failed")):
            self.assertFalse(app.backup_hosts_file(self.hosts))
        self.assertEqual(list(self.backups.glob("*.adblock_backup")), [])
        self.assertEqual(self.hosts.read_bytes(), self.initial)

    def test_backup_refuses_empty_or_oversize_source(self):
        self.hosts.write_bytes(b"")
        self.assertFalse(app.backup_hosts_file(self.hosts))
        self.assertFalse(list(self.backups.iterdir()))


    def test_non_utf8_service_write_does_not_destroy_legacy_bytes(self):
        self.hosts.write_bytes(self.initial)
        self.assertFalse(app.apply_service_changes(
            self.hosts, {"social.example": "0.0.0.0"}, True, "Test"))
        self.assertEqual(self.hosts.read_bytes(), self.initial)

    def test_non_utf8_manual_redirect_write_refused(self):
        self.hosts.write_bytes(self.initial)
        self.assertFalse(app.add_redirect_to_hosts(
            self.hosts, "ads.example", "192.0.2.3"))
        self.assertEqual(self.hosts.read_bytes(), self.initial)

    def test_direct_restore_requires_digest(self):
        entry = self.original_backup()
        with self.assertRaises(ValueError):
            restore_backup(self.hosts, entry["path"], [self.backups],
                           None, app.install_hosts_file)


if __name__ == "__main__":
    unittest.main()
