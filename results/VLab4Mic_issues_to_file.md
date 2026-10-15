# VLab4Mic 0.1.6 bugs to file (Issues are disabled on CellMigrationLab/LabConstrictor-VLab4Mic)

## 1. compare_images accepts a flat or all-zero reference image and returns a wrong result (VL-5)
Only the simulated image gets the `flat_image` refusal. With a flat or all-zero reference, compare_images completes: Pearson null, SSIM 0.173 (flat) and 0.864 (all-zero). Expected: refuse with a sentence.

## 2. simulate_sample with an unsupported structure_file fails with a raw AttributeError; a missing file blames the network (VL-4)
`labconstrictor-tools run VLab4Mic simulate_sample random_seed=1 structure_file=a.csv` -> `[AttributeError] 'MolecularReplicates' object has no attribute 'struct'`; the log has the real cause ("CSV is not a valid format. Valid options are PDB or CIF."). A missing file says "Could not get the structure 1XI5 ... check the internet connection". Expected: refuse before running, naming the file and the supported types.

## 3. Sweeps notebook ignores the saving directory chosen in the file chooser (VL-3, from code reading)
vlab4micjupyter/sweep_parameters_widgets.py ~706-712: `save_results` sets the misspelled `sweep_gen.ouput_directory`, nothing reads it; `save_analysis(output_name=...)` is called without `output_directory`. Same typo at ~611 and ~741.

## 4. Images written by simulate_sample carry no pixel size (VL-12)
simulated.tif / noiseless.tif have ResolutionUnit NONE, 1/1 resolution; Napari shows scale 1.0 though the tool reports pixel_size_um. Suggest writing the pixel size (um) into the output metadata.
