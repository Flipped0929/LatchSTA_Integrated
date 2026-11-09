#!/bin/sh
# shortcut: fixed tiny/TT/ideal-clock case; generalize only when the case adapters support it.
set -eu

if [ "$#" -ne 2 ]; then
    echo "Usage: sh run_flow.sh /path/to/main /path/to/new_run_directory" >&2
    exit 2
fi
case_dir=$(cd -- "$(dirname -- "$0")" && pwd)
repo_dir=$(cd -- "$case_dir/../.." && pwd)
solver=$(cd -- "$(dirname -- "$1")" && pwd)/$(basename -- "$1")
[ -f "$solver" ] && [ -x "$solver" ] || { echo "Solver is not executable: $solver" >&2; exit 2; }
for tool in yosys sta python3 sha256sum; do
    command -v "$tool" >/dev/null || { echo "Missing tool: $tool" >&2; exit 2; }
done

# mkdir refuses an existing destination, including earlier incomplete runs.
mkdir -- "$2"
run_dir=$(cd -- "$2" && pwd)
trap 'flow_status=$?; if [ "$flow_status" -ne 0 ]; then echo "Flow failed; partial results retained in $run_dir" >&2; fi; exit "$flow_status"' EXIT
work_dir="$run_dir/examples/tiny_sky130"
mkdir -p -- "$work_dir/reports" "$run_dir/sky130_pdk" "$run_dir/logs"
for file in tiny.v tiny.sdc export.ys run_sta.tcl export_pin_graph.tcl convert_opensta_reports.py check_flow_reports.py run_flow.sh; do
    cp -- "$case_dir/$file" "$work_dir/"
done
for file in sky130_fd_sc_hd__tt_025C_1v80.lib sky130_fd_sc_hd__common.lib.json sky130_fd_sc_hd__dlxtp_1__tt_025C_1v80.lib.json extract_latch_timing.py; do
    cp -- "$repo_dir/sky130_pdk/$file" "$run_dir/sky130_pdk/"
done
sha256sum -- "$solver" > "$run_dir/solver.sha256"
printf '%s\n' "$solver" > "$run_dir/solver_path.txt"
if command -v git >/dev/null && git -C "$repo_dir" rev-parse HEAD > "$run_dir/source_revision.txt" 2>/dev/null; then
    git -C "$repo_dir" status --porcelain > "$run_dir/source_status.txt"
else
    printf '%s\n' 'Git revision unavailable; executed scripts and inputs are copied into this run.' > "$run_dir/source_revision.txt"
fi
{
    yosys -V
    sta -version
    python3 --version
} > "$run_dir/tool_versions.txt" 2>&1
cd -- "$run_dir"
find examples sky130_pdk -type f -exec sha256sum -- {} + > inputs.sha256
cd -- "$work_dir"
unset MCR_SDC MCR_REPORT_DIR

echo '[1/5] Yosys: check and export the standard-cell netlist'
yosys -l reports/yosys.log -s export.ys > "$run_dir/logs/yosys.log" 2>&1
echo '[2/5] OpenSTA: baseline reports and complete pin graph'
sta -no_init -no_splash -exit run_sta.tcl > reports/opensta_rerun.log 2>&1
echo '[3/5] Convert baseline reports and check reported constraints'
python3 convert_opensta_reports.py > "$run_dir/logs/conversion.log" 2>&1
python3 check_flow_reports.py reports reports/opensta_rerun.log latch_timing.json > "$run_dir/baseline_check.json"
echo '[4/5] Solver: optimize and export the Howard candidate SDC'
printf '%s\n' "$solver" "$work_dir/tiny.blif.out" 1 100 "$work_dir/latch_timing.json" --export-sdc "$work_dir/candidate_howard.sdc" > "$run_dir/solver_arguments.txt"
"$solver" "$work_dir/tiny.blif.out" 1 100 "$work_dir/latch_timing.json" \
    --export-sdc "$work_dir/candidate_howard.sdc" > "$run_dir/logs/solver.log" 2>&1
[ -s candidate_howard.sdc ]
echo '[5/5] OpenSTA: independently check the candidate'
MCR_SDC="$work_dir/candidate_howard.sdc" MCR_REPORT_DIR="$work_dir/reports_candidate" \
    sta -no_init -no_splash -exit run_sta.tcl > "$run_dir/logs/opensta_candidate.log" 2>&1
python3 check_flow_reports.py reports_candidate "$run_dir/logs/opensta_candidate.log" latch_timing.json \
    > "$run_dir/candidate_check.json"
cd -- "$run_dir"
sha256sum -c inputs.sha256 > logs/input_integrity.log
sha256sum -c solver.sha256 >> logs/input_integrity.log
echo "Reported timing checks passed. Results: $run_dir/candidate_check.json"
echo 'This is the fixed tiny/TT ideal-clock case; reported checks are not physical clock-tree signoff.'
