#!/usr/bin/env python3
"""Verify physical results and preserved counter connectivity; no timing analysis."""
import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess

HERE = Path(__file__).resolve().parent


def rows(path):
    with path.open() as stream:
        return list(csv.DictReader(stream, delimiter='\t'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', nargs='?', type=Path, default=HERE/'run_03')
    args = parser.parse_args()
    run = args.run.resolve()
    reports, results = run/'reports', run/'results'
    before = {r['instance']:r for r in rows(reports/'01_import_instances.tsv')}
    after = {r['instance']:r for r in rows(reports/'08_routed_instances.tsv')}
    bp = {(r['instance'],r['pin']):r for r in rows(reports/'01_import_pins.tsv')}
    ap = {(r['instance'],r['pin']):r for r in rows(reports/'08_routed_pins.tsv')}
    assert len(before) == 18
    for name, inst in before.items():
        assert name in after and after[name]['master'] == inst['master'], f'Cell changed: {name}'
    for r in after.values():
        assert r['status'] in ('PLACED','LOCKED','FIRM'), f'Unplaced instance: {r}'
    clock_buffers = {name:r for name,r in after.items()
                     if name not in before and r['master'].startswith('sky130_fd_sc_hd__clkbuf_')}
    drivers = {ap[name,'X']['net']:name for name in clock_buffers if ap[name,'X']['net']}
    clock_paths = []
    checked_signal_pins = 0
    for key, pin in bp.items():
        if pin['signal_type'] in ('POWER','GROUND'):
            continue
        checked_signal_pins += 1
        current = ap[key]
        if key[1] in ('GATE','GATE_N'):
            assert pin['net'] == 'clk'
            net = current['net']
            path = []
            while net != 'clk':
                assert net in drivers and drivers[net] not in path, f'Invalid clock path: {key}'
                driver = drivers[net]
                path.append(driver)
                net = ap[driver,'A']['net']
            assert len(path) == 2, f'Unexpected clock depth: {key}: {path}'
            clock_paths.append(dict(instance=key[0], pin=key[1], leaf_net=current['net'],
                                    buffer_depth=len(path), root_to_sink_buffers=list(reversed(path))))
        else:
            assert current['net'] == pin['net'], f'Signal connection changed: {key}'
    assert len(clock_paths) == 8
    for pin in ap.values():
        if pin['signal_type'] == 'POWER':
            assert pin['net'] == 'VDD', pin
        elif pin['signal_type'] == 'GROUND':
            assert pin['net'] == 'VSS', pin
    physical = {name:r for name,r in after.items() if name not in before and name not in clock_buffers}
    assert all(r['master'].startswith(('sky130_fd_sc_hd__fill_', 'sky130_fd_sc_hd__tapvpwrvgnd_'))
               for r in physical.values()), 'Unexpected added logic'
    ports = {r['port']:r for r in rows(reports/'ports.tsv')}
    assert set(ports) == {'clk','en','rst_n','count[0]','count[1]','count[2]','count[3]','VDD','VSS'}
    for bit in range(4):
        assert ports[f'count[{bit}]']['net'] == f'slave[{bit}]'

    log_path = run.parent/(run.name+'.openroad.log')
    log = log_path.read_text()
    assert 'PHYSICAL_IMPLEMENTATION_COMPLETE' in log and '[ERROR' not in log
    violations = [int(n) for n in re.findall(r'Number of violations = (\d+)',log)]
    assert violations and violations[-1] == 0
    assert (reports/'detailed_route_drc.rpt').exists() and not (reports/'detailed_route_drc.rpt').read_text().strip()
    congestion = re.search(r'^Total\s+\d+\s+\d+\s+[\d.]+%\s+(\d+)\s*/\s*(\d+)\s*/\s*(\d+)', log, re.M)
    assert congestion and congestion.groups() == ('0','0','0')
    checks = (reports/'physical_checks.txt').read_text()
    assert 'design_is_routed=1' in checks
    assert 'placement_legal=PASS' in checks
    assert 'VDD_connectivity=PASS' in checks and 'VSS_connectivity=PASS' in checks
    assert '[ERROR' not in (run/'logs/audit.log').read_text()
    sdc = (results/'08_routed.sdc').read_text()
    period = float(re.search(r'create_clock -name clk -period ([\d.]+)',sdc)[1])
    assert abs(period-1.65) < 1e-6 and 'set_propagated_clock' in sdc
    assert not re.search(r'set_clock_latency.*get_pins',sdc)
    flow = (run/'inputs/flow.tcl').read_text()
    forbidden = r'^\s*(?:extract_parasitics|estimate_parasitics|read_spef|report_checks|report_worst_slack|report_tns|report_wns)\b'
    assert not re.search(forbidden,flow,re.M)
    assert not list(run.rglob('*.spef')) and not list(run.rglob('*.sdf'))

    routes = []
    for line in (reports/'wire_length_by_net.rpt').read_text().splitlines():
        if line.startswith('drt:'):
            fields = line.split()
            routes.append(dict(net=fields[1],wirelength_um=float(fields[2]),
                               pins=int(fields[3]),vias=int(fields[4])))
    assert len(routes) == 24 and all(r['wirelength_um'] > 0 for r in routes)
    used_cts = set(drivers.values())
    dummy = set(clock_buffers)-used_cts
    assert len(used_cts) == 3 and len(dummy) == 1
    counts = Counter(r['master'] for r in after.values())
    filler_count = sum(n for master,n in counts.items() if master.startswith('sky130_fd_sc_hd__fill_'))
    endcap_count = sum(name.startswith('PHY_EDGE_') for name in after)
    all_tap_count = counts['sky130_fd_sc_hd__tapvpwrvgnd_1']
    summary = dict(status='PASS',openroad_version=subprocess.check_output(['openroad','-version'],text=True).strip(),
                   sdc_clock_period_ns=period,die_um=[0,0,60,60],core_um=[10.12,10.88,49.68,48.96],
                   core_area_um2=39.56*38.08,original_cell_area_um2=178.9216,
                   original_instances=18,preserved_latches=8,preserved_signal_pins=checked_signal_pins,
                   clock_tree_buffers=3,clock_balance_dummy_loads=1,clock_buffer_depths=[2,2],
                   tap_cells=all_tap_count-endcap_count,endcap_cells=endcap_count,
                   filler_cells=filler_count,final_instances=len(after),
                   final_total_nets=26,routed_signal_clock_nets=24,global_route_overflow=0,
                   detailed_route_drc_violations=0,all_signal_nets_routed=True,
                   pdn_vdd_connected=True,pdn_vss_connected=True,placement_legal=True,
                   detailed_signal_clock_wirelength_um=round(sum(r['wirelength_um'] for r in routes),6),
                   detailed_route_vias=int(re.findall(r'Total number of vias = (\d+)',log)[-1]),
                   instance_counts_by_master=dict(sorted(counts.items())),clock_paths=clock_paths,
                   parasitic_extraction='NOT RUN',design_parasitic_estimation='NOT RUN',post_route_sta='NOT RUN')
    (reports/'verification.json').write_text(json.dumps(summary,indent=2)+'\n')
    with (reports/'clock_paths.tsv').open('w',newline='') as stream:
        writer=csv.writer(stream,delimiter='\t')
        writer.writerow(['instance','pin','leaf_net','buffer_depth','root_to_sink_buffers'])
        for row in clock_paths:
            writer.writerow([row['instance'],row['pin'],row['leaf_net'],row['buffer_depth'],' -> '.join(row['root_to_sink_buffers'])])
    # Capture the exact input set, including source PDK files and executed Tcl.
    sources=rows(run/'inputs/sources.tsv')
    hashes=[]
    for row in sources:
        path=Path(row['path'])
        hashes.append(dict(kind=row['kind'],path=str(path.resolve()),sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    for rel in ['inputs/flow.tcl','inputs/counter_mapped.v','inputs/counter_opt.sdc',
                'results/08_routed.odb','results/08_routed.def','results/counter_routed.v','results/08_routed.sdc']:
        path=run/rel
        hashes.append(dict(kind='artifact',path=rel,sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    (run/'manifest.json').write_text(json.dumps(dict(inputs_and_outputs=hashes),indent=2)+'\n')
    shutil.copyfile(log_path,run/'logs/flow.log')

    dot=['digraph CTS {','rankdir=LR;','graph [bgcolor="white",pad="0.25",nodesep="0.35",ranksep="0.7"];',
         'node [shape=box,fontname="DejaVu Sans",fontsize=11,style=filled,fillcolor="#e5f3ff"];',
         'edge [color="#475569"];','clk [shape=oval,label="clk input\\n1.65 ns"];']
    for name in sorted(used_cts):
        dot.append(f'"{name}" [label="{name}\\nclkbuf_4"];')
        input_net=ap[name,'A']['net']
        parent='clk' if input_net=='clk' else drivers[input_net]
        dot.append(f'"{parent}" -> "{name}";')
    for row in clock_paths:
        name=row['instance']
        typ=before[name]['master'].split('__')[1]
        dot.append(f'"{name}" [label="{name} / {typ}\\n{row["pin"]}",fillcolor="#dcfce7"];')
        dot.append(f'"{row["root_to_sink_buffers"][-1]}" -> "{name}";')
    for name in dummy:
        parent=drivers[ap[name,'A']['net']]
        dot.append(f'"{name}" [label="{name} / clkbuf_1\\nbalancing load (X open)",fillcolor="#fef3c7"];')
        dot.append(f'"{parent}" -> "{name}" [style=dashed];')
    dot.append('}')
    (reports/'cts_topology.dot').write_text('\n'.join(dot)+'\n')
    subprocess.run(['dot','-Tsvg',str(reports/'cts_topology.dot'),'-o',str(run/'images/cts_topology.svg')],check=True)
    subprocess.run(['dot','-Tpng',str(reports/'cts_topology.dot'),'-o',str(run/'images/cts_topology.png')],check=True)
    print(json.dumps({k:summary[k] for k in ['status','original_instances','preserved_latches','clock_tree_buffers',
          'clock_balance_dummy_loads','final_instances','routed_signal_clock_nets','global_route_overflow',
          'detailed_route_drc_violations','detailed_signal_clock_wirelength_um','detailed_route_vias',
          'parasitic_extraction','post_route_sta']},indent=2))


if __name__=='__main__':
    main()
