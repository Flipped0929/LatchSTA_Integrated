import json
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from convert_opensta_reports import CELL, COMMON, PDK, ROOT, convert, parse_arc, parse_paths, parse_sdc, write_outputs


def path_report(source="L1", target="L2", analysis="max"):
    start = source + "/Q" if source.startswith("L") else source
    end = target + "/D" if target.startswith("L") else target
    start_kind = "positive level-sensitive latch" if source.startswith("L") else "input port"
    end_kind = "positive level-sensitive latch" if target.startswith("L") else "output port"
    constraint = "library setup time -0.200000" if analysis == "max" else " -0.015000 -0.015000 library hold time"
    return f"""Startpoint: {source} ({start_kind} clocked by clk)
Endpoint: {target} ({end_kind} clocked by clk)
Path Type: {analysis}
 0.050000 5.000000 5.000000 clock clk (rise edge)
 1.000000 6.000000 ^ input external delay
 0.002000 0.050000 0.800000 6.800000 ^ {start} ({'latch' if source.startswith('L') else 'in'})
 0.050000 0.000000 6.800000 ^ U_BUFFER/A (buffer)
 0.002000 0.050000 0.200000 7.000000 ^ U_BUFFER/X (buffer)
 0.050000 0.000000 7.000000 ^ {end} ({'latch' if target.startswith('L') else 'out'})
 7.000000 data arrival time
 -1.000000 9.000000 output external delay
{constraint}
"""


