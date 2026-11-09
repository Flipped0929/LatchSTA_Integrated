"""Check graph export against a synthetic SWIG fixture and an exhaustive path oracle."""
import csv
import math
import os
import shutil
import subprocess
import tempfile
import unittest
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TCL = os.environ.get("TCLSH") or shutil.which("tclsh")


@unittest.skipUnless(TCL, "tclsh is required")
class PinGraphTests(unittest.TestCase):
    def run_export(self, scenario="normal", success=True):
        temporary = tempfile.TemporaryDirectory(dir=ROOT)
        self.addCleanup(temporary.cleanup)
        directory = Path(temporary.name) / "reports"
        directory.mkdir()
        result = subprocess.run([TCL, str(ROOT / "tests/test_pin_graph.tcl"),
                                 str(ROOT / "examples/tiny_3_latch_circuit/export_pin_graph.tcl"),
                                 str(directory), scenario], capture_output=True, text=True)
        if not success:
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((directory / "pin_graph").exists())
            return result.stderr
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        tables = {}
        for file in (directory / "pin_graph").glob("*.tsv"):
            with file.open(encoding="utf-8", newline="") as stream:
                tables[file.stem] = list(csv.DictReader(stream, delimiter="\t"))
        return tables

    def assert_oracle(self, data):
        pins = {r["pin_id"]: r for r in data["pins"]}
        vertices = {r["vertex_id"]: pins[r["pin_id"]] for r in data["vertices"]}
        edges = {r["edge_id"]: r for r in data["edges"]}
        arcs = {(r["arc_id"], r["scene"], r["analysis"]): r for r in data["arc_delays"]}
        conditions = {(r["scene"], r["analysis"]) for r in data["arc_delays"]}
        expected = defaultdict(list)
        for scene, analysis in conditions:
            outgoing = defaultdict(list)
            for arc in data["arc_delays"]:
                edge = edges[arc["edge_id"]]
                if (arc["scene"], arc["analysis"]) == (scene, analysis) and arc["status"] == "calculated" and edge["role"] in {"wire", "combinational"}:
                    outgoing[edge["from_vertex"]].append(arc)

            # Exhaustively enumerate the small fixture; independent of the exporter's DAG DP.
            def walk(source, vertex, rf, delay, seen):
                pin = vertices[vertex]
                if seen and pin["boundary_role"] in {"output", "latch_d"}:
                    expected[source, pin["boundary"], scene, analysis].append(delay)
                    return
                self.assertNotIn(vertex, seen)
                for arc in outgoing[vertex]:
                    if arc["from_rf"] == rf:
                        edge = edges[arc["edge_id"]]
                        walk(source, edge["to_vertex"], arc["to_rf"], delay + float(arc["delay_ns"]), seen | {vertex})

            for vertex, pin in vertices.items():
                if pin["boundary_role"] in {"input", "latch_q"}:
                    for rf in ("rise", "fall"):
                        walk(pin["boundary"], vertex, rf, 0.0, set())
        self.assertEqual({(r["source"], r["target"], r["scene"]) for r in data["boundary_edges"]},
                         {key[:3] for key in expected})
        paths = {r["path_id"]: r for r in data["boundary_paths"]}
        for row in data["boundary_edges"]:
            pair = row["source"], row["target"], row["scene"]
            self.assertAlmostEqual(float(row["min_delay_ns"]), min(expected[pair + ("min",)]), places=12)
            self.assertAlmostEqual(float(row["max_delay_ns"]), max(expected[pair + ("max",)]), places=12)
            for analysis in ("min", "max"):
                self.assertAlmostEqual(float(paths[row[f"{analysis}_path_id"]]["delay_ns"]), float(row[f"{analysis}_delay_ns"]), places=12)
        for path in paths.values():
            vertex_ids = path["vertex_ids"].split(",")
            edge_ids = path["edge_ids"].split(",")
            arc_ids = path["arc_ids"].split(",")
            self.assertEqual(len(vertex_ids), len(edge_ids) + 1)
            self.assertEqual(len(edge_ids), len(arc_ids))
            delay = 0.0
            rf = path["from_rf"]
            for i, (edge_id, arc_id) in enumerate(zip(edge_ids, arc_ids)):
                edge = edges[edge_id]
                arc = arcs[arc_id, path["scene"], path["analysis"]]
                self.assertEqual((edge["from_vertex"], edge["to_vertex"]), tuple(vertex_ids[i:i + 2]))
                self.assertEqual(arc["edge_id"], edge_id)
                self.assertEqual(arc["from_rf"], rf)
                rf = arc["to_rf"]
                delay += float(arc["delay_ns"])
                self.assertIn(edge["role"], {"wire", "combinational"})
            self.assertEqual(rf, path["to_rf"])
            self.assertAlmostEqual(delay, float(path["delay_ns"]), places=12)
            self.assertEqual(vertices[vertex_ids[0]]["boundary"], path["source"])
            self.assertEqual(vertices[vertex_ids[-1]]["boundary"], path["target"])

    def test_full_structure_and_extrema(self):
        data = self.run_export()
        self.assertEqual(len(data["pins"]), 29)
        self.assertEqual(len(data["vertices"]), 29)
        self.assertEqual({r["boundary_role"] for r in data["pins"]},
                         {"", "input", "output", "clock_source", "latch_d", "latch_q", "latch_clock"})
        self.assertEqual({r["role"] for r in data["edges"]},
                         {"wire", "combinational", "Latch D to Q", "Latch En to Q", "setup", "hold"})
        self.assertEqual({(r["source"], r["target"]) for r in data["boundary_edges"]},
                         {("i_din", "L1"), ("L1", "L2"), ("L2", "L3"), ("L3", "o_dout")})
        row = next(r for r in data["boundary_edges"] if r["source"] == "L1")
        self.assertAlmostEqual(float(row["min_delay_ns"]), 0.08)
        self.assertAlmostEqual(float(row["max_delay_ns"]), 0.96)
        self.assert_oracle(data)

    def test_transition_scenes_wires_and_disabled_edges(self):
        for scenario in ("invert", "scenes", "net_delay", "disabled", "feedback", "disconnected", "no_vertex", "units_ps"):
            with self.subTest(scenario=scenario):
                data = self.run_export(scenario)
                self.assert_oracle(data)
                if scenario == "scenes":
                    self.assertEqual({r["scene"] for r in data["boundary_edges"]}, {"S_tt", "S_slow"})
                    for row in data["slews"]:
                        self.assertTrue(math.isfinite(float(row["slew_ns"])))
                    tt = next(r for r in data["slews"] if r["scene"] == "S_tt")
                    slow = next(r for r in data["slews"] if r["scene"] == "S_slow" and all(r[k] == tt[k] for k in ("vertex_id", "analysis", "rf")))
                    self.assertAlmostEqual(float(slow["slew_ns"]), 2 * float(tt["slew_ns"]))
                if scenario == "disabled":
                    self.assertTrue(any(r["disabled_reason"] == "constraint" for r in data["edges"]))
                    self.assertTrue(any(r["status"] == "disabled" and not r["delay_ns"] for r in data["arc_delays"]))
                if scenario in {"disconnected", "no_vertex"}:
                    self.assertTrue(any(r["name"] == "U_INPUT/UNCONNECTED" for r in data["pins"]))
                if scenario == "no_vertex":
                    self.assertEqual(len(data["pins"]), len(data["vertices"]) + 1)
                if scenario == "units_ps":
                    row = next(r for r in data["slews"] if r["rf"] == "rise" and r["analysis"] == "min")
                    self.assertAlmostEqual(float(row["slew_ns"]), 0.05)

    def test_cycles_and_invalid_timing_are_not_published(self):
        for scenario, message in (("cycle", "Combinational cycle"), ("nonfinite", "Non-finite"),
                                  ("missing_slew", "Non-finite"), ("empty_arcs", "Timing edge has no arcs")):
            with self.subTest(scenario=scenario):
                self.assertIn(message, self.run_export(scenario, success=False))

    def test_deterministic_ids(self):
        self.assertEqual(self.run_export(), self.run_export())


if __name__ == "__main__":
    unittest.main()
