"""Convert counter OpenSTA reports to a mixed-polarity timing interchange, not legacy v3."""

import argparse
import csv
import hashlib
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
NUMBER = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
ROW = re.compile(r"^\s*(.*?)\s+([\^v])\s+(\S+)\s+\(([^()]+)\)\s*$")
LIBRARY = "sky130_fd_sc_hd__tt_025C_1v80"
CELLS = {"sky130_fd_sc_hd__dlxtn_1": ("GATE_N", "negative"),
         "sky130_fd_sc_hd__dlxtp_1": ("GATE", "positive")}
INPUTS = {"en", "rst_n"}
OUTPUTS = {f"count[{i}]" for i in range(4)}
MODEL = "counter_mixed_polarity_feedback_v1"


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


def parse_sdc(text):
    clock = None
    io = {"inputs": {}, "outputs": {}}
    conditions = {}
    uncertainty = {}
    latencies = set()
    def unique(mapping, key, value):
        if key in mapping:
            raise ValueError(f"Duplicate SDC field: {key}")
        mapping[key] = value
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or line == "current_design counter":
            continue
        m = re.fullmatch(r"create_clock -name clk -period ("+NUMBER+r") -waveform \{("+NUMBER+r") ("+NUMBER+r")\} \[get_ports \{clk\}\]", line)
        if m:
            if clock is not None:
                raise ValueError("Duplicate clock")
            period, rise, fall = map(finite, m.groups())
            if period <= 0 or abs(rise-period/2) > 1e-6 or abs(fall-period) > 1e-6:
                raise ValueError("Require the counter's 50% clock with waveform {T/2 T}")
            clock = {"name": "clk", "port": "clk", "period_ns": period, "rise_ns": rise, "fall_ns": fall}
            continue
        m = re.fullmatch(r"set_(input|output)_delay ("+NUMBER+r") -clock \[get_clocks \{clk\}\] -(min|max) -add_delay \[get_ports \{([^{}]+)\}\]", line)
        if m:
            direction, value, kind, port = m.groups()
            ports = INPUTS if direction == "input" else OUTPUTS
            if port not in ports:
                raise ValueError(f"Unexpected IO port: {port}")
            unique(io[direction+"s"].setdefault(port, {}), kind+"_delay_ns", finite(value))
            continue
        m = re.fullmatch(r"set_clock_latency (-source )?("+NUMBER+r") \[get_clocks \{clk\}\]", line)
        if m:
            kind = "source" if m[1] else "network"
            if finite(m[2]) != 0 or kind in latencies:
                raise ValueError("Require explicit zero source and network clock latency")
            latencies.add(kind)
            continue
        m = re.fullmatch(r"set_clock_uncertainty (?:(-setup|-hold) )?("+NUMBER+r") clk", line)
        if m:
            for kind in ([m[1][1:]] if m[1] else ["setup", "hold"]):
                unique(uncertainty, kind+"_ns", finite(m[2]))
            continue
        m = re.fullmatch(r"set_clock_transition ("+NUMBER+r") \[get_clocks \{clk\}\]", line)
        if m:
            unique(conditions, "clock_transition_ns", finite(m[1]))
            continue
        m = re.fullmatch(r"set_input_transition ("+NUMBER+r") \[get_ports \{([^{}]+)\}\]", line)
        if m and m[2] in INPUTS:
            unique(io["inputs"].setdefault(m[2], {}), "transition_ns", finite(m[1]))
            continue
        m = re.fullmatch(r"set_load -pin_load ("+NUMBER+r") \[get_ports \{([^{}]+)\}\]", line)
        if m and m[2] in OUTPUTS:
            unique(io["outputs"].setdefault(m[2], {}), "load_pf", finite(m[1]))
            continue
        raise ValueError(f"Unsupported effective SDC command: {line}")
    if clock is None or latencies != {"source", "network"} or set(uncertainty) != {"setup_ns", "hold_ns"} or not conditions:
        raise ValueError("Incomplete clock conditions")
    for direction, ports, extra in [("inputs", INPUTS, "transition_ns"), ("outputs", OUTPUTS, "load_pf")]:
        if set(io[direction]) != ports:
            raise ValueError(f"Incomplete {direction} coverage")
        for entry in io[direction].values():
            if set(entry) != {"min_delay_ns", "max_delay_ns", extra} or entry["min_delay_ns"] > entry["max_delay_ns"] or entry[extra] < 0:
                raise ValueError("Invalid IO budget or condition")
    if conditions["clock_transition_ns"] < 0 or any(v < 0 for v in uncertainty.values()):
        raise ValueError("Negative slew or uncertainty")
    io["uncertainty"] = uncertainty
    return clock, io, conditions


