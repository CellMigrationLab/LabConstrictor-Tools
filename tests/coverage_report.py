"""Coverage of the PRODUCTION package, and the production code that only tests (or nothing) reach.

    cd tests
    python -m coverage run -m unittest discover -p "test_*.py"
    python -m coverage combine
    python coverage_report.py [--fail-under 85]

Prints, in this order:
  1. line and branch coverage per module (the settings are in pyproject.toml: only labconstrictor_tools, no tests, no examples);
  2. functions, methods and classes that nothing in the package refers to (vulture, confidence 60) but that the tests EXECUTE:
     the tests call them directly, no production code path does, so their coverage proves nothing about the product;
  3. the same names when not even a test executes them;
  4. modules that no other production module imports (entry points and the package root are expected).
Exit status 1 when the total is below --fail-under.
"""

import argparse
import ast
import io
import sys
from pathlib import Path

import coverage

ROOT = Path(__file__).resolve().parent.parent
PACKAGE = ROOT / "labconstrictor_tools"
ENTRY_MODULES = {"__init__", "__main__"}  # the package root and `python -m labconstrictor_tools`
CALLED_BY_PYTHON = ("__enter__", "__exit__", "__init__", "__repr__", "__iter__", "load_ipython_extension")
CODE_KINDS = ("function", "method", "property", "class")


def load(rcfile: Path) -> coverage.Coverage:
    cov = coverage.Coverage(config_file=str(rcfile))
    cov.load()
    return cov


def production_files(package: Path) -> list[Path]:
    return sorted(p for p in package.glob("*.py"))


def module_table(cov: coverage.Coverage, package: Path) -> tuple[str, float]:
    out = io.StringIO()
    total = cov.report(
        file=out,
        show_missing=False,
        skip_empty=True,
        include=[str(package) + "/*"],
        omit=[str(package / "examples") + "/*"],
    )
    return out.getvalue(), total


def executed_lines(cov: coverage.Coverage, path: Path) -> tuple[set[int], set[int]]:
    """(statement lines, executed statement lines) of one file."""
    _, statements, _, missing, _ = cov.analysis2(str(path))
    return set(statements), set(statements) - set(missing)


def is_executed(cov: coverage.Coverage, path: Path, first_line: int, last_line: int) -> bool:
    statements, hit = executed_lines(cov, path)
    body = {
        n for n in statements if first_line < n <= last_line
    }  # the def line itself runs when the module is imported
    return bool(body & hit)


def unreferenced_names(package: Path) -> list[tuple[str, str, Path, int, int]]:
    """(kind, name, file, first line, last line) of what nothing in the package refers to, from vulture at confidence 60."""
    import vulture

    scanner = vulture.Vulture()
    scanner.scavenge([str(package)], exclude=[str(package / "examples")])
    found = []
    for item in scanner.get_unused_code(min_confidence=60):
        if item.typ in CODE_KINDS and item.name not in CALLED_BY_PYTHON:
            found.append((item.typ, item.name, Path(item.filename), item.first_lineno, item.last_lineno))
    return sorted(found, key=lambda f: (str(f[2]), f[3]))


def modules_imported_by_nobody(package: Path) -> list[str]:
    names = {p.stem for p in production_files(package)}
    imported = set()
    for path in production_files(package):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.level >= 1:
                if node.module:
                    imported.add(node.module.split(".")[0])
                imported.update(alias.name for alias in node.names)
            elif (
                isinstance(node, ast.ImportFrom)
                and node.module
                and node.module.startswith("labconstrictor_tools.")
            ):
                imported.add(node.module.split(".")[1])
            elif (
                isinstance(node, ast.Call) and getattr(node.func, "attr", "") == "import_module" and node.args
            ):
                if isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                    imported.add(node.args[0].value.rsplit(".", 1)[-1])
        for node in ast.walk(tree):  # `from labconstrictor_tools import client` inside a function
            if isinstance(node, ast.ImportFrom) and node.module == "labconstrictor_tools":
                imported.update(alias.name for alias in node.names)
    return sorted(names - imported - ENTRY_MODULES)


def _shown(path: Path, package: Path) -> str:
    return str(path.relative_to(package.parent))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--fail-under", type=float, default=0.0, help="exit 1 below this total percentage")
    parser.add_argument(
        "--package", type=Path, default=PACKAGE, help="the package folder (default: labconstrictor_tools)"
    )
    parser.add_argument("--rcfile", type=Path, default=ROOT / "pyproject.toml", help="the coverage settings")
    args = parser.parse_args()
    cov = load(args.rcfile)
    table, total = module_table(cov, args.package.resolve())
    print("== 1. line and branch coverage of labconstrictor_tools (tests and examples excluded)")
    print(table)
    names = unreferenced_names(args.package)
    reached_by_tests = [n for n in names if is_executed(cov, n[2], n[3], n[4])]
    not_reached = [n for n in names if n not in reached_by_tests]
    print(
        "== 2. executed by the tests, referred to by no production code (the tests call them directly): %d"
        % len(reached_by_tests)
    )
    for kind, name, path, first, _ in reached_by_tests:
        print("   %s:%d  %s %s" % (_shown(path, args.package), first, kind, name))
    print("== 3. not executed by anything and referred to by no production code: %d" % len(not_reached))
    for kind, name, path, first, _ in not_reached:
        print("   %s:%d  %s %s" % (_shown(path, args.package), first, kind, name))
    lonely = modules_imported_by_nobody(args.package)
    print(
        "== 4. modules that no other production module imports (besides the entry points): %s"
        % (", ".join(lonely) or "none")
    )
    print("\nTOTAL %.2f%%" % total)
    if total < args.fail_under:
        print("coverage %.2f%% is below the floor %.2f%%" % (total, args.fail_under), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
