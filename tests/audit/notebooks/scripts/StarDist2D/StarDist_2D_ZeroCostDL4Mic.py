"""Click script and oracle of StarDist_2D_ZeroCostDL4Mic.ipynb (StarDist2D 1.2.1): every step form from section 3.1 to 6.2, driven through its own Form object.

How the forms are driven: each step cell calls `notebook.<step>(session);`, which displays a `Form` (fields named as the 1.20.8 parameters, one button). The
stage after the cell takes the NEWEST button with the step's label ("Run", "Start training", "Show", "Export", "Predict"), recovers its Form from the click
handler's closure, sets the fields by parameter name (refusing an option the dropdown does not offer), clicks, and checks the outcome: no exception, Form.succeeded
True and no red "⚠" line (the forms show expected problems as one red line instead of raising, so "the click did not raise" proves nothing). A traitlets observer
on the button records its descriptions while the step runs: the 1.1.2 fix shows "Running…" on the disabled button (one row per click, aggregated in ORACLE_KERNEL).

Data: section 3.1 copies the shipped example dataset (6 training pairs, 2 test pairs, 1024x1024) into a scratch base folder; the default relative paths of 3.2 and
5.2 then resolve there. scripts/_stardist2d.py writes a 256x256 image of 12 discs (6.1) and a TWO-frame 1024x1024 stack of 40 and 80 discs (6.2).

Clicks and values:
* 3.1 base_folder = <work>/sd2d, dataset = the shipped example, download_full_dataset off.
* 3.2 model_name audit_model (model_path "models"), number_of_epochs 2, Use_Default_Advanced_Parameters off, batch_size 2, number_of_steps 3, patch_size 128,
  percentage_validation 20 (1 validation image of 6), n_rays 32, grid_parameter 2.
* 3.3 Use_Data_augmentation on, Multiply_dataset_by 2 (the steps are fixed by 3.2, so the factor does not lengthen training).
* 3.4 Use_pretrained_model on, Weights_choice best, the choice set in turn to 2D_demo, 2D_versatile_he, CML HUVEC nuclei, CML neutrophils, BMZ CHO and LAST
  2D_versatile_fluo, then Model_from_file with the 2D_versatile_fluo folder just copied (training then starts from it: a near-untrained network makes the
  threshold optimisation slow). Each one must download (no "could not be downloaded" / NoneType / download_failed: tester bug), its copied folder must load
  with stardist2d.model.load_model_folder and predict a 128x128 image. The BioImage Model Zoo choice is HUMAN (a Model Zoo id and bioimage.io).
* 4.1 overwrite_existing_model on; 4.2 Start training (2 epochs x 3 steps on the CPU).
* 5 current model; 5.1 Show; 5.2 the default test folders; 5.3 Export with a description.
* 6.1 the small image, Single_Images, ROIs on: with the trained model, with Pretrained_model 2D_versatile_fluo, with Pretrained_model "CML: HUVEC nuclei".
* 6.2 the two-frame stack, Pretrained_model 2D_versatile_fluo, block_size 512 x 512, min_overlap 50, n_tiles 1 x 1, Is_stack, Mask_images and ROIs on (tester
  bug: frame 2 failed with "array already exists" in image.zarr).

Oracle (files on disk, checked against the construction): the example copy is the shipped one (6 pairs, no Zenodo download); each 3.4 model folder holds
config.json, thresholds.json and weights_best.h5; the trained model's config.json carries the form's patch 128, 32 rays and grid 2, its training_evaluation.csv has
2 epochs, both PDFs exist; QC table has the 2 test images; the BMZ zip exists; 6.1 wrote labels, ROIs, centres and counts for each model and the pretrained models
count the 12 discs within 30 %; 6.2 wrote frame_00000.tif and frame_00001.tif (1024x1024) and a ROI zip per frame, with 40 and 80 discs within 30 %. Whole
notebook: no output of the notebook's own cells contains "Form(" (tester complaint: forms printed "Form(title=...)" under the cell).
"""

