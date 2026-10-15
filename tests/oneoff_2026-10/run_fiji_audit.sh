#!/bin/bash
# usage: run_fiji_audit.sh APP LC_HOME TESTS OUTDIR [script|jar]
A=$1; MODE=${5:-script}
export LC_APP=$A LC_APP_TESTS=$3 LC_HOME=$2 LC_EXPECT_FIJI=listed LC_SHOTS=$4 LC_FIJI_HOME=/home/user/hosts/fiji/Fiji LC_HOST_VERSION=v0.1.0-alpha.3
if [ "$MODE" = jar ]; then export LC_FIJI_MODE=jar LC_FIJI_JAR=$(ls /home/user/hosts/alpha3/fiji/*.jar); else export LC_FIJI_PLUGIN_DIR=/home/user/a3/fiji_script; fi
mkdir -p $4; cd /home/user/wt3_fiji
exec xvfb-run -a -s "-screen 0 1600x1000x24" /home/user/w/venv/bin/python tests/ui_audit.py
