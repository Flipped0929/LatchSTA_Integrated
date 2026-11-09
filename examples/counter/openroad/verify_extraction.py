#!/usr/bin/env python3
"""Validate SPEF, OpenDB RC values and routed geometry without STA."""
import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
import math
from pathlib import Path
import re
import shutil

HERE = Path(__file__).resolve().parent


def tsv(path):
    with path.open() as stream:
        return list(csv.DictReader(stream, delimiter='\t'))


def numeric(token):
    result = float(token)
    assert math.isfinite(result) and result >= 0, f'Invalid RC value: {token}'
    return result


def validate_pex_archive(pex):
    """Verify saved artifacts and resolve archived sources in a relocated checkout."""
    entries = json.loads((pex/'manifest.json').read_text())['inputs_and_outputs']
    routed_odb = Path(next(item['path'] for item in entries if item['kind'] == 'routed_odb'))
    pnr = pex.parent/routed_odb.parents[1].name
    sources = {
        'routed_odb': pnr/'results'/routed_odb.name,
        'extraction_rules': pex/'inputs/sky130hd_rcx_patterns.rules',
        'netlist': pex/'inputs/counter_routed.v',
        'sdc_reference_only': pex/'inputs/counter_routed.sdc',
    }
    for entry in entries:
        path = pex/entry['path'] if entry['kind'] == 'artifact' else sources[entry['kind']]
        if hashlib.sha256(path.read_bytes()).hexdigest() != entry['sha256']:
            raise ValueError(f'Extraction input/output changed: {path}')
    return pnr


def parse_spef(path):
    text = path.read_text()
    assert '\0' not in text and '*DESIGN "counter"' in text
    assert '*C_UNIT 1 PF' in text and '*R_UNIT 1 OHM' in text
    assert '"PIN_CAP NONE"' in text
    names, nets, ports = {}, {}, {}
    section = None
    current = None

    def expand(node):
        return re.sub(r'^\*(\d+)', lambda m: names[int(m[1])], node)

    for line in text.splitlines():
        a = line.split()
        if not a:
            continue
        if a[0] == '*NAME_MAP':
            section = 'map'
        elif a[0] == '*PORTS':
            section = 'ports'
        elif a[0] == '*D_NET':
            name = expand(a[1])
            assert name not in nets, f'Duplicate net {name}'
            current = dict(name=name, total_pf=numeric(a[2]), connections={},
                           internal=set(), ground=[], coupling=[], resistors=[])
            nets[name] = current
            section = None
        elif a[0] in ('*CONN', '*CAP', '*RES'):
            section = a[0]
        elif a[0] == '*END':
            section = None
        elif section == 'map':
            idx = int(a[0][1:])
            assert idx not in names, f'Duplicate name map ID {idx}'
            names[idx] = a[1]
        elif section == 'ports':
            ports[expand(a[0])] = a[1]
        elif section == '*CONN':
            node = expand(a[1])
            if a[0] == '*N':
                current['internal'].add(node)
            else:
                assert a[0] in ('*P','*I')
                assert node not in current['connections']
                current['connections'][node] = (a[0], a[2])
        elif section == '*CAP':
            assert a[0].isdigit()
            if len(a) == 3:
                current['ground'].append((expand(a[1]), numeric(a[2])))
            else:
                assert len(a) == 4
                current['coupling'].append((expand(a[1]), expand(a[2]), numeric(a[3])))
        elif section == '*RES':
            assert len(a) == 4 and a[0].isdigit()
            current['resistors'].append((expand(a[1]), expand(a[2]), numeric(a[3])))
    return nets, ports


def intervals(rectangles, x0, x1):
    spans = sorted((y0,y1) for a,y0,b,y1 in rectangles if a <= x0 and b >= x1)
    result = []
    for a,b in spans:
        if result and a <= result[-1][1]:
            result[-1] = (result[-1][0],max(b,result[-1][1]))
        else:
            result.append((a,b))
    return result


