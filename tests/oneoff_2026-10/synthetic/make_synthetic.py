#!/usr/bin/env python3
"""Generate the synthetic datasets of every LabConstrictor app (deterministic: fixed seeds, no network, numpy/scipy/pandas/tifffile only).

    python make_synthetic.py --out /home/user/synthetic [--app NAME ...]

Writes `<out>/<AppName>/` for each app: `cases.json` (the format of the app's own lc_tests/cases.json, usable through LC_APP_TESTS by the sandbox
`cases` check and the host UI-audit drivers), `fixtures/` (the files; `fixtures/ome/` holds OME-TIFF copies of calibrated images), `truth/`,
`ground_truth.json`, `README.md` and `check_ground_truth.py`. An existing app folder is deleted first, so a run always starts clean.

This driver is the only file that knows all apps; each `<App>/make_<app>.py` is self-contained (it needs only `common.py` and
`check_ground_truth.py`) and can be lifted into the app's own repository and run alone: `python make_<app>.py OUT_DIR`.
"""

from __future__ import annotations

import argparse
import importlib.util
import shutil
import sys
from pathlib import Path
from types import ModuleType

HERE = Path(__file__).resolve().parent
APPS = {
    "NucleiSky": ("NucleiSky", "make_nucleisky.py"),
    "LabConstrictor-Playground": ("LabConstrictor-Playground", "make_playground.py"),
    "LabConstrictor-VLab4Mic": ("LabConstrictor-VLab4Mic", "make_vlab4mic.py"),
    "GuessTheCondition": ("GuessTheCondition", "make_guessthecondition.py"),
    "CellTracksColab": ("CellTracksColab", "make_celltracks.py"),
}


def load_module(folder: str, script: str) -> ModuleType:
    path = HERE / folder / script
    spec = importlib.util.spec_from_file_location("make_" + folder.replace("-", "_"), path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--app", action="append", choices=sorted(APPS), help="only this app (repeatable); default all"
    )
    args = parser.parse_args(argv)
    for app in args.app or list(APPS):
        folder, script = APPS[app]
        target = args.out / app
        if target.exists():
            shutil.rmtree(target)
        target.mkdir(parents=True)
        suite = load_module(folder, script).build(target)
        suite.write(HERE / "check_ground_truth.py")
        size = sum(f.stat().st_size for f in target.rglob("*") if f.is_file()) / 1e6
        print(
            "%-28s %3d datasets %3d cases %7.1f MB  %s"
            % (app, len(suite.datasets), len(suite.cases), size, target)
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
