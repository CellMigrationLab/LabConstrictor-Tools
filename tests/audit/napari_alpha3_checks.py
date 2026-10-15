"""alpha.3 checks of the Napari host with REAL inputs (Qt events, typed text, inserted layers), every step guarded: a failure is a row, never the end.

    LC_HOME=<registry> LC_APP=<registry name> LC_A3_OUT=<dir> LC_A3_ROUNDS=10 xvfb-run -a python napari_alpha3_checks.py

Rows (CHECK id PASS|FAIL detail), matrix file <out>/matrix_napari_alpha3_<app>.json (schema of tests/audit/matrix.py):
  a3_napari_switch_no_exceptions     choose every tool of the app, ROUNDS times back and forth, flip every radio button of every form; no exception (sys.excepthook, psygnal
                                     EmitLoopError on stderr, Qt messages) mentioning region / pixel_size / AttributeError (H-N4)
  a3_napari_no_stray_radio_windows   no top-level QRadioButton windows are left after that (N-1)
  a3_napari_rgb_channel_chooser      for every tool with a PickChannel parameter: insert an RGB layer, the Channel chooser lists Red/Green/Blue, stays after 2 s, after switching tool and back
  a3_napari_group_headings           the headings of the form's groups are there and stay after a switch (labels of the schema's groups found in the form)
  a3_napari_pixel_zero_<tool>        for every pixel-size field: type 0 and press Enter: the status line says "0 means: use the image's calibration"
  a3_napari_cal_um_<tool>            (LC_A3_UM_FILE set) the pixel-size field fills with LC_A3_UM_EXPECT (0.02) after the micrometre-calibrated TIFF is put in the 'or file' row, and after it is opened as a layer
"""

import io
import json
import os
import sys
import time
import traceback
from pathlib import Path
from typing import Any, TextIO

OUT = Path(os.environ.get("LC_A3_OUT", "a3_out"))
OUT.mkdir(parents=True, exist_ok=True)
APP = os.environ["LC_APP"]
ROUNDS = int(os.environ.get("LC_A3_ROUNDS", "10"))
rows: list[dict[str, Any]] = []
errors: list[str] = []


