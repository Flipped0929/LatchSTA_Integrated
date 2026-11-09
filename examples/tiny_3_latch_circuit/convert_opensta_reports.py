"""Convert this example's OpenSTA reports to combinational .blif.out and latch JSON."""

import argparse
import hashlib
import json
import math
import os
import re
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PDK = ROOT.parents[1] / "sky130_pdk"
sys.path.insert(0, str(PDK))
from extract_latch_timing import CELL, COMMON, extract_pulse_width

NUMBER = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
ROW = re.compile(r"^\s*(.*?)\s+([\^v])\s+(\S+)\s+\(([^()]+)\)\s*$")


def finite(text):
    value = float(text)
    if not math.isfinite(value):
        raise ValueError(f"Non-finite value: {text}")
    return value


def required(pattern, text, context):
    match = re.search(pattern, text, re.M)
    if match is None:
        raise ValueError(f"Missing {context}")
    return match


def parse_paths(text, analysis, instances):
    # shortcut: OpenSTA 3.1.0 text layout; use graph/JSON export for arbitrary layouts or full coverage.
    blocks = re.split(r"(?m)^Startpoint:\s*", text)[1:]
    if not blocks:
        raise ValueError(f"No {analysis} timing paths")
    paths = []
    for block in blocks:
        source = block.splitlines()[0].split()[0]
        target = required(r"^Endpoint:\s+(\S+)", block, "endpoint").group(1)
        kind = required(r"^Path Type:\s+(\S+)", block, "path type").group(1)
        if kind != analysis:
            raise ValueError(f"Expected {analysis} path, found {kind}")
        source_latch, target_latch = source in instances, target in instances
        source_description = block.splitlines()[0]
        target_description = required(r"^Endpoint:.*$", block, "endpoint description").group()
        for name, is_latch, description, port_kind in (
            (source, source_latch, source_description, "input port"),
            (target, target_latch, target_description, "output port"),
        ):
            expected = "positive level-sensitive latch" if is_latch else port_kind
            if expected not in description:
                raise ValueError(f"Unsupported or unlisted endpoint: {name}")
        if "data arrival time" not in block:
            raise ValueError(f"Missing data arrival for {source}->{target}")
        rows = []
        for line in block.split("data arrival time", 1)[0].splitlines():
            match = ROW.match(line)
            if match:
                numbers = [finite(v) for v in match.group(1).split()]
                if len(numbers) not in (3, 4):
                    raise ValueError("Expected report fields {slew capacitance input_pin net}")
                rows.append({"pin": match.group(3), "transition": match.group(2),
                             "cell": match.group(4), "increment_ns": numbers[-2],
                             "arrival_ns": numbers[-1]})
        start_pin = source + "/Q" if source_latch else source
        end_pin = target + "/D" if target_latch else target
        starts = [i for i, row in enumerate(rows) if row["pin"] == start_pin]
        stops = [i for i, row in enumerate(rows) if row["pin"] == end_pin]
        if len(starts) != 1 or len(stops) != 1 or stops[0] < starts[0]:
            raise ValueError(f"Cannot isolate combinational segment {start_pin}->{end_pin}")
        segment = rows[starts[0]:stops[0] + 1]
        if any(row["pin"].rsplit("/", 1)[0] in instances for row in segment[1:-1]):
            raise ValueError("Reported segment crosses an intermediate latch")
        delay = sum(row["increment_ns"] for row in segment[1:])
        if delay < 0 or any(row["increment_ns"] < 0 for row in segment[1:]):
            raise ValueError("Negative combinational delay")
        tolerance = max(1e-5, len(segment) * 1e-6)
        if abs(delay - (segment[-1]["arrival_ns"] - segment[0]["arrival_ns"])) > tolerance:
            raise ValueError(f"Increment/arrival mismatch for {start_pin}->{end_pin}")
        setup = hold = None
        if target_latch:
            if analysis == "max":
                match = re.search(r"^library setup time\s+(" + NUMBER + r")", block, re.M)
                if match is None:
                    match = required(r"^\s*(" + NUMBER + r")\s+(?:" + NUMBER +
                                     r"\s+)?library setup time", block, "library setup contribution")
                setup = -finite(match.group(1))
            else:
                hold = finite(required(r"^\s*(" + NUMBER + r")\s+(?:" + NUMBER +
                                       r"\s+)?library hold time", block, "library hold time").group(1))
        external = [{"kind": m.group(2), "signed_contribution_ns": finite(m.group(1))}
                    for m in re.finditer(r"^\s*(" + NUMBER + r")\s+" + NUMBER +
                                         r"\s+(?:[\^v]\s+)?(input|output) external delay", block, re.M)]
        paths.append({"source": source if source_latch else "INPUT",
                      "target": target if target_latch else "OUTPUT",
                      "source_pin": start_pin, "target_pin": end_pin,
                      "analysis": analysis, "transition": segment[0]["transition"],
                      "delay_ns": round(delay, 6), "pins": [row["pin"] for row in segment],
                      "setup_ns": setup, "hold_ns": hold,
                      "external_delay_contributions": external})
    return paths


