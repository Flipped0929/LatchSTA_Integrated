#!/bin/sh
# This archived synthesis/STA flow does not invoke the separate counter_solver command.
set -eu
if [ "$#" -ne 1 ]; then
    echo "Usage: sh examples/counter/run_flow.sh /path/to/new_run_directory" >&2
    echo "This flow performs synthesis and STA; run counter_solver separately for optimization." >&2
    exit 2
fi
case_dir=$(cd -- "$(dirname -- "$0")" && pwd)
repo_dir=$(cd -- "$case_dir/../.." && pwd)
for file in counter.v counter.sdc export.ys latch_map.v run_sta.tcl run_flow.sh; do
    [ -f "$case_dir/$file" ] || { echo "Missing input: $file" >&2; exit 2; }
done
library="$repo_dir/sky130_pdk/sky130_fd_sc_hd__tt_025C_1v80.lib"
[ -f "$library" ] || { echo "Missing SKY130 TT Liberty" >&2; exit 2; }
for tool in yosys sta python3 sha256sum; do
    command -v "$tool" >/dev/null || { echo "Missing tool: $tool" >&2; exit 2; }
done
mkdir -- "$1"
run_dir=$(cd -- "$1" && pwd)
trap 'flow_status=$?; if [ "$flow_status" -ne 0 ]; then echo "Flow failed or reported checks need attention; results retained in $run_dir" >&2; fi; exit "$flow_status"' EXIT
work_dir="$run_dir/examples/counter"
mkdir -p -- "$work_dir/reports" "$run_dir/sky130_pdk" "$run_dir/logs"
printf '%s\n' '{"status":"incomplete","optimization":{"status":"not_run"}}' > "$run_dir/flow_status.json"
for file in counter.v counter.sdc export.ys latch_map.v run_sta.tcl run_flow.sh; do
    cp -- "$case_dir/$file" "$work_dir/"
done
cp -- "$library" "$run_dir/sky130_pdk/"
if [ -f "$repo_dir/sky130_pdk/LICENSE.upstream" ]; then
    cp -- "$repo_dir/sky130_pdk/LICENSE.upstream" "$run_dir/sky130_pdk/"
fi
if command -v git >/dev/null && git -C "$repo_dir" rev-parse HEAD > "$run_dir/source_revision.txt" 2>/dev/null; then
    git -C "$repo_dir" status --porcelain > "$run_dir/source_status.txt"
else
    printf '%s\n' 'Git revision unavailable; executed scripts and inputs are copied into this run.' > "$run_dir/source_revision.txt"
fi
{ yosys -V; sta -version; python3 --version; } > "$run_dir/tool_versions.txt" 2>&1
cd -- "$run_dir"
find examples sky130_pdk -type f -exec sha256sum -- {} + > inputs.sha256
cd -- "$work_dir"
unset COUNTER_REPORT_DIR COUNTER_SDC MCR_SDC MCR_REPORT_DIR
echo '[1/3] Yosys: synthesize and map eight latches with synchronous reset logic'
yosys -l reports/yosys.log -s export.ys > "$run_dir/logs/yosys.log" 2>&1
echo '[2/3] OpenSTA: zero-skew clock, both latch phases and synchronous reset paths'
sta -no_init -no_splash -exit run_sta.tcl > "$run_dir/logs/opensta.log" 2>&1
cd -- "$run_dir"
sha256sum -c inputs.sha256 > logs/input_integrity.log
echo '[3/3] Check report completeness and summarize reported timing'
python3 - "$run_dir" <<'PY'
import csv
import json
import re
import sys
from pathlib import Path

root = Path(sys.argv[1])
reports = root / "examples/counter/reports"
issues = []
summary = {"status": "incomplete", "timing": {}, "optimization": {
    "status": "not_run",
    "reasons": ["This synthesis/STA flow does not invoke the separate counter_solver command"]}}
try:
    log = (root / "logs/opensta.log").read_text(encoding="utf-8")
    if "Counter reports written to " not in log:
        issues.append("OpenSTA completion marker missing")
    if re.search(r"(?m)^\s*(?:Error|ERROR|Warning|WARNING)(?:\s|:)", log):
        issues.append("OpenSTA reported errors or warnings; inspect logs/opensta.log")
    if (reports / "check_setup.rpt").read_text(encoding="utf-8").strip():
        issues.append("Structural/constraint checks require review")
    with (reports / "latches.tsv").open(encoding="utf-8", newline="") as stream:
        latches = list(csv.DictReader(stream, delimiter="\t"))
    if len(latches) != 8 or len({r["instance"] for r in latches}) != 8:
        issues.append("Expected eight unique latch records")
    for row in latches:
        for suffix in ("instance", "arrival", "load", "dq_min", "dq_max", "cq_min", "cq_max"):
            if not (reports / (row["instance"] + "_" + suffix + ".rpt")).is_file():
                issues.append("Missing latch report: " + row["instance"] + "_" + suffix)
    for name in ("constraints.sdc", "effective.sdc"):
        path = reports / name
        if not path.is_file() or path.stat().st_size == 0:
            issues.append("Missing/empty constraints: " + name)
    for name in ("units", "clocks", "setup", "hold", "en_setup", "en_hold", "rst_n_setup", "rst_n_hold", "pulse_width", "checks", "violations"):
        text = (reports / (name + ".rpt")).read_text(encoding="utf-8")
        met, violated = text.count("(MET)"), text.count("(VIOLATED)")
        if name in {"setup", "hold", "en_setup", "en_hold", "rst_n_setup", "rst_n_hold", "pulse_width"} and not met + violated:
            issues.append("No reported checks: " + name)
        if violated:
            issues.append("Reported violations in " + name + ".rpt")
        if re.search(r"(?i)(?:^|\s)[+-]?(?:nan|inf(?:inity)?)(?=\s|$)", text):
            issues.append("Non-finite value in " + name + ".rpt")
        if name in {"setup", "hold", "en_setup", "en_hold", "rst_n_setup", "rst_n_hold", "pulse_width", "checks"}:
            summary["timing"][name] = {"reported_met": met, "reported_violated": violated}
    summary["status"] = "reports_need_review" if issues else "reported_checks_passed"
except (OSError, ValueError, KeyError) as error:
    issues.append(str(error))
summary["issues"] = issues
summary["limitations"] = ["Finite report limits and summary checks are not exhaustive signoff.",
                          "Synchronous reset and enable timing assume the IO budgets in counter.sdc; this flow does not run functional simulation.",
                          "Ideal zero-skew analysis at the requested period; no frequency search, solver input or pin graph is generated."]
(root / "flow_status.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n", encoding="utf-8")
print("Counter STA result:", root / "flow_status.json")
print("Optimization not run; use counter_solver with converted v4 timing data.")
sys.exit(1 if issues else 0)
PY
