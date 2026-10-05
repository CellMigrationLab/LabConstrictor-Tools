#!/bin/bash
# run Windows python under Wine; stdin must be valid and stdout a pipe (Wine quirk)
export WINEPREFIX=$HOME/wineprefix WINEDEBUG=-all LANG=C.UTF-8 LC_ALL=C.UTF-8 LC_HOME=C:\\users\\root\\lchome
xvfb-run -a env PYTHONIOENCODING=utf-8 PIP_CERT='Z:\root\.ccr\ca-bundle.crt' "$@" < /dev/null 2>&1 | cat | grep -v "X connection to"