def parse_arc(text, kind, library, cell):
    if required(r"^Library:\s+(\S+)", text, "arc library").group(1) != library:
        raise ValueError("Arc library does not match instance")
    if required(r"^Cell:\s+(\S+)", text, "arc cell").group(1) != cell:
        raise ValueError("Arc cell does not match instance")
    related = "D" if kind.startswith("dq") else "GATE"
    chunks = list(re.finditer(r"^" + related + r"\s+([\^v])\s+->\s+Q\s+([\^v])\s*$", text, re.M))
    values = {}
    for i, match in enumerate(chunks):
        section = text[match.end():chunks[i + 1].start() if i + 1 < len(chunks) else len(text)]
        delays = re.findall(r"^Delay\s*=\s*(\S+)\s*$", section, re.M)
        if len(delays) != 1 or match.group(2) in values:
            raise ValueError(f"Ambiguous {kind} arc")
        if (related == "D" and match.group(1) != match.group(2)) or (related == "GATE" and match.group(1) != "^"):
            raise ValueError(f"Unsupported {kind} polarity")
        delay = finite(delays[0])
        if delay < 0:
            raise ValueError(f"Negative {kind} delay")
        values[match.group(2)] = delay
    if set(values) != {"^", "v"}:
        raise ValueError(f"Missing rise/fall {kind} delays")
    return {"rise_ns": values["^"], "fall_ns": values["v"]}


def parse_sdc(text, clock):
    """Read only this example's explicit, single-clock SDC subset; never execute Tcl."""
    entries = {}
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        match = re.fullmatch(r"create_clock -name (\w+) -period (" + NUMBER +
                             r") -waveform \{(" + NUMBER + r") (" + NUMBER + r")\} \[get_ports (\w+)\]", line)
        if match:
            key = "clock"
            value = (match[1], *(finite(match[i]) for i in (2, 3, 4)), match[5])
        else:
            match = re.fullmatch(r"set_(input|output)_delay -clock (\w+) -(min|max) (" + NUMBER + r") \[get_ports (\w+)\]", line)
            if match:
                key = match[1] + "_" + match[3]
                value = (match[2], finite(match[4]), match[5])
            else:
                match = re.fullmatch(r"set_clock_uncertainty -(setup|hold) (" + NUMBER + r") \[get_clocks (\w+)\]", line)
                if match:
                    key, value = "uncertainty_" + match[1], (match[3], finite(match[2]))
                else:
                    match = re.fullmatch(r"(set_clock_transition|set_input_transition|set_load) (" + NUMBER + r") \[get_(clocks|ports) (\w+)\]", line)
                    if not match:
                        raise ValueError(f"Unsupported SDC command: {line}")
                    key, value = match[1], (match[3], finite(match[2]), match[4])
        if key in entries:
            raise ValueError(f"Duplicate SDC entry: {key}")
        entries[key] = value
    expected = {"clock", "input_min", "input_max", "output_min", "output_max",
                "uncertainty_setup", "uncertainty_hold", "set_clock_transition", "set_input_transition", "set_load"}
    if set(entries) != expected:
        raise ValueError("Missing explicit clock, IO, uncertainty or operating-condition SDC entries")
    name, period, rise, fall, clock_port = entries["clock"]
    if name != clock["name"] or any(abs(a - b) > 0.005 for a, b in zip(
            (period, rise, fall), (clock["period_ns"], clock["rise_ns"], clock["fall_ns"]))):
        raise ValueError("SDC clock does not match the STA clock report")
    if period <= 0 or abs(fall - period) > 1e-9 or not 0.5 <= rise / period < 1.0:
        raise ValueError("IO model requires a closing edge at T and high duty in (0, 0.5]")
    ports = {}
    for direction in ("input", "output"):
        lo, hi = entries[direction + "_min"], entries[direction + "_max"]
        if lo[0] != name or hi[0] != name or lo[2] != hi[2] or lo[1] > hi[1] or lo[2] == clock_port:
            raise ValueError(f"Invalid {direction} SDC delay range, clock or port")
        ports[direction] = {"port": lo[2], "min_delay_ns": lo[1], "max_delay_ns": hi[1]}
    if ports["input"]["port"] == ports["output"]["port"]:
        raise ValueError("Input and output ports must be distinct")
    for label, target_kind, target in (("set_clock_transition", "clocks", name),
                                      ("set_input_transition", "ports", ports["input"]["port"]),
                                      ("set_load", "ports", ports["output"]["port"])):
        kind, value, obj = entries[label]
        if kind != target_kind or obj != target or value < 0:
            raise ValueError(f"Invalid SDC operating condition: {label}")
    for check in ("setup", "hold"):
        ref, value = entries["uncertainty_" + check]
        if ref != name or value < 0:
            raise ValueError("Invalid SDC clock uncertainty")
    io = {"model": "single_clock_rise_dag_v1", "clock": name, **ports,
            "setup_uncertainty_ns": entries["uncertainty_setup"][1],
            "hold_uncertainty_ns": entries["uncertainty_hold"][1],
            "setup_capture_cycles": 1, "hold_capture_cycles": 0, "path_cycle_shift": 0}
    conditions = {"clock_port": clock_port, "clock_transition_ns": entries["set_clock_transition"][1],
                  "input_transition_ns": entries["set_input_transition"][1], "output_load_pf": entries["set_load"][1]}
    return io, conditions


