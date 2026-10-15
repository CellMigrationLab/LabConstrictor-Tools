"""Experiment writer, counting oracle and case builder of the Guess the Condition datasets. Specific to the analysis of this app."""

from __future__ import annotations

import math
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import tifffile
from scipy import stats

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parent)]
from common import (
    Suite,
    chk_message,
    chk_status,
    chk_table,
    chk_value,
)  # noqa: E402

APP, VERSION = "GuessTheCondition", "0.0.1"
Counts = dict[tuple[str, str], int]  # (condition, repeat) -> images
SEED = 11


def picture(
    rng: np.random.Generator, level: float, shape: tuple[int, ...] = (24, 24), dtype: Any = np.uint16
) -> np.ndarray:
    """Noise around `level` (a brighter condition is a real visual difference for the hosts)."""
    return np.clip(rng.normal(level, 0.1 * level, shape), 1, np.iinfo(dtype).max).astype(dtype)


def write_experiment(root: Path, counts: Counts, seed: int = 1) -> list[Path]:
    rng = np.random.default_rng(seed)
    conditions = sorted({c for c, _ in counts}, key=lambda c: (c.lower(), c))
    files = []
    for (condition, repeat), n in sorted(counts.items()):
        for k in range(n):
            path = root / condition / repeat / ("img%d.tif" % (k + 1))
            path.parent.mkdir(parents=True, exist_ok=True)
            tifffile.imwrite(path, picture(rng, 200 + 600 * conditions.index(condition)))
            files.append(path)
    return files


def analysis_truth(counts: Counts, guess: str) -> dict[str, Any]:
    """The analysis of a player who named `guess` for every image of the experiment: all numbers by counting."""
    conditions = sorted({c for c, _ in counts}, key=lambda c: (c.lower(), c))
    repeats = sorted({r for _, r in counts})
    total = sum(counts.values())
    share = {c: sum(n for (cc, _), n in counts.items() if cc == c) / total for c in conditions}
    chance = max(share.values())
    rows: list[dict[str, Any]] = []
    for r in repeats:
        cell = {c: counts.get((c, r), 0) for c in conditions}
        n = sum(cell.values())
        testable = sum(1 for v in cell.values() if v) >= 2
        c_r = max(cell.values()) / n if testable else float("nan")
        acc = cell.get(guess, 0) / n
        rows.append(
            {
                "biological_repeat": r,
                "n": n,
                "correct": cell.get(guess, 0),
                "accuracy": acc,
                "chance": c_r,
                "accuracy_minus_chance": acc - c_r if testable else float("nan"),
                "testable": testable,
            }
        )
    diffs: list[float] = [float(row["accuracy_minus_chance"]) for row in rows if row["testable"]]
    k = len(diffs)
    p = float("nan")
    if k >= 3 and max(diffs) != min(diffs):
        mean, sem = sum(diffs) / k, np.std(diffs, ddof=1) / math.sqrt(k)
        p = float(stats.t.sf(mean / sem, k - 1))
    by_condition = [
        {
            "condition": c,
            "n": int(round(share[c] * total)),
            "correct": int(round(share[c] * total)) if c == guess else 0,
            "recall": 1.0 if c == guess else 0.0,
        }
        for c in conditions
    ]
    correct = sum(n for (c, _), n in counts.items() if c == guess)
    return {
        "n": total,
        "correct": correct,
        "accuracy": correct / total,
        "chance": chance,
        "repeats": rows,
        "k": k,
        "above": sum(1 for d in diffs if d > 0),
        "p_across": p,
        "by_condition": by_condition,
        "untestable": [row["biological_repeat"] for row in rows if not row["testable"]],
    }