def geometry_check(before, after):
    def collect(rows):
        metal = defaultdict(list)
        vias = Counter()
        for row in rows:
            rect = tuple(int(row[k]) for k in ('xmin','ymin','xmax','ymax'))
            if row['kind'] == 'via':
                vias[(row['net'],row['via'],*rect)] += 1
            else:
                metal[row['net'],row['layer']].append(rect)
        return metal,vias
    bm,bv = collect(before)
    am,av = collect(after)
    assert bv == av, 'Physical vias changed during extraction'
    assert set(bm) == set(am), 'Routed layer coverage changed'
    for key in bm:
        xs = sorted({x for r in bm[key]+am[key] for x in (r[0],r[2])})
        for x0,x1 in zip(xs,xs[1:]):
            assert intervals(bm[key],x0,x1) == intervals(am[key],x0,x1), f'Metal geometry changed: {key}'
    return dict(status='PASS', via_shapes=sum(bv.values()), net_layer_groups=len(bm),
                metal_shapes_before=sum(map(len,bm.values())), metal_shapes_after=sum(map(len,am.values())),
                comparison='Exact rectangle-union equality per net/layer; via shapes including multiplicity')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run',nargs='?',type=Path,default=HERE/'pex_02')
    args=parser.parse_args()
    run=args.run.resolve()
    nets,ports=parse_spef(run/'results/counter.nominal.spef')
    expected=defaultdict(dict)
    directions={'INPUT':'I','OUTPUT':'O','INOUT':'B'}
    for row in tsv(run/'reports/expected_connections.tsv'):
        node=row['pin'] if row['kind']=='port' else row['instance']+':'+row['pin']
        kind='*P' if row['kind']=='port' else '*I'
        expected[row['net']][node]=(kind,directions[row['direction']])
    assert set(nets)==set(expected) and len(nets)==24, 'Missing/extra extracted nets'
    assert ports=={'clk':'I','en':'I','rst_n':'I',**{f'count[{i}]':'O' for i in range(4)}}
    owners={}
    for name,net in nets.items():
        assert net['connections']==expected[name], f'SPEF connection mismatch for {name}'
        local=set(net['connections']) | net['internal'] | {n for r in net['resistors'] for n in r[:2]}
        for node in local:
            assert node not in owners, f'Node belongs to more than one net: {node}'
            owners[node]=name
        assert {n for n,c in net['ground']}==local, f'Incomplete ground-cap node list: {name}'
        adjacency=defaultdict(set)
        for a,b,res in net['resistors']:
            assert a!=b
            adjacency[a].add(b);adjacency[b].add(a)
        reached=set()
        stack=[next(iter(local))]
        while stack:
            node=stack.pop()
            if node in reached:continue
            reached.add(node);stack.extend(adjacency[node]-reached)
        assert reached==local, f'Disconnected extracted RC network: {name}'
        assert len(net['resistors'])==len(local)-1, f'Expected resistor tree: {name}'
    coupling=defaultdict(list)
    data=[]
    db={r['net']:r for r in tsv(run/'reports/after_rc.tsv')}
    for name,net in nets.items():
        ground=sum(c for node,c in net['ground'])
        cc=sum(c for a,b,c in net['coupling'])
        assert math.isclose(net['total_pf'],ground+cc,rel_tol=1e-5,abs_tol=1e-9), f'Capacitance sum mismatch: {name}'
        for a,b,c in net['coupling']:
            assert a in owners and b in owners, f'Unknown coupling node: {a} / {b}'
            assert owners[a]!=owners[b] and name in (owners[a],owners[b])
            coupling[tuple(sorted((a,b)))].append((name,c))
        resistance=sum(r for a,b,r in net['resistors'])
        row=db[name]
        assert int(row['rsegs'])==len(net['resistors'])
        assert int(row['cap_nodes'])==len(net['ground'])
        assert math.isclose(float(row['resistance_sum_ohm']),resistance,rel_tol=1e-5,abs_tol=1e-5)
        assert math.isclose(float(row['ground_cap_sum_ff']),ground*1000,rel_tol=1e-5,abs_tol=1e-6)
        data.append(dict(net=name,connections=len(net['connections']),resistors=len(net['resistors']),
                         ground_cap_nodes=len(net['ground']),coupling_entries=len(net['coupling']),
                         resistance_sum_ohm=resistance,ground_cap_ff=ground*1000,
                         coupling_cap_incident_ff=cc*1000,d_net_total_ff=net['total_pf']*1000))
    for pair,entries in coupling.items():
        assert len(entries)==2 and {n for n,c in entries}=={owners[n] for n in pair}, f'Nonreciprocal coupling: {pair}'
        assert entries[0][1]==entries[1][1], f'Coupling value mismatch: {pair}'
    geo=geometry_check(tsv(run/'reports/before_geometry.tsv'),tsv(run/'reports/after_geometry.tsv'))
    before=(run/'inputs/before_extract.def').read_text()
    after=(run/'results/09_extracted.def').read_text()
    assert before.split('\nNETS ',1)[0]==after.split('\nNETS ',1)[0], 'Placement/pins/PDN changed'
    # Confirm the original implementation had no RC objects before extraction.
    for row in tsv(run/'reports/before_rc.tsv'):
        assert int(row['rsegs'])==int(row['cap_nodes'])==0
    log_source=run.parent/(run.name+'.openroad.log')
    log=log_source.read_text()
    assert '[ERROR' not in log and '[WARNING' not in log and 'PARASITIC_EXTRACTION_COMPLETE' in log
    rcx_counts = re.search(r'Extract (\d+) nets, (\d+) rsegs, (\d+) caps, (\d+) ccs',log)
    assert rcx_counts
    logged_nets,logged_rsegs,logged_caps,logged_ccs = map(int,rcx_counts.groups())
    assert logged_nets == len(nets)
    assert logged_rsegs == sum(len(n['resistors']) for n in nets.values()) + len(nets)
    assert logged_caps == sum(len(n['ground']) for n in nets.values())
    assert logged_ccs == len(coupling)
    flow=(run/'inputs/extract.tcl').read_text()
    assert not re.search(r'^\s*(?:read_liberty|read_sdc|read_spef|report_checks|report_wns|report_tns|report_worst_slack|repair_timing)\b',flow,re.M)
    status=(run/'reports/extraction_status.txt').read_text()
    assert 'post_route_sta=NOT RUN' in status and 'sta_spef_annotation=NOT RUN' in status
    summary=dict(status='PASS',design='counter',corner='nominal',routed_nets=len(nets),ports=len(ports),
                 connection_terminals=sum(len(n['connections']) for n in nets.values()),
                 exported_resistors=sum(len(n['resistors']) for n in nets.values()),
                 ground_cap_nodes=sum(len(n['ground']) for n in nets.values()),
                 unique_coupling_capacitors=len(coupling),
                 positive_unique_coupling_capacitors=sum(v[0][1]>0 for v in coupling.values()),
                 zero_unique_coupling_capacitors=sum(v[0][1]==0 for v in coupling.values()),
                 coupling_entries_in_spef=sum(len(n['coupling']) for n in nets.values()),
                 total_ground_cap_ff=sum(d['ground_cap_ff'] for d in data),
                 unique_coupling_cap_sum_ff=sum(v[0][1] for v in coupling.values())*1000,
                 sum_d_net_total_cap_ff=sum(d['d_net_total_ff'] for d in data),
                 sum_resistor_values_ohm=sum(d['resistance_sum_ohm'] for d in data),
                 resistance_units='OHM',spef_capacitance_units='PF',report_capacitance_units='fF',
                 pin_capacitance_included=False,external_sdc_load_included=False,
                 power_grid_rc_networks_included=False,geometry=geo,
                 rc_values_match_saved_odb=True,resistor_networks_connected=True,
                 coupling_pairs_reciprocal=True,post_route_sta='NOT RUN',sta_spef_annotation='NOT RUN')
    with (run/'reports/net_parasitics.csv').open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(data[0]));writer.writeheader();writer.writerows(data)
    (run/'reports/verification.json').write_text(json.dumps(summary,indent=2)+'\n')
    (run/'reports/geometry_verification.json').write_text(json.dumps(geo,indent=2)+'\n')
    cc_rows=[]
    for (a,b),entries in coupling.items():
        cc_rows.append(dict(node1=a,node2=b,net1=owners[a],net2=owners[b],capacitance_ff=entries[0][1]*1000))
    with (run/'reports/coupling_capacitors.csv').open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(cc_rows[0]));writer.writeheader();writer.writerows(cc_rows)
    manifest=[]
    for row in tsv(run/'inputs/sources.tsv'):
        path=Path(row['path'])
        manifest.append(dict(kind=row['kind'],path=str(path),resolved_path=str(path.resolve()),
                             sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    for rel in ['inputs/extract.tcl','inputs/sky130hd_rcx_patterns.rules','inputs/counter_routed.v',
                'inputs/counter_routed.sdc','results/counter.nominal.spef','results/09_extracted.odb','results/09_extracted.def']:
        manifest.append(dict(kind='artifact',path=rel,sha256=hashlib.sha256((run/rel).read_bytes()).hexdigest()))
    assert next(r['sha256'] for r in manifest if r['kind']=='extraction_rules')==hashlib.sha256((run/'inputs/sky130hd_rcx_patterns.rules').read_bytes()).hexdigest()
    original_db=Path(next(r['path'] for r in manifest if r['kind']=='routed_odb'))
    original_manifest=json.loads((original_db.parents[1]/'manifest.json').read_text())
    original_sha=next(r['sha256'] for r in original_manifest['inputs_and_outputs'] if r['path']=='results/08_routed.odb')
    assert original_sha==hashlib.sha256(original_db.read_bytes()).hexdigest(), 'Original routed database changed'
    (run/'manifest.json').write_text(json.dumps(dict(inputs_and_outputs=manifest),indent=2)+'\n')
    shutil.copyfile(log_source,run/'logs/extraction.log')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    main()
