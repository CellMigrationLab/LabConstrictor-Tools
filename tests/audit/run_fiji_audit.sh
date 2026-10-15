#!/bin/bash
# The Fiji host's UI audit (tests/ui_audit.py of the LabConstrictor-Fiji checkout) against one app, under Xvfb.
# usage: run_fiji_audit.sh APP LC_HOME TESTS OUTDIR [script|jar]
# Required environment (no defaults: a wrong guess would audit the wrong build):
#   LC_FIJI_CHECKOUT      checkout of the Fiji host repository (it holds tests/ui_audit.py)
#   LC_FIJI_HOME          the Fiji installation
#   LC_HOST_VERSION       release under test, e.g. v0.1.0-alpha.4
#   LC_FIJI_JAR           (jar mode) the release jar; LC_FIJI_PLUGIN_DIR (script mode) the folder of the Jython script
#   LC_AUDIT_PYTHON       interpreter with the audit's requirements
# Optional: LC_EXPECT_FIJI (default listed: the app must appear in Fiji's menu; "hidden" when it must not)
set -euo pipefail
A=${1:?APP}; HOME_DIR=${2:?LC_HOME}; TESTS=${3:?TESTS}; OUT=${4:?OUTDIR}; MODE=${5:-script}
: "${LC_FIJI_CHECKOUT:?set LC_FIJI_CHECKOUT}" "${LC_FIJI_HOME:?set LC_FIJI_HOME}" "${LC_HOST_VERSION:?set LC_HOST_VERSION}" "${LC_AUDIT_PYTHON:?set LC_AUDIT_PYTHON}"
export LC_APP=$A LC_APP_TESTS=$TESTS LC_HOME=$HOME_DIR LC_EXPECT_FIJI=${LC_EXPECT_FIJI:-listed} LC_SHOTS=$OUT LC_FIJI_HOME LC_HOST_VERSION
if [ "$MODE" = jar ]; then
  : "${LC_FIJI_JAR:?set LC_FIJI_JAR for jar mode}"
  export LC_FIJI_MODE=jar LC_FIJI_JAR
else
  : "${LC_FIJI_PLUGIN_DIR:?set LC_FIJI_PLUGIN_DIR for script mode}"
  export LC_FIJI_PLUGIN_DIR
fi
mkdir -p "$OUT"
cd "$LC_FIJI_CHECKOUT"
exec xvfb-run -a -s "-screen 0 1600x1000x24" "$LC_AUDIT_PYTHON" tests/ui_audit.py
