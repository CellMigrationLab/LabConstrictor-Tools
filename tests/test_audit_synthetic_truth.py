"""The synthetic ground truth follows the alpha.4 behaviour of the apps (generated for real, into a temporary folder; numpy, pandas and tifffile only):
VLab4Mic refuses a flat or all-zero REFERENCE with flat_image and no longer asserts a similarity for unrelated sparse images; CellTracksColab refuses two spots of
a track at one time (same_time_twice) and an infinite position (non_finite_position)."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

import _paths  # noqa: F401  (must come first)
from _paths import ROOT

SYNTHETIC = ROOT / "tests" / "audit" / "synthetic"


class GroundTruthTests(unittest.TestCase):
    truth: dict[str, dict[str, dict[str, Any]]] = {}

    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temporary.cleanup)
        out = Path(cls.temporary.name)
        done = subprocess.run(
            [
                sys.executable,
                str(SYNTHETIC / "make_synthetic.py"),
                "--out",
                str(out),
                "--app",
                "CellTracksColab",
                "--app",
                "LabConstrictor-VLab4Mic",
            ],
            capture_output=True,
            text=True,
            timeout=300,
        )
        if done.returncode != 0:
            raise AssertionError("generators failed: " + done.stdout + done.stderr)
        for app in ("CellTracksColab", "LabConstrictor-VLab4Mic"):
            document = json.loads((out / app / "ground_truth.json").read_text(encoding="utf-8"))
            cls.truth[app] = {d["id"]: d for d in document["datasets"]}

    def refusal_code(self, app: str, dataset: str) -> str | None:
        entry = self.truth[app][dataset]
        self.assertEqual(entry["expected"], "refused", dataset)
        statuses = [c for c in entry["checks"] if c["kind"] == "status"]
        self.assertEqual(len(statuses), 1, dataset)
        self.assertEqual(statuses[0]["status"], "FAILED", dataset)
        code: str | None = statuses[0].get("code")
        return code

    def test_vlab4mic_flat_and_zero_references_are_refused_with_flat_image(self) -> None:
        for dataset in ("vm_flat_reference", "vm_zero_reference", "vm_flat_simulated", "vm_zero_simulated"):
            self.assertEqual(self.refusal_code("LabConstrictor-VLab4Mic", dataset), "flat_image", dataset)

    def test_vlab4mic_unrelated_images_assert_no_ssim(self) -> None:
        for entry in self.truth["LabConstrictor-VLab4Mic"].values():
            if "unrelated" in entry["purpose"] or entry["id"] == "vm_different_fields":
                keys = [c.get("key") for c in entry["checks"] if c["kind"] == "value"]
                self.assertNotIn("ssim", keys, entry["id"])

    def test_celltracks_duplicate_time_is_refused_with_same_time_twice(self) -> None:
        self.assertEqual(self.refusal_code("CellTracksColab", "ct_duplicate_time"), "same_time_twice")

    def test_celltracks_infinite_position_is_refused_with_non_finite_position(self) -> None:
        self.assertEqual(self.refusal_code("CellTracksColab", "ct_inf_position"), "non_finite_position")


if __name__ == "__main__":
    unittest.main()
