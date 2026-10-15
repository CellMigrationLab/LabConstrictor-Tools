#!/bin/bash
# The Napari host's synthetic-dataset driver (tests/ui_synthetic_napari.py of the LabConstrictor-Napari checkout): every synthetic case through the real form.
# usage: syn_napari.sh APP SYNDIR LC_HOME OUTDIR [file|layer]
# Required environment: LC_NAPARI_CHECKOUT (the Napari host repository), LC_AUDIT_PYTHON (interpreter with napari)
# Optional: LC_EXPECT_NAPARI (default listed)
set -euo pipefail
A=${1:?APP}; SYN=${2:?SYNDIR}; HOME_DIR=${3:?LC_HOME}; OUT=${4:?OUTDIR}
: "${LC_NAPARI_CHECKOUT:?set LC_NAPARI_CHECKOUT}" "${LC_AUDIT_PYTHON:?set LC_AUDIT_PYTHON}"
export LC_APP=$A LC_APP_TESTS=$SYN LC_HOME=$HOME_DIR LC_EXPECT_NAPARI=${LC_EXPECT_NAPARI:-listed} LC_SHOTS=$OUT/audit_scratch LC_SYN_OUT=$OUT/reports LC_UI_INPUT=${5:-layer}
mkdir -p "$LC_SHOTS"
cd "$LC_NAPARI_CHECKOUT"
exec xvfb-run -a -s "-screen 0 1600x1000x24" "$LC_AUDIT_PYTHON" tests/ui_synthetic_napari.py