class Games:
    def __init__(self, suite: Suite) -> None:
        self.s = suite
        self.results = suite.fixtures / "results"
        self.results.mkdir(exist_ok=True)
        (suite.out / "truth").mkdir(exist_ok=True)

    def exp(self, ident: str, counts: Counts, seed: int = 1) -> tuple[Path, list[Path]]:
        root = self.s.fixtures / ident / "experiment"
        return root, write_experiment(root, counts, seed)

    def prepare(self, root: Path, user: str, pct: int = 100, comment: str = "", **values: Any) -> int:
        inputs = {
            "experiment_folder": self.s.rel(root),
            "results_folder": self.s.rel(self.results),
            "user_name": user,
            "percentage_to_test": pct,
            "restart": True,
            "random_seed": SEED,
        }
        return self.s.case(
            "prepare_game",
            inputs,
            {"max_seconds": 120, "results": {"values": values}} if values else {"max_seconds": 120},
            comment,
        )

    def play(self, user: str, guess: str | None, expect: dict[str, Any], comment: str) -> int:
        inputs: dict[str, Any] = {"results_folder": self.s.rel(self.results), "user_name": user}
        if guess is not None:
            inputs["guess"] = guess
        return self.s.case("play_round", inputs, expect, comment)

    def game(
        self,
        ident: str,
        purpose: str,
        counts: Counts,
        guesses: Sequence[str],
        truth_guess: str,
        derivation: str,
        outcome_text: str = "",
        with_undo: bool = False,
    ) -> None:
        """Prepare at 100 %, show the first image, guess every image with `guesses[i % len]`, analyse. Dataset = the analysis case."""
        root, files = self.exp(ident, counts)
        user = "u_" + ident
        total = sum(counts.values())
        conditions = sorted({c for c, _ in counts}, key=lambda c: (c.lower(), c))
        text = " | ".join("%d: %s" % (i, c) for i, c in enumerate(conditions, 1))
        self.prepare(
            root,
            user,
            100,
            "[%s] prepare: %d images, all to guess" % (ident, total),
            images=total,
            to_guess=total,
            guessed=0,
            remaining=total,
            conditions=text,
        )
        self.play(
            user,
            None,
            {"max_seconds": 120, "results": {"values": {"image": "1 of %d" % total, "conditions": text}}},
            "[%s] the first image" % ident,
        )
        if with_undo:
            self.s.case(
                "list_conditions",
                {"results_folder": self.s.rel(self.results), "user_name": user},
                {"results": {"values": {"conditions": text, "choices": conditions}}},
                "[%s] the options of the guess list: the conditions in alphabetical order" % ident,
            )
        for i in range(total):
            last = i == total - 1
            expect = (
                {"status": "FAILED", "code": "no_result", "message_contains": "last image"}
                if last
                else {"max_seconds": 120, "results": {"values": {"image": "%d of %d" % (i + 2, total)}}}
            )
            self.play(
                user,
                guesses[i % len(guesses)],
                expect,
                "[%s] guess %d of %d: %s" % (ident, i + 1, total, guesses[i % len(guesses)]),
            )
            if with_undo and i == 0:
                self.s.case(
                    "undo_last_guess",
                    {"results_folder": self.s.rel(self.results), "user_name": user},
                    {"results": {"values": {"forgotten_guess": truth_guess, "guessed": 0}}},
                    "[%s] undo the first guess: it is forgotten" % ident,
                )
                self.play(
                    user,
                    guesses[0],
                    {"max_seconds": 120, "results": {"values": {"image": "2 of %d" % total}}},
                    "[%s] the undone image is guessed again" % ident,
                )
        t = analysis_truth(counts, truth_guess)
        rep = pd.DataFrame(t["repeats"])
        cond = pd.DataFrame(t["by_condition"])
        rep_path, cond_path = self.s.out / "truth" / (ident + "_by_repeat.csv"), self.s.out / "truth" / (
            ident + "_by_condition.csv"
        )
        rep.to_csv(rep_path, index=False)
        cond.to_csv(cond_path, index=False)
        values = {
            "images_guessed": t["n"],
            "accuracy": round(t["accuracy"], 4),
            "chance": round(t["chance"], 4),
            "biological_repeats": t["k"],
            "repeats_above_chance": t["above"],
            "p_randomization_these_images_exploratory": 1.0,
        }
        checks: list[dict[str, Any]] = [
            chk_status("COMPLETE"),
            chk_value("images_guessed", t["n"]),
            chk_value("accuracy", t["accuracy"], 6e-5),
            chk_value("chance", t["chance"], 6e-5),
            chk_value("biological_repeats", t["k"]),
            chk_value("repeats_above_chance", t["above"]),
            chk_value("p_randomization_these_images_exploratory", 1.0, 1e-9),
            chk_table(
                "by_repeat",
                "biological_repeat",
                self.s.rel(rep_path),
                ["n", "correct", "accuracy", "chance", "accuracy_minus_chance"],
                rtol=1e-6,
                atol=1e-6,
                rows=len(rep),
            ),
            chk_table(
                "by_condition",
                "condition",
                self.s.rel(cond_path),
                ["n", "correct", "recall"],
                rtol=1e-6,
                atol=1e-6,
                rows=len(cond),
            ),
            chk_message("readout", "Not above chance"),
        ]
        if math.isnan(t["p_across"]):
            checks.append({"kind": "absent_value", "key": "p_across_repeats"})
        else:
            checks.append(chk_value("p_across_repeats", round(t["p_across"], 5), 1e-5))
        for ident_untestable in t["untestable"]:
            checks.append(
                chk_value("notes", contains="Repeat %s holds images of one condition only" % ident_untestable)
            )
        expect_analyze = {
            "max_seconds": 120,
            "results": {
                "values": {k: v for k, v in values.items()},
                "by_repeat": {"rows": len(rep)},
                "by_condition": {"rows": len(cond)},
                "readout": {"contains": "Not above chance"},
            },
        }
        self.s.dataset(
            ident,
            purpose,
            "works",
            derivation=derivation,
            files=files + [rep_path, cond_path],
            tool="analyze_results",
            inputs={"results_folder": self.s.rel(self.results), "user_name": user},
            expect=expect_analyze,
            checks=checks,
            outcome_text=outcome_text
            or "analysis equals the truth (accuracy %.4f, chance %.4f, %d repeats)"
            % (t["accuracy"], t["chance"], t["k"]),
        )
