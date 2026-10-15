"""Static coverage check of the click scripts, run with an app interpreter (numpy, pandas and nbclient are needed):

    <prefix>/bin/python check_scripts.py SRC_ROOT [APP ...]

For every notebook of every app checkout under SRC_ROOT (the notebooks construct.yaml ships) it requires a script scripts/<app>/<notebook>.py that imports, whose stages exist, whose
cell indexes are code cells of the notebook at the checked-out tag, whose cell edits find their target text, whose inputs() runs and is JSON-serialisable, and that has an oracle or says why it has none.
Prints one line per problem and `scripts ok: N notebooks` when there is none (exit 0), else exit 1. Needs no installed app."""

import importlib.util
import json
import sys
import tempfile
from pathlib import Path
from types import ModuleType

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "scripts"))

from nb_common import discover, read_cells, script_path  # noqa: E402
from nb_kernel_run import Ctx  # noqa: E402


def load(app: str, notebook: str) -> ModuleType | None:
    path = script_path(HERE / "scripts", app, notebook)
    if not path.is_file():
        return None
    spec = importlib.util.spec_from_file_location("check_%s_%s" % (app.replace("-", "_"), notebook), path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def problems_of(app: str, src: Path, name: str, relative: str, work: Path) -> list[str]:
    script = load(app, name)
    if script is None:
        return ["%s/%s: no script scripts/%s/%s.py" % (app, name, app, name)]
    cells = read_cells(src / relative)
    code = {i for i, (kind, source) in enumerate(cells) if kind == "code" and source.strip()}
    found: list[str] = []
    stages = getattr(script, "STAGES", {})
    for index, stage in getattr(script, "AFTER_CELL", {}).items():
        if index not in code:
            found.append("AFTER_CELL index %d is not a code cell" % index)
        if stage not in stages:
            found.append("stage %r of AFTER_CELL is not in STAGES" % stage)
    for index in getattr(script, "HUMAN_CELLS", {}):
        if index not in code:
            found.append("HUMAN_CELLS index %d is not a code cell" % index)
    in_kernel = any('"oracle_' in code or "'oracle_" in code for code in stages.values())  # a stage that prints oracle_* assertions is an oracle
    if not hasattr(script, "oracle") and not getattr(script, "NO_ORACLE", "") and not getattr(script, "ORACLE_KERNEL", "") and not in_kernel:
        found.append("neither oracle() nor NO_ORACLE: the notebook would have no outcome check and no stated reason")
    if getattr(script, "NO_ORACLE", "") is None:
        found.append("NO_ORACLE is None")
    scratch = work / app / name
    scratch.mkdir(parents=True, exist_ok=True)
    ctx = Ctx(app, name, Path("/nonexistent-prefix"), src, "tag", scratch, "lc_home", scratch, scratch, scratch)
    if hasattr(script, "inputs"):
        try:
            json.dumps(script.inputs(ctx), default=str)
        except Exception as problem:  # any failure of the script's own data generation is a finding
            found.append("inputs() raised %s: %s" % (type(problem).__name__, problem))
    if hasattr(script, "edit_cells"):
        try:
            for index, pairs in script.edit_cells(ctx).items():
                for old, _new in pairs:
                    if index not in code or old not in cells[index][1]:
                        found.append("edit of cell %d: %r not found in the notebook at the tag" % (index, old[:50]))
        except Exception as problem:
            found.append("edit_cells() raised %s: %s" % (type(problem).__name__, problem))
    return ["%s/%s: %s" % (app, name, text) for text in found]


def main() -> int:
    root = Path(sys.argv[1])
    apps = sys.argv[2:] or sorted(p.name for p in root.iterdir() if (p / "construct.yaml").is_file())
    work = Path(tempfile.mkdtemp(prefix="nb_check_scripts_"))
    problems: list[str] = []
    count = 0
    for app in apps:
        for notebook in discover(root / app):
            count += 1
            problems += problems_of(app, root / app, notebook.name, notebook.src_rel, work)
    for line in problems:
        print("PROBLEM", line)
    if not problems:
        print("scripts ok: %d notebooks of %d apps" % (count, len(apps)))
    import shutil

    shutil.rmtree(work, ignore_errors=True)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
