# Upstream pull requests for VLab4Mic (drafts to paste)

Both patches were made against the current `main` of the upstream repositories (anonymous clone, 15 Oct 2026). They compile; they have **not** been run (the widgets need Jupyter and the library is not installed in our test environment). Please run the existing tests and check the behaviour described under "How to check" before opening the pull requests.

---

## 1. Repository `HenriquesLab/VLab4Mic-jupyter` (package `vlab4micjupyter`)
Patch file: `vlab4micjupyter_sweeps_saving_folder.patch`. Branch name suggestion: `fix-sweeps-saving-folder`.

**Title:** Parameter sweeps: use the folder chosen in "Select output directory" when saving results

**Body:**
In the parameter-sweeps analysis widget (`sweep_parameters_widgets.py`, `analyse_sweep`), the saving folder chosen with the file chooser is stored on the sweep generator under a misspelled attribute, `ouput_directory`. `SweepGenerator.save_analysis` reads `self.output_directory`, so the chosen folder is ignored and the files are written to the generator's default folder. The same misspelling is read when the chooser starts, so the chooser always starts in `.`.

Change:
* `save_results` calls the generator's own `set_output_directory(output_directory)` instead of assigning the misspelled attribute.
* the chooser starts in `sweep_gen.output_directory` (or `.` when it is not set); the local variable is renamed so it no longer shadows the `output_directory` of `save_results`.

How to check: run the parameter-sweeps notebook, press "Analyse", choose a folder other than the default in "Select output directory", press save: the CSV files and plots are in the chosen folder (before: in the default one).

Found while testing the LabConstrictor packaging of VLab4Mic (LabConstrictor-VLab4Mic).

---

## 2. Repository `HenriquesLab/VLab4Mic` (package `vlab4mic`)
Patch file: `vlab4mic_unsupported_structure_format_raises.patch`. Branch name suggestion: `raise-on-unsupported-structure-format`.

**Title:** Raise a clear error when a structure file is not PDB or CIF

**Body:**
`MolecularStructureParser.initialise_parsers` (`generate/molecular_structure.py`) handles `PDB` and `CIF`; for any other format it only prints "<format> is not a valid format. Valid options are PDB or CIF." and carries on. The format comes from the file extension (`experiments.py`: `structure_path.split(".")[-1].upper()`), so for example a `.csv` structure file gets through to the next step and fails there with `AttributeError: 'MolecularReplicates' object has no attribute 'struct'` (the message a user sees; the real cause is only in the printed line).

Change: raise `ValueError("<format> is not a valid structure format. Valid options are PDB or CIF.")` instead of printing.

How to check: call `experiments.image_vsample(structure="some.csv", structure_is_path=True, ...)` (or the structure loader with a `.csv` file): a `ValueError` naming the format, instead of the later `AttributeError`.

Note: callers that relied on the print-and-continue behaviour for a format other than PDB/CIF would now fail early; none in this repository continue meaningfully without `self.struct`.

Found while testing the LabConstrictor packaging of VLab4Mic (LabConstrictor-VLab4Mic), which now checks the file type before calling the library.