import csv
import sys
import zipfile
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from _stardist2d import (  # noqa: E402
    TOLERANCE,
    construct_version,
    executed_cells,
    make_inputs,
    output_text,
)

NOTEBOOK = "notebooks/StarDist_2D/StarDist_2D_ZeroCostDL4Mic.ipynb"
MODEL_NAME = "audit_model"
EPOCHS = 2
PATCH = 128
PRETRAINED = (  # (section 3.4 choice, folder name it is copied to = StarDist registry name); 2D_versatile_fluo LAST: training starts from it
    ("2D_Demo_Model_from_Stardist_Github", "2D_demo"),
    ("Versatile_H&E_nuclei", "2D_versatile_he"),
    ("CML: HUVEC nuclei (fluorescence)", "cml_huvec_nuclei"),
    ("CML: neutrophils (brightfield)", "cml_neutrophils_bf"),
    ("BMZ: CHO mitotic rounding (brightfield)", "bmz_cho_mitotic_rounding_bf"),
    ("2D_versatile_fluo_from_Stardist_Fiji", "2D_versatile_fluo"),
)
NO_PRETRAINED = "None (use the model above)"
PREDICT_RUNS = (  # section 6.1: (ident, results key of INPUTS, Pretrained_model choice)
    ("predict_trained", "pred_trained", NO_PRETRAINED),
    ("predict_fluo", "pred_fluo", "2D_versatile_fluo"),
    ("predict_cml", "pred_cml", "CML: HUVEC nuclei (fluorescence)"),
)

HELPERS = r'''
import json as _json, re as _re, time as _time
from pathlib import Path as _Path
I = lcnb.INPUTS
_SD_RUNNING = globals().setdefault("_SD_RUNNING", [])

def _sd_button(label):
    """The newest Button reading `label`: the stage runs right after the cell that built the form, so the newest one is that form's."""
    hits = [w for w in lcnb.all_widgets() if type(w).__name__ == "Button" and (w.description or "").strip() == label]
    if not hits:
        raise lcnb.WidgetNotFound("no Button %r; buttons: %s" % (label, sorted({str(w.description) for w in lcnb.all_widgets() if type(w).__name__ == "Button"})))
    return hits[-1]

def _sd_form(button):
    """The stardist2d Form behind a step button (its click handler is `lambda _: self.run()`, so the Form is in the closure)."""
    for callback in getattr(getattr(button, "_click_handlers", None), "callbacks", []):
        for cell in getattr(callback, "__closure__", None) or ():
            try:
                candidate = cell.cell_contents
            except ValueError:
                continue
            if type(candidate).__name__ == "Form":
                return candidate
    raise RuntimeError("button %r has no stardist2d Form in its click handler" % button.description)

def _sd_text(value):
    return _re.sub(r"\s+", " ", _re.sub(r"<[^>]+>", " ", str(value))).strip()

def _sd_run(ident, label, values, oracle=False):
    """Fill the form of the newest `label` button with `values` (by parameter name), click it like a user and check the step succeeded."""
    button = _sd_button(label)
    form = _sd_form(button)
    for name, value in values.items():
        if name not in form.controls:
            raise KeyError("form %r has no field %r (fields: %s)" % (form.title, name, list(form.controls)))
        control = form.controls[name]
        if hasattr(control, "options") and value not in tuple(control.options):
            raise ValueError("field %r of %r has no option %r (options: %s)" % (name, form.title, value, list(control.options)))
        lcnb.set_value(control, value)
    seen = []
    def watch(change):
        seen.append((change["new"], bool(button.disabled)))
    button.observe(watch, names="description")
    before = {w.model_id for w in lcnb.all_widgets()}
    error, result, started = "", {"stdout": "", "stderr": "", "outputs": []}, _time.time()
    try:
        result = lcnb.click(button)
    except Exception as problem:  # a failing step is a FAIL row, the stage goes on
        error = "%s: %s" % (type(problem).__name__, problem)
    finally:
        button.unobserve(watch, names="description")
    seconds = _time.time() - started
    messages = [_sd_text(w.value) for w in lcnb.all_widgets() if w.model_id not in before and type(w).__name__ in ("HTML", "Label")]
    warnings = [m for m in messages if m.startswith("⚠")]
    ok = not error and form.succeeded is True and not warnings
    lcnb.check(("oracle_" if oracle else "click_") + ident, ok,
               "%s (%s) in %.0f s; succeeded=%s; %s; messages: %s; stdout: %s"
               % (form.title, ", ".join("%s=%r" % kv for kv in values.items()) or "defaults", seconds, form.succeeded,
                  error or "no exception", " | ".join(messages)[-260:], result["stdout"].strip()[-120:]))
    running = ("Running…", True) in seen and (button.description or "") == label and not button.disabled
    _SD_RUNNING.append((ident, running))
    lcnb.check("click_%s_running_label" % ident, running,
               "button (description, disabled) while the step ran: %s; after: %r, disabled=%s" % (seen, button.description, button.disabled))
    return {"ok": ok, "messages": messages, "error": error, "form": form,
            "text": " ".join(messages) + "\n" + result["stdout"] + "\n" + result["stderr"] + "\n" + error}
'''

