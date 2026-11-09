#!/bin/sh
set -eu
counter_pnr_script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
counter_pnr_output=${1:-"$counter_pnr_script_dir/run_$(date +%Y%m%d_%H%M%S)"}
case "$counter_pnr_output" in
    /*) ;;
    *) counter_pnr_output="$PWD/$counter_pnr_output" ;;
esac
if [ -e "$counter_pnr_output" ]; then
    printf 'Output already exists: %s\n' "$counter_pnr_output" >&2
    exit 1
fi
export COUNTER_PNR_RUN="$counter_pnr_output"
exec openroad -no_init -exit -log "$counter_pnr_output.openroad.log" "$counter_pnr_script_dir/flow.tcl"
