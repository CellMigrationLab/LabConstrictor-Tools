"""The GitHub Pages site of this repository is only redirects (scripts/build_redirect_site.py): every docs page's old address leads to
its new home on the LabConstrictor website, or to the file on GitHub for a maintainers' page."""

import importlib.util
import tempfile
import unittest
from pathlib import Path

import _paths  # noqa: F401  (must come first)
from _paths import ROOT

SPEC = importlib.util.spec_from_file_location(
    "build_redirect_site", ROOT / "scripts" / "build_redirect_site.py"
)
assert SPEC is not None and SPEC.loader is not None
redirect = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(redirect)


class RedirectSite(unittest.TestCase):
    def test_every_docs_page_has_a_destination(self) -> None:
        names = {p.stem for p in (ROOT / "docs").glob("*.md")}
        self.assertEqual(set(redirect.targets(ROOT / "docs")) & names, names)

    def test_published_pages_go_to_the_website_and_the_rest_to_github(self) -> None:
        found = redirect.targets(ROOT / "docs")
        self.assertEqual(
            found["PROTOCOL"], "https://cellmigrationlab.github.io/LabConstrictor-Site/guides/protocol/"
        )
        self.assertEqual(found["index"], "https://cellmigrationlab.github.io/LabConstrictor-Site/connect/")
        self.assertEqual(
            found["TESTING"],
            "https://github.com/CellMigrationLab/LabConstrictor-Tools/blob/main/docs/TESTING.md",
        )
        for name in redirect.NOT_PUBLISHED:
            self.assertTrue((ROOT / "docs" / (name + ".md")).is_file(), name)

    def test_the_pages_are_written_at_the_old_addresses_and_keep_the_section(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            redirect.build(out, ROOT / "docs")
            text = (out / "MANIFEST" / "index.html").read_text(encoding="utf-8")
            self.assertTrue((out / "index.html").is_file() and (out / "404.html").is_file())
        target = "https://cellmigrationlab.github.io/LabConstrictor-Site/guides/tool-markers/"
        self.assertIn("location.replace('%s' + location.hash)" % target, text)
        self.assertIn('<link rel="canonical" href="%s">' % target, text)
        self.assertIn('content="1; url=%s"' % target, text)

    def test_a_docs_page_without_a_destination_stops_the_build(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            docs = Path(tmp)
            (docs / "PROTOCOL.md").write_text("# p\n", encoding="utf-8")
            (docs / "NEW_PAGE.md").write_text("# new\n", encoding="utf-8")
            with self.assertRaises(SystemExit) as ctx:
                redirect.targets(docs)
        self.assertIn("NEW_PAGE", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
