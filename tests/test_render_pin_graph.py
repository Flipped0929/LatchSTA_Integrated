"""Small graph and image smoke tests; no OpenSTA or Graphviz required."""

import csv
import importlib.util
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("render_pin_graph", ROOT / "examples/tiny_3_latch_circuit/render_pin_graph.py")
renderer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(renderer)


class RenderTests(unittest.TestCase):
    def setUp(self):
        scratch = tempfile.TemporaryDirectory(dir=ROOT)
        self.addCleanup(scratch.cleanup)
        self.root = Path(scratch.name)
        self.data = self.root / "graph"
        self.data.mkdir()
        self.rows = {
            "manifest": [dict(key="schema_version", value="1"), dict(key="time_unit", value="ns")],
            "pins": [dict(zip(("pin_id", "name", "direction", "instance", "port", "boundary", "boundary_role"), row)) for row in [
                ("n1", "din", "input", "", "din", "din", "input"),
                ("n2", "L1/D", "input", "L1", "D", "L1", "latch_d"),
                ("n3", "L1/Q", "output", "L1", "Q", "L1", "latch_q"),
                ("n4", "L1/GATE", "input", "L1", "GATE", "L1", "latch_clock"),
                ("n5", "L1/IQ", "internal", "L1", "IQ", "", ""),
                ("n6", "dout", "output", "", "dout", "dout", "output"),
                ("n7", "clk", "input", "", "clk", "", "clock_source")]],
            "vertices": [dict(vertex_id="v" + str(i), pin_id="n" + str(i), bidirect_driver="0") for i in (1, 2, 3, 4, 6, 7)],
            "edges": [dict(edge_id="e" + str(i), from_vertex=u, to_vertex=v, kind=kind, role=role, disabled_reason="")
                      for i, (u, v, kind, role) in enumerate([
                          ("v1", "v2", "net", "wire"), ("v2", "v3", "cell", "Latch D to Q"),
                          ("v3", "v6", "net", "wire"), ("v7", "v4", "net", "wire"),
                          ("v4", "v2", "cell", "setup"), ("v4", "v2", "cell", "hold"),
                          ("v4", "v4", "cell", "width")], 1)],
            "boundary_edges": [dict(boundary_edge_id="b1", source="din", target="L1", scene="default", min_delay_ns="0.1", max_delay_ns="0.2"),
                               dict(boundary_edge_id="b2", source="L1", target="dout", scene="default", min_delay_ns="0.3", max_delay_ns="0.4")],
        }
        self.write()

    def write(self):
        for name, rows in self.rows.items():
            with (self.data / (name + ".tsv")).open("w", encoding="utf-8", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=list(rows[0]), delimiter="\t")
                writer.writeheader()
                writer.writerows(rows)

    def test_preserves_isolated_pins_parallel_edges_and_self_checks(self):
        graph, boundary, pins, vertices = renderer.load_graphs(self.data)
        self.assertEqual((pins, vertices, len(graph), graph.number_of_edges()), (7, 6, 7, 7))
        self.assertIn("pin:n5", graph)
        self.assertEqual(len(graph["v4"]["v2"]), 2)
        self.assertTrue(graph.has_edge("v4", "v4"))
        positions, _ = renderer.pin_layout(graph)
        self.assertEqual(set(positions), set(graph))
        self.assertEqual(boundary.number_of_edges(), 2)

    def test_rejects_bad_units_references_duplicates_and_delays(self):
        mutations = [("manifest", 1, "value", "ps"), ("vertices", 0, "pin_id", "UNKNOWN"),
                     ("vertices", 0, "vertex_id", "v2"), ("edges", 0, "to_vertex", "UNKNOWN"),
                     ("boundary_edges", 0, "min_delay_ns", "nan"),
                     ("boundary_edges", 0, "min_delay_ns", "0.9")]
        for name, i, key, value in mutations:
            old = self.rows[name][i][key]
            with self.subTest(name=name, key=key, value=value):
                self.rows[name][i][key] = value
                self.write()
                with self.assertRaises(ValueError):
                    renderer.load_graphs(self.data)
            self.rows[name][i][key] = old

    def test_render_images_and_refuse_overwrite(self):
        output = self.root / "figures"
        renderer.render(self.data, output)
        for name in ("pin_graph", "boundary_graph"):
            with Image.open(output / (name + ".png")) as image:
                self.assertGreater(image.width, 1000)
                self.assertGreater(image.width / image.height, 1.5 if name == "boundary_graph" else 1.0)
            ET.parse(output / (name + ".svg"))
        before = (output / "pin_graph.png").read_bytes()
        with self.assertRaises(FileExistsError):
            renderer.render(self.data, output)
        self.assertEqual((output / "pin_graph.png").read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
