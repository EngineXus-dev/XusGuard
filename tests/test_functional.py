"""Functional, offline regression tests. All writes use temporary files."""
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("xusguard_test_app", ROOT / "uniadblock.py")
APP = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(APP)


class HostSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.hosts = self.root / "hosts"
        self.hosts.write_text("127.0.0.1 localhost\n192.0.2.2 private.example\n", encoding="utf-8")
        self.backups = self.root / "backups"
        self.backups.mkdir()
        patcher = mock.patch.object(APP, "get_backup_directory", return_value=self.backups)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_strict_domains(self):
        good = ["ads.example", "a-b.example.com", "EXAMPLE.ORG"]
        bad = ["", "localhost", "ads.local", "host", "-bad.example",
               "evil_.example", "evil.example\n0.0.0.0 localhost",
               "https://evil.example", "a..example", "127.0.0.1",
               "example.com.", "a" * 64 + ".example"]
        for x in good:
            with self.subTest(valid=x):
                self.assertIsNotNone(APP.normalize_domain(x))
        for x in bad:
            with self.subTest(invalid=x):
                self.assertIsNone(APP.normalize_domain(x))

    def test_drops_hostfile_injection(self):
        content = ("0.0.0.0 ad.example tracker.example\n"
                   "192.0.2.10 bank.example\n"
                   "bad.example extra.example\n"
                   "127.0.0.1 localhost\n"
                   "not.example # comment\n"
                   "ads.example\n")
        entries = APP.parse_hosts_file(content)
        self.assertIn(("0.0.0.0", "ad.example"), entries)
        self.assertIn(("0.0.0.0", "tracker.example"), entries)
        self.assertNotIn(("0.0.0.0", "bank.example"), entries)
        self.assertNotIn(("0.0.0.0", "bad.example"), entries)
        self.assertNotIn(("0.0.0.0", "localhost"), entries)

    def test_preserves_unmanaged_lines_when_replacing(self):
        first = APP.replace_managed_section(self.hosts.read_text(), "0.0.0.0 ads.example")
        second = APP.replace_managed_section(first, "0.0.0.0 tracking.example")
        self.assertEqual(second.count(APP.MANAGED_START), 1)
        self.assertEqual(second.count(APP.MANAGED_END), 1)
        self.assertNotIn("ads.example", second)
        self.assertIn("192.0.2.2 private.example", second)
        self.assertIn("0.0.0.0 tracking.example", second)

    def test_refuses_malformed_markers(self):
        with self.assertRaises(ValueError):
            APP.replace_managed_section("# BEGIN XUSGUARD MANAGED\nother\n", "0.0.0.0 ads.example")

    def test_atomic_hosts_update_makes_backup(self):
        previous = self.hosts.read_text()
        new_text = previous + "# added safely\n"
        self.assertTrue(APP.install_hosts_file(self.hosts, new_text))
        self.assertEqual(self.hosts.read_text(), new_text)
        matches = list(self.backups.glob("*.adblock_backup"))
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].read_text(), previous)

    def test_backup_failure_blocks_update(self):
        previous = self.hosts.read_bytes()
        with mock.patch.object(APP, "backup_hosts_file", return_value=False):
            self.assertFalse(APP.install_hosts_file(self.hosts, "0.0.0.0 evil.example\n"))
        self.assertEqual(self.hosts.read_bytes(), previous)

    def test_atomic_replace_failure_preserves_original(self):
        previous = self.hosts.read_bytes()
        with mock.patch.object(APP, "replace_preserving_metadata", side_effect=PermissionError("blocked")):
            self.assertFalse(APP.install_hosts_file(self.hosts, "0.0.0.0 new.example\n"))
        self.assertEqual(self.hosts.read_bytes(), previous)
        self.assertEqual(list(self.root.glob(".xusguard-*")), [])

    def test_symlink_host_rejected(self):
        link = self.root / "linked_hosts"
        try:
            link.symlink_to(self.hosts)
        except (OSError, NotImplementedError):
            self.skipTest("Symlink support disabled")
        previous = self.hosts.read_bytes()
        self.assertFalse(APP.install_hosts_file(link, "0.0.0.0 bad.example\n"))
        self.assertEqual(self.hosts.read_bytes(), previous)

    def test_marked_redirect_round_trip(self):
        previous = self.hosts.read_text()
        self.assertTrue(APP.add_redirect_to_hosts(self.hosts, "test.example", "192.0.2.3"))
        self.assertIn("# XusGuard redirect: test.example", self.hosts.read_text())
        self.assertTrue(APP.remove_redirect_from_hosts(self.hosts, "test.example", "192.0.2.3"))
        self.assertEqual(self.hosts.read_text(), previous)

    def test_unowned_redirect_is_not_deleted(self):
        self.assertFalse(APP.remove_redirect_from_hosts(self.hosts, "private.example", "192.0.2.2"))
        self.assertIn("private.example", self.hosts.read_text())

    def test_noninteractive_cleanup_cannot_delete_backups(self):
        (self.backups / "preserve.adblock_backup").write_text("important")
        self.assertFalse(APP.cleanup_project(non_interactive=True))
        self.assertTrue((self.backups / "preserve.adblock_backup").exists())

    def test_download_refuses_http_without_network(self):
        with mock.patch.object(APP.urllib.request, "build_opener") as opener:
            self.assertIsNone(APP.download_hosts_file("http://example.org/list"))
            opener.assert_not_called()

    def test_source_name_cannot_inject_hosts_line(self):
        self.assertNotIn("\n", APP.safe_comment("feed\n0.0.0.0 banking.example"))


class OwnershipTests(unittest.TestCase):
    def test_no_upstream_network_references(self):
        for path in ("uniadblock.py", "install.sh", "install.bat", "README.md"):
            with self.subTest(path=path):
                txt = (ROOT / path).read_text(encoding="utf-8").lower()
                self.assertNotIn("raw.githubusercontent.com/infosecredd", txt)
                self.assertNotIn("github.com/infosecredd", txt)

    def test_no_automatic_package_installs(self):
        app = (ROOT / "uniadblock.py").read_text(encoding="utf-8")
        self.assertNotIn("setup_venv()", app)
        self.assertNotIn("pip', 'install'", app)


if __name__ == "__main__":
    unittest.main()
