"""Build the GitHub Pages site of this repository: one redirect page per address the old docs site had.

The documentation is published on the LabConstrictor website (https://cellmigrationlab.github.io/LabConstrictor-Site/), which fetches
the pages from docs/. This repository's Pages site (https://cellmigrationlab.github.io/LabConstrictor-Tools/) only keeps the old
addresses working: each one sends the reader to the page's new home, keeping a `#section` part of the link. Maintainers' pages, which
the website does not publish, go to the file on GitHub.

    python scripts/build_redirect_site.py [--out site]

Standard library only. An unknown page in REDIRECTS is a programming error; a docs page that is neither redirected nor listed in
NOT_PUBLISHED stops the build (so a new page cannot silently lose its old address).
"""

from __future__ import annotations

import argparse
import html
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://cellmigrationlab.github.io/LabConstrictor-Site/"
GITHUB = "https://github.com/CellMigrationLab/LabConstrictor-Tools/blob/main/docs/"

# old page (docs/<name>.md, served at /<name>/) -> its address on the LabConstrictor website
REDIRECTS = {
    "index": SITE + "connect/",
    "user-guide": SITE + "guides/image-software/",
    "CAPABILITIES": SITE + "guides/capabilities/",
    "AUTHORING": SITE + "guides/writing-tools/",
    "MANIFEST": SITE + "guides/tool-markers/",
    "HOST_FEATURES": SITE + "guides/host-features/",
    "INSTALL": SITE + "guides/tools-install/",
    "OPERATIONS": SITE + "guides/tools-operations/",
    "PUBLISHING": SITE + "guides/publishing/",
    "REPOSITORIES": SITE + "guides/repositories/",
    "LABCONSTRICTOR_INTEGRATION": SITE + "guides/template-registration/",
    "PROTOCOL": SITE + "guides/protocol/",
}
# maintainers' pages: the website does not publish them, so their old address leads to the file on GitHub
NOT_PUBLISHED = ("CONFORMANCE", "TESTING", "REGRESSION_LEDGER", "SPEC_WRONG_SCIENCE")

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Moved: {title}</title>
<link rel="canonical" href="{target}">
<meta name="robots" content="noindex">
<script>location.replace({target_js} + location.hash);</script>
<meta http-equiv="refresh" content="1; url={target}">
</head>
<body>
<p>This page has moved to <a href="{target}">{target}</a>.</p>
</body>
</html>
"""


def targets(docs: Path) -> dict[str, str]:
    """Every old page name -> where its address now leads. Stops (SystemExit) when a docs page has no destination."""
    found = {**REDIRECTS, **{name: GITHUB + name + ".md" for name in NOT_PUBLISHED}}
    missing = sorted(p.stem for p in docs.glob("*.md") if p.stem not in found)
    if missing:
        raise SystemExit(
            "docs pages without a redirect: %s; add each to REDIRECTS (its website address) or NOT_PUBLISHED"
            % ", ".join(missing)
        )
    return found


def page(name: str, target: str) -> str:
    """The redirect page for one old address: a script that keeps the #section, then (without JavaScript) a meta refresh and a link."""
    return PAGE.format(
        title=html.escape(name), target=html.escape(target, quote=True), target_js=repr(target)
    )


def build(out: Path, docs: Path) -> list[Path]:
    """Write <out>/index.html, <out>/<name>/index.html for every page and <out>/404.html. Returns the files written."""
    written = []
    for name, target in targets(docs).items():
        path = out / "index.html" if name == "index" else out / name / "index.html"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(page(name, target), encoding="utf-8")
        written.append(path)
    not_found = out / "404.html"  # an address the old site never had: the Connect an app track
    not_found.write_text(page("LabConstrictor Tools", REDIRECTS["index"]), encoding="utf-8")
    written.append(not_found)
    return written


def main(argv: list[str]) -> int:
    """Command line: build the redirect site into --out (default: site)."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default=str(ROOT / "site"))
    args = parser.parse_args(argv)
    files = build(Path(args.out), ROOT / "docs")
    print("wrote %d redirect pages to %s" % (len(files), args.out))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
