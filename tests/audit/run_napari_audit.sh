#!/bin/bash
# The Napari host's UI audit (tests/ui_audit.py of the LabConstrictor-Napari checkout) against one app, under Xvfb.
# usage: run_napari_audit.sh APP LC_HOME TESTS OUTDIR
# Required environment: LC_NAPARI_CHECKOUT (the Napari host repository), LC_AUDIT_PYTHON (interpreter with napari and the audit's requirements)
# Optional: LC_EXPECT_NAPARI (default listed; "hidden" when the app must not appear)
set -euo pipefail
A=${1:?APP}; HOME_DIR=${2:?LC_HOME}; TESTS=${3:?TESTS}; OUT=${4:?OUTDIR}
: "${LC_NAPARI_CHECKOUT:?set LC_NAPARI_CHECKOUT}" "${LC_AUDIT_PYTHON:?set LC_AUDIT_PYTHON}"
export LC_APP=$A LC_APP_TESTS=$TESTS LC_HOME=$HOME_DIR LC_EXPECT_NAPARI=${LC_EXPECT_NAPARI:-listed} LC_SHOTS=$OUT
mkdir -p "$OUT"
cd "$LC_NAPARI_CHECKOUT"
exec xvfb-run -a -s "-screen 0 1600x1000x24" "$LC_AUDIT_PYTHON" tests/ui_audit.py
