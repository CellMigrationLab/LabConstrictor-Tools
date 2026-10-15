"""Click script and oracle of GuessTheCondition.ipynb (the interactive game). Fixtures: lc_tests/make_fixtures.py of the app checkout, run on a COPY: 2 conditions
(Control dark, Mutant bright) x 3 repeats x 2 images = 12 images, 25 % to guess = 3.

Workflow by clicks: fill the form and press "Prepare the game"; press "Start / continue"; submit with no condition chosen (must be refused); answer image 1 correctly,
answer image 2 WRONG then "Undo last guess" and answer it correctly, answer image 3 WRONG; the analysis cell then runs. The simulated player decides from the pixels of the
image on screen (Mutant is the bright condition), not from the file name.

Oracle (files on disk, recomputed from the fixture folder names, not from the widgets): game_results.csv holds 3 guesses, the undone guess is gone, the number correct is
2 (of 3, 66.7 %) both recomputed from the csv and as the report says, and the PDF report and tables exist."""

from pathlib import Path
from typing import Any

AFTER_CELL = {5: "prepare", 7: "play"}
STAGES = {
    "prepare": '''
I = lcnb.INPUTS
lcnb.set_value(lcnb.find(kind="Text", description="Your name"), "Ana")
lcnb.set_value(lcnb.find(kind="Text", description="Experiment folder"), I["experiment"])
lcnb.set_value(lcnb.find(kind="Text", description="Results folder"), I["results"])
lcnb.set_value(lcnb.find(kind="IntSlider", description="% to guess"), 25)
lcnb.set_value(lcnb.find(kind="Checkbox", description="Start again"), True)
lcnb.set_value(lcnb.find(kind="Checkbox", description="Fix the order"), True)
lcnb.set_value(lcnb.find(kind="IntText", description="Seed"), 7)
out = lcnb.click(lcnb.find(kind="Button", description="Prepare the game"))
text = out["stdout"]
lcnb.check("click_prepare_ready", "Ready" in text, "output: " + text.replace(chr(10), " | ")[:300])
lcnb.check("click_prepare_counts", ("Images to guess: %d" % I["expect_target"]) in text and I["expect_conditions"] in text, "expected %d images to guess and conditions %s" % (I["expect_target"], I["expect_conditions"]))
''',
    "play": '''
import tifffile
I = lcnb.INPUTS
ns = get_ipython().user_ns
start = lcnb.find(kind="Button", description="Start / continue")
submit = lcnb.find(kind="Button", description="Submit guess")
undo = lcnb.find(kind="Button", description="Undo last guess")
choice = lcnb.find(kind="ToggleButtons", description="Condition")

def on_screen_brightness():
    pending = ns["session"].state["pending"]["image_file"]
    return float(tifffile.imread(str(ns["session"].experiment_dir / pending)).mean())

def truth_guess():
    return "Mutant" if on_screen_brightness() > 500 else "Control"

def wrong_guess():
    return "Control" if truth_guess() == "Mutant" else "Mutant"

out = lcnb.click(start)
lcnb.check("click_play_first_image", "Image 1 of %d" % I["expect_target"] in " ".join(str(w.value) for w in lcnb.all_widgets() if type(w).__name__ == "HTML"), "after Start / continue the progress label reads Image 1 of %d; choices %s" % (I["expect_target"], list(choice.options)))
refused = lcnb.click(submit)
lcnb.check("click_play_no_choice_refused", ns["session"].n_answered == 0 and "Choose a condition first" in refused["stdout"], "submit with no condition chosen answered %d images (must stay 0); the notebook says: %s" % (ns["session"].n_answered, refused["stdout"].strip()[:80]))
lcnb.set_value(choice, truth_guess()); lcnb.click(submit)
lcnb.check("click_play_answer_1", ns["session"].n_answered == 1, "after the first submit %d guessed" % ns["session"].n_answered)
lcnb.set_value(choice, wrong_guess()); lcnb.click(submit)
lcnb.check("click_play_answer_2_wrong", ns["session"].n_answered == 2, "after the second (wrong) submit %d guessed" % ns["session"].n_answered)
lcnb.click(undo)
lcnb.check("click_play_undo", ns["session"].n_answered == 1, "after Undo last guess %d guessed (expected 1)" % ns["session"].n_answered)
lcnb.set_value(choice, truth_guess()); lcnb.click(submit)
lcnb.set_value(choice, wrong_guess()); last = lcnb.click(submit)
lcnb.check("click_play_finished", ns["session"].n_answered == I["expect_target"] and "Thank you" in last["stdout"] + str(last["outputs"]), "after the last submit %d guessed; the notebook says: %s" % (ns["session"].n_answered, last["stdout"].replace(chr(10), " | ")[:200]))
''',
}


