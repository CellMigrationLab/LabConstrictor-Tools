"""The cross-version read test (tests/compat_matrix.py) and its frozen schema fixtures.

CI runs the script against the newest git tag (job `compat`); here it runs against the interpreter of the tests, which
proves the script itself works on every system on every run.
"""

import hashlib
import json
import subprocess
import sys
import unittest

import _paths  # noqa: F401  (must come first)
from _paths import ROOT

from labconstrictor_tools import registry

FIXTURES = ROOT / "tests" / "fixtures" / "schemas"
# frozen: a fixture changes only by adding a new file for a new Tools version, never by editing one
SHA256 = {
    "tools_0.1.schema.json": "3ae96405701fffb6207bfc38b35446f0ab42d27171e04037bec82c6353d700f2",
    "tools_0.2.schema.json": "0a8d3c9ecb361bd4ce690ed42a71d0147891268c7871a77385c504044e493a36",
    "tools_0.3.schema.json": "d79c50e47e6ac5f70e89ccec866e7ca5cfb63fe43d7c6af5e98d5defc30210dc",
}


class Fixtures(unittest.TestCase):
    def test_fixtures_are_frozen_and_loadable(self) -> None:
        for name, digest in SHA256.items():
            data = (FIXTURES / name).read_bytes().replace(b"\r\n", b"\n")
            self.assertEqual(
                hashlib.sha256(data).hexdigest(), digest, name + " was edited: add a new fixture instead"
            )
            registry._validated_schema(json.loads(data))

    def test_the_0_1_fixture_has_no_version_fields_and_the_0_2_one_has_both(self) -> None:
        old = json.loads((FIXTURES / "tools_0.1.schema.json").read_text("utf-8"))
        new = json.loads((FIXTURES / "tools_0.2.schema.json").read_text("utf-8"))
        self.assertFalse({"tools_version", "features"} & set(old))
        self.assertTrue({"tools_version", "features"} <= set(new))
        newest = json.loads((FIXTURES / "tools_0.3.schema.json").read_text("utf-8"))
        self.assertEqual(newest["tools_version"], "0.3.0a1")
        self.assertIn("shm_order_v1", newest["features"])


class Script(unittest.TestCase):
    def run_script(self, old_python: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(ROOT / "tests" / "compat_matrix.py"), "--old-python", old_python],
            capture_output=True, text=True, encoding="utf-8", timeout=300,
        )  # fmt: skip

    def test_every_check_of_the_matrix_passes_against_itself(self) -> None:
        result = self.run_script(sys.executable)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout.count("ok  "), 14, result.stdout)
        self.assertNotIn("FAIL", result.stdout)

    def test_an_old_install_that_cannot_run_fails_the_matrix(self) -> None:
        result = self.run_script(str(ROOT / "no" / "such" / "python"))
        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
