"""Click script and oracle of VLab4Mic_main.ipynb (six EZInput widget steps built by the vlab4micjupyter package; the widgets are shown, never assigned, so they are found by their
descriptions).

Clicks, in the order of the notebook: Step 1 structure 1XI5 ("Select structure"), Step 2 an example probe ("Select example probe", then "Select probes and create labelled structure"),
Step 3 "Select parameters and build virtual sample" (1 particle, 1000 x 1000 x 100 nm: the defaults), Step 4 modality STED ("Add Modality", then "Select modalities and update virtual
microscope"), Step 5 "Set" the acquisition parameters, Step 6 name the experiment and press "Run Simulation", then "Show Results". Native pickers (saving directory chooser, load from
file, upload) are not used: the default output folder is $HOME/vlab4mic_outputs (the scratch home); the file route is HUMAN.

Oracle (files and numbers recomputed from the inputs, not read from the widgets): the run writes at least one .tif under the output folder whose name carries the experiment name; the STED
image is 2D with 1000 // 15 = 66 pixels per side (the same value the app's own `simulate_sample` case expects for the default sample), not constant, with finite values."""

from pathlib import Path
from typing import Any

AFTER_CELL = {8: "structure", 11: "probe", 14: "sample", 17: "modality", 20: "acquisition", 23: "run"}
STAGES = {
    "structure": '''
ns = get_ipython().user_ns
lcnb.set_value(lcnb.find(kind="Dropdown", description="Select Structure"), lcnb.INPUTS["structure"])
lcnb.click(lcnb.find(kind="Button", description="Select structure", exact=True))
lcnb.check("click_structure_selected", ns["my_experiment"].structure_id == lcnb.INPUTS["structure"], "my_experiment.structure_id = %r" % ns["my_experiment"].structure_id)
lcnb.check("click_structure_message", any("Structure loaded successfully" in str(w.value) for w in lcnb.all_widgets() if type(w).__name__ in ("Label", "HTML")), "the widget reports that the structure loaded")
''',
    "probe": '''
ns = get_ipython().user_ns
drop = lcnb.find(kind="Dropdown", description="Example probes")
lcnb.set_value(drop, lcnb.INPUTS["probe"] if lcnb.INPUTS["probe"] in list(drop.options) else list(drop.options)[0])
lcnb.click(lcnb.find(kind="Button", description="Select example probe", exact=True))
lcnb.click(lcnb.find(kind="Button", description="Select probes and create labelled structure", exact=True))
lcnb.check("click_probe_labelled", any("labelled structure" in str(w.value).lower() and "no labelled structure created yet" not in str(w.value).lower() for w in lcnb.all_widgets() if type(w).__name__ == "HTML"), "the labelled-structure message changed from 'No labelled structure created yet.' (probe %s)" % drop.value)
''',
    "sample": '''
lcnb.click(lcnb.find(kind="Button", description="Select parameters and build virtual sample", exact=True))
lcnb.check("click_sample_built", any("Current sample parameters" in str(w.value) or "number_of_particles" in str(w.value) for w in lcnb.all_widgets() if type(w).__name__ in ("HTML", "Label")), "the sample widget lists the selected parameters")
''',
    "modality": '''
ns = get_ipython().user_ns
lcnb.set_value(lcnb.find(kind="Dropdown", description="Modality", exact=True, index=0), "STED")
lcnb.click(lcnb.find(kind="Button", description="Add Modality", exact=True))
lcnb.click(lcnb.find(kind="Button", description="Select modalities and update virtual microscope", exact=True))
lcnb.check("click_modality_selected", "STED" in ns["my_experiment"].selected_mods, "my_experiment.selected_mods keys: %s" % list(ns["my_experiment"].selected_mods))
''',
    "acquisition": '''
lcnb.click(lcnb.find(kind="Button", description="Set", exact=True))
lcnb.note("click_acquisition_set", "pressed Set with the default acquisition parameters of STED")
''',
    "run": '''
ns = get_ipython().user_ns
area = [w for w in lcnb.all_widgets() if type(w).__name__ == "Textarea" and w.value == "Exp_name"]
lcnb.check("click_run_name_field", len(area) == 1, "found the experiment-name field with the default value Exp_name (%d matches)" % len(area))
if area:
    area[0].value = lcnb.INPUTS["experiment_name"]
lcnb.click(lcnb.find(kind="Button", description="Run Simulation", exact=True))
messages = [str(w.value) for w in lcnb.all_widgets() if type(w).__name__ == "HTML" and "Simulation" in str(w.value)]
lcnb.check("click_run_completed", any("completed successfully" in m for m in messages), "run messages: %s" % messages[-2:])
lcnb.click(lcnb.find(kind="Button", description="Show Results", exact=True))
lcnb.human("click_load_structure_from_file", "the 'Load structure from file' route needs a PDB/CIF file chosen in a file chooser: not driven")
''',
}
ORACLE_KERNEL = '''
import json
ns = get_ipython().user_ns
res = ns["my_experiment"].results
json.dump({k: {"shape": list(v["ch0"].shape)} for k, v in res.items()}, open(ns["my_experiment"].output_directory + "/_nb_results_state.json", "w"))
'''


def inputs(ctx: Any) -> dict[str, Any]:
    return {"structure": "1XI5", "probe": "NHS_ester", "experiment_name": "nbrun"}


def oracle(ctx: Any) -> list[tuple[str, str, str]]:
    import json

    import numpy as np
    import tifffile

    out = ctx.home / "vlab4mic_outputs"
    rows: list[tuple[str, str, str]] = []
    tifs = sorted(out.rglob("*.tif")) + sorted(out.rglob("*.tiff"))
    named = [t for t in tifs if "nbrun" in str(t)]
    rows.append(("files_written", "PASS" if named else "FAIL", "%d tif files under %s, %d carry the experiment name nbrun: %s" % (len(tifs), out, len(named), [t.name for t in tifs[:6]])))
    sted = [t for t in named if "STED" in str(t)]
    if sted:
        image = tifffile.imread(sted[0])
        side = 1000 // 15
        ok = image.ndim >= 2 and tuple(image.shape[-2:]) == (side, side) and np.isfinite(image).all() and float(image.max()) > float(image.min())
        rows.append(("sted_image", "PASS" if ok else "FAIL", "%s shape %s (expected %dx%d), min %.3g max %.3g" % (sted[0].name, image.shape, side, side, float(image.min()), float(image.max()))))
    else:
        rows.append(("sted_image", "FAIL", "no STED image written under %s" % out))
    state = out / "_nb_results_state.json"
    rows.append(("kernel_state", "PASS" if state.is_file() and "STED" in json.loads(state.read_text()) else "FAIL", "results held by the notebook: %s" % (state.read_text() if state.is_file() else "state file missing")))
    return rows
