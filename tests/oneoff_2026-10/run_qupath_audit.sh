#!/bin/bash
# usage: run_qupath_audit.sh APP LC_HOME TESTS OUTDIR
export QUPATH=/home/user/hosts/qupath/QuPath LC_HOME=$2 LC_APP=$1 LC_APP_TESTS=$3 LC_SHOTS=$4 LC_RELEASE_DIR=/home/user/hosts/alpha3/qupath PYTHON=/home/user/w/venv/bin/python
mkdir -p $4; cd /home/user/wt3_qupath
exec tests/run_ui_audit.sh
