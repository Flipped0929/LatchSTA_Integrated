"""Counter Tcl contracts and shell integration with mock tools; never real STA evidence."""
import json
import os
import shutil
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "examples/counter"
TCL = os.environ.get("TCLSH") or shutil.which("tclsh")
SH = os.environ.get("COUNTER_TEST_SH") or shutil.which("sh")

MOCK_DRIVER = r'''
import csv, hashlib, os, sys
from pathlib import Path
tool, *args = sys.argv[1:]
mode = os.environ.get("COUNTER_MOCK_SCENARIO", "normal")
if tool == "sha256sum":
    if args[0] == "-c":
        failed = False
        for line in Path(args[1]).read_text().splitlines():
            digest, name = line.split("  ", 1)
            good = hashlib.sha256(Path(name).read_bytes()).hexdigest() == digest
            print(name + (": OK" if good else ": FAILED"))
            failed |= not good
        sys.exit(int(failed))
    if args[0] == "--": args.pop(0)
    for name in args:
        print(hashlib.sha256(Path(name).read_bytes()).hexdigest() + "  " + name)
    sys.exit()
if args in [["-V"], ["-version"]]:
    print("MOCK " + tool + "; NOT REAL TOOL EVIDENCE")
    sys.exit()
if mode == "tool_failure" and tool == "yosys":
    sys.exit(7)
if tool == "yosys":
    Path("counter_mapped.v").write_text("// MOCK NETLIST, NOT REAL SYNTHESIS\n")
    Path("reports/yosys.log").write_text("MOCK SYNTHESIS LOG\n")
    sys.exit()
reports = Path("reports")
latches = []
for i in range(8):
    name = "latch_" + str(i)
    latches.append([name, "sky130_fd_sc_hd__dlxtn_1" if i < 4 else "sky130_fd_sc_hd__dlxtp_1"])
    for suffix in ("instance", "arrival", "load", "dq_min", "dq_max", "cq_min", "cq_max"):
        (reports / (name + "_" + suffix + ".rpt")).write_text("MOCK REPORT; NOT STA EVIDENCE\n")
with (reports/"latches.tsv").open("w",newline="") as f:
    w=csv.writer(f,delimiter="\t");w.writerow(["instance","cell"]);w.writerows(latches)
for kind in ("units", "clocks", "check_setup", "setup", "hold", "en_setup", "en_hold", "rst_n_setup", "rst_n_hold", "pulse_width", "checks", "violations"):
    text = "" if kind in {"check_setup", "violations"} else "MOCK REPORT; NOT STA EVIDENCE\n0.100000 slack (MET)\n"
    if mode == "violation" and kind == "hold": text = "MOCK REPORT\n-0.010000 slack (VIOLATED)\n"
    if mode == "missing_reset_path" and kind == "rst_n_setup": text = "MOCK: no checks\n"
    (reports/(kind+".rpt")).write_text(text)
for name in ("constraints.sdc", "effective.sdc"):
    if mode != "missing_constraints" or name != "effective.sdc":
        (reports/name).write_text("# MOCK SDC\n")
if mode == "mutate_input": Path("counter.sdc").write_text("MOCK MUTATION\n")
print("MOCK OUTPUT ONLY; NOT STA EVIDENCE")
print("Counter reports written to mock")
'''


class CounterFlowTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(dir=ROOT)
        self.addCleanup(self.cleanup_scratch)
        self.scratch = Path(self.temporary.name)

    def cleanup_scratch(self):
        for attempt in range(5):
            try:
                self.temporary.cleanup()
                return
            except PermissionError:
                if attempt == 4:
                    raise
                time.sleep(0.2)

    @unittest.skipUnless(TCL, "tclsh required")
    def test_sta_polarity_reset_and_rejections(self):
        for scenario in ("normal", "missing_pin", "wrong_cell"):
            with self.subTest(scenario=scenario):
                result = subprocess.run([TCL, str(ROOT / "tests/test_counter_sta.tcl"),
                                         str(CASE / "run_sta.tcl"), str(self.scratch / scenario), scenario],
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    @unittest.skipUnless(SH, "POSIX sh required")
    def test_shell_syntax(self):
        result = subprocess.run([SH, "-n", str(CASE / "run_flow.sh")], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def mock_environment(self, scenario):
        repo = self.scratch / scenario
        case = repo / "examples/counter"
        case.mkdir(parents=True)
        for name in ("counter.v", "counter.sdc", "export.ys", "latch_map.v", "run_sta.tcl", "run_flow.sh"):
            shutil.copyfile(CASE / name, case / name)
        pdk = repo / "sky130_pdk"; pdk.mkdir()
        (pdk / "sky130_fd_sc_hd__tt_025C_1v80.lib").write_text("MOCK LIBRARY; NOT REAL STA INPUT\n")
        tools = repo / "tools"; tools.mkdir()
        driver = tools / "mock_driver.py"; driver.write_text(MOCK_DRIVER)
        for name in ("yosys", "sta", "sha256sum"):
            path = tools / name
            path.write_text('#!/bin/sh\nexec "$COUNTER_MOCK_PYTHON" "$COUNTER_MOCK_DRIVER" ' + name + ' "$@"\n', newline="\n")
            path.chmod(0o755)
        path = tools / "python3"
        path.write_text('#!/bin/sh\nexec "$COUNTER_MOCK_PYTHON" "$@"\n', newline="\n")
        path.chmod(0o755)
        env = os.environ.copy()
        import sys
        env.update(COUNTER_MOCK_PYTHON=Path(sys.executable).as_posix(),
                   COUNTER_MOCK_DRIVER=driver.as_posix(), COUNTER_MOCK_SCENARIO=scenario)
        # Forward slashes allow MSYS sh to use the mock directory on Windows.
        env["PATH"] = os.pathsep.join((tools.as_posix(), Path(SH).parent.as_posix(), env["PATH"]))
        return repo, case, env

    @unittest.skipUnless(SH, "POSIX sh required")
    def test_shell_flow_status_and_failures(self):
        for scenario in ("normal", "violation", "missing_constraints", "missing_reset_path", "tool_failure", "mutate_input"):
            with self.subTest(scenario=scenario):
                repo, case, env = self.mock_environment(scenario)
                output = repo / "new run with spaces"
                result = subprocess.run([SH, str(case / "run_flow.sh"), str(output)],
                                        cwd=repo, env=env, capture_output=True, text=True)
                self.assertTrue((output / "flow_status.json").exists(), result.stdout + result.stderr)
                status = json.loads((output / "flow_status.json").read_text())
                self.assertEqual(status["optimization"]["status"], "not_run")
                if scenario == "normal":
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertEqual(status["status"], "reported_checks_passed")
                    repeat = subprocess.run([SH, str(case / "run_flow.sh"), str(output)],
                                            cwd=repo, env=env, capture_output=True, text=True)
                    self.assertNotEqual(repeat.returncode, 0)
                    self.assertEqual(json.loads((output / "flow_status.json").read_text()), status)
                else:
                    self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertNotEqual(status["status"], "reported_checks_passed")
                self.assertFalse((output / "examples/counter/candidate_howard.sdc").exists())


if __name__ == "__main__":
    unittest.main()
