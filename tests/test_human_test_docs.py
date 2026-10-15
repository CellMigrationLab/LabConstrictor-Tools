"""The human-test pages stay consistent: row ids of the matrix are unique, differ from the protocol's check ids, match the results CSV, the result words are one
vocabulary, every test id the matrix cites exists in the protocol or the app files, and every internal link and anchor resolves.
"""

import csv
import re
from pathlib import Path

DOCS = Path(__file__).resolve().parent.parent / "docs"
MATRIX = (DOCS / "TEST_MATRIX.md").read_text(encoding="utf-8")
ROW = re.compile(r"^\|[^|]*\| \*\*((?:WIN|MAC|LIN)-\d\d)\. ", re.M)


def slug(heading: str) -> str:
    text = re.sub(r"[`*_]", "", heading.strip().lower())
    return re.sub(r"\s", "-", re.sub(r"[^\w\s-]", "", text))


def defined_test_ids() -> set[str]:
    found: set[str] = set()
    files = [DOCS / "HUMAN_TEST_PROTOCOL.md", *sorted((DOCS / "human_tests").glob("*.md"))]
    for path in files:
        text = path.read_text(encoding="utf-8")
        found.update(
            m.group(1)
            for m in re.finditer(r"^#{2,4} ([A-Z]{1,3}[0-9]*(?:-[A-Z]?[0-9A-Z]+)?)[.:]", text, re.M)
        )
        found.update(m.group(1) for m in re.finditer(r"\*\*([A-Z]{1,3}-?[A-Z]?[0-9]+)[ .:]", text))
        found.update(m.group(1) for m in re.finditer(r"^- \[ \] \*\*([WML][0-9]+)", text, re.M))
    return found


def test_matrix_row_ids_are_unique_and_not_the_protocols() -> None:
    ids = ROW.findall(MATRIX)
    assert len(ids) == len(set(ids)) and len(ids) >= 30, ids
    protocol = (DOCS / "HUMAN_TEST_PROTOCOL.md").read_text(encoding="utf-8")
    assert not [i for i in ids if re.search(r"\*\*%s\*\*" % re.escape(i), protocol)]


def test_results_csv_has_exactly_the_matrix_rows() -> None:
    with (DOCS / "TEST_RESULTS_TEMPLATE.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert [r["row_id"] for r in rows] == ROW.findall(
        MATRIX
    ), "regenerate docs/TEST_RESULTS_TEMPLATE.csv from the matrix rows"
    assert {r["result"] for r in rows} == {"NOT TESTED"}


def test_one_result_vocabulary() -> None:
    for name in ("TESTER_START_HERE.md", "TEST_MATRIX.md", "HUMAN_TEST_PROTOCOL.md"):
        assert "NOT RUN" not in (DOCS / name).read_text(encoding="utf-8"), name
    for path in [DOCS / "HUMAN_TEST_PROTOCOL.md", *(DOCS / "human_tests").glob("*.md")]:
        for line in path.read_text(encoding="utf-8").splitlines():
            if "- [ ] PASS" in line:
                assert "- [ ] FAIL  - [ ] BLOCKED  - [ ] N/A" in line, (path.name, line)


def test_every_test_id_the_matrix_cites_exists() -> None:
    known = defined_test_ids()
    missing = set()
    rows = [line for line in MATRIX.splitlines() if line.startswith("| ")]
    for segment in re.findall(r"tests ([^|)]+)", "\n".join(rows)):
        for item in re.findall(r"\b(?:[A-Z]{2}-[A-Z]?[0-9]+|NB[0-9]|[SDEUWMLCNFQ][0-9]+)\b", segment):
            if item not in known and not item.startswith(("WIN", "MAC", "LIN")):
                missing.add(item)
    assert not missing, sorted(missing)


def test_internal_links_and_anchors_resolve() -> None:
    pages = sorted(DOCS.glob("*.md")) + sorted((DOCS / "human_tests").glob("*.md"))
    heads = {
        p.resolve(): {
            slug(m.group(2)) for m in re.finditer(r"^(#{1,6}) (.+)$", p.read_text(encoding="utf-8"), re.M)
        }
        for p in pages
    }
    problems = []
    for page in pages:
        for target, anchor in re.findall(
            r"\]\(([^)#\s]*)(?:#([^)\s]+))?\)", page.read_text(encoding="utf-8")
        ):
            if target.startswith(("http", "mailto")):
                continue
            path = (page.parent / target).resolve() if target else page.resolve()
            if not path.exists():
                problems.append("%s -> %s" % (page.name, target))
            elif anchor and path in heads and anchor not in heads[path]:
                problems.append("%s -> %s#%s" % (page.name, target, anchor))
    assert not problems, problems
