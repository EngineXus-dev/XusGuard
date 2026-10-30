"""Offline security regression tests. Never alter /etc/hosts."""
import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SecurityTests(unittest.TestCase):
    def test_python_compiles(self):
        source = (ROOT / "xusguard.py").read_text(encoding="utf-8")
        compile(source, "xusguard.py", "exec")

    def test_tls_verification_not_bypassed(self):
        source = (ROOT / "xusguard.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        insecure = {"_create_unverified_context", "CERT_NONE"}
        self.assertFalse(any(
            isinstance(node, ast.Attribute) and node.attr in insecure
            for node in ast.walk(tree)
        ))
        self.assertIn("ssl.create_default_context()", source)
        self.assertIn("HTTPSOnlyRedirectHandler", source)

    def test_no_remote_code_execution_in_installers(self):
        for path in ("install.sh", "install.bat"):
            source = (ROOT / path).read_text(encoding="utf-8").lower()
            with self.subTest(path=path):
                self.assertNotIn("raw.githubusercontent.com", source)
                self.assertNotIn("invoke-webrequest", source)
                self.assertNotIn("curl -", source)

    def test_sources_are_https(self):
        import json
        sources = json.loads((ROOT / "sources.json").read_text(encoding="utf-8"))
        for item in sources.values():
            with self.subTest(source=item["name"]):
                self.assertTrue(item["url"].startswith("https://"))


if __name__ == "__main__":
    unittest.main()