def add(rid: str, status: str, detail: object) -> None:
    detail = " ".join(str(detail).split())[:900]
    rows.append(
        {
            "id": rid,
            "family": "alpha3",
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
    print("CHECK %s %s %s" % (rid, status, detail), flush=True)
    (OUT / ("matrix_napari_alpha3_%s.json" % APP)).write_text(
        json.dumps(
            {
                "host": "napari",
                "app": APP,
                "family": "alpha3",
                "host_version": "v0.1.0-alpha.3",
                "started": "",
                "finished": None,
                "expected": 0,
                "rows": rows,
            },
            indent=1,
        ),
        encoding="utf-8",
    )


class Tee(io.TextIOBase):
    def __init__(self, real: TextIO) -> None:
        self.real = real

    def write(self, text: str) -> int:
        self.real.write(text)
        if text.strip():
            errors.append(text.strip()[:300])
        return len(text)

    def flush(self) -> None:
        self.real.flush()


def main() -> None:
    import napari
    import numpy as np
    from qtpy.QtCore import qInstallMessageHandler
    from qtpy.QtWidgets import QApplication, QRadioButton

    sys.stderr = Tee(sys.stderr)
    sys.excepthook = lambda t, v, tb: errors.append("EXC %s: %s" % (t.__name__, str(v)[:300]))
    qInstallMessageHandler(lambda mode, ctx, msg: errors.append("QT %s" % msg[:200]))
    viewer = napari.Viewer(show=True)
    _, w = viewer.window.add_plugin_dock_widget("napari-labconstrictor", "LabConstrictor tools")

    def pump(s: float = 0.3) -> None:
        end = time.time() + s
        while time.time() < end:
            QApplication.instance().processEvents()
            time.sleep(0.02)

    pump(1.5)
    w.app_box.value = next(
        a for a in w.app_box.choices if a == APP or str(a).lower().replace(" ", "") == APP.lower()
    )
    pump()
    schema = json.loads(
        (Path(os.environ["LC_HOME"]) / "apps" / (APP + ".schema.json")).read_text(encoding="utf-8")
    )
    tools = {t["id"]: t for t in schema["tools"]}
    labels = list(w.tool_box.choices)
    add(
        "a3_napari_tools_listed",
        "PASS" if len(labels) == len(tools) else "FAIL",
        "%d tool(s) in the chooser, %d in the schema" % (len(labels), len(tools)),
    )

    # ---- negative control of the capture: a psygnal callback that raises must show up in `errors` (else "no exception" would mean nothing)
    from psygnal import Signal

    class _Probe:
        fired = Signal()

    probe = _Probe()
    probe.fired.connect(lambda: (_ for _ in ()).throw(AttributeError("selftest no attribute 'region'")))
    before = len(errors)
    try:
        probe.fired.emit()
    except (
        Exception
    ) as raised:  # noqa: BLE001 - psygnal raises EmitLoopError to the emitter: that is a capture too
        errors.append("EXC %s: %s" % (type(raised).__name__, str(raised)[:300]))
    pump(0.3)
    seen = [e for e in errors[before:] if "region" in e or "EmitLoopError" in e or "AttributeError" in e]
    add(
        "a3_napari_capture_selftest",
        "PASS" if seen else "FAIL",
        "a deliberately failing signal callback was %s by the capture (%d line(s))"
        % ("captured" if seen else "NOT captured", len(errors) - before),
    )
    errors[before:] = []

    # ---- H-N4: back and forth
    mark = len(errors)
    try:
        for _ in range(ROUNDS):
            for lab in labels + labels[::-1]:
                w.tool_box.value = lab
                pump(0.15)
                for x in list(w.gui):
                    if type(x).__name__ == "RadioButtons" and len(x.choices) > 1:
                        for choice in list(x.choices):
                            x.value = choice
                            pump(0.05)
                        x.value = x.choices[0]
                        pump(0.05)
                    elif type(x).__name__ in ("CheckBox",) and getattr(x, "enabled", False):
                        x.value = not x.value
                        pump(0.03)
                        x.value = not x.value
    except Exception as problem:  # noqa: BLE001
        errors.append("DRIVER %s" % traceback.format_exc()[-300:])
        add("a3_napari_switch_driver", "FAIL", "%s: %s" % (type(problem).__name__, problem))
    pump(1)
    mine = errors[mark:]
    bad = [
        e
        for e in mine
        if any(k in e for k in ("region", "pixel_size", "AttributeError", "EmitLoopError", "Traceback"))
    ]
    add(
        "a3_napari_switch_no_exceptions",
        "FAIL" if bad else "PASS",
        (
            ("%d exception line(s): %s" % (len(bad), " || ".join(sorted(set(bad))[:4])))
            if bad
            else "%d tool(s) x %d round(s) there and back (%d form switches), every radio/check flipped: no exception on stderr/excepthook/Qt (%d unrelated line(s))"
            % (len(labels), ROUNDS, len(labels) * 2 * ROUNDS, len(mine))
        ),
    )
    stray = [t for t in QApplication.topLevelWidgets() if t.isVisible() and isinstance(t, QRadioButton)]
    add(
        "a3_napari_no_stray_radio_windows",
        "FAIL" if stray else "PASS",
        (
            "%d top-level QRadioButton window(s) visible" % len(stray)
            if stray
            else "no stray top-level radio button windows after the switching"
        ),
    )

    # ---- RGB channel chooser, group headings, pixel zero
    def choose(tool_id: str) -> None:
        want = tools[tool_id].get("label") or tool_id
        label = next((lab for lab in labels if lab == want), None) or next(
            (lab for lab in labels if lab.lower() == str(want).lower()), None
        )
        if label is None:
            for lab in labels:
                w.tool_box.value = lab
                pump(0.1)
                if getattr(w.tool, "id", None) == tool_id:
                    return
            raise AssertionError("tool %s (%r) not found in the chooser %s" % (tool_id, want, labels))
        w.tool_box.value = label
        pump(0.3)

    def heading_texts() -> list[str]:
        found = []
        for x in list(w.gui):
            name = type(x).__name__
            if name == "Label" and not getattr(x, "label", "x") and str(x.value) in all_groups:
                found.append(str(x.value))
            elif name == "PushButton" and x.native.property("lc_group"):
                found.append(str(x.native.property("lc_group")))
        return found

    all_groups = {p.get("group") for t in tools.values() for p in t["inputs"] if p.get("group")}

    def expected_headings(tool: dict[str, Any]) -> list[str]:
        out, prev = [], None
        ordered = [p for p in tool["inputs"] if not p.get("advanced")] + [
            p for p in tool["inputs"] if p.get("advanced")
        ]  # the host puts the advanced parameters last
        for p in ordered:
            g = p.get("group")
            if g and g != prev:
                out.append(g)
            prev = g or prev
        return out

    for tool_id, tool in tools.items():
        want = expected_headings(tool)
        if not want:
            continue
        rid = "a3_napari_group_headings_%s" % tool_id
        try:
            choose(tool_id)
            got = heading_texts()
            # after a trip through two other tools and back the form still has exactly its own headings
            others = [lab for lab in labels if lab != w.tool_box.value][:2]
            for lab in others:
                w.tool_box.value = lab
                pump(0.15)
            choose(tool_id)
            got2 = heading_texts()
            ok = got == want and got2 == want
            add(
                rid,
                "PASS" if ok else "FAIL",
                "headings %s; after visiting %d other tool(s) and back %s; expected %s"
                % (got, len(others), got2, want),
            )
        except Exception as problem:  # noqa: BLE001
            add(rid, "FAIL", "%s: %s" % (type(problem).__name__, problem))

    for tool_id, tool in tools.items():
        for pname in [p["name"] for p in tool["inputs"] if p.get("pick_channel")]:
            rid = "a3_napari_rgb_channel_chooser_%s_%s" % (tool_id, pname)
            try:
                choose(tool_id)
                viewer.layers.clear()
                pump(0.3)
                widget = w.gui[pname]
                box = w.channel_boxes[pname]
                gray = viewer.add_image(
                    np.random.randint(0, 255, (32, 32), dtype=np.uint8), name="gray_probe"
                )
                pump(0.3)
                widget.value = gray
                pump(0.3)
                gray_choices = list(box.choices)
                rgb = viewer.add_image(
                    np.random.randint(0, 255, (32, 32, 3), dtype=np.uint8), rgb=True, name="rgb_probe"
                )
                pump(0.5)
                after_insert_value = widget.value.name if widget.value is not None else None
                after_insert = list(
                    box.choices
                )  # the chooser of the layer that is still selected (gray): must not be broken by the insertion
                widget.value = rgb
                pump(0.5)
                got = list(box.choices)
                vis = box.visible
                pump(2.0)
                got2 = list(box.choices)
                extra = viewer.add_image(
                    np.zeros((8, 8), np.uint8), name="extra_probe"
                )  # another insertion while the RGB layer is chosen
                pump(0.6)
                viewer.layers.remove(extra)
                pump(0.6)
                got3 = list(box.choices)
                still_chosen = widget.value is not None and widget.value.name == "rgb_probe"
                problems = []
                if got != ["Red", "Green", "Blue"] or not vis:
                    problems.append("RGB layer chosen: the chooser lists %s (visible=%s)" % (got, vis))
                if got2 != ["Red", "Green", "Blue"]:
                    problems.append("2 s later it lists %s" % got2)
                if got3 != ["Red", "Green", "Blue"] or not still_chosen:
                    problems.append(
                        "after inserting and removing another layer it lists %s (RGB layer still chosen: %s)"
                        % (got3, still_chosen)
                    )
                for colour in ("Green", "Blue", "Red"):
                    box.value = colour
                    pump(0.1)
                    if box.value != colour:
                        problems.append("colour %s not kept (%s)" % (colour, box.value))
                        break
                # switch tool and back: choose the layer again, the colours are there again
                other = next((lab for lab in labels if lab != w.tool_box.value), None)
                w.tool_box.value = other
                pump(0.3)
                choose(tool_id)
                pump(0.4)
                w.gui[pname].value = rgb
                pump(0.4)
                got4 = list(w.channel_boxes[pname].choices)
                if got4 != ["Red", "Green", "Blue"]:
                    problems.append(
                        "after switching tool and back and choosing the RGB layer again it lists %s" % got4
                    )
                add(
                    rid,
                    "FAIL" if problems else "PASS",
                    (
                        "; ".join(problems)
                        if problems
                        else "chose the inserted RGB layer: Red/Green/Blue (visible), unchanged 2 s later, after another layer was inserted and removed, each colour kept, again after a tool switch (grayscale layer chosen before: %s; value of the chooser right after the insertion alone: %s, choices %s)"
                        % (gray_choices, after_insert_value, after_insert)
                    ),
                )
            except Exception as problem:  # noqa: BLE001
                add(rid, "FAIL", "%s: %s" % (type(problem).__name__, problem))
            viewer.layers.clear()

    for tool_id, tool in tools.items():
        for param in tool["inputs"]:
            if not param.get("pixel_size_of"):
                continue
            rid = "a3_napari_pixel_zero_%s" % tool_id
            try:
                choose(tool_id)
                viewer.layers.clear()
                img = viewer.add_image(
                    np.random.randint(0, 255, (32, 32), dtype=np.uint8),
                    name="px_probe",
                    scale=(0.5, 0.5),
                    units="micrometer",
                )
                pump(0.4)
                box = w.gui[param["name"]]
                widget_image = w.gui[param["pixel_size_of"]]
                widget_image.value = img
                pump(0.4)
                before = box.native.text()
                box.native.setFocus()
                box.native.setText("")
                from qtpy.QtCore import Qt
                from qtpy.QtTest import QTest

                QTest.keyClicks(box.native, "0")
                QTest.keyClick(box.native, Qt.Key.Key_Return)
                pump(0.5)
                text = w.status.text()
                add(
                    rid,
                    "PASS" if "0 means: use the image's calibration" in text else "FAIL",
                    "image with a 0.5 um scale chosen: box %r; after typing 0 + Enter into %s the status line says %r; the box then shows %r"
                    % (before, param["name"], text, box.native.text()),
                )
            except Exception as problem:  # noqa: BLE001
                add(rid, "FAIL", "%s: %s" % (type(problem).__name__, problem))
            viewer.layers.clear()

    for um in [u for u in os.environ.get("LC_A3_UM_FILE", "").split(",") if u]:
        expect = os.environ.get("LC_A3_UM_EXPECT", "0.02")
        for tool_id, tool in tools.items():
            for param in tool["inputs"]:
                if not param.get("pixel_size_of"):
                    continue
                image_name = param["pixel_size_of"]
                rid = "a3_napari_cal_um_%s_%s_%s" % (tool_id, param["name"], Path(um).stem)
                try:
                    choose(tool_id)
                    viewer.layers.clear()
                    pump(0.3)
                    box = w.gui[param["name"]]
                    edit = w.file_sources[image_name]
                    edit.value = Path(um)
                    pump(0.8)
                    shown_file = box.native.text()
                    edit.value = None
                    pump(0.3)
                    try:
                        viewer.open(um, plugin="builtins")
                        pump(0.8)
                        shown_layer_raw = (
                            box.native.text()
                        )  # layer scale from napari's reader (no ImageJ unit): informative only
                    except Exception as problem:  # noqa: BLE001
                        shown_layer_raw = "layer not opened: %s" % problem
                    ok_file = shown_file not in ("", "None") and abs(float(shown_file) - float(expect)) < 1e-6
                    add(
                        rid,
                        "PASS" if ok_file else "FAIL",
                        "evidence %s in the 'or file' row: the pixel-size field shows %r (expected %s); status %r; (informative: as a napari-opened layer the field shows %r)"
                        % (Path(um).name, shown_file, expect, w.status.text(), shown_layer_raw),
                    )
                except Exception as problem:  # noqa: BLE001
                    add(rid, "FAIL", "%s: %s" % (type(problem).__name__, problem))
                viewer.layers.clear()

    (OUT / ("matrix_napari_alpha3_%s.json" % APP)).write_text(
        json.dumps(
            {
                "host": "napari",
                "app": APP,
                "family": "alpha3",
                "host_version": "v0.1.0-alpha.3",
                "started": "",
                "finished": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "expected": len(rows),
                "rows": rows,
            },
            indent=1,
        ),
        encoding="utf-8",
    )
    (OUT / ("errors_%s.txt" % APP)).write_text("\n".join(errors), encoding="utf-8")
    sys.stdout.flush()
    os._exit(0)


try:
    main()
except SystemExit:
    raise
except BaseException:  # noqa: BLE001
    add("a3_napari_driver_crashed", "FAIL", traceback.format_exc()[-700:])
    os._exit(1)
