"""Reject incomplete/violating reports from the fixed tiny OpenSTA flow."""

import argparse
import json
import math
import re
from pathlib import Path


NUMBER = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"


def check(reports, log, timing):
    text = log.read_text(encoding="utf-8")
    if (re.search(r"\b(?:Error|ERROR|Warning|WARNING):", text)
            or "Reports written to " not in text or "Complete pin graph written to " not in text):
        raise ValueError("OpenSTA log has errors/warnings or lacks completion markers")
    if (reports / "check_setup.rpt").read_text(encoding="utf-8").strip():
        raise ValueError("OpenSTA reports missing clocks/constraints or unconstrained endpoints")
    for name in ("pins", "vertices", "edges", "arc_delays", "slews", "boundary_paths", "boundary_edges", "manifest"):
        path = reports / "pin_graph" / (name + ".tsv")
        if not path.is_file() or path.stat().st_size == 0:
            raise ValueError("Incomplete pin graph: " + name)
    data = json.loads(timing.read_text(encoding="utf-8"))
    ports = {"INPUT": data["io_constraints"]["input"]["port"],
             "OUTPUT": data["io_constraints"]["output"]["port"]}
    expected = {(ports.get(e["source"], e["source"]), ports.get(e["target"], e["target"]))
                for e in data["edges"]}
    result = {"status": "reported_checks_passed"}
    for kind in ("setup", "hold"):
        text = (reports / (kind + ".rpt")).read_text(encoding="utf-8")
        blocks = re.split(r"(?m)^Startpoint:\s*", text)[1:]
        pairs, slacks = set(), []
        if not blocks or "(VIOLATED)" in text:
            raise ValueError("Missing or violating " + kind + " paths")
        for block in blocks:
            target = re.search(r"(?m)^Endpoint:\s+(\S+)", block)
            values = re.findall(r"(?m)^\s*(" + NUMBER + r")\s+slack \(MET\)\s*$", block)
            if not target or len(values) != 1 or not math.isfinite(float(values[0])) or float(values[0]) < 0:
                raise ValueError("Incomplete or invalid " + kind + " path")
            pairs.add((block.split()[0], target[1]))
            slacks.append(float(values[0]))
        if pairs != expected:
            raise ValueError(kind + " boundary coverage differs from the converted input")
        result[kind] = {"reported_paths": len(slacks), "worst_slack_ns": min(slacks)}
    text = (reports / "pulse_width.rpt").read_text(encoding="utf-8")
    rows = re.findall(r"(?m)^\s*(\S+)\s+\((high|low)\)\s+(" + NUMBER + r")\s+(" + NUMBER +
                      r")\s+(" + NUMBER + r")\s+\(MET\)\s*$", text)
    latch_pins = {node["instance"] + "/GATE" for node in data["nodes"]}
    if (not rows or len(rows) != len(re.findall(r"(?m)^\s*\S+\s+\((?:high|low)\)", text))
            or "(VIOLATED)" in text
            or any(row[0] not in latch_pins or not all(math.isfinite(float(v)) for v in row[2:])
                   or any(float(v) < 0 for v in row[2:]) for row in rows)):
        raise ValueError("Missing or violating pulse-width checks")
    result["pulse_width"] = {"reported_checks": len(rows), "pins": sorted({row[0] for row in rows}),
                             "worst_slack_ns": min(float(row[4]) for row in rows)}
    result["limitations"] = ["Checks cover reported paths and pulse checks; path sensitization and physical clock implementation are not verified.",
                             "A worst-only pulse summary does not separately list every latch."]
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reports", type=Path)
    parser.add_argument("log", type=Path)
    parser.add_argument("timing", type=Path)
    args = parser.parse_args()
    try:
        result = check(args.reports, args.log, args.timing)
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, f"Flow validation failed: {error}\n")
    print(json.dumps(result, indent=2, allow_nan=False))
