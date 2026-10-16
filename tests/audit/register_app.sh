#!/bin/bash
# Register an installed app into a FRESH private registry, the way the installer's post-install does (so that retention and prune checks see only this app's runs).
# usage: register_app.sh NAME PREFIX SRC_CHECKOUT PRIVATE_LC_HOME
set -euo pipefail
N=${1:?NAME}; P=${2:?PREFIX}; S=${3:?SRC_CHECKOUT}; H=${4:?PRIVATE_LC_HOME}
[ ! -e "$H" ] || { echo "refusing: $H already exists (a registry that may hold other runs)" >&2; exit 2; }
mod=$(ls "$S/src" | grep _lc_tools | head -1)
[ -n "$mod" ] || { echo "no *_lc_tools package under $S/src" >&2; exit 2; }
man=$(ls "$P"/*/labconstrictor-app.yaml 2>/dev/null | head -1 || true)
LC_HOME=$H "$P/bin/python" -m labconstrictor_tools register --name "$N" --prefix "$P" --module "$mod" --version 0 --display-name "$N" ${man:+--app-manifest "$man"}
