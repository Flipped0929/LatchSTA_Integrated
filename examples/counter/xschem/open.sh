#!/bin/sh
set -eu
counter_schematic_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$counter_schematic_dir"
exec xschem --rcfile "$counter_schematic_dir/xschemrc" "$counter_schematic_dir/counter.sch"
