"""Checker tests using archived reports and explicitly mocked graph/log fixtures; no STA execution."""

import importlib.util
import shutil
import tempfile
import unittest
from pathlib import Path


CASE = Path(__file__).resolve().parents[1] / "examples" / "tiny_3_latch_circuit"
spec = importlib.util.spec_from_file_location("check_flow_reports", CASE / "check_flow_reports.py")
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


class FlowReportTests(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory(dir=CASE.parents[1])
        self.addCleanup(self.scratch.cleanup)
        self.reports = Path(self.scratch.name)
        for name in ("setup.rpt", "hold.rpt", "pulse_width.rpt", "check_setup.rpt"):
            shutil.copyfile(CASE / "reports_howard_01" / name, self.reports / name)
        graph = self.reports / "pin_graph"
        graph.mkdir()
        for name in ("pins", "vertices", "edges", "arc_delays", "slews", "boundary_paths", "boundary_edges", "manifest"):
            (graph / (name + ".tsv")).write_text("MOCK GRAPH FILE; NOT STA EVIDENCE\n", encoding="utf-8")
        self.log = self.reports / "mock.log"
        self.log.write_text("MOCK LOG; NOT STA EVIDENCE\nComplete pin graph written to mock\nReports written to mock\n", encoding="utf-8")

    def check(self):
        return checker.check(self.reports, self.log, CASE / "latch_timing.json")

    def test_archived_slacks_and_explicit_coverage_limit(self):
        result = self.check()
        self.assertEqual(result["setup"]["reported_paths"], 10)
        self.assertEqual(result["setup"]["worst_slack_ns"], 0.0)
        self.assertEqual(result["hold"]["worst_slack_ns"], 0.974505)
        self.assertEqual(result["pulse_width"]["reported_checks"], 1)
        self.assertTrue(result["limitations"])

    def test_violations_and_missing_checks_fail(self):
        for name in ("setup.rpt", "hold.rpt", "pulse_width.rpt"):
            path = self.reports / name
            original = path.read_text(encoding="utf-8")
            for content in (original.replace("(MET)", "(VIOLATED)", 1), ""):
                with self.subTest(name=name, empty=not content):
                    path.write_text(content, encoding="utf-8")
                    with self.assertRaises(ValueError):
                        self.check()
            path.write_text(original, encoding="utf-8")

    def test_tool_error_and_truncated_log_fail(self):
        original = self.log.read_text(encoding="utf-8")
        for content in (original + "Error: mocked failure\n", original + "Warning: mocked warning\n", ""):
            self.log.write_text(content, encoding="utf-8")
            with self.assertRaises(ValueError):
                self.check()

    def test_nonfinite_and_unknown_pulse_checks_fail(self):
        path = self.reports / "pulse_width.rpt"
        original = path.read_text(encoding="utf-8")
        for text in (original.replace("0.231014", "1e999"), original.replace("L1/GATE", "UNKNOWN/GATE")):
            path.write_text(text, encoding="utf-8")
            with self.assertRaises(ValueError):
                self.check()

    def test_constraint_warning_incomplete_graph_and_missing_boundary_fail(self):
        path = self.reports / "check_setup.rpt"
        path.write_text("MOCK: unconstrained endpoint\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            self.check()
        path.write_text("", encoding="utf-8")
        edge_file = self.reports / "pin_graph" / "edges.tsv"
        edge_file.unlink()
        with self.assertRaises(ValueError):
            self.check()
        edge_file.write_text("MOCK\n", encoding="utf-8")
        path = self.reports / "setup.rpt"
        path.write_text(path.read_text(encoding="utf-8").replace("Endpoint: L2", "Endpoint: UNKNOWN"), encoding="utf-8")
        with self.assertRaises(ValueError):
            self.check()


if __name__ == "__main__":
    unittest.main()
