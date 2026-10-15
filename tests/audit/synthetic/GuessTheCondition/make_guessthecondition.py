#!/usr/bin/env python3
"""Synthetic experiment folders (conditions x repeats x images) with a KNOWN analysis result for Guess the Condition.

    python make_guessthecondition.py OUT_DIR   # standalone: numpy, scipy, pandas, tifffile; common.py and check_ground_truth.py next to it or one folder up

The game is interactive and the condition of an image is never shown, so the known answers come from a player who gives the SAME guess
for every image (by name, by number or in another letter case): accuracy is then the share of that condition among the guessed
images, chance is the share of the most common condition, and every table follows by counting. Played at 100 % the answer does not
depend on the (random) order of the images. Truth is computed here with plain counting and scipy's t distribution, not with the app's code.

`cases.json` plays each game in order (prepare, show, guess N times, analyse); the case runner must run the cases in order, in a COPY of
the folder (the results folder is written into).
"""

from __future__ import annotations

import sys
from collections.abc import Sequence
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent)]
from common import (
    Suite,
    chk_status,
    chk_value,
    standalone_main,
)  # noqa: E402

APP, VERSION = "GuessTheCondition", "0.0.1"
Counts = dict[tuple[str, str], int]  # (condition, repeat) -> images
SEED = 11


from gtc_core import Games  # noqa: E402
from gtc_views import add_image_kinds, add_scan, add_stress  # noqa: E402


def add_games(g: Games) -> None:
    balanced = {(c, r): 2 for c in ("Control", "Mutant") for r in ("R1", "R2", "R3")}
    g.game(
        "gtc_balanced_const",
        "2 conditions x 3 repeats x 2 images (12), the player always says Control",
        balanced,
        ["Control"],
        "Control",
        "Balanced design: the share of Control is 6/12 = 0.5 and so is chance (always naming the most common condition): accuracy 0.5, every repeat 2/4 correct, "
        "accuracy minus chance 0 in every repeat (the t-test across repeats is undefined: p_across_repeats absent), none above chance. Control recall 1, Mutant recall 0. "
        "Constant guess: every shuffle of the randomization test gives the same count, so p = (1 + 10000)/(1 + 10000) = 1.",
    )
    unbalanced = {
        **{("Control", r): 2 for r in ("R1", "R2", "R3")},
        **{("Mutant", r): 1 for r in ("R1", "R2", "R3")},
    }
    g.game(
        "gtc_unbalanced_const",
        "Control 2 and Mutant 1 images per repeat (9), the player always says Mutant",
        unbalanced,
        ["Mutant"],
        "Mutant",
        "Mutant is 3 of 9 images: accuracy 1/3; chance is the share of the MOST COMMON condition, Control: 2/3 (also in every repeat: 2/3). Accuracy minus chance -1/3 in every repeat, none above chance.",
    )
    three = {
        **{("Control", r): 1 for r in ("R1", "R2", "R3")},
        **{("Drug1", r): 2 for r in ("R1", "R2", "R3")},
        **{("Drug2", r): 3 for r in ("R1", "R2", "R3")},
    }
    g.game(
        "gtc_three_by_number",
        "3 conditions (1, 2, 3 images per repeat), guesses '3' and 'dRuG2' alternately",
        three,
        ["3", "dRuG2"],
        "Drug2",
        "Conditions are numbered in alphabetical order (1: Control | 2: Drug1 | 3: Drug2): '3' and 'dRuG2' both mean Drug2, 9 of 18 images: accuracy 0.5 = chance (Drug2 is the most common). "
        "A wrong number mapping would give 1/6 or 1/3. The first guess is undone and made again: the result must be the same.",
        with_undo=True,
    )
    partial = {**{(c, r): 2 for c in ("Control", "Mutant") for r in ("R1", "R2")}, ("Control", "R3"): 2}
    g.game(
        "gtc_one_condition_repeat",
        "repeat R3 holds Control images only (10 images), the player always says Control",
        partial,
        ["Control"],
        "Control",
        "R3 has one condition: it cannot be compared with chance (chance n/a, left out of the test across repeats, said in the notes). R1 and R2: 2/4 correct, chance 0.5. "
        "Overall 6/10 = 0.6 = chance (Control is the most common). Two testable repeats: a pilot, no test across repeats.",
    )


def add_demo(g: Games) -> None:
    s = g.s
    out = s.fixtures / "gtc_demo_out"
    out.mkdir(exist_ok=True)
    (out / ".keep").write_text("", encoding="utf-8")
    s.dataset(
        "gtc_demo_experiment",
        "'Create a demo experiment' with 2 images per repeat",
        "works",
        derivation="2 conditions x 3 repeats x 2 images = 12 images, in a folder GuessTheCondition_demo made inside the given folder.",
        files=[out / ".keep"],
        tool="create_demo_experiment",
        inputs={"output_folder": s.rel(out), "images_per_repeat": 2},
        expect={"results": {"values": {"images": 12}}},
        checks=[chk_status("COMPLETE"), chk_value("images", 12)],
    )
    for ident, n, text in (("gtc_demo_zero", 0, "must be >="), ("gtc_demo_too_many", 51, "must be <=")):
        s.dataset(
            ident,
            "'Create a demo experiment' with images_per_repeat = %d (declared range 1..50)" % n,
            "refused",
            derivation="Outside the declared range.",
            tool="create_demo_experiment",
            inputs={"output_folder": s.rel(out), "images_per_repeat": n},
            expect={"status": "FAILED", "code": "invalid_parameter", "message_contains": text},
            checks=[chk_status("FAILED", "invalid_parameter", text)],
            outcome_text="refused: invalid_parameter",
        )


