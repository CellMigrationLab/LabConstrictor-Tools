"""Napari host check for an installed app (LC_APP; LC_EXTRAS=playground adds the Playground's stress scenarios) (run in a venv with napari + labconstrictor-tools + napari-labconstrictor, under xvfb).
LC_HOME must hold the app's registry entry (none when the app ships no tools).

LC_EXPECT_NAPARI is required and never defaulted: `listed` (the app and every tool of it are offered) or `not_listed` (the app
is NOT offered, and when it is registered the sentence of the hosts rule is in the Tools log: LC_EXPECT_SENTENCE). The value
comes from tests/release_sandbox/expected_hosts.json (docs/PROTOCOL.md, "App hosts")."""

import json
import os
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING, NoReturn

EXPECT = os.environ.get("LC_EXPECT_NAPARI", "")
SENTENCE = os.environ.get("LC_EXPECT_SENTENCE", "")
if EXPECT not in ("listed", "not_listed"):
    sys.exit("LC_EXPECT_NAPARI must be 'listed' or 'not_listed' (from expected_hosts.json), got %r" % EXPECT)

import napari
import numpy as np
from qtpy.QtWidgets import QApplication

if TYPE_CHECKING:
    from typing import Any

APP = os.environ["LC_APP"]
EXTRAS = os.environ.get("LC_EXTRAS", "") == "playground"
bad = []


def rec(cid: str, ok: bool, detail: object = "") -> None:
    print(
        "CHECK %s %s %s" % (cid, "PASS" if ok else "FAIL", str(detail).replace("\n", " | ")[:500]), flush=True
    )
    if not ok:
        bad.append(cid)


v = napari.Viewer(show=True)
qa = QApplication.instance()
_, w = v.window.add_plugin_dock_widget("napari-labconstrictor", "LabConstrictor tools")


def pump(sec: float = 0.3) -> None:
    end = time.time() + sec
    while time.time() < end:
        qa.processEvents()
        time.sleep(0.02)


def pick(app: str, label: str) -> None:
    w.app_box.value = app
    pump(0.2)
    w.tool_box.value = label
    pump(0.4)


def wait(timeout: float = 180) -> "Any":
    end = time.time() + timeout
    while (w.last_task is None or w.task is not w.last_task) and time.time() < end:
        qa.processEvents()
        time.sleep(0.05)
    pump(1.0)
    return w.last_task


def run() -> "Any":
    w.last_task = None
    w.gui()
    return wait()


def finish() -> NoReturn:
    print("NAPARI SUMMARY failed=%s" % bad, flush=True)
    v.close()
    pump(3.0)
    sys.exit(1 if bad else 0)


def log_text() -> str:
    log = Path(os.environ["LC_HOME"]) / "logs" / "labconstrictor.log"
    return log.read_text(encoding="utf-8", errors="replace") if log.exists() else ""


pump(1.0)
apps = list(w.app_box.choices)
if EXPECT == "not_listed":
    rec("napari_does_not_list_the_app", APP not in apps, "apps=%s" % apps)
    if (Path(os.environ["LC_HOME"]) / "apps" / (APP + ".json")).exists():
        rec(
            "napari_logs_why_it_skipped_the_app",
            bool(SENTENCE) and SENTENCE in log_text(),
            "sentence=%r" % SENTENCE,
        )
    else:
        print("NOTE napari_no_registry_entry: the app ships no tools, there is nothing to skip", flush=True)
    finish()
rec("napari_lists_the_app", APP in apps, "apps=%s" % apps)
w.app_box.value = APP
pump(0.5)
labels = list(w.tool_box.choices)
from pathlib import Path as _P

_schema = json.loads(
    (_P(os.environ["LC_HOME"]) / "apps" / (APP + ".schema.json")).read_text(encoding="utf-8")
)
rec(
    "napari_lists_every_tool_of_the_app",
    len(labels) == len(_schema["tools"]) and len(labels) > 0,
    "widget=%d schema=%d %s" % (len(labels), len(_schema["tools"]), labels),
)
print("STATUS after rescan:", w.status.text(), flush=True)

if EXTRAS:
    # a normal run: Look inside a file with the file source (or a table tool)
    pick(APP, "Stress: many points")
    w.gui["count"].value = 2000
    t = run()
    rec(
        "napari_run_many_points",
        t is not None and t.status == "COMPLETE",
        "%s | %s" % (getattr(t, "status", None), w.status.text()),
    )

    # cancel of a polite tool
    pick(APP, "Stress: slow run with progress")
    w.gui["seconds"].value = 30
    w.last_task = None
    w.gui()
    pump(3.0)
    w.cancel()
    t = wait(60)
    rec(
        "napari_cancel_polite",
        t is not None and t.status == "CANCELED" and w.status.text().startswith("cancelled"),
        "%s | %s" % (getattr(t, "status", None), w.status.text()),
    )

    # cancel of a tool that ignores Cancel: the worker is stopped, still 'cancelled'
    pick(APP, "Stress: a tool that ignores Cancel")
    w.gui["seconds"].value = 60
    w.last_task = None
    w.gui()
    pump(3.0)
    w.cancel()
    t = wait(90)
    rec(
        "napari_crash_after_cancel_is_cancelled",
        t is not None and t.status in ("CANCELED", "CRASHED") and w.status.text().startswith("cancelled"),
        "%s | %s" % (getattr(t, "status", None), w.status.text()),
    )

    # a crash without cancel
    pick(APP, "Stress: crash the worker")
    t = run()
    rec(
        "napari_crash_reported",
        t is not None and t.status == "CRASHED" and w.status.text().startswith("✖"),
        "%s | %s" % (getattr(t, "status", None), w.status.text()),
    )

    # the source changed size while the tool ran
    pick(APP, "Feature tour")
    big = (np.random.default_rng(0).random((1500, 1500)) * 1000).astype(np.uint16)
    layer = v.add_image(big, name="resizeme")
    pump(0.5)
    w.gui["image"].value = layer
    pump(0.3)
    w.last_task = None
    w.gui()
    pump(0.1)
    layer.data = np.zeros((10, 10), dtype=np.uint16)  # a different size, right after the click
    end = time.time() + 240
    while (w.last_task is None or w.task is not w.last_task) and time.time() < end:
        qa.processEvents()
        time.sleep(0.5)
        (
            print("  resize run status:", w.status.text()[:120], flush=True)
            if int(time.time()) % 15 == 0
            else None
        )
    pump(1.0)
    t = w.last_task
    txt = w.status.text()
    rec(
        "napari_source_changed_size",
        "changed size while the tool ran" in txt,
        "%s | %s" % (getattr(t, "status", None), txt),
    )


finish()
