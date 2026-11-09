#!/bin/sh
set -eu
counter_rcx_script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
counter_rcx_output=${1:-"$counter_rcx_script_dir/pex_$(date +%Y%m%d_%H%M%S)"}
case "$counter_rcx_output" in
    /*) ;;
    *) counter_rcx_output="$PWD/$counter_rcx_output" ;;
esac
if [ -e "$counter_rcx_output" ]; then
    printf 'Output already exists: %s\n' "$counter_rcx_output" >&2
    exit 1
fi
export COUNTER_RCX_RUN="$counter_rcx_output"
exec openroad -no_init -exit -log "$counter_rcx_output.openroad.log" "$counter_rcx_script_dir/extract.tcl"
