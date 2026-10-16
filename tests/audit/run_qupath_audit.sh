#!/bin/bash
# The QuPath host's UI audit (tests/run_ui_audit.sh of the LabConstrictor-QuPath checkout) against one app.
# usage: run_qupath_audit.sh APP LC_HOME TESTS OUTDIR
# Required environment: LC_QUPATH_CHECKOUT (the QuPath host repository), QUPATH (the QuPath installation), LC_RELEASE_DIR (folder with the release under test),
#   LC_AUDIT_PYTHON (interpreter for the audit's helpers)
# Optional: LC_EXPECT_QUPATH (default listed; "hidden" when the app must not appear)
set -euo pipefail
A=${1:?APP}; HOME_DIR=${2:?LC_HOME}; TESTS=${3:?TESTS}; OUT=${4:?OUTDIR}
: "${LC_QUPATH_CHECKOUT:?set LC_QUPATH_CHECKOUT}" "${QUPATH:?set QUPATH}" "${LC_RELEASE_DIR:?set LC_RELEASE_DIR}" "${LC_AUDIT_PYTHON:?set LC_AUDIT_PYTHON}"
export LC_EXPECT_QUPATH=${LC_EXPECT_QUPATH:-listed} QUPATH LC_HOME=$HOME_DIR LC_APP=$A LC_APP_TESTS=$TESTS LC_SHOTS=$OUT LC_RELEASE_DIR PYTHON=$LC_AUDIT_PYTHON
mkdir -p "$OUT"
cd "$LC_QUPATH_CHECKOUT"
exec tests/run_ui_audit.sh
