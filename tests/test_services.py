"""Regression tests for data-driven, opt-in service blocking (no real hosts edits)."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("xusguard_services_test", ROOT / "xusguard.py")
APP = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(APP)


class ServiceCatalogTests(unittest.TestCase):
    def test_catalog_has_small_explicit_scope(self):
        categories, services = APP.load_service_catalog()
        self.assertEqual(len(categories), 6)
        self.assertEqual(len(services), 31)
        self.assertNotIn("Government/Surveillance", categories)
        self.assertNotIn("Fake News", categories)
        self.assertTrue(all(0 < len(x["domains"]) <= 40 for x in services.values()))

    def test_catalog_does_not_include_shared_cloud_infrastructure(self):
        _, services = APP.load_service_catalog()
        domains = {d for s in services.values() for d in s["domains"]}
        self.assertNotIn("amazonaws.com", domains)
        self.assertNotIn("office.com", domains)
        self.assertNotIn("unrealengine.com", domains)

    def test_invalid_catalog_raises_without_hosts_modification(self):
        with tempfile.TemporaryDirectory() as tmp:
            test_json = Path(tmp) / "services.json"
            test_json.write_text(json.dumps({
                "schema_version": 1, "categories": ["Test"],
                "services": [{"name": "Unsafe", "category": "Test",
                              "domains": ["good.example\\n0.0.0.0 bad.example"]}]
            }), encoding="utf-8")
            class FakePath:
                def __init__(self, parent):
                    self.parent = parent
            with mock.patch.object(APP, "__file__", str(Path(tmp) / "xusguard.py")):
                with self.assertRaises(ValueError):
                    APP.load_service_catalog()


class ManagedServiceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.hosts = self.base / "hosts"
        self.backups = self.base / "backups"
        self.backups.mkdir()
        self.original = ("127.0.0.1 localhost\n"
                         "192.0.2.44 internal.example\n"
                         "# BEGIN XUSGUARD MANAGED\n"
                         "0.0.0.0 ads.example\n"
                         "0.0.0.0 shared.example\n"
                         "# END XUSGUARD MANAGED\n")
        self.hosts.write_text(self.original, encoding="utf-8")
        patcher = mock.patch.object(APP, "get_backup_directory", return_value=self.backups)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_service_changes_never_remove_downloaded_list_domains(self):
        self.assertTrue(APP.apply_service_changes(
            str(self.hosts), {"shared.example": "0.0.0.0", "social.example": "0.0.0.0"}, True, "Test"))
        content = self.hosts.read_text()
        self.assertEqual(content.count("0.0.0.0 shared.example"), 1)
        self.assertIn("0.0.0.0\\tsocial.example", content)
        self.assertTrue(APP.apply_service_changes(
            str(self.hosts), {"shared.example": "0.0.0.0", "social.example": "0.0.0.0"}, False, "Test"))
        result = self.hosts.read_text()
        self.assertIn("0.0.0.0 shared.example", result)
        self.assertIn("192.0.2.44 internal.example", result)
        self.assertNotIn(APP.SERVICE_START, result)
        self.assertEqual(APP.get_service_blocked_domains(result), set())

    def test_malformed_owned_service_markers_fail_closed(self):
        bad = self.original + "# BEGIN XUSGUARD SERVICES\n0.0.0.0 test.example\n"
        self.hosts.write_text(bad, encoding="utf-8")
        self.assertFalse(APP.apply_service_changes(
            self.hosts, {"test.example": "0.0.0.0"}, True, "Test"))
        self.assertEqual(self.hosts.read_text(), bad)

    def test_existing_service_rules_preserved_across_list_updates(self):
        content = APP.update_service_section(self.original, {"social.example"})
        revised = APP.replace_managed_section(content, "0.0.0.0 tracker.example\n")
        self.assertIn("0.0.0.0\\tsocial.example", revised)
        self.assertIn("tracker.example", revised)
        self.assertNotIn("ads.example", revised)
        self.assertIn("192.0.2.44 internal.example", revised)

    def test_invalid_domain_never_reaches_file_writer(self):
        with mock.patch.object(APP, "install_hosts_file", side_effect=AssertionError("unsafe write")):
            self.assertFalse(APP.apply_service_changes(
                self.hosts, {"test.example\\n127.0.0.1 localhost": "0.0.0.0"}, True, "Test"))

    def test_service_enable_requires_backup(self):
        old = self.hosts.read_bytes()
        with mock.patch.object(APP, "backup_hosts_file", return_value=False):
            self.assertFalse(APP.apply_service_changes(
                self.hosts, {"social.example": "0.0.0.0"}, True, "Test"))
        self.assertEqual(self.hosts.read_bytes(), old)


if __name__ == "__main__":
    unittest.main()
