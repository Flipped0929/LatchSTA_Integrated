#!/usr/bin/env python3
"""Convert routed Verilog + distributed SPEF to native SKY130 transistor SPICE."""
import argparse
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
import csv
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))
import run_counter as base
spec = importlib.util.spec_from_file_location('extraction', ROOT/'openroad/verify_extraction.py')
extraction = importlib.util.module_from_spec(spec)
spec.loader.exec_module(extraction)
PDK_CELLS = Path(os.environ.get('COUNTER_SKY130_CELL_SOURCE',
                                HERE.parents[4]/'pdk_work/sources/sky130_fd_sc_hd')).resolve()/'cells'
PDK_LIB = Path(os.environ.get('COUNTER_SKY130_NGSPICE_LIB',
                             Path.home()/'eda/pdk/sky130A/libs.tech/ngspice/sky130.lib.spice')).resolve()
PERIOD = 1.8
CYCLES = base.CYCLES


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def convert(out):
    pex = ROOT/'openroad/pex_02'
    extraction.validate_pex_archive(pex)
    spef = pex/'results/counter.nominal.spef'
    verilog = pex/'inputs/counter_routed.v'
    assert digest(spef) == digest(ROOT/'openroad/sta_postroute_1p8ns_01/inputs/counter.nominal.spef')
    inputs = out/'inputs'
    models = out/'models'
    inputs.mkdir(); models.mkdir()
    version = subprocess.run([shutil.which('ngspice'), '--version'], capture_output=True, text=True, check=True)
    (out/'ngspice_version.txt').write_text(version.stdout+version.stderr)
    init = Path.home()/'.spiceinit'
    if init.exists():
        shutil.copyfile(init, inputs/'spiceinit.reference')
    shutil.copyfile(Path(__file__), inputs/'run_postlayout.py.reference')
    shutil.copyfile(HERE/'run_counter.py', inputs/'run_counter.py.reference')
    shutil.copyfile(ROOT/'openroad/verify_extraction.py', inputs/'verify_extraction.py.reference')
    shutil.copyfile(spef, inputs/'counter.nominal.spef')
    shutil.copyfile(verilog, inputs/'counter_routed.v')
    nets, ports = extraction.parse_spef(spef)
    owners = {}
    coupling = defaultdict(list)
    for net, obj in nets.items():
        local = set(obj['connections']) | obj['internal'] | {n for r in obj['resistors'] for n in r[:2]}
        assert {n for n,c in obj['ground']} == local
        for n in local:
            assert n not in owners
            owners[n] = net
        for a,b,c in obj['coupling']:
            coupling[tuple(sorted((a,b)))].append(c)
    for (a,b), caps in coupling.items():
        assert a in owners and b in owners and owners[a] != owners[b]
        assert len(caps) == 2 and caps[0] == caps[1]
    names = {n:f'n{i:04d}' for i,n in enumerate(sorted(owners))}
    names.update({'clk':'clk', 'rst_n':'rst_n', 'en':'en', **{f'count[{i}]':f'q{i}' for i in range(4)}})
    for i in range(4):
        names.update({f'_{17+i}_:Q':f'master[{i}]', f'_{17+i}_:D':f'_00_[{i}]',
                      f'_{17+i}_:GATE_N':f'ckm[{i}]', f'_{21+i}_:GATE':f'cks[{i}]',
                      f'_{21+i}_:Q':f'slave[{i}]'})
    for inst, alias in [('clkbuf_0_clk','clk_root_out'),('clkbuf_1_0__f_clk','clk_leaf0_out'),('clkbuf_1_1__f_clk','clk_leaf1_out')]:
        names[inst+':X'] = alias
    assert set(names) == set(owners) and len(set(n.lower() for n in names.values())) == len(names)
    with (models/'node_map.csv').open('w', newline='') as f:
        w=csv.writer(f);w.writerow(['spef_node','spice_dut_node','logical_net'])
        w.writerows((n,names[n],owners[n]) for n in sorted(names))
    instances = re.findall(r'(sky130_fd_sc_hd__\w+)\s+(\w+)\s*\((.*?)\);', verilog.read_text(), re.S)
    assert len(instances) == 22
    aliases = {f'count[{i}]':f'slave[{i}]' for i in range(4)}
    pins_used = set()
    native = {}
    body = ['* Distributed routed interconnect; pin capacitance supplied by native MOS devices.',
            '.subckt counter_postroute clk rst_n en VPWR VGND q3 q2 q1 q0']
    mos_count = 0
    for cell, inst, text in instances:
        pins = dict(re.findall(r'\.(\w+)\(([^()]*)\)', text))
        if cell not in native:
            family = cell.split('__')[1].rsplit('_',1)[0]
            path = PDK_CELLS/family/(cell+'.spice')
            native[cell] = (path,path.read_text())
        path, model = native[cell]
        order = re.search(r'^\.subckt\s+'+re.escape(cell)+r'\s+([^\n]+)',model,re.M|re.I)[1].split()
        nodes=[]
        for pin in order:
            if pin in ('VGND','VNB','VPB','VPWR'):
                nodes.append('VGND' if pin in ('VGND','VNB') else 'VPWR')
            elif inst == 'clkload0' and pin == 'X':
                assert pin not in pins
                nodes.append('dummy_clkload0_x')
            else:
                node = inst+':'+pin
                assert node in owners and owners[node] == aliases.get(pins[pin],pins[pin]), (node,pins)
                assert node not in pins_used
                pins_used.add(node);nodes.append(names[node])
        mos_count += len(re.findall(r'^X\S+.*sky130_fd_pr__',model,re.M))
        body.append('X'+inst+' '+' '.join(nodes)+' '+cell)
    expected_pins = {n for obj in nets.values() for n,(kind,direction) in obj['connections'].items() if kind == '*I'}
    assert pins_used == expected_pins and len(pins_used) == 73
    assert mos_count == 248, mos_count
    resistors=[];ground=[]
    for obj in nets.values():
        resistors.extend(obj['resistors']);ground.extend(obj['ground'])
    for i,(a,b,r) in enumerate(resistors):
        assert r > 0
        body.append(f'Rwire{i} {names[a]} {names[b]} {r:.12g}')
    for i,(n,c) in enumerate(ground):
        if c > 0:
            body.append(f'Cg{i} {names[n]} VGND {c:.12g}p')
    for i,((a,b),caps) in enumerate(sorted(coupling.items())):
        if caps[0] > 0:
            body.append(f'Cc{i} {names[a]} {names[b]} {caps[0]:.12g}p')
    body.append('.ends counter_postroute')
    (models/'counter_postroute.spice').write_text('\n'.join(body)+'\n')
    (models/'sky130_cells.spice').write_text('\n'.join(native[k][1] for k in sorted(native)))
    audit = dict(status='PASS', routed_nets=len(nets), rc_nodes=len(names), instance_count=len(instances),
                 cell_types=dict(Counter(c for c,i,t in instances)), mos_devices=mos_count,
                 cell_pins_backannotated=len(pins_used), ports=len(ports), resistors=len(resistors),
                 ground_cap_entries=len(ground), positive_ground_capacitors=sum(c>0 for n,c in ground),
                 distinct_coupling_pairs=len(coupling), positive_coupling_capacitors=sum(v[0]>0 for v in coupling.values()),
                 ground_cap_sum_ff=sum(c for n,c in ground)*1000,
                 coupling_cap_sum_ff=sum(v[0] for v in coupling.values())*1000,
                 summed_spef_d_net_ff=sum(o['total_pf'] for o in nets.values())*1000,
                 resistor_sum_ohm=sum(r for a,b,r in resistors),
                 coupling_handling='One capacitor per reciprocal SPEF pair; full two-node coupling retained.',
                 pin_cap_handling='SPEF PIN_CAP NONE; native MOS intrinsic capacitance, no Liberty pin-cap duplication.',
                 dummy_clock_load='clkload0 included; its unconnected X output is left open.',
                 source_pex_manifest_verified=True, matches_1p8ns_sta_spef=True,
                 sources=[dict(path=str(path),sha256=digest(path)) for path in [verilog,spef,PDK_LIB]+[native[k][0] for k in sorted(native)]])
    assert audit['resistors']==89 and audit['rc_nodes']==113 and audit['positive_coupling_capacitors']==166
    (out/'conversion_audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    return audit


def deck(out, step):
    save=['v(clk)','v(rst_n)','v(en)','i(VDD)']+[f'v(q{i})' for i in range(4)]
    save += [f'v(xdut.{sig}[{i}])' for sig in ('master','_00_','ckm','cks','slave') for i in range(4)]
    save += [f'v(xdut.{s})' for s in ('clk_root_out','clk_leaf0_out','clk_leaf1_out')]
    return f'''Post-layout counter T=1.8ns; native MOS + CTS + distributed SPEF RC
.lib "{PDK_LIB}" tt
.include "{out/'models/sky130_cells.spice'}"
.include "{out/'models/counter_postroute.spice'}"
.temp 25
.option reltol=1e-4 abstol=1e-12 vntol=1e-6
VDD VPWR 0 1.8
VSS VGND 0 0
VCLK clk 0 PULSE(0 1.8 0.85n 100p 100p 0.8n 1.8n)
VRST rst_n 0 {base.pwl(PERIOD,0,1.0)}
VEN en 0 {base.pwl(PERIOD,1,1.0)}
XDUT clk rst_n en VPWR VGND q3 q2 q1 q0 counter_postroute
C0 q0 0 10f
C1 q1 0 10f
C2 q2 0 10f
C3 q3 0 10f
.save {' '.join(save)}
.control
set num_threads=1
set filetype=binary
tran {step:g}p {(CYCLES+.45)*PERIOD:.12g}n 0 {step:g}p
write counter.raw
.endc
.end
'''


def crossings(t,v,np, rising=True):
    if rising:
        idx=np.flatnonzero((v[:-1]<.9)&(v[1:]>=.9))
    else:
        idx=np.flatnonzero((v[:-1]>.9)&(v[1:]<=.9))
    return t[idx]+(.9-v[idx])*(t[idx+1]-t[idx])/(v[idx+1]-v[idx])


def analyze(result,out,np):
    folder=out/result['name']
    names,data=base.raw_data(folder/'counter.raw',np)
    t=data[:,0]*1e9
    def wave(name):return data[:,names.index('v('+name+')')]
    root=crossings(t,wave('clk'),np)
    assert len(root)==CYCLES and np.allclose(root,(np.arange(CYCLES)+.5)*PERIOD,atol=1e-6,rtol=0)
    q=np.column_stack([wave(f'q{i}') for i in range(4)])
    rows=[];expected=0;previous=0;wraps=0;control_errors=[]
    for n in range(CYCLES):
        rst,en=base.controls(n)
        for signal,want in [('rst_n',rst),('en',en)]:
            value=np.interp(root[n]-.05,t,wave(signal))
            if not (value>=1.44 if want else value<=.36):
                control_errors.append(dict(cycle=n,signal=signal,actual_v=float(value)))
        previous=expected
        expected=0 if not rst else (expected+en)%16
        wraps+=int(rst and en and previous==15)
        row=dict(cycle=n,rising_edge_ns=float(root[n]),rst_n=rst,en=en,expected=expected)
        bits=np.array([(expected>>i)&1 for i in range(4)])
        passed=True
        # Predetermined settled/late samples, relative to the source rising edge.
        # These check functional behavior, not an external receiver setup constraint.
        for label,phase in [('settled',.65),('late',.90)]:
            ts=root[n]+phase*PERIOD
            volts=np.array([np.interp(ts,t,q[:,i]) for i in range(4)])
            valid=((volts<=.36)|(volts>=1.44)).all()
            observed=int(sum((volts>=1.44)*2**np.arange(4))) if valid else -1
            passed &= bool(valid and observed==expected)
            row[label+'_sample_ns']=float(ts);row[label+'_observed']=observed
            for i,v in enumerate(volts):row[f'{label}_q{i}_v']=float(v)
        a,b=np.searchsorted(t,[root[n]+.65*PERIOD,root[n]+.95*PERIOD])
        stable=bool(np.where(bits,q[a:b]>=1.44,q[a:b]<=.36).all())
        passed &= stable
        start=np.searchsorted(t,root[n])
        good=np.where(bits,q[start:b]>=1.44,q[start:b]<=.36).all(axis=1)
        bad=np.flatnonzero(~good)
        k=start if not len(bad) else start+int(bad[-1])+1
        settling=float(t[k]-root[n]) if k<b else None
        row.update(stable_window_pass=stable,passed=passed,settling_to_20_80_ns=settling)
        rows.append(row)
    clocks={}
    for sig in [f'{s}[{i}]' for s in ('ckm','cks') for i in range(4)]:
        v=wave('xdut.'+sig)
        rise=crossings(t,v,np);fall=crossings(t,v,np,False)
        assert len(rise)==CYCLES and len(fall)==CYCLES, (sig,len(rise),len(fall))
        assert np.all(fall>rise) and np.all(rise[1:]>fall[:-1])
        clocks[sig]=dict(rising_edges=len(rise),falling_edges=len(fall),
                        rise_latency_min_ns=float(min(rise-root)),rise_latency_max_ns=float(max(rise-root)),
                        high_width_min_ns=float(min(fall-rise)),low_width_min_ns=float(min(rise[1:]-fall[:-1])))
    with (folder/'samples.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    with gzip.open(folder/'waveforms.csv.gz','wt',newline='') as f:
        w=csv.writer(f);w.writerow(names);w.writerows(data)
    summary=dict(result,status='PASS' if all(r['passed'] for r in rows) and not control_errors else 'FAIL',
                 cycles_checked=CYCLES,failed_cycles=[r['cycle'] for r in rows if not r['passed']],
                 control_errors=control_errors,states_covered=sorted(set(r['expected'] for r in rows)),
                 modulo_16_wraps=wraps,enable_hold_cycles=sum(r['rst_n'] and not r['en'] for r in rows),
                 reset_cycles=sum(not r['rst_n'] for r in rows),raw_points=len(t),stop_ns=float(t[-1]),
                 clock_period_ns=float(np.median(np.diff(root))),sink_clocks=clocks,
                 max_settling_to_20_80_ns=max((r['settling_to_20_80_ns'] for r in rows if r['settling_to_20_80_ns'] is not None),default=None),
                 validation_window_ns_after_source_rise=[.65*PERIOD,.95*PERIOD],
                 sample_offsets_ns_after_source_rise=[.65*PERIOD,.9*PERIOD],
                 valid_low_max_v=.36,valid_high_min_v=1.44)
    (folder/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    return summary,names,data,rows


def plot(result,out,np):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    summary,names,data,rows=result
    t=data[:,0]*1e9
    plt.rcParams.update({'font.size':9,'axes.spines.top':False,'axes.spines.right':False})
    colors=['#2563eb','#16a34a','#ea580c','#9333ea']
    panels=[('overview',0,128.45),('count_and_hold',0,53),('reset_and_enable',60,86),('wrap_detail',18.5,21.3)]
    signals=['clk','xdut.ckm[0]','xdut.cks[3]','rst_n','en','q3','q2','q1','q0']
    for name,start,stop in panels:
        mask=(t>=start*PERIOD)&(t<=stop*PERIOD)
        fig,axes=plt.subplots(10,1,figsize=(16,13),sharex=True,layout='constrained',gridspec_kw={'height_ratios':[1]*9+[1.6]})
        for j,sig in enumerate(signals):
            ax=axes[j];ax.plot(t[mask],data[mask,names.index('v('+sig+')')],lw=.85,color=colors[(j-5)%4] if j>=5 else '#475569')
            label=sig.replace('xdut.','')
            ax.set_ylabel(label+'\n(V)',rotation=0,ha='right',va='center');ax.set_ylim(-.2,2.0);ax.set_yticks([0,1.8]);ax.grid(alpha=.2)
        ts=np.array([r['settled_sample_ns'] for r in rows]);good=(ts>=start*PERIOD)&(ts<=stop*PERIOD)
        expected=np.array([r['expected'] for r in rows]);observed=np.array([r['settled_observed'] for r in rows])
        axes[-1].step(ts[good],expected[good],where='mid',color='#94a3b8',lw=1.3,label='Expected at samples')
        axes[-1].plot(ts[good],observed[good],'.',ms=4,color='#2563eb',label='SPICE settled sample')
        axes[-1].set_ylabel('Count');axes[-1].set_yticks([0,4,8,12,15]);axes[-1].set_ylim(-1.5,16.5);axes[-1].grid(alpha=.2);axes[-1].legend(loc='upper right',ncol=2)
        axes[-1].set_xlabel('Time (ns)');axes[-1].set_xlim(start*PERIOD,stop*PERIOD)
        axes[0].set_title('Post-layout counter | T = 1.8 ns | SKY130 TT, 1.8 V, 25 C | CTS + distributed SPEF RC | 10 fF/output\n'+
                          f"{summary['status']}: {summary['cycles_checked']} cycles, {summary['modulo_16_wraps']} wraps | max step {summary['max_step_ps']} ps",loc='left',fontsize=12)
        for ext in ('png','svg'):fig.savefig(out/(name+'.'+ext),dpi=160,bbox_inches='tight',pad_inches=.15)
        plt.close(fig)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=HERE/'postlayout_1p8ns_01')
    parser.add_argument('--prepare-only',action='store_true')
    parser.add_argument('--resume',action='store_true')
    args=parser.parse_args()
    out=args.output.resolve()
    if not args.resume:
        out.mkdir(parents=True,exist_ok=False)
        audit=convert(out)
        jobs=[(f'T_1p8ns_{str(step).replace(".","p")}ps',PERIOD,step,deck(out,step)) for step in (2.5,1.25)]
        for name,p,step,text in jobs:(out/(name+'_tb.spice')).write_text(text)
        print(json.dumps(audit,indent=2),flush=True)
        if args.prepare_only:return
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(lambda j:base.run_one(j,shutil.which('ngspice'),out),jobs))
        (out/'runs.json').write_text(json.dumps(results,indent=2)+'\n')
    import numpy as np
    results=json.loads((out/'runs.json').read_text())
    analyzed=[analyze(r,out,np) for r in results]
    first,second=analyzed
    sampled_diff=max(abs(a[f'{label}_q{i}_v']-b[f'{label}_q{i}_v']) for a,b in zip(first[3],second[3]) for label in ('settled','late') for i in range(4))
    convergence=dict(status='PASS' if all(x[0]['status']=='PASS' for x in analyzed) and sampled_diff<.01 else 'FAIL',
                     max_sample_voltage_difference_v=sampled_diff,
                     max_settling_difference_ns=max(abs(a['settling_to_20_80_ns']-b['settling_to_20_80_ns']) for a,b in zip(first[3],second[3]) if a['settling_to_20_80_ns'] is not None and b['settling_to_20_80_ns'] is not None))
    (out/'summary.json').write_text(json.dumps(dict(status=convergence['status'],period_ns=PERIOD,frequency_mhz=1000/PERIOD,
        model_corner='TT',temperature_c=25,supply_v=1.8,output_load_ff=10,input_rise_fall_ps=100,
        input_control_delay_ns=1.0,runs=[x[0] for x in analyzed],time_step_convergence=convergence),indent=2)+'\n')
    plot(first,out,np)
    manifest=[]
    for path in sorted(out.rglob('*')):
        if path.is_file() and path.name!='manifest.json':manifest.append(dict(path=str(path.relative_to(out)),sha256=digest(path),bytes=path.stat().st_size))
    (out/'manifest.json').write_text(json.dumps(dict(artifacts=manifest),indent=2)+'\n')
    print(json.dumps(dict(status=convergence['status'],runs=[x[0] for x in analyzed],convergence=convergence),indent=2),flush=True)
    if convergence['status']!='PASS':raise SystemExit(1)


if __name__=='__main__':main()