def convert(reports, pdk=PDK):
    sources = {}

    def read(name):
        path = reports / name
        raw = path.read_bytes()
        sources[name] = hashlib.sha256(raw).hexdigest()
        return raw.decode("utf-8-sig")

    units = read("units.rpt")
    required(r"^\s*time\s+1ns\s*$", units, "1ns time unit")
    required(r"^\s*capacitance\s+1pF\s*$", units, "1pF capacitance unit")
    if read("check_setup.rpt").strip():
        raise ValueError("Resolve check_setup warnings before conversion")
    log = read("opensta_rerun.log")
    if "Reports written to " not in log or re.search(r"^.*\b(?:Error|ERROR)\b", log, re.M):
        raise ValueError("OpenSTA run did not complete successfully")
    clocks = re.findall(r"^\s*(\S+)\s+(" + NUMBER + r")\s+(" + NUMBER + r")\s+(" + NUMBER + r")\s*$",
                        read("clocks.rpt"), re.M)
    if len(clocks) != 1:
        raise ValueError("Expected one clock")
    clock_name, period, rise, fall = clocks[0]
    clock = dict(zip(("period_ns", "rise_ns", "fall_ns"), map(finite, (period, rise, fall))))
    if clock["period_ns"] <= 0:
        raise ValueError("Clock period must be positive")
    clock["name"] = clock_name
    instances = {}
    for path in sorted(reports.glob("*_instance.rpt")):
        text = read(path.name)
        name = required(r"^Instance\s+(\S+)", text, "instance name").group(1)
        if name in {"INPUT", "OUTPUT"} or "/" in name or name in instances or path.name != name + "_instance.rpt":
            raise ValueError(f"Unsupported or duplicate instance name: {name}")
        cell = required(r"^\s*Cell:\s+(\S+)", text, "instance cell").group(1)
        library = required(r"^\s*Library:\s+(\S+)", text, "instance library").group(1)
        for pin, direction in (("D", "input"), ("GATE", "input"), ("Q", "output")):
            required(r"^\s*" + pin + r"\s+" + direction + r"\s+", text, pin + " pin")
        instances[name] = {"cell": cell, "library": library}
    if not instances:
        raise ValueError("No latch instance reports")
    setup_text, hold_text = read("setup.rpt"), read("hold.rpt")
    paths = parse_paths(setup_text, "max", instances) + parse_paths(hold_text, "min", instances)
    io, conditions = parse_sdc(read("constraints.sdc"), clock)
    for path in paths:
        if path["source"] == "INPUT" and path["source_pin"] != io["input"]["port"]:
            raise ValueError("STA input port does not match SDC")
        if path["target"] == "OUTPUT" and path["target_pin"] != io["output"]["port"]:
            raise ValueError("STA output port does not match SDC")
        for direction, active in (("input", path["source"] == "INPUT"), ("output", path["target"] == "OUTPUT")):
            contributions = [item["signed_contribution_ns"] for item in path["external_delay_contributions"] if item["kind"] == direction]
            if active:
                key = "max_delay_ns" if path["analysis"] == "max" else "min_delay_ns"
                expected = io[direction][key] * (1 if direction == "input" else -1)
                if len(contributions) != 1 or abs(contributions[0] - expected) > 1e-6:
                    raise ValueError(f"STA/SDC {direction} delay mismatch")
    for check, text in (("setup", setup_text), ("hold", hold_text)):
        uncertainty = io[check + "_uncertainty_ns"]
        values = re.findall(r"^\s*(" + NUMBER + r")\s+(?:" + NUMBER + r"\s+)?clock uncertainty\s*$", text, re.M)
        values += re.findall(r"^\s*clock uncertainty\s+(" + NUMBER + r")\s*$", text, re.M)
        if (uncertainty and not values) or any(abs(abs(finite(v)) - uncertainty) > 1e-6 for v in values):
            raise ValueError("STA/SDC uncertainty mismatch")
    pulse_sources = []
    library_data = []
    for filename in (COMMON, CELL):
        raw = (pdk / filename).read_bytes()
        pulse_sources.append({"file": filename, "sha256": hashlib.sha256(raw).hexdigest()})
        library_data.append(json.loads(raw.decode("utf-8-sig")))
    common, cell_data = library_data
    edges = []
    for source, target in sorted({(p["source"], p["target"]) for p in paths}):
        candidates = {a: [p for p in paths if (p["source"], p["target"], p["analysis"]) == (source, target, a)]
                      for a in ("min", "max")}
        if not all(candidates.values()):
            raise ValueError(f"Missing min or max path for {source}->{target}")
        earliest = min(candidates["min"], key=lambda p: p["delay_ns"])
        latest = max(candidates["max"], key=lambda p: p["delay_ns"])
        if earliest["delay_ns"] > latest["delay_ns"]:
            raise ValueError(f"min exceeds max for {source}->{target}")
        edges.append({"source": source, "target": target, "min_delay_ns": earliest["delay_ns"],
                      "max_delay_ns": latest["delay_ns"], "min_witness": earliest, "max_witness": latest})
    incoming = {name: 0 for name in ["INPUT", "OUTPUT", *instances]}
    outgoing = {name: [] for name in incoming}
    for edge in edges:
        outgoing[edge["source"]].append(edge["target"])
        incoming[edge["target"]] += 1
    if (incoming["INPUT"] or outgoing["OUTPUT"] or not outgoing["INPUT"] or not incoming["OUTPUT"] or
            any(not incoming[name] or not outgoing[name] for name in instances)):
        raise ValueError("IO conversion requires every latch on an input-to-output path")
    ready = [name for name, count in incoming.items() if count == 0]
    visited = 0
    while ready:
        name = ready.pop()
        visited += 1
        for target in outgoing[name]:
            incoming[target] -= 1
            if incoming[target] == 0:
                ready.append(target)
    if visited != len(incoming):
        raise ValueError("IO conversion requires an acyclic same-transaction graph")
    nodes = []
    for name, instance in instances.items():
        setup = [p["setup_ns"] for p in paths if p["target"] == name and p["setup_ns"] is not None]
        hold = [p["hold_ns"] for p in paths if p["target"] == name and p["hold_ns"] is not None]
        if not setup or not hold:
            raise ValueError(f"Missing setup/hold checks for {name}")
        arcs = {kind: parse_arc(read(name + "_" + kind + ".rpt"), kind, instance["library"], instance["cell"])
                for kind in ("dq_min", "dq_max", "cq_min", "cq_max")}
        timing = {"tsu": max(setup), "thd": max(hold), "tdqMin": min(arcs["dq_min"].values()),
                  "tdqMax": max(arcs["dq_max"].values()), "tcqMin": min(arcs["cq_min"].values()),
                  "tcqMax": max(arcs["cq_max"].values())}
        if timing["tdqMin"] > timing["tdqMax"] or timing["tcqMin"] > timing["tcqMax"]:
            raise ValueError(f"Invalid propagation envelope for {name}")
        if CELL != instance["cell"] + "__tt_025C_1v80.lib.json" or instance["library"] != "sky130_fd_sc_hd__tt_025C_1v80":
            raise ValueError("Pulse-width extraction only supports the supplied SKY130 TT latch")
        slews = {finite(value) for value in re.findall(
            r"^\s*(" + NUMBER + r")\s+" + NUMBER + r"\s+" + NUMBER +
            r"\s+[\^v]\s+" + re.escape(name) + r"/GATE\s+\(", setup_text + "\n" + hold_text, re.M)}
        if len(slews) != 1:
            raise ValueError(f"Expected one fixed clock slew at {name}/GATE")
        slew = slews.pop()
        if abs(slew - conditions["clock_transition_ns"]) > 1e-6:
            raise ValueError("STA/SDC clock transition mismatch")
        try:
            checks = extract_pulse_width(common, cell_data, slew)
        except (KeyError, TypeError) as error:
            raise ValueError(f"Invalid pulse-width library data for {name}") from error
        nodes.append({"instance": name, **instance, "parameters_ns": timing, "reported_arcs": arcs,
                      "clock_checks_ns": checks, "clock_checks_conditions": {"clock_slew_ns": slew}})
    pulse_rows = re.findall(r"^\s*(\S+)/GATE\s+\((high|low)\)\s+(" + NUMBER + r")\s+",
                            read("pulse_width.rpt"), re.M)
    if not pulse_rows:
        raise ValueError("No pulse-width report checks for library cross-check")
    by_name = {node["instance"]: node for node in nodes}
    for name, level, value in pulse_rows:
        if name not in by_name:
            raise ValueError(f"Unknown pulse-width report instance: {name}")
        extracted = by_name[name]["clock_checks_ns"]["min_pulse_width_" + level]
        if extracted is None or abs(extracted - finite(value)) > 1e-6:
            raise ValueError(f"Library/report pulse-width mismatch for {name}/GATE ({level})")
    return {"schema_version": 3, "units": {"time": "ns", "capacitance": "pF"}, "clock": clock,
            "io_constraints": io, "sta_conditions": conditions,
            "nodes": nodes, "edges": edges, "paths": paths, "source_sha256": sources,
            "pulse_width_sources": pulse_sources,
            "semantics": "Edges contain only combinational delay. IO delays are excluded; signed report contributions and original port names are retained in paths. Setup contributions are negated; hold signs are preserved.",
            "limitations": ["Only paths present in the reports are exported; report truncation can omit connectivity or extrema.",
                            "Single clock, flat positive-level D/GATE/Q latches and the supplied OpenSTA text layout only.",
                            "Values are rounded envelopes at reported operating points, not a multi-PVT envelope.",
                            "Pulse widths use supplied TT Liberty JSON tables at a fixed reported ideal-clock slew; null means no check in that arc.",
                            "IO supports one input/output, ideal related rising-edge clocks and same-transaction acyclic paths only; other SDC commands are rejected.",
                            "Hold checks use a conservative opening-edge lower bound for latch-launched paths; this may reject feasible schedules."]}