def add_percentages(g: Games) -> None:
    counts = {(c, r): 1 for c in ("Control", "Mutant") for r in ("R1", "R2", "R3", "R4", "R5")}  # 10 images
    root, files = g.exp("gtc_percentages", counts)
    for pct, to_guess in ((1, 1), (25, 3), (33, 4), (50, 5), (51, 6), (100, 10)):
        user = "pct%d" % pct
        inputs = {
            "experiment_folder": g.s.rel(root),
            "results_folder": g.s.rel(g.results),
            "user_name": user,
            "percentage_to_test": pct,
            "restart": True,
            "random_seed": SEED,
        }
        g.s.dataset(
            "gtc_percentage_%d" % pct,
            "10 images, %d %% to guess" % pct,
            "works",
            derivation="The share is rounded UP (never down, at least 1, at most all): ceil(%d x 10 / 100) = %d."
            % (pct, to_guess),
            files=files if pct == 1 else [],
            tool="prepare_game",
            inputs=inputs,
            expect={"results": {"values": {"images": 10, "to_guess": to_guess, "remaining": to_guess}}},
            checks=[
                chk_status("COMPLETE"),
                chk_value("images", 10),
                chk_value("to_guess", to_guess),
                chk_value("remaining", to_guess),
                chk_value("guessed", 0),
            ],
        )
    for pct, code in ((0, "invalid_parameter"), (101, "invalid_parameter")):
        g.s.dataset(
            "gtc_percentage_%d" % pct,
            "percentage %d (declared range 1..100)" % pct,
            "refused",
            derivation="Outside the declared range.",
            tool="prepare_game",
            inputs={
                "experiment_folder": g.s.rel(root),
                "results_folder": g.s.rel(g.results),
                "user_name": "pctbad",
                "percentage_to_test": pct,
                "restart": True,
            },
            expect={"status": "FAILED", "code": code, "message_contains": "must be"},
            checks=[chk_status("FAILED", code, "must be")],
            outcome_text="refused: invalid_parameter",
        )


def add_refusals(g: Games) -> None:
    s = g.s
    one = {("OnlyCondition", r): 1 for r in ("R1", "R2")}
    root, files = g.exp("gtc_single_condition", one)

    def refuse(
        ident: str,
        purpose: str,
        root: Path,
        files: Sequence[Path],
        code: str | None,
        contains: str | None,
        derivation: str,
        user: str = "refuse",
    ) -> None:
        s.dataset(
            ident,
            purpose,
            "refused",
            derivation=derivation,
            files=files,
            tool="prepare_game",
            inputs={
                "experiment_folder": s.rel(root),
                "results_folder": s.rel(g.results),
                "user_name": user,
                "restart": True,
            },
            expect={
                "status": "FAILED",
                **({"code": code} if code else {}),
                **({"message_contains": contains} if contains else {}),
            },
            checks=[chk_status("FAILED", code, contains)],
            outcome_text="refused%s" % (": " + code if code else ""),
        )

    refuse(
        "gtc_single_condition",
        "an experiment with one condition",
        root,
        files,
        "bad_experiment",
        "at least two",
        "Nothing to guess between: the game needs two conditions.",
    )
    root2 = s.fixtures / "gtc_no_images" / "experiment"
    for c in ("Control", "Mutant"):
        (root2 / c / "R1").mkdir(parents=True, exist_ok=True)
        (root2 / c / "R1" / "readme.txt").write_text("no image here\n", encoding="utf-8")
    refuse(
        "gtc_no_images",
        "conditions and repeats but no TIFF image",
        root2,
        [root2 / "Control" / "R1" / "readme.txt"],
        "bad_experiment",
        "No TIFF image was found",
        "No image, no game.",
    )
    root3, files3 = g.exp("gtc_case_clash", {("Control", "R1"): 1, ("control", "R1"): 1})
    refuse(
        "gtc_case_clash",
        "conditions 'Control' and 'control' (differ only in letter case)",
        root3,
        files3,
        "bad_experiment",
        "differ only in upper/lower case",
        "A guess could not tell them apart.",
    )
    refuse(
        "gtc_no_experiment",
        "an experiment folder that does not exist",
        s.fixtures / "does_not_exist",
        [],
        None,
        None,
        "The folder is missing.",
    )
    refuse(
        "gtc_bad_user_name",
        "a user name that is not a folder name ('a/b')",
        root,
        [],
        "bad_user_name",
        "folder name",
        "The name becomes a folder name.",
        user="a/b",
    )


def build(out: Path) -> Suite:
    s = Suite(APP, out, VERSION)
    g = Games(s)
    add_games(g)
    add_demo(g)
    add_percentages(g)
    add_refusals(g)
    add_scan(g)
    add_image_kinds(g)
    add_stress(g)
    return s


if __name__ == "__main__":
    sys.exit(standalone_main(build, HERE, __doc__ or ""))
