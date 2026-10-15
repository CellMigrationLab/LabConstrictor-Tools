#!/bin/bash
# usage: run_napari_audit.sh APP LC_HOME TESTS OUTDIR
A=$1; export LC_APP=$A LC_APP_TESTS=$3 LC_HOME=$2 LC_EXPECT_NAPARI=listed LC_SHOTS=$4
mkdir -p $4; cd /home/user/wt3_napari
exec xvfb-run -a -s "-screen 0 1600x1000x24" /home/user/w/venv/bin/python tests/ui_audit.py