def parse_paths(text, analysis, nodes):
    paths = []
    for block in re.split(r"(?m)^Startpoint:\s*", text)[1:]:
        source = block.split()[0]
        target = required(r"^Endpoint:\s+(\S+)", block, "endpoint")[1]
        if required(r"^Path Type:\s+(\S+)", block, "path type")[1] != analysis:
            raise ValueError("Wrong path analysis")
        for name, description, ports in [(source, block.splitlines()[0], INPUTS),
                (target, required(r"^Endpoint:.*$", block, "endpoint description")[0], OUTPUTS)]:
            if name in nodes:
                expected = nodes[name]["polarity"]+" level-sensitive latch"
            elif name in ports:
                expected = "input port" if ports is INPUTS else "output port"
            else:
                raise ValueError(f"Unknown endpoint: {name}")
            if expected not in description:
                raise ValueError(f"Wrong endpoint polarity/type: {name}")
        arrival_section = block.split("data arrival time", 1)
        if len(arrival_section) != 2:
            raise ValueError("Missing data arrival section")
        rows = []
        for line in arrival_section[0].splitlines():
            m = ROW.match(line)
            if m:
                numbers = list(map(finite, m[1].split()))
                if len(numbers) not in {3, 4}:
                    raise ValueError("Unsupported STA row layout")
                rows.append({"pin": m[3], "transition": m[2], "cell": m[4], "delay_ns": numbers[-2], "arrival_ns": numbers[-1]})
        first = source+"/Q" if source in nodes else source
        last = target+"/D" if target in nodes else target
        starts = [i for i, row in enumerate(rows) if row["pin"] == first]
        stops = [i for i, row in enumerate(rows) if row["pin"] == last]
        if len(starts) != 1 or len(stops) != 1 or starts[0] > stops[0]:
            raise ValueError(f"Cannot isolate {first}->{last}")
        segment = rows[starts[0]:stops[0]+1]
        if any(row["pin"].split("/")[0] in nodes for row in segment[1:-1]):
            raise ValueError("Path crosses an intermediate latch")
        delay = sum(row["delay_ns"] for row in segment[1:])
        if any(row["delay_ns"] < 0 for row in segment[1:]) or abs(delay-segment[-1]["arrival_ns"]+segment[0]["arrival_ns"]) > max(1e-5, len(segment)*1e-6):
            raise ValueError("Invalid combinational delay or arrival reconciliation")
        checks = {}
        if target in nodes:
            if analysis == "max":
                m = re.search(r"^library setup time\s+("+NUMBER+r")", block, re.M)
                if m is None:
                    m = required(r"^\s*("+NUMBER+r")\s+"+NUMBER+r"\s+library setup time", block, "setup time")
                checks["setup_ns"] = -finite(m[1])
            else:
                checks["hold_ns"] = finite(required(r"^\s*("+NUMBER+r")\s+"+NUMBER+r"\s+library hold time", block, "hold time")[1])
        external = [{"kind": m[2], "contribution_ns": finite(m[1])} for m in re.finditer(
            r"^\s*("+NUMBER+r")\s+"+NUMBER+r"\s+(?:[\^v]\s+)?(input|output) external delay", block, re.M)]
        paths.append({"source": source, "target": target, "analysis": analysis,
                      "source_transition": segment[0]["transition"], "target_transition": segment[-1]["transition"],
                      "delay_ns": round(delay, 6), "pins": [row["pin"] for row in segment],
                      "checks": checks, "external_delays": external})
    if not paths:
        raise ValueError(f"No {analysis} paths")
    return paths


def parse_arc(text, kind, node, clock_slew):
    for label, expected in [("Library", LIBRARY), ("Cell", node["cell"])]:
        if required(r"^"+label+r":\s+(\S+)", text, label)[1] != expected:
            raise ValueError(f"Wrong arc {label}")
    related = "D" if kind.startswith("dq") else node["gate_pin"].split("/")[1]
    chunks = list(re.finditer(r"^"+related+r"\s+([\^v]) -> Q ([\^v])\s*$", text, re.M))
    values = {}
    for i, m in enumerate(chunks):
        section = text[m.end():chunks[i+1].start() if i+1 < len(chunks) else len(text)]
        if related != "D":
            slews = {finite(v) for v in re.findall(r"input_net_transition = ("+NUMBER+r")", section)}
            if slews != {clock_slew}:
                raise ValueError("Arc/SDC clock slew mismatch")
        delays = re.findall(r"^Delay = ("+NUMBER+r")\s*$", section, re.M)
        opening = "v" if node["polarity"] == "negative" else "^"
        if len(delays) != 1 or m[2] in values or m[1] != (m[2] if related == "D" else opening):
            raise ValueError(f"Ambiguous arc or wrong opening polarity: {kind}")
        values[m[2]] = finite(delays[0])
    if set(values) != {"^", "v"} or min(values.values()) < 0:
        raise ValueError(f"Missing or negative {kind} rise/fall delays")
    return values