class ConversionTests(unittest.TestCase):
    def test_current_reports_and_all_four_edges(self):
        data = convert(ROOT / "reports")
        expected = {("INPUT", "L1"): (0.083593, 0.074577),
                    ("L1", "L2"): (0.336778, 0.177533),
                    ("L2", "L3"): (0.072031, 0.070218),
                    ("L3", "OUTPUT"): (0.095645, 0.088638)}
        self.assertEqual({(e["source"], e["target"]): (e["max_delay_ns"], e["min_delay_ns"])
                          for e in data["edges"]}, expected)
        latches = {n["instance"]: n["parameters_ns"] for n in data["nodes"]}
        self.assertEqual(latches["L1"], {"tsu": 0.191980, "thd": -0.015695,
                                       "tdqMin": 0.218371, "tdqMax": 0.327392,
                                       "tcqMin": 0.273814, "tcqMax": 0.315624})
        self.assertEqual(set(latches), {"L1", "L2", "L3"})
        self.assertEqual(data["schema_version"], 3)
        self.assertEqual(data["io_constraints"]["input"], {"port": "i_din", "min_delay_ns": 0.2, "max_delay_ns": 1.0})
        self.assertEqual(data["io_constraints"]["output"], {"port": "o_dout", "min_delay_ns": -0.05, "max_delay_ns": 1.0})
        self.assertEqual({s["file"] for s in data["pulse_width_sources"]}, {CELL, COMMON})
        for node in data["nodes"]:
            self.assertAlmostEqual(node["clock_checks_ns"]["min_pulse_width_high"], 0.231014, places=6)
            self.assertIsNone(node["clock_checks_ns"]["min_pulse_width_low"])
            self.assertEqual(node["clock_checks_conditions"]["clock_slew_ns"], 0.05)
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            output = Path(directory) / "tiny.blif.out"
            sidecar = Path(directory) / "latch_timing.json"
            write_outputs(data, output, sidecar, ROOT / "reports")
            rows = [line.split() for line in output.read_text().splitlines()
                    if line and not line.startswith(("Network", "#")) and "max_delay" not in line]
            self.assertEqual({(r[0], r[1]): (float(r[2]), float(r[3])) for r in rows}, expected)
            self.assertEqual(json.loads(sidecar.read_text())["nodes"], data["nodes"])

    def test_excludes_source_latch_clock_and_external_io_delay(self):
        for source, target in (("L1", "L2"), ("i_din", "L2"), ("L1", "o_dout"), ("i_din", "o_dout")):
            with self.subTest(source=source, target=target):
                path = parse_paths(path_report(source, target), "max", {"L1": {}, "L2": {}})[0]
                self.assertEqual(path["delay_ns"], 0.2)
                self.assertEqual(path["source_pin"], source + "/Q" if source.startswith("L") else source)
                self.assertEqual(path["external_delay_contributions"],
                                 [{"kind": "input", "signed_contribution_ns": 1.0},
                                  {"kind": "output", "signed_contribution_ns": -1.0}])

    def test_setup_sign_and_negative_hold(self):
        self.assertEqual(parse_paths(path_report(), "max", {"L1": {}, "L2": {}})[0]["setup_ns"], 0.2)
        self.assertEqual(parse_paths(path_report(analysis="min"), "min", {"L1": {}, "L2": {}})[0]["hold_ns"], -0.015)
        text = path_report().replace("library setup time -0.200000", " 0.020000 9.000000 library setup time")
        self.assertEqual(parse_paths(text, "max", {"L1": {}, "L2": {}})[0]["setup_ns"], -0.02)

    def test_bad_rows_and_unsupported_paths_are_rejected(self):
        for text in ("No paths found", path_report().replace("7.000000 ^ L2/D", "9.000000 ^ L2/D"),
                     path_report().replace("0.200000 7.000000", "nan 7.000000"),
                     path_report().replace("Endpoint: L2", "Endpoint: L9"),
                     path_report().replace("U_BUFFER/A", "L3/D")):
            with self.subTest(text=text[:80]), self.assertRaises(ValueError):
                parse_paths(text, "max", {"L1": {}, "L2": {}, "L3": {}})

    def test_nonfinite_and_ambiguous_arc_rejected(self):
        text = (ROOT / "reports" / "L1_dq_max.rpt").read_text()
        library, cell = "sky130_fd_sc_hd__tt_025C_1v80", "sky130_fd_sc_hd__dlxtp_1"
        for malformed in (text.replace("Delay = 0.327392", "Delay = nan"), text + text,
                          text.replace("D v -> Q v", "D ^ -> Q v")):
            with self.assertRaises(ValueError):
                parse_arc(malformed, "dq_max", library, cell)

    def test_incomplete_analysis_and_wrong_units_rejected(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            reports = Path(directory)
            for source in (ROOT / "reports").glob("*.rpt"):
                (reports / source.name).write_bytes(source.read_bytes())
            (reports / "opensta_rerun.log").write_bytes((ROOT / "reports" / "opensta_rerun.log").read_bytes())
            (reports / "constraints.sdc").write_bytes((ROOT / "reports" / "constraints.sdc").read_bytes())
            original = (reports / "hold.rpt").read_text()
            kept = [block for block in original.split("Startpoint: ")[1:] if not block.startswith("L3 ")]
            (reports / "hold.rpt").write_text("".join("Startpoint: " + block for block in kept))
            with self.assertRaisesRegex(ValueError, "Missing min or max"):
                convert(reports)
            (reports / "hold.rpt").write_text(original)
            (reports / "units.rpt").write_text("time 1ps\ncapacitance 1pF\n")
            with self.assertRaisesRegex(ValueError, "1ns"):
                convert(reports)

    def test_input_overwrite_is_rejected(self):
        data = convert(ROOT / "reports")
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            root = Path(directory)
            source = root / "source.json"
            source.write_text("original input")
            output = root / "tiny.blif.out"
            output.write_text("previous output")
            with self.assertRaisesRegex(ValueError, "overwrite"):
                write_outputs(data, output, source, root)
            self.assertEqual(source.read_text(), "original input")
            self.assertEqual(output.read_text(), "previous output")

    def test_pulse_report_cross_check_and_missing_clock_slew(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            reports = Path(directory)
            for source in (ROOT / "reports").glob("*.rpt"):
                (reports / source.name).write_bytes(source.read_bytes())
            (reports / "opensta_rerun.log").write_bytes((ROOT / "reports" / "opensta_rerun.log").read_bytes())
            (reports / "constraints.sdc").write_bytes((ROOT / "reports" / "constraints.sdc").read_bytes())
            pulse = reports / "pulse_width.rpt"
            original = pulse.read_text()
            pulse.write_text(original.replace("0.231014", "0.331014"))
            with self.assertRaisesRegex(ValueError, "pulse-width mismatch"):
                convert(reports)
            pulse.write_text(original)
            for name in ("setup.rpt", "hold.rpt"):
                path = reports / name
                path.write_text(path.read_text().replace("L2/GATE", "L2/MISSING"))
            with self.assertRaisesRegex(ValueError, "clock slew"):
                convert(reports)

    def test_pulse_library_input_protected(self):
        data = convert(ROOT / "reports")
        source = PDK / CELL
        original = source.read_bytes()
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            with self.assertRaisesRegex(ValueError, "overwrite"):
                write_outputs(data, Path(directory) / "tiny.blif.out", source, ROOT / "reports")
        self.assertEqual(source.read_bytes(), original)

    def test_sdc_rejects_unsupported_and_incomplete_constraints(self):
        text = (ROOT / "reports" / "constraints.sdc").read_text()
        clock = {"name": "clk", "period_ns": 10.0, "rise_ns": 5.0, "fall_ns": 10.0}
        for malformed in (text + "\nset_false_path -from [get_ports i_din]\n",
                          text.replace("set_output_delay -clock clk -min -0.05 [get_ports o_dout]", ""),
                          text.replace("-min 0.2", "-min 2.0"),
                          text.replace("-setup 0.0", "-setup -0.1"),
                          text.replace("{5 10}", "{4 10}"),
                          text + "\nset_clock_uncertainty -hold 0.0 [get_clocks clk]\n"):
            with self.subTest(text=malformed[-80:]), self.assertRaises(ValueError):
                parse_sdc(malformed, clock)
        io, conditions = parse_sdc(text.replace("-setup 0.0", "-setup 0.2").replace("-hold 0.0", "-hold 0.1"), clock)
        self.assertEqual((io["setup_uncertainty_ns"], io["hold_uncertainty_ns"]), (0.2, 0.1))
        self.assertEqual(conditions, {"clock_port": "i_clk", "clock_transition_ns": 0.05,
                                      "input_transition_ns": 0.05, "output_load_pf": 0.005})

    def test_sdc_must_match_reported_io_delays(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as directory:
            reports = Path(directory)
            for source in (ROOT / "reports").glob("*.rpt"):
                (reports / source.name).write_bytes(source.read_bytes())
            for name in ("constraints.sdc", "opensta_rerun.log"):
                (reports / name).write_bytes((ROOT / "reports" / name).read_bytes())
            sdc = reports / "constraints.sdc"
            original = sdc.read_text()
            sdc.write_text(original.replace("-min -0.05", "-min -0.5"))
            with self.assertRaisesRegex(ValueError, "output delay mismatch"):
                convert(reports)
            sdc.write_text(original.replace("-setup 0.0", "-setup 0.1"))
            with self.assertRaisesRegex(ValueError, "uncertainty mismatch"):
                convert(reports)
            with (reports / "setup.rpt").open("a") as stream:
                stream.write("\nclock uncertainty -0.100000\n")
            self.assertEqual(convert(reports)["io_constraints"]["setup_uncertainty_ns"], 0.1)
            sdc.write_text(sdc.read_text().replace("set_clock_transition 0.05", "set_clock_transition 0.1"))
            with self.assertRaisesRegex(ValueError, "clock transition mismatch"):
                convert(reports)

    def test_io_conversion_rejects_feedback_and_disconnected_output(self):
        data = convert(ROOT / "reports")
        for feedback in (False, True):
            paths = [p.copy() for p in data["paths"] if feedback or p["target"] != "OUTPUT"]
            if feedback:
                for analysis in ("min", "max"):
                    paths.append({"source": "L3", "target": "L1", "source_pin": "L3/Q", "target_pin": "L1/D",
                                  "analysis": analysis, "delay_ns": 0.1, "external_delay_contributions": []})
            grouped = [[p for p in paths if p["analysis"] == analysis] for analysis in ("max", "min")]
            with patch("convert_opensta_reports.parse_paths", side_effect=grouped), self.assertRaisesRegex(ValueError, "acyclic|input-to-output"):
                convert(ROOT / "reports")


if __name__ == "__main__":
    unittest.main()