STAGES = {
    "deps": HELPERS
    + """
import stardist2d
lcnb.check("oracle_versions", stardist2d.__version__ == I["version"] == current_version,
           "stardist2d.__version__ %r, notebook current_version %r, construct.yaml %r (must agree: 1.1.1 was released with a stale version)" % (stardist2d.__version__, current_version, I["version"]))
lcnb.check("click_session", type(session).__name__ == "Session", "section 1.3 returned %r" % type(session).__name__)
""",
    "data": HELPERS
    + """
_r = _sd_run("example_data", "Run", {"base_folder": I["base"], "download_full_dataset": False})
lcnb.check("click_example_data_shipped", any(m.startswith("Example dataset ready in") for m in _r["messages"]), "messages: %s" % _r["messages"][:3])
lcnb.human("example_data_zenodo", "the other datasets of 3.1 and download_full_dataset download 100-580 MB from Zenodo: not exercised by the audit (the shipped copy is used)")
""",
    "params": HELPERS + """
_r = _sd_run("training_parameters", "Run", {
    "model_name": "%s", "number_of_epochs": %d, "Use_Default_Advanced_Parameters": False, "batch_size": 2, "number_of_steps": 3,
    "patch_size": %d, "percentage_validation": 20, "n_rays": 32, "grid_parameter": 2})
lcnb.check("click_training_parameters_initiated", "Parameters initiated." in _r["messages"], "messages: %%s" %% _r["messages"][-3:])
""" % (MODEL_NAME, EPOCHS, PATCH),
    "augmentation": HELPERS
    + """
_sd_run("augmentation", "Run", {"Use_Data_augmentation": True, "Multiply_dataset_by": 2})
""",
    "pretrained": HELPERS
    + """
import gc as _gc
import numpy as _np
from stardist2d import model as _sd_model
for _choice, _name in I["pretrained"]:
    _r = _sd_run("pretrained_" + _name, "Run", {"Use_pretrained_model": True, "pretrained_model_choice": _choice, "Weights_choice": "best"}, oracle=True)
    _bad = [w for w in ("download_failed", "NoneType", "could not be downloaded") if w.lower() in _r["text"].lower()]
    lcnb.check("oracle_pretrained_%s_no_download_error" % _name, not _bad, "%s: %s" % (_choice, ("found %s in: %s" % (_bad, _r["text"].strip()[-250:])) if _bad else "no download error"))
    _w = session.pretrained_weights
    lcnb.check("oracle_pretrained_%s_weights" % _name, _w is not None and _Path(_w).is_file() and _Path(_w).parent.name == _name,
               "session.pretrained_weights = %s (expected %s/weights_best.h5 under the base folder)" % (_w, _name))
    def _load(folder=_Path(_w).parent if _w is not None else None):
        loaded = _sd_model.load_model_folder(folder)
        channels = int(loaded.config.n_channel_in)
        image = _np.random.default_rng(0).random((128, 128) if channels == 1 else (128, 128, channels)).astype("float32")
        labels, _details = loaded.predict_instances(image)
        return loaded, channels, labels
    if _w is not None:
        _got = lcnb.guarded("oracle_pretrained_%s_loads" % _name, _load)
        if _got is not None:
            lcnb.check("oracle_pretrained_%s_loads" % _name, _got[2].shape == (128, 128),
                       "%s loads from the copied folder (%d channel(s), %d parameters, thresholds %s) and predicts a 128x128 image" % (_name, _got[1], _got[0].keras_model.count_params(), _got[0].thresholds))
        _got = None
        _gc.collect()
_folder = _Path(I["base"]) / "2D_versatile_fluo"
_r = _sd_run("pretrained_model_from_file", "Run", {"Use_pretrained_model": True, "pretrained_model_choice": "Model_from_file", "pretrained_model_path": str(_folder), "Weights_choice": "best"}, oracle=True)
lcnb.check("oracle_pretrained_model_from_file_weights", str(session.pretrained_weights) == str(_folder / "weights_best.h5"),
           "Model_from_file with the folder 3.4 just copied (%s): session.pretrained_weights = %s" % (_folder, session.pretrained_weights))
lcnb.note("pretrained_for_training", "training (4.1) starts from %s" % session.pretrained_weights)
lcnb.human("pretrained_bioimage_model_zoo", "the 'BioImage Model Zoo' choice of 3.4 needs a Model Zoo id or URL and imports it from bioimage.io: not exercised by the audit")
""",
    "prepare": HELPERS + """
_r = _sd_run("prepare_training", "Run", {"overwrite_existing_model": True}, oracle=True)
lcnb.check("click_prepare_training_steps", "Number of steps: 3" in _r["messages"], "messages: %%s" %% _r["messages"][-3:])
lcnb.check("click_prepare_training_patch", session.training is not None and session.training.patch_size == %d,
           "patch size %%s (3.2 asked for %d)" %% (getattr(session.training, "patch_size", None),))
""" % (PATCH, PATCH),
    "train": HELPERS + """
_r = _sd_run("train", "Start training", {}, oracle=True)
lcnb.check("click_train_progress", any(m.startswith("Epoch %d/%d") for m in _r["messages"]) and any(m.startswith("Training done") for m in _r["messages"]),
           "messages: %%s" %% _r["messages"][-3:])
""" % (EPOCHS, EPOCHS),
    "qc_model": HELPERS
    + """
_sd_run("qc_model", "Run", {"Use_the_current_trained_model": True})
""",
    "loss": HELPERS
    + """
_sd_run("loss_curves", "Show", {})
""",
    "qc": HELPERS
    + """
_sd_run("quality_control", "Run", {})
""",
    "export": HELPERS
    + """
_sd_run("bmz_export", "Export", {"Trained_model_description": "Audit model: 2 epochs on the shipped StarDist2D example data"})
""",
    "predict": HELPERS
    + """
for _ident, _key, _choice in I["predict_runs"]:
    _r = _sd_run(_ident, "Predict", {"Data_folder": I["small_dir"], "Results_folder": I[_key], "Data_type": "Single_Images",
                                     "Region_of_interests": True, "Use_the_current_trained_model": True, "Prediction_model_folder": "",
                                     "Pretrained_model": _choice}, oracle=True)
    lcnb.check("click_%s_completed" % _ident, "Predictions completed" in _r["messages"], "messages: %s" % _r["messages"][-3:])
    if _choice.startswith("CML"):
        lcnb.check("click_%s_citation" % _ident, any("please cite doi:10.5281/zenodo." in m for m in _r["messages"]), "the notebook says what to cite: %s" % _r["messages"][:2])
""",
    "bigdata": HELPERS
    + """
_r = _sd_run("big_data_stack", "Predict", {
    "Data_folder": I["big_dir"], "Results_folder": I["big_out"], "Use_the_current_trained_model": True, "Prediction_model_folder": "",
    "Pretrained_model": "2D_versatile_fluo", "block_size_Y": 512, "block_size_X": 512, "min_overlap": 50, "n_tiles_Y": 1, "n_tiles_X": 1,
    "Is_stack": True, "Mask_images": True, "Region_of_interests": True}, oracle=True)
lcnb.check("oracle_big_data_no_array_exists", "already exists" not in _r["text"], "tester bug (frame 2: 'array already exists' in image.zarr): %s" % _r["text"].strip()[-250:])
lcnb.check("click_big_data_completed", "Predictions completed for 1 image(s)" in _r["messages"], "messages: %s" % _r["messages"][-3:])
""",
}
AFTER_CELL = {
    11: "deps",  # 1.3 load_dependencies -> session
    23: "data",  # 3.1 download_example_data
    26: "params",  # 3.2 training_parameters
    29: "augmentation",  # 3.3 data_augmentation
    31: "pretrained",  # 3.4 pretrained_weights
    35: "prepare",  # 4.1 prepare_training
    37: "train",  # 4.2 start_training
    39: "qc_model",  # 5 choose_qc_model
    41: "loss",  # 5.1 loss_curves
    43: "qc",  # 5.2 quality_control
    45: "export",  # 5.3 export_bioimage_model_zoo
    49: "predict",  # 6.1 predictions
    51: "bigdata",  # 6.2 big_data_predictions
}
ORACLE_KERNEL = """
_runs = globals().get("_SD_RUNNING", [])
_without = [i for i, ok in _runs if not ok]
lcnb.check("oracle_running_label", bool(_runs) and not _without,
           "%d of %d step clicks showed 'Running…' on their disabled button while the step ran; without it: %s" % (len(_runs) - len(_without), len(_runs), _without or "none"))
lcnb.human("running_label_rendered", "the widget state says 'Running…' while a step runs (checked above); that JupyterLab paints it on the button, and how the kernel busy circle behaves for a widget callback, needs a person watching a long step (4.2 Start training)")
"""
_DATA: dict[str, Any] = {}


