"""alpha.4 N-1 check of the Napari host: with a form that has a radio shown (VLab4Mic simulate_sample), insert and remove layers many times and count the stray
top-level visible QRadioButton windows (must be 0). Repeated for every tool that has a radio.

    LC_HOME=<registry> LC_APP=VLab4Mic LC_OUT=<dir> xvfb-run -a python napari_alpha4_radio_check.py

Rows (CHECK id PASS|FAIL detail) go to stdout and to <out>/matrix_napari_alpha4_<app>.json (schema of tests/audit/matrix.py). Exit code 0 after the last row is written.
"""

import gc
import json
import os
import time
from pathlib import Path
from typing import Any

import napari
import numpy as np
from qtpy.QtWidgets import QApplication, QRadioButton

APP = os.environ["LC_APP"]
OUT = Path(os.environ["LC_OUT"])
rows: list[dict[str, Any]] = []


def add(row_id: str, status: str, detail: str) -> None:
    print("CHECK", row_id, status, detail, flush=True)
    rows.append(
        {
            "id": row_id,
            "family": "alpha4",
            "host": "napari",
            "app": APP,
            "tool": "",
            "control": "",
            "status": status,
            "detail": detail,
            "seconds": 0,
            "screenshot": None,
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
    )
    document = {
        "host": "napari",
        "app": APP,
        "family": "alpha4",
        "host_version": "v0.1.0-alpha.4",
        "started": "",
        "finished": None,
        "expected": 0,
        "rows": rows,
    }
    (OUT / ("matrix_napari_alpha4_%s.json" % APP)).write_text(
        json.dumps(document, indent=1), encoding="utf-8"
    )


def pump(seconds: float = 0.3) -> None:
    end = time.time() + seconds
    while time.time() < end:
        QApplication.instance().processEvents()
        time.sleep(0.02)


def stray() -> list[Any]:
    return [t for t in QApplication.topLevelWidgets() if t.isVisible() and isinstance(t, QRadioButton)]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    viewer = napari.Viewer(show=True)
    _, widget = viewer.window.add_plugin_dock_widget("napari-labconstrictor", "LabConstrictor tools")
    pump(1.5)
    widget.app_box.value = APP
    pump()
    base = len(stray())
    add(
        "a4_n1_baseline",
        "PASS" if base == 0 else "FAIL",
        "%d stray top-level radio windows before any layer event" % base,
    )

    def cycle(count: int, tag: str) -> None:
        for k in range(count):
            viewer.add_image(np.zeros((16, 16), np.uint8), name="%s%d" % (tag, k))
            pump(0.15)
        viewer.layers.clear()
        pump(0.3)

    def has_radio() -> bool:
        return any(type(x).__name__ == "RadioButtons" for x in widget.gui)

    for label in list(widget.tool_box.choices):
        widget.tool_box.value = label
        pump(0.4)
        radio = has_radio()
        if not radio:
            continue
        counts = []
        for count in (1, 3, 3, 3, 6, 6, 10):
            cycle(count, "p")
            counts.append(len(stray()))
        for _ in range(20):  # insert and remove one image at a time, many times
            viewer.add_image(np.zeros((8, 8), np.uint8), name="q")
            pump(0.08)
            viewer.layers.pop(0)
            pump(0.08)
        counts.append(len(stray()))
        gc.collect()
        pump(0.5)
        counts.append(len(stray()))
        add(
            "a4_n1_no_stray_radios_%s" % label.replace(" ", "_")[:40],
            "PASS" if max(counts) == 0 else "FAIL",
            "form has radio=%s; strays after cycles of 1/3/3/3/6/6/10 layers, 20 single insert-removes, gc: %s"
            % (radio, counts),
        )
    add("a4_n1_no_stray_end", "PASS" if len(stray()) == 0 else "FAIL", "%d stray at end" % len(stray()))
    os._exit(0)  # a Qt event loop of napari does not return cleanly under Xvfb; every row is already on disk


if __name__ == "__main__":
    main()
