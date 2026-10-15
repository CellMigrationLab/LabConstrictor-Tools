"""The static checks of one notebook, run in the app's interpreter: `packaged` (cell types and sources equal to the file at the release tag) and `valid`
(nbformat validation, and the kernelspec the notebook resolves to is the app's own interpreter)."""

import os
from pathlib import Path
from typing import Any

import nbformat
from jupyter_client.kernelspec import KernelSpecManager, NoSuchKernel
from nb_common import first_difference, read_cells


def packaged(emit: Any, installed: Path, released: Path) -> None:
    if not released.is_file():
        emit.row("packaged", "FAIL", "the release file is missing in the source checkout: %s" % released)
        return
    if not installed.is_file():
        emit.row("packaged", "FAIL", "not installed: %s" % installed)
        return
    difference = first_difference(read_cells(installed), read_cells(released))
    count = len(read_cells(released))
    emit.row(
        "packaged",
        "FAIL" if difference else "PASS",
        difference
        or "%d cells, types and sources equal to the release (installer rewrites outputs and metadata only)"
        % count,
    )


def valid(emit: Any, installed: Path, prefix: Path) -> str | None:
    """Emits the `valid` row and returns the kernelspec name of the notebook (None when it could not be read)."""
    if not installed.is_file():
        emit.row("valid", "FAIL", "not installed: %s" % installed)
        return None
    document = nbformat.read(str(installed), as_version=4)
    try:
        nbformat.validate(document)
    except nbformat.ValidationError as problem:
        emit.row("valid", "FAIL", "nbformat validation failed: %s" % str(problem).splitlines()[0][:300])
        return None
    name = document.metadata.get("kernelspec", {}).get("name", "python3")
    try:
        spec = KernelSpecManager().get_kernel_spec(name)
    except NoSuchKernel:
        emit.row(
            "valid",
            "FAIL",
            "nbformat ok, but kernelspec %r does not resolve (JUPYTER_DATA_DIR=%s)"
            % (name, os.environ.get("JUPYTER_DATA_DIR")),
        )
        return None
    argv0 = spec.argv[0]
    expected = prefix / "bin" / "python"
    same = os.path.realpath(argv0) == os.path.realpath(expected)
    detail = "nbformat %d.%d valid; kernelspec %r resolves to %s (spec dir %s); app interpreter %s" % (
        document.nbformat,
        document.nbformat_minor,
        name,
        argv0,
        spec.resource_dir,
        expected,
    )
    emit.row(
        "valid",
        "PASS" if same else "FAIL",
        detail if same else "kernel resolves to a different interpreter: " + detail,
    )
    return name
