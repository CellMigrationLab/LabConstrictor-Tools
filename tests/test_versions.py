"""Tools versioning: the version has one source, and the tagging procedure is written down (docs/OPERATIONS.md)."""

import re
import unittest
from importlib import metadata

import _paths  # noqa: F401  (must come first)
from _paths import ROOT

import labconstrictor_tools
from labconstrictor_tools import _version


class VersionHasOneSource(unittest.TestCase):
    def test_package_version_is_the_version_module(self):
        self.assertEqual(labconstrictor_tools.__version__, _version.__version__)
        self.assertRegex(_version.__version__, r"^\d+\.\d+\.\d+((a|b|rc)\d+)?$")

    def test_pyproject_does_not_repeat_the_version(self):
        text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        project = text.split("[project]", 1)[1].split("\n[", 1)[0]
        self.assertIsNone(re.search(r"^version\s*=", project, re.M), "a second, static version in [project]")
        self.assertIn('dynamic = ["version"]', project)
        self.assertIn("labconstrictor_tools._version.__version__", text)

    def test_installed_metadata_matches_the_source(self):
        try:
            installed = metadata.version("labconstrictor-tools")
        except metadata.PackageNotFoundError:
            self.skipTest("run from a source folder: no installed metadata to compare")
        self.assertEqual(installed, _version.__version__, "reinstall: pip install -e .")

    def test_tagging_procedure_is_documented(self):
        text = (ROOT / "docs" / "OPERATIONS.md").read_text(encoding="utf-8")
        self.assertTrue("## Releases and tags" in text)
        for needle in ("vX.Y.Z", "v0.2.0-rc.1", "the maintainer tags", "Claude and CI never create tags"):
            self.assertTrue(needle in text, "OPERATIONS.md lacks: " + needle)

    def test_installer_pinning_is_documented_with_the_files_to_change(self):
        text = (ROOT / "docs" / "OPERATIONS.md").read_text(encoding="utf-8")
        section = text.split("### Pinning Tools in app installers", 1)[1].split("\n## ", 1)[0]
        for needle in ("LC_TOOLS_SPEC", "refs/tags/", "refs/heads/main.zip", "post_install.sh", "post_install.bat"):
            self.assertTrue(needle in section, "pinning section lacks: " + needle)


if __name__ == "__main__":
    unittest.main()
