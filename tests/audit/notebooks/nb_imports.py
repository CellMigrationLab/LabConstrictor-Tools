"""The `imports` check: collect every import of the code cells with `ast` (IPython magics and `!` lines are transformed first, so `%pip` / `!pip` cannot crash it),
then resolve each in the app's own interpreter in a probe subprocess. Imports in try/except ImportError are optional, imports behind a Colab test are Colab-only:
a failure of either is a NOTE, any other failure is a FAIL."""

import ast
import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

PROBE = Path(__file__).with_name("imports_probe.py")
FUTURE = "__future__"


@dataclass
class ImportRef:
    module: str
    names: list[str] = field(default_factory=list)
    cell: int = 0
    line: int = 0
    kind: str = "required"  # required | optional | colab


def _guards(node: ast.AST, parents: dict[ast.AST, ast.AST]) -> str:
    """'optional' inside a try whose handler catches ImportError (or everything), 'colab' inside an `if` that tests for Colab, else 'required'."""
    child, parent = node, parents.get(node)
    while parent is not None:
        if isinstance(parent, ast.Try) and child in parent.body:
            for handler in parent.handlers:
                names = [ast.unparse(handler.type)] if handler.type is not None else ["BaseException"]
                if any(
                    n in ("ImportError", "ModuleNotFoundError", "Exception", "BaseException")
                    or "ImportError" in n
                    for n in names
                ):
                    return "optional"
        if isinstance(parent, ast.If) and "colab" in ast.unparse(parent.test).lower():
            return "colab" if child in parent.body else "required"
        child, parent = parent, parents.get(parent)
    return "required"


def extract(cells: list[tuple[str, str]]) -> tuple[list[ImportRef], list[str]]:
    """(imports, problems): `problems` names every code cell that could not be parsed (a syntax error in a shipped notebook is a finding)."""
    from IPython.core.inputtransformer2 import TransformerManager

    transformer = TransformerManager()
    refs: list[ImportRef] = []
    problems: list[str] = []
    for index, (cell_type, source) in enumerate(cells):
        if cell_type != "code" or not source.strip():
            continue
        try:
            tree = ast.parse(transformer.transform_cell(source))
        except SyntaxError as problem:
            problems.append("cell %d: SyntaxError %s (line %s)" % (index, problem.msg, problem.lineno))
            continue
        parents = {child: parent for parent in ast.walk(tree) for child in ast.iter_child_nodes(parent)}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                refs += [
                    ImportRef(a.name, [], index, node.lineno, _guards(node, parents)) for a in node.names
                ]
            elif (
                isinstance(node, ast.ImportFrom) and node.level == 0 and node.module and node.module != FUTURE
            ):
                refs.append(
                    ImportRef(
                        node.module,
                        [a.name for a in node.names if a.name != "*"],
                        index,
                        node.lineno,
                        _guards(node, parents),
                    )
                )
    return refs, problems


def probe(
    refs: list[ImportRef], python: str, env: dict[str, str], cwd: Path, timeout: int
) -> list[dict[str, str]]:
    """Resolve the imports with `python` (the app's interpreter): one result per distinct (module, names): {'module', 'status': ok|fail, 'error'}.
    A hung or crashed probe returns a single 'fail' result naming it."""
    wanted = sorted({(r.module, tuple(r.names)) for r in refs})
    payload = json.dumps([{"module": m, "names": list(n)} for m, n in wanted])
    try:
        done = subprocess.run(
            [python, str(PROBE)],
            input=payload,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            cwd=cwd,
            errors="replace",
        )
    except subprocess.TimeoutExpired as late:
        partial = (
            late.stdout.decode("utf-8", "replace") if isinstance(late.stdout, bytes) else (late.stdout or "")
        )
        return _parse(partial) + [
            {"module": "(probe)", "status": "fail", "error": "import probe timed out after %d s" % timeout}
        ]
    results = _parse(done.stdout)
    if done.returncode != 0 or len(results) != len(wanted):
        results.append(
            {
                "module": "(probe)",
                "status": "fail",
                "error": "probe exit %d after %d of %d imports: %s"
                % (done.returncode, len(results), len(wanted), done.stderr[-300:]),
            }
        )
    return results


def _parse(text: str) -> list[dict[str, str]]:
    results = []
    for line in text.splitlines():
        try:
            results.append(json.loads(line))
        except json.JSONDecodeError:
            print("imports probe: ignoring non-JSON line %r" % line[:120], file=sys.stderr)
    return results