def inputs(ctx: Any) -> dict[str, Any]:
    _DATA.update(make_inputs(ctx.work))
    _DATA["version"] = construct_version(ctx)
    _DATA["pretrained"] = [list(pair) for pair in PRETRAINED]
    _DATA["predict_runs"] = [list(run) for run in PREDICT_RUNS]
    return dict(_DATA)


def _row(ident: str, ok: bool, detail: str) -> tuple[str, str, str]:
    return ident, "PASS" if ok else "FAIL", detail


def _objects(path: Path) -> int:
    import numpy as np
    import tifffile

    labels = tifffile.imread(path)
    return int(np.count_nonzero(np.unique(labels)))


def _within(found: int, expected: int) -> bool:
    return abs(found - expected) <= TOLERANCE * expected


def oracle(ctx: Any) -> list[tuple[str, str, str]]:
    import json

    import tifffile

    rows: list[tuple[str, str, str]] = []
    base = Path(_DATA["base"])
    shipped = base / "data" / "Stardist"
    pairs = {
        sub: len(list((shipped / sub).glob("*.tif")))
        for sub in ("Training - Images", "Training - Masks", "Test - Images", "Test - Masks")
    }
    rows.append(
        _row(
            "example_data_shipped",
            pairs == {"Training - Images": 6, "Training - Masks": 6, "Test - Images": 2, "Test - Masks": 2},
            "3.1 copied %s into %s (the shipped copy has 6 training and 2 test pairs; 45 pairs would mean the Zenodo download)"
            % (pairs, shipped),
        )
    )
    for _choice, name in PRETRAINED:
        folder = base / name
        files = {
            f: (folder / f).is_file() and (folder / f).stat().st_size > 0
            for f in ("config.json", "thresholds.json", "weights_best.h5")
        }
        rows.append(_row("pretrained_%s_files" % name, all(files.values()), "%s: %s" % (folder, files)))

    model = base / "models" / MODEL_NAME
    config_path = model / "config.json"
    if config_path.is_file():
        config = json.loads(config_path.read_text(encoding="utf-8"))
        got = (config.get("train_patch_size"), config.get("n_rays"), config.get("grid"))
        rows.append(
            _row(
                "model_config",
                list(got[0] or []) == [PATCH, PATCH] and got[1] == 32 and list(got[2] or []) == [2, 2],
                "config.json train_patch_size %s, n_rays %s, grid %s (the form asked for %d, 32, 2)"
                % (got[0], got[1], got[2], PATCH),
            )
        )
    else:
        rows.append(_row("model_config", False, "%s was not written (4.1/4.2)" % config_path))
    weights = sorted(p.name for p in model.glob("weights_*.h5"))
    rows.append(
        _row(
            "model_weights",
            "weights_best.h5" in weights and (model / "thresholds.json").is_file(),
            "weights %s, thresholds.json %s" % (weights, (model / "thresholds.json").is_file()),
        )
    )
    evaluation = model / "Quality Control" / "training_evaluation.csv"
    epochs = (
        len(list(csv.reader(evaluation.read_text(encoding="utf-8").splitlines()))) - 1
        if evaluation.is_file()
        else -1
    )
    rows.append(
        _row(
            "training_evaluation",
            epochs == EPOCHS,
            "%s has %d epoch rows (trained for %d)" % (evaluation, epochs, EPOCHS),
        )
    )
    report = model / ("%s_training_report.pdf" % MODEL_NAME)
    rows.append(
        _row(
            "training_report",
            report.is_file() and report.stat().st_size > 1000,
            "%s exists: %s" % (report.name, report.is_file()),
        )
    )
    qc_table = model / "Quality Control" / ("Quality_Control for %s.csv" % MODEL_NAME)
    qc_rows = (
        len(list(csv.reader(qc_table.read_text(encoding="utf-8").splitlines()))) - 1
        if qc_table.is_file()
        else -1
    )
    rows.append(_row("qc_table", qc_rows == 2, "%s has %d rows (2 test images)" % (qc_table.name, qc_rows)))
    for ident, name in (
        ("qc_loss_plot", "lossCurvePlots.png"),
        ("qc_report", "%s_QC_report.pdf" % MODEL_NAME),
    ):
        exists = (model / "Quality Control" / name).is_file()
        rows.append(_row(ident, exists, "Quality Control/%s exists: %s" % (name, exists)))
    bmz = base / "models" / ("%sbioimageio.zip" % MODEL_NAME)
    rows.append(
        _row(
            "bmz_export_zip", bmz.is_file() and bmz.stat().st_size > 0, "%s exists: %s" % (bmz, bmz.is_file())
        )
    )

    for ident, key, choice in PREDICT_RUNS:
        out = Path(_DATA[key])
        names = ("small_blobs.tif", "small_blobs.zip", "small_blobs_Nuclei_centre.csv", "Nuclei_count.csv")
        present = {n: (out / n).is_file() for n in names}
        rows.append(_row(ident + "_files", all(present.values()), "6.1 with %s wrote %s" % (choice, present)))
        if not present["small_blobs.tif"]:
            continue
        labels = tifffile.imread(out / "small_blobs.tif")
        count = _objects(out / "small_blobs.tif")
        listed: list[list[str]] = (
            list(csv.reader((out / "Nuclei_count.csv").read_text(encoding="utf-8").splitlines()))
            if present["Nuclei_count.csv"]
            else []
        )
        counted = [r for r in listed if r]
        rows.append(
            _row(
                ident + "_count_table",
                bool(counted) and counted[-1][-1].strip() == str(count),
                "Nuclei_count.csv %s, label image has %d objects" % (counted[-1:], count),
            )
        )
        if choice == NO_PRETRAINED:
            rows.append(
                (
                    "%s_objects" % ident,
                    "NOTE",
                    "the 2-epoch model found %d of %d discs (not asserted: a 6-step training)"
                    % (count, _DATA["small_count"]),
                )
            )
        elif choice != "2D_versatile_fluo":
            # a model trained on other cells (CML: HUVEC nuclei found 3 of the 12 synthetic discs): the count says nothing about the app;
            # that the model downloads, loads and writes its outputs is asserted above, and its own tool case on real nuclei passes
            rows.append(
                (
                    "%s_objects" % ident,
                    "NOTE",
                    "%s found %d of %d synthetic discs (not asserted: the discs are not the cells this model was trained on)"
                    % (choice, count, _DATA["small_count"]),
                )
            )
        else:
            rows.append(
                _row(
                    ident + "_objects",
                    labels.shape == (256, 256) and _within(count, _DATA["small_count"]),
                    "%s found %d objects in a %s image of %d discs (+/- %d %%)"
                    % (choice, count, labels.shape, _DATA["small_count"], TOLERANCE * 100),
                )
            )

    big = Path(_DATA["big_out"])
    counts = []
    for index, expected in enumerate(_DATA["frame_counts"]):
        frame = big / "stack" / ("frame_%05d.tif" % index)
        rois = big / "stack_labels_roi" / ("frame_%05d.zip" % index)
        if not frame.is_file():
            rows.append(
                _row(
                    "big_frame_%d" % index,
                    False,
                    "%s was not written (6.2, Is_stack, block_size 512)" % frame,
                )
            )
            counts.append(-1)
            continue
        shape = tifffile.imread(frame).shape
        count = _objects(frame)
        counts.append(count)
        rows.append(
            _row(
                "big_frame_%d" % index,
                shape == (1024, 1024) and _within(count, expected),
                "%s: shape %s, %d objects for %d discs (+/- %d %%)"
                % (frame.name, shape, count, expected, TOLERANCE * 100),
            )
        )
        roi_count = len(zipfile.ZipFile(rois).namelist()) if rois.is_file() else -1
        rows.append(
            _row(
                "big_frame_%d_rois" % index,
                rois.is_file() and _within(roi_count, expected),
                "%s: %d ROIs for %d discs" % (rois, roi_count, expected),
            )
        )
    rows.append(
        _row(
            "big_frames_differ",
            len(counts) == 2 and counts[1] > counts[0] > 0,
            "frame object counts %s: frame 1 (80 discs) must have more than frame 0 (40), so it was predicted from its own pixels"
            % counts,
        )
    )

    path, cells = executed_cells(ctx, NOTEBOOK)
    if cells is None:
        rows.append(
            (
                "no_form_repr",
                "FAIL",
                "the executed notebook %s does not exist: the outputs cannot be checked" % path,
            )
        )
    else:
        printed = []
        for index, outputs in cells:
            for output in outputs:
                if output.get("output_type") in (
                    "stream",
                    "execute_result",
                    "display_data",
                ) and "Form(" in output_text(output):
                    printed.append("cell %d: %s" % (index, output_text(output).strip()[:80]))
        results = [
            index
            for index, outputs in cells
            if any(o.get("output_type") == "execute_result" for o in outputs)
        ]
        rows.append(
            _row(
                "no_form_repr",
                not printed,
                "outputs of the notebook's %d cells containing 'Form(': %s; cells with an execute_result: %s"
                % (len(cells), printed[:4] or "none", results or "none"),
            )
        )
    return rows
