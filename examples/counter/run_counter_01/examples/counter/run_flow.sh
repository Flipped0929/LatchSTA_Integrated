#!/bin/sh
# shortcut: counter STA/export only; enable optimization after mixed-polarity/reset/feedback/IO model support.
set -eu
if [ "$#" -ne 1 ]; then
    echo "Usage: sh examples/counter/run_flow.sh /path/to/new_run_directory" >&2
    echo "This flow performs synthesis and STA; the current tiny optimizer does not support counter." >&2
    exit 2
fi
case_dir=$(cd -- "$(dirname -- "$0")" && pwd)
repo_dir=$(cd -- "$case_dir/../.." && pwd)
exporter=
for file in "$case_dir/export_pin_graph.tcl" "$case_dir/../tiny_3_latch_circuit/export_pin_graph.tcl" "$case_dir/../tiny_sky130/export_pin_graph.tcl"; do
    if [ -f "$file" ]; then exporter=$file; break; fi
done
[ -n "$exporter" ] || { echo "Missing shared export_pin_graph.tcl" >&2; exit 2; }
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
printf '%s\n' '{"status":"incomplete","optimization":{"status":"unsupported"}}' > "$run_dir/flow_status.json"
for file in counter.v counter.sdc export.ys latch_map.v run_sta.tcl run_flow.sh; do
    cp -- "$case_dir/$file" "$work_dir/"
done
cp -- "$exporter" "$work_dir/export_pin_graph.tcl"
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
unset COUNTER_REPORT_DIR MCR_SDC MCR_REPORT_DIR
echo '[1/3] Yosys: synthesize and map eight resettable latches'
yosys -l reports/yosys.log -s export.ys > "$run_dir/logs/yosys.log" 2>&1
echo '[2/3] OpenSTA: both clock phases, reset checks and full pin graph'
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
    "status": "unsupported",
    "reasons": ["mixed-polarity resettable latches", "feedback and multiple IOs are outside current MCR v3"]}}
try:
    log = (root / "logs/opensta.log").read_text(encoding="utf-8")
    if "Counter reports written to " not in log or "Complete pin graph written to " not in log:
        issues.append("OpenSTA/export completion markers missing")
    if re.search(r"(?m)^\s*(?:Error|ERROR|Warning|WARNING)(?:\s|:)", log):
        issues.append("OpenSTA reported errors or warnings; inspect logs/opensta.log")
    if (reports / "check_setup.rpt").read_text(encoding="utf-8").strip():
        issues.append("Structural/constraint checks require review")
    with (reports / "latches.tsv").open(encoding="utf-8", newline="") as stream:
        latches = list(csv.DictReader(stream, delimiter="\t"))
    if len(latches) != 8 or len({r["instance"] for r in latches}) != 8:
        issues.append("Expected eight unique latch records")
    for row in latches:
        for suffix in ("instance", "arrival", "load", "dq_min", "dq_max", "cq_min", "cq_max", "reset_q_min", "reset_q_max"):
            if not (reports / (row["instance"] + "_" + suffix + ".rpt")).is_file():
                issues.append("Missing latch report: " + row["instance"] + "_" + suffix)
    graph = reports / "pin_graph"
    for name in ("pins", "vertices", "edges", "arc_delays", "slews", "boundary_paths", "boundary_edges", "manifest"):
        path = graph / (name + ".tsv")
        if not path.is_file() or path.stat().st_size == 0:
            issues.append("Missing/empty graph table: " + name)
    for name in ("units", "clocks", "setup", "hold", "recovery", "removal", "pulse_width", "checks", "violations"):
        text = (reports / (name + ".rpt")).read_text(encoding="utf-8")
        met, violated = text.count("(MET)"), text.count("(VIOLATED)")
        if name in {"setup", "hold", "pulse_width", "recovery", "removal"} and not met + violated:
            issues.append("No reported checks: " + name)
        if violated:
            issues.append("Reported violations in " + name + ".rpt")
        if re.search(r"(?i)(?:^|\s)[+-]?(?:nan|inf(?:inity)?)(?=\s|$)", text):
            issues.append("Non-finite value in " + name + ".rpt")
        if name in {"setup", "hold", "pulse_width", "recovery", "removal", "checks"}:
            summary["timing"][name] = {"reported_met": met, "reported_violated": violated}
    summary["status"] = "reports_need_review" if issues else "reported_checks_passed"
except (OSError, ValueError, KeyError) as error:
    issues.append(str(error))
summary["issues"] = issues
summary["limitations"] = ["Finite report limits and summary checks are not exhaustive signoff.",
                          "Reset timing assumes the external release budgets in counter.sdc; no reset functional simulation was run.",
                          "No solver input or candidate SDC is generated; graph boundary edges are structural GBA results."]
(root / "flow_status.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n", encoding="utf-8")
print("Counter STA result:", root / "flow_status.json")
print("Optimization unsupported for this circuit by the current tiny MCR model.")
sys.exit(1 if issues else 0)
PY
