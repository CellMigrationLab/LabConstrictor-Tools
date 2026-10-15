"""Click script and oracle of VLab4Mic_parameter_sweeps.ipynb (a parameter sweep: structure, probes and modalities, parameter values, a reference image, the analysis).

Clicks: Step 1 structure 1XI5 -> "Select"; Step 2 the first listed probe and the Widefield modality (the cheapest) -> the newest "Select"; Step 3 "Use parameter" and "Use list of values"
for the labelling efficiency with the list 0.5, 1.0 -> "Select parameters for sweep"; Step 4 "Generate image reference" and "Preview reference"; Step 5 one repeat, metric SSIM ->
"Run analysis" -> "save analysis" (into the notebook's own folder, the scratch copy of the app). Native pickers (load structure or reference from file, saving directory chooser) are HUMAN.

Oracle: the analysis is saved (files named vlab4mic_analysis* exist in the notebook folder and are not empty), and the sweep has exactly the 2 labelling-efficiency values asked for."""

from pathlib import Path
from typing import Any

AFTER_CELL = {7: "structure", 9: "mods", 11: "values", 13: "reference", 15: "analyse"}
STAGES = {
    "structure": '''
dd = lcnb.find(kind="Dropdown", description="", index=0)
lcnb.set_value(dd, next(o for o in dd.options if str(o).startswith(lcnb.INPUTS["structure"])))
lcnb.click(lcnb.find(kind="Button", description="Select", exact=True, index=-1))
lcnb.check("click_structure_selected", [str(x).split(":")[0] for x in get_ipython().user_ns["sweep_generator"].structures] == [lcnb.INPUTS["structure"]], "sweep_generator.structures = %s" % get_ipython().user_ns["sweep_generator"].structures)
''',
    "mods": '''
ns = get_ipython().user_ns
probes = lcnb.find(kind="SelectMultiple", description="probes")
mods = lcnb.find(kind="SelectMultiple", description="modalities")
probes.value = (probes.options[0],)
mods.value = ("Widefield",)
lcnb.click(lcnb.find(kind="Button", description="Select", exact=True, index=-1))
lcnb.check("click_mods_selected", list(ns["sweep_generator"].modalities) == ["Widefield"] and len(ns["sweep_generator"].probes) == 1, "modalities %s probes %s" % (ns["sweep_generator"].modalities, ns["sweep_generator"].probes))
''',
    "values": '''
ns = get_ipython().user_ns
boxes = [w for w in lcnb.all_widgets() if type(w).__name__ == "VBox" and len(w.children) == 7 and type(w.children[1]).__name__ == "Checkbox" and ("labelling efficiency" in str(w.children[0].value).lower() or "labeling efficiency" in str(w.children[0].value).lower())]
lcnb.check("click_values_widget_found", len(boxes) == 1, "%d parameter blocks named Labelling efficiency" % len(boxes))
block = boxes[0]
lcnb.set_value(block.children[1], True)
lcnb.set_value(block.children[2], True)
lcnb.set_value(block.children[6], "0.5, 1.0")
lcnb.click(lcnb.find(kind="Button", description="Select parameters for sweep", exact=True))
lcnb.check("click_values_set", any("Parameters set successfully" in str(w.value) for w in lcnb.all_widgets() if type(w).__name__ == "HTML"), "the widget says Parameters set successfully")
''',
    "reference": '''
lcnb.click(lcnb.find(kind="Button", description="Generate image reference", exact=True))
lcnb.check("click_reference_set", any(str(w.value) == "Reference Set" for w in lcnb.all_widgets() if type(w).__name__ == "HTML"), "the reference widget says Reference Set")
lcnb.click(lcnb.find(kind="Button", description="Preview reference", exact=True))
lcnb.human("click_structure_from_file", "'Load structure from file', 'Upload image reference' and the saving-directory chooser need files chosen in a file chooser: not driven")
''',
    "analyse": '''
reps = lcnb.find(kind="BoundedIntText", description="Repeats")
lcnb.set_value(reps, 1)
md = lcnb.find(kind="Dropdown", description="Metric for image comparison")
lcnb.set_value(md, next(o for o in md.options if str(o).lower() == "ssim"))
lcnb.click(lcnb.find(kind="Button", description="Run analysis", exact=True))
lcnb.click(lcnb.find(kind="Button", description="save analysis", exact=True))
''',
}


def inputs(ctx: Any) -> dict[str, Any]:
    return {"structure": "1XI5"}


def oracle(ctx: Any) -> list[tuple[str, str, str]]:
    saved = sorted(p for p in ctx.home.rglob("*") if p.is_file() and ("vlab4mic_analysis" in p.name.lower() or ("vlab4mic_results" in p.name.lower() and p.suffix == ".csv")))
    rows = [("analysis_saved", "PASS" if saved and all(p.stat().st_size > 0 for p in saved) else "FAIL", "%d files named vlab4mic_analysis* under %s: %s" % (len(saved), ctx.home, [p.name for p in saved[:6]]))]
    text = " ".join(p.read_text(encoding="utf-8", errors="replace") for p in saved if p.suffix in (".csv", ".json", ".yaml", ".txt"))
    rows.append(("two_values_in_analysis", "PASS" if "0.5" in text and "1.0" in text else "FAIL", "the saved analysis text mentions both labelling-efficiency values 0.5 and 1.0 (%d text chars read)" % len(text)))
    return rows