def write_outputs(data, output, json_output, reports, pdk=PDK):
    if not output.name.endswith(".blif.out") or json_output.suffix != ".json":
        raise ValueError("Outputs must be .blif.out and .json files")
    inputs = {Path(__file__).resolve()} | {p.resolve() for p in reports.iterdir() if p.is_file()}
    inputs |= {(pdk / filename).resolve() for filename in (COMMON, CELL, "extract_latch_timing.py")}
    if output.resolve() == json_output.resolve() or any(p.resolve() in inputs for p in (output, json_output)):
        raise ValueError("Output must not overwrite an input file")
    lines = ["Network " + output.name.removesuffix(".blif.out"), "latch latch max_delay min_delay",
             "INPUT latch max_delay min_delay", "latch OUTPUT max_delay min_delay", "# unit ns; combinational delays only"]
    lines += [f"{e['source']} {e['target']} {e['max_delay_ns']:.6f} {e['min_delay_ns']:.6f}" for e in data["edges"]]
    contents = ((output, "\n".join(lines) + "\n"),
                (json_output, json.dumps(data, indent=2, allow_nan=False) + "\n"))
    for path, content in contents:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n", dir=path.parent,
                                             prefix=path.name + ".", delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(content)
            os.replace(temporary, path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reports", type=Path, default=ROOT / "reports")
    parser.add_argument("--pdk", type=Path, default=PDK, help="Directory containing the supplied SKY130 Liberty JSON tables")
    parser.add_argument("--output", type=Path, default=ROOT / "tiny.blif.out")
    parser.add_argument("--json-output", type=Path, default=ROOT / "latch_timing.json")
    args = parser.parse_args()
    try:
        data = convert(args.reports, args.pdk)
        write_outputs(data, args.output, args.json_output, args.reports, args.pdk)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(f"Saved {len(data['edges'])} edges: {args.output}")
    print(f"Saved {len(data['nodes'])} latch parameter sets: {args.json_output}")


if __name__ == "__main__":
    main()