def structural_pairs(text, nodes, paths):
    if not re.search(r'assign\s+count\s*=\s*slave\s*;', text):
        raise ValueError("Missing count/slave output alias")
    connections = {}
    for cell, name, body in re.findall(r'sky130_fd_sc_hd__(\w+)\s+(\w+)\s*\((.*?)\);', text, re.S):
        connections[name] = ("sky130_fd_sc_hd__"+cell, dict(re.findall(r'\.(\w+)\(([^)]+)\)', body)))
    if len(connections) != 18 or set(nodes) != {n for n,(cell,pins) in connections.items() if cell in CELLS}:
        raise ValueError("Expected the current 18-cell counter netlist")
    pin_nets = {name+"/"+pin:net for name,(_,pins) in connections.items() for pin,net in pins.items()}
    pin_nets.update({port:port for port in INPUTS})
    pin_nets.update({f"count[{i}]":f"slave[{i}]" for i in range(4)})
    for path in paths:
        for first,last in zip(path["pins"],path["pins"][1:]):
            if first not in pin_nets or last not in pin_nets:
                raise ValueError("Unknown report pin in netlist")
            if pin_nets[first] == pin_nets[last]:
                continue
            if "/" not in first or "/" not in last:
                raise ValueError("Report/netlist wire mismatch")
            source,source_pin = first.split("/")
            target,target_pin = last.split("/")
            if source != target or source in nodes or source_pin in {"X","Y"} or target_pin not in {"X","Y"}:
                raise ValueError("Report/netlist wire or combinational arc mismatch")
    targets = {}
    for name,node in nodes.items():
        cell, pins = connections[name]
        if cell != node["cell"] or pins[node["gate_pin"].split("/")[1]] != "clk":
            raise ValueError("Netlist/report latch mismatch")
        targets.setdefault(pins["D"], set()).add(name)
    for i in range(4):
        targets.setdefault(f"slave[{i}]", set()).add(f"count[{i}]")
    combinational = []
    for name,(cell,pins) in connections.items():
        if name in nodes:
            continue
        output = "X" if "X" in pins else "Y"
        combinational.append((set(v for p,v in pins.items() if p != output), pins[output]))
    pairs = set()
    sources = {p:p for p in INPUTS}
    sources.update({n:connections[n][1]["Q"] for n in nodes})
    for source, net in sources.items():
        pending = [net]
        visited = set()
        while pending:
            net = pending.pop()
            if net in visited:
                continue
            visited.add(net)
            pairs.update((source,target) for target in targets.get(net, set()))
            pending.extend(output for inputs,output in combinational if net in inputs)
    return pairs


