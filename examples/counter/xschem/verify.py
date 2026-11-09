#!/usr/bin/env python3
"""Check actual xschem exports against Yosys; optionally simulate SKY130 models."""
import argparse
from pathlib import Path
import re
import subprocess
import tempfile

HERE = Path(__file__).resolve().parent


def parse_verilog(path):
    text = path.read_text()
    assert '\0' not in text, f'NUL bytes in {path}; re-export using export.tcl'
    cells = {}
    for typ, name, body in re.findall(
            r'(sky130_fd_sc_hd__\w+)\s+(x?_\d+_)\s*\((.*?)\);', text, re.S):
        name = name.removeprefix('x')
        assert name not in cells, f'Duplicate instance {name}'
        pins = {pin: net.strip().replace('slave[', 'count[')
                for pin, net in re.findall(r'\.(\w+)\s*\(([^)]+)\)', body)}
        cells[name] = (typ, pins)
    return cells


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--simulate', action='store_true')
    parser.add_argument('--cell-source', type=Path,
                        default=HERE.parents[3] / 'pdk_work/sources/sky130_fd_sc_hd')
    args = parser.parse_args()
    original = parse_verilog(HERE.parent / 'counter_mapped.v')
    exported = parse_verilog(HERE / 'simulation/counter.v')
    assert len(original) == 18 and original == exported, 'Verilog cell/pin/net mismatch'
    verilog = (HERE / 'simulation/counter.v').read_text()
    assert re.search(r'output\s+wire\s+\[3:0\]\s+count', verilog), 'Bad count port'
    print('PASS: exported Verilog matches all 18 Yosys instances and signal pins')

    # Independent SPICE pin orders, including wells, taken from SKY130 subckt interfaces.
    pin_orders = {
        'o21ai_0': 'A1 A2 B1 VGND VNB VPB VPWR Y',
        'a21oi_1': 'A1 A2 B1 VGND VNB VPB VPWR Y',
        'and3_1': 'A B C VGND VNB VPB VPWR X',
        'a41o_1': 'A1 A2 A3 A4 B1 VGND VNB VPB VPWR X',
        'nand2_1': 'A B VGND VNB VPB VPWR Y',
        'a31oi_1': 'A1 A2 A3 B1 VGND VNB VPB VPWR Y',
        'nor3b_1': 'A B C_N VGND VNB VPB VPWR Y',
        'dlxtn_1': 'D GATE_N VGND VNB VPB VPWR Q',
        'dlxtp_1': 'D GATE VGND VNB VPB VPWR Q',
    }
    spice = (HERE / 'simulation/counter.spice').read_text()
    assert '\0' not in spice, 'NUL bytes in SPICE; re-export using export.tcl'
    header = re.search(r'^\.subckt counter (.*)$', spice, re.M)
    assert header and header[1].split() == [
        'clk', 'rst_n', 'en', 'VPWR', 'VGND', 'count[3]', 'count[2]', 'count[1]', 'count[0]']
    seen = set()
    for line in spice.splitlines():
        if not line.startswith('x_'):
            continue
        name, *nets, typ = line.split()
        name = name.removeprefix('x')
        assert name not in seen, f'Duplicate SPICE instance {name}'
        seen.add(name)
        expected_type, expected_pins = original[name]
        assert typ == expected_type, f'SPICE type mismatch: {name}'
        order = pin_orders[typ.split('__')[1]].split()
        assert len(nets) == len(order), f'SPICE pin count mismatch: {name}'
        actual = dict(zip(order, nets))
        expected_pins = dict(expected_pins, VGND='VGND', VNB='VGND', VPB='VPWR', VPWR='VPWR')
        assert actual == expected_pins, f'SPICE pin/net mismatch: {name}'
    assert seen == set(original), 'Missing or extra SPICE instances'
    erc = (HERE / 'simulation/erc.txt').read_text()
    assert not re.search(r'warning|error|unconnected|open net', erc, re.I), erc
    print('PASS: SPICE signal/power/well connections and 9-port subcircuit; clean xschem ERC')

    if args.simulate:
        # Flatten only `include directives. Preserve the upstream model contents/license.
        included = set()

        def model_text(path):
            path = path.resolve()
            if path in included:
                return ''
            included.add(path)
            return re.sub(r'`include\s+"([^"]+)"',
                          lambda m: model_text(path.parent / m[1]), path.read_text())

        with tempfile.TemporaryDirectory(prefix='counter-functional-') as tmp_name:
            tmp = Path(tmp_name)
            models = []
            for typ in sorted({typ for typ, _ in original.values()}):
                cell = typ.split('__')[1].rsplit('_', 1)[0]
                models.append(model_text(args.cell_source / 'cells' / cell / f'{typ}.functional.v'))
            (tmp / 'models.v').write_text('\n'.join(models))
            for src, dst, module in [(HERE.parent / 'counter.v', 'rtl.v', 'counter_rtl'),
                                     (HERE.parent / 'counter_mapped.v', 'mapped.v', 'counter_mapped')]:
                (tmp / dst).write_text(re.sub(r'\bmodule\s+counter\b', f'module {module}', src.read_text(), count=1))
            subprocess.run(['iverilog', '-g2012', '-s', 'tb_counter', '-o', str(tmp / 'sim'),
                            str(tmp / 'models.v'), str(tmp / 'rtl.v'), str(tmp / 'mapped.v'),
                            str(HERE / 'simulation/counter.v'), str(HERE / 'tb_counter.v')], check=True)
            result = subprocess.run(['vvp', str(tmp / 'sim')], check=True, capture_output=True, text=True)
            print(result.stdout.strip())


if __name__ == '__main__':
    main()