def inputs(ctx: Any) -> dict[str, Any]:
    """Fixtures on a copy of lc_tests (the checkout is never touched) and the expectations counted from them on disk."""
    copy = ctx.copy_of("lc_tests")
    done = ctx.run_python([str(copy / "make_fixtures.py"), str(copy / "fixtures")])
    if done.returncode != 0:
        raise RuntimeError("make_fixtures.py failed: " + done.stderr[-300:])
    experiment = copy / "fixtures" / "experiment"
    images = sorted(experiment.rglob("*.tif"))
    return {
        "experiment": str(experiment),
        "results": str(copy / "fixtures" / "results"),
        "expect_images": len(images),
        "expect_target": int(0.25 * len(images)),
        "expect_conditions": " | ".join("%d: %s" % (i + 1, p.name) for i, p in enumerate(sorted(d for d in experiment.iterdir() if d.is_dir()))),
    }


def oracle(ctx: Any) -> list[tuple[str, str, str]]:
    import pandas as pd

    fixtures = ctx.work / "lc_tests" / "fixtures"
    found = sorted((fixtures / "results").rglob("game_results.csv"))
    if len(found) != 1:
        return [("game_csv", "FAIL", "expected exactly one game_results.csv under %s, found %s" % (fixtures / "results", found))]
    table = pd.read_csv(found[0])
    guessed = table[table["guess"].notna()]
    truth = guessed["image_file"].map(lambda f: Path(f).parts[0])
    correct = int((guessed["guess"] == truth).sum())
    rows = [
        ("game_csv_guesses", "PASS" if len(guessed) == 3 else "FAIL", "%d guesses in %s (expected 3: 25%% of 12 images, the undone guess is gone)" % (len(guessed), found[0])),
        ("game_csv_columns", "PASS" if {"condition", "biological_repeat", "guess", "decision_time_s"} <= set(table.columns) else "FAIL", "columns %s" % list(table.columns)),
        ("game_csv_condition_matches_folder", "PASS" if (guessed["condition"] == truth).all() else "FAIL", "the condition column equals the folder name of every guessed image"),
        ("correct_is_2_of_3", "PASS" if correct == 2 else "FAIL", "recomputed from the csv and the fixture folders: %d correct of %d (expected 2: the first and the re-answered image right, the last wrong)" % (correct, len(guessed))),
    ]
    folder = found[0].parent / "analysis"
    summary = (folder / "summary.txt").read_text(encoding="utf-8") if (folder / "summary.txt").is_file() else ""
    rows.append(("report_states_2_of_3", "PASS" if "Images guessed: 3, correct: 2 (accuracy 66.7%" in summary else "FAIL", "summary.txt says: " + summary[summary.find("Images guessed"):][:90].replace("\n", " ")))
    pdf = folder / "analysis_results.pdf"
    rows.append(("report_pdf", "PASS" if pdf.is_file() and pdf.read_bytes()[:4] == b"%PDF" and pdf.stat().st_size > 5000 else "FAIL", "%s: %s" % (pdf, pdf.stat().st_size if pdf.is_file() else "missing")))
    tables = [n for n in ("per_repeat.csv", "per_condition.csv", "confusion_counts.csv") if (folder / n).is_file()]
    rows.append(("report_tables", "PASS" if len(tables) == 3 else "FAIL", "tables present: %s" % tables))
    return rows
