"""Oracle of GuessTheCondition_API_Example.ipynb: a script, not a widget builder (no buttons). The notebook builds a synthetic experiment (2 conditions x 3 repeats x
8 images of 64x64 noise, the second condition brighter), plays 50 % of it with a simulated player who is right 85 % of the time (seed 0), analyses and writes the report.

There are no widgets to click. Oracle (files on disk, recomputed from the csv and the fixture folders, not from the notebook's variables): 48 images, 24 guesses, the
accuracy computed from the csv equals what summary.txt reports, the PDF and the tables exist, and re-reading game_results.csv (last cell) gives the same readout.
"""

from pathlib import Path
from typing import Any

AFTER_CELL: dict[int, str] = {}
STAGES: dict[str, str] = {}
ORACLE_KERNEL = """
import json
ns = get_ipython().user_ns
json.dump({"work": str(ns["work"]), "folder": str(ns["session"].folder), "marker": ns["again"].readout.marker, "chip": ns["again"].readout.chip}, open(ns["work"].parent / "api_state.json", "w"))
"""


def oracle(ctx: Any) -> list[tuple[str, str, str]]:
    import json

    import pandas as pd

    states = sorted((ctx.home / "tmp").glob("api_state.json"))
    if not states:
        return [
            (
                "state",
                "FAIL",
                "the kernel-side state file was not written (the notebook did not get as far as the last cell, or the work folder is not under %s)"
                % (ctx.home / "tmp"),
            )
        ]
    state = json.loads(states[0].read_text(encoding="utf-8"))
    folder, work = Path(state["folder"]), Path(state["work"])
    images = list((work / "Experiment").rglob("*.tif"))
    table = pd.read_csv(folder / "game_results.csv")
    guessed = table[table["guess"].notna()]
    truth = guessed["image_file"].map(lambda f: Path(f).parts[0])
    correct = int((guessed["guess"] == truth).sum())
    summary = (folder / "analysis" / "summary.txt").read_text(encoding="utf-8")
    rows = [
        (
            "images_on_disk",
            "PASS" if len(images) == 48 else "FAIL",
            "%d tif files in the synthetic experiment (expected 48)" % len(images),
        ),
        (
            "guesses_24",
            "PASS" if len(guessed) == 24 else "FAIL",
            "%d guesses in game_results.csv (expected 24 = 50%% of 48)" % len(guessed),
        ),
        (
            "accuracy_in_report",
            (
                "PASS"
                if ("correct: %d (accuracy %.1f%%" % (correct, 100.0 * correct / len(guessed))) in summary
                else "FAIL"
            ),
            "recomputed %d/%d correct; summary.txt: %s"
            % (correct, len(guessed), summary[summary.find("Images guessed") :][:80].replace("\n", " ")),
        ),
        (
            "report_pdf",
            "PASS" if (folder / "analysis" / "analysis_results.pdf").read_bytes()[:4] == b"%PDF" else "FAIL",
            "analysis_results.pdf starts with %PDF",
        ),
        (
            "reread_readout",
            "PASS" if state["marker"] and state["chip"] else "FAIL",
            "the readout of the re-read results is %r %r" % (state["marker"], state["chip"]),
        ),
    ]
    return rows