def convert(reports, netlist=ROOT / "counter_mapped.v"):
    sources = {}
    def read(name):
        raw = (reports/name).read_bytes()
        sources[name] = hashlib.sha256(raw).hexdigest()
        return raw.decode("utf-8-sig")
    units = read("units.rpt")
    required(r"^\s*time 1ns\s*$", units, "ns units")
    required(r"^\s*capacitance 1pF\s*$", units, "pF units")
    if read("check_setup.rpt").strip():
        raise ValueError("Resolve check_setup warnings first")
    clock, io, conditions = parse_sdc(read("effective.sdc"))
    clock_row = required(r"^\s*clk\s+("+NUMBER+r")\s+("+NUMBER+r")\s+("+NUMBER+r")\s*$", read("clocks.rpt"), "clock report")
    if any(abs(finite(v)-clock[key]) > .005 for v,key in zip(clock_row.groups(),["period_ns","rise_ns","fall_ns"])):
        raise ValueError("SDC/report clock mismatch")
    nodes = {}
    table = csv.DictReader(read("latches.tsv").splitlines(), delimiter="\t", strict=True)
    if table.fieldnames != ["instance","cell","gate_pin","data_pin","output_pin"]:
        raise ValueError("Unexpected latches.tsv columns")
    for row in table:
        name,cell = row["instance"],row["cell"]
        if cell not in CELLS or name in nodes or not re.fullmatch(r"_[0-9]+_",name):
            raise ValueError("Unsupported or duplicate latch")
        gate,polarity = CELLS[cell]
        if [row[k] for k in ["gate_pin","data_pin","output_pin"]] != [name+"/"+gate,name+"/D",name+"/Q"]:
            raise ValueError("Inconsistent latch pin mapping")
        instance = read(name+"_instance.rpt")
        for label,value in [("Instance",name),("Cell:",cell),("Library:",LIBRARY)]:
            required(r"^\s*"+label+r"\s+"+re.escape(value)+r"\s*$",instance,label)
        nodes[name] = {**row,"polarity":polarity,"library":LIBRARY,
                       "window_fraction": [0.0,.5] if polarity=="negative" else [.5,1.0]}
    if len(nodes)!=8 or sum(n["polarity"]=="negative" for n in nodes.values())!=4:
        raise ValueError("Require four master and four slave latches")
    setup_text,hold_text = read("setup.rpt"),read("hold.rpt")
    paths = parse_paths(setup_text,"max",nodes)+parse_paths(hold_text,"min",nodes)
    for kind,text in [("setup",setup_text),("hold",hold_text)]:
        values = re.findall(r"^\s*("+NUMBER+r")\s+"+NUMBER+r"\s+clock uncertainty\s*$",text,re.M)
        if not values or any(abs(abs(finite(v))-io["uncertainty"][kind+"_ns"])>1e-6 for v in values):
            raise ValueError("SDC/report clock uncertainty mismatch")
    nettext = netlist.read_text(encoding="utf-8-sig")
    sources["netlist:"+netlist.name] = hashlib.sha256(netlist.read_bytes()).hexdigest()
    expected = structural_pairs(nettext,nodes,paths)
    edges = []
    for analysis in ["max","min"]:
        observed = {(p["source"],p["target"]) for p in paths if p["analysis"]==analysis}
        if observed != expected:
            raise ValueError(f"{analysis} boundary pair coverage mismatch: missing={expected-observed}, extra={observed-expected}")
    for source,target in sorted(expected):
        selected = [p for p in paths if (p["source"],p["target"])==(source,target)]
        values = {}
        for analysis in ["min","max"]:
            group = [p for p in selected if p["analysis"]==analysis]
            if any({p[key] for p in group}!={"^","v"} for key in ["source_transition","target_transition"]):
                raise ValueError(f"Incomplete transition coverage: {source}->{target}")
            values[analysis] = (min if analysis=="min" else max)(p["delay_ns"] for p in group)
        if not 0 <= values["min"] <= values["max"]:
            raise ValueError("Invalid path delay envelope")
        edges.append({"source":source,"target":target,"min_delay_ns":values["min"],"max_delay_ns":values["max"]})
    for p in paths:
        wanted=[]
        for kind,active,port,direction in [("input",p["source"] in INPUTS,p["source"],"inputs"),("output",p["target"] in OUTPUTS,p["target"],"outputs")]:
            if active:
                wanted.append((kind,io[direction][port][p["analysis"]+"_delay_ns"]*(1 if kind=="input" else -1)))
        actual=[(v["kind"],v["contribution_ns"]) for v in p["external_delays"]]
        if len(actual)!=len(wanted) or any(k!=wk or abs(v-wv)>1e-6 for (k,v),(wk,wv) in zip(actual,wanted)):
            raise ValueError("SDC/report external delay mismatch")
    for name,node in nodes.items():
        arcs={kind:parse_arc(read(name+"_"+kind+".rpt"),kind,node,conditions["clock_transition_ns"]) for kind in ["dq_min","dq_max","cq_min","cq_max"]}
        parameters={"tsu":max(p["checks"]["setup_ns"] for p in paths if p["target"]==name and p["analysis"]=="max"),
                    "thd":max(p["checks"]["hold_ns"] for p in paths if p["target"]==name and p["analysis"]=="min")}
        parameters.update({key:fn(arcs[kind].values()) for key,kind,fn in [("tdqMin","dq_min",min),("tdqMax","dq_max",max),("tcqMin","cq_min",min),("tcqMax","cq_max",max)]})
        if parameters["tdqMin"]>parameters["tdqMax"] or parameters["tcqMin"]>parameters["tcqMax"]:
            raise ValueError("Invalid cell propagation envelope")
        node.update(parameters_ns=parameters,reported_arcs=arcs)
    pulse_rows=re.findall(r"^\s*(\S+)/(GATE_N|GATE)\s+\((high|low)\)\s+("+NUMBER+r")\s+("+NUMBER+r")\s+("+NUMBER+r")\s+\((MET|VIOLATED)\)",read("pulse_width.rpt"),re.M)
    if len(pulse_rows)!=8 or {r[0] for r in pulse_rows}!=set(nodes):
        raise ValueError("Incomplete pulse-width coverage")
    for name,gate,level,required_width,actual,slack,status in pulse_rows:
        node=nodes[name]
        if gate!=node["gate_pin"].split("/")[1] or level!=("low" if node["polarity"]=="negative" else "high"):
            raise ValueError("Pulse polarity mismatch")
        required_width,actual,slack=map(finite,[required_width,actual,slack])
        if required_width<0 or abs(actual-clock["period_ns"]/2)>1e-6 or abs(actual-required_width-slack)>2e-6:
            raise ValueError("Invalid pulse-width report")
        node["reported_pulse_check"]={"level":level,"required_ns":required_width,"actual_ns":actual,"slack_ns":slack,"status":status}
    return {"schema_version":4,"timing_model":MODEL,"units":{"time":"ns","capacitance":"pF"},
            "clock":clock,"clock_skew_ns":0.0,"io_constraints":io,"sta_conditions":conditions,
            "nodes":list(nodes.values()),"edges":edges,"paths":paths,"source_sha256":sources,
            "solver_compatibility":{"current_cpp_supported":True,"mode":"zero_skew_50pct",
                                    "reason":"C++ v4 supports zero-skew 50% duty with opposite-phase feedback and certified opening-response hold bounds."},
            "semantics":"Edges contain only the reported combinational Q-to-D/port delay, excluding latch arcs and IO budgets. Phase windows are relative to cycle start. Feedback event/cycle mapping must be defined by the solver adapter; no uniform per-edge cycle shift is assumed.",
            "limitations":["Only the present 18-cell counter and supplied OpenSTA text layout are supported.","Topology and rise/fall pair coverage are checked; report truncation or omitted reconvergent alternatives can still affect extrema.","Scalar cell envelopes are fixed-condition report values, not multi-PVT characterization.","Pulse requirements are copied from reports; unreported checks are not claimed absent from Liberty.","This is a schema-v4 interchange, not executable v3 solver input."]}


