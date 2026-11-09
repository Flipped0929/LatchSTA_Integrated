#!/bin/sh
set -eu
counter_pnr_view_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
counter_pnr_view_run=${1:-"$counter_pnr_view_dir/run_03"}
case "$counter_pnr_view_run" in
    /*) ;;
    *) counter_pnr_view_run="$PWD/$counter_pnr_view_run" ;;
esac
export COUNTER_PNR_RUN="$counter_pnr_view_run"
exec openroad -gui -no_init "$counter_pnr_view_dir/view.tcl"