def write_outputs(data, output, json_output, reports):
    output,json_output=Path(output),Path(json_output)
    if not output.name.endswith(".blif.out") or json_output.suffix!=".json":
        raise ValueError("Outputs must be .blif.out and .json")
    for path in [output,json_output]:
        if path.exists() or path.is_symlink() or path.resolve().is_relative_to(reports.resolve()):
            raise ValueError(f"Refusing to overwrite outputs or reports: {path}")
        if not path.parent.is_dir():
            raise ValueError(f"Missing output directory: {path.parent}")
    if output.resolve()==json_output.resolve():
        raise ValueError("Output paths must differ")
    # The model marker selects v4 semantics instead of silently treating ports/polarities as legacy latches.
    lines=["TimingModel "+MODEL,"Network counter","source target max_delay min_delay","# ns; combinational delays only; requires accompanying schema-v4 JSON"]
    lines += [f"{e['source']} {e['target']} {e['max_delay_ns']:.6f} {e['min_delay_ns']:.6f}" for e in data["edges"]]
    contents=[(output,"\n".join(lines)+"\n"),(json_output,json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False)+"\n")]
    created=[]
    try:
        for path,text in contents:
            with path.open("x",encoding="utf-8",newline="\n") as stream:
                created.append(path)
                stream.write(text)
    except OSError:
        for path in created:
            path.unlink()
        raise


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reports",type=Path,default=ROOT/"reports_opensta_10ns")
    parser.add_argument("--netlist",type=Path,default=ROOT/"counter_mapped.v")
    parser.add_argument("--output",type=Path,default=ROOT/"counter.blif.out")
    parser.add_argument("--json-output",type=Path,default=ROOT/"counter_timing.json")
    args=parser.parse_args()
    try:
        data=convert(args.reports,args.netlist)
        write_outputs(data,args.output,args.json_output,args.reports)
    except (OSError,ValueError,KeyError,csv.Error) as error:
        parser.error(str(error))
    print(f"Saved {len(data['edges'])} boundary edges and {len(data['paths'])} path witnesses: {args.output}")
    print(f"Saved {len(data['nodes'])} mixed-polarity latch parameter sets: {args.json_output}")
    print("Solver mode: counter_solver or main --no-skew; fixed 50% duty and certified hold bounds are required.")


if __name__=="__main__":
    main()
