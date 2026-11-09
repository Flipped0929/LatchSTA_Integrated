#!/usr/bin/env python3
"""Prepare a logical STA view and run post-route OpenSTA without implementation edits."""
import argparse
import csv
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import os
import math

from verify_extraction import validate_pex_archive

HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def logical_sta_view(text):
    match = re.search(r'\bmodule\s+counter\s*\((.*?)\);', text, re.S)
    assert match
    ports = [p.strip() for p in match[1].split(',')]
    assert set(ports) == {'clk','en','rst_n','count','VDD','VSS'}
    body = text[match.end():]
    for name in ['VDD','VSS']:
        body,count = re.subn(r'^\s*inout\s+'+name+r'\s*;\s*$', '', body, count=1, flags=re.M)
        assert count == 1
        assert not re.search(r'\b'+name+r'\b', body), f'{name} is connected; refusing to remove it'
    header = 'module counter ('+', '.join(p for p in ports if p not in ('VDD','VSS'))+');'
    result = '// STA view: only disconnected VDD/VSS top ports removed; all 22 cells retained.\n'+header+body
    # Prove every instance, named pin connection and output alias is identical.
    pattern = r'sky130_fd_sc_hd__\w+\s+\w+\s*\(.*?\);'
    assert re.findall(pattern,text,re.S) == re.findall(pattern,result,re.S)
    assert len(re.findall(pattern,result,re.S)) == 22
    assert re.findall(r'assign[^;]+;',text) == re.findall(r'assign[^;]+;',result)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pex',type=Path,default=HERE/'pex_02')
    parser.add_argument('--output',type=Path,default=HERE/('sta_postroute_'+datetime.now().strftime('%Y%m%d_%H%M%S')))
    parser.add_argument('--sta',default=shutil.which('sta'))
    parser.add_argument('--period-ns',type=float,
                        help='Override the clock period and use the existing low-start 50%% duty cycle')
    args=parser.parse_args()
    out,pex=args.output.resolve(),args.pex.resolve()
    if out.exists(): parser.error('Output already exists; select a new directory')
    if not args.sta: parser.error('OpenSTA executable not found')
    if args.period_ns is not None and (not math.isfinite(args.period_ns) or args.period_ns <= 0):
        parser.error('--period-ns must be finite and positive')
    pnr=validate_pex_archive(pex)
    pnr_manifest=json.loads((pnr/'manifest.json').read_text())['inputs_and_outputs']
    liberty_entry=next(e for e in pnr_manifest if e['kind']=='liberty')
    liberty=HERE.parents[2]/'sky130_pdk'/Path(liberty_entry['path']).name
    if not liberty.is_file() or sha(liberty)!=liberty_entry['sha256']:
        liberty=Path(liberty_entry['path'])
    assert sha(liberty)==liberty_entry['sha256'], 'Liberty differs from the implementation library'
    for subdir in ['inputs','reports','results','logs']: (out/subdir).mkdir(parents=True)
    source=pex/'inputs/counter_routed.v'
    shutil.copyfile(source,out/'inputs/counter_routed_original.v')
    (out/'inputs/counter_sta.v').write_text(logical_sta_view(source.read_text()))
    sdc_source=pex/'inputs/counter_routed.sdc'
    shutil.copyfile(sdc_source,out/'inputs/counter_routed_original.sdc')
    sdc=sdc_source.read_text()
    clock_lines=re.findall(r'^create_clock[^\n]+$',sdc,re.M)
    assert len(clock_lines)==1 and '-name clk ' in clock_lines[0]
    source_period=float(re.search(r'-period\s+([\d.eE+-]+)',clock_lines[0])[1])
    period=source_period if args.period_ns is None else args.period_ns
    if args.period_ns is not None:
        clock_line=(f'create_clock -name clk -period {period:.15g} '
                    f'-waveform {{{period/2:.15g} {period:.15g}}} [get_ports {{clk}}]')
        sdc=sdc.replace(clock_lines[0],clock_line,1)
        assert sdc.replace(clock_line,clock_lines[0],1)==sdc_source.read_text()
    (out/'inputs/counter_routed.sdc').write_text(sdc)
    shutil.copyfile(pex/'results/counter.nominal.spef',out/'inputs/counter.nominal.spef')
    shutil.copyfile(HERE/'postroute_sta.tcl',out/'inputs/postroute_sta.tcl')
    env=dict(os.environ,COUNTER_POSTSTA_RUN=str(out),COUNTER_POSTSTA_LIBERTY=str(liberty),
             COUNTER_POSTSTA_PERIOD_NS=str(period))
    with (out/'logs/opensta.log').open('w') as stream:
        result=subprocess.run([args.sta,'-no_init','-no_splash','-exit',str(out/'inputs/postroute_sta.tcl')],
                              env=env,stdout=stream,stderr=subprocess.STDOUT)
    log=(out/'logs/opensta.log').read_text()
    if result.returncode or 'POST_ROUTE_STA_COMPLETE' not in log or re.search(r'^Error',log,re.M):
        print(log,end='')
        raise SystemExit('Post-route STA failed; inspect '+str(out/'logs/opensta.log'))
    print('POST_ROUTE_STA_COMPLETE:',out)
    files=[dict(kind='liberty',path=str(liberty),sha256=sha(liberty))]
    for rel in ['inputs/counter_routed_original.v','inputs/counter_sta.v','inputs/counter_routed_original.sdc','inputs/counter_routed.sdc',
                'inputs/counter.nominal.spef','inputs/postroute_sta.tcl','results/effective.sdc']:
        files.append(dict(kind='artifact',path=rel,sha256=sha(out/rel)))
    (out/'manifest.json').write_text(json.dumps(dict(
        sta_version=subprocess.check_output([args.sta,'-version'],text=True).strip(),
        pex_source=str(pex),pnr_source=str(pnr),files=files,
        netlist_adaptation='Only disconnected VDD/VSS top ports removed; all named cell connections preserved',
        clock_period_ns=period,source_sdc_clock_period_ns=source_period,
        period_overridden=args.period_ns is not None,
        clock_source_transition_ns=0.06,coupling_reduction_factor=1.0,crpr_enabled=True,
        crpr_mode='same_transition',library_corner='TT 025C 1v80',rc_corner='nominal'),indent=2)+'\n')
    with (out/'reports/metrics.tsv').open() as stream:
        metrics={r['metric']:r['value'] for r in csv.DictReader(stream,delimiter='\t')}
    print(json.dumps(metrics,indent=2))
    print('Reports:',out)


if __name__=='__main__':
    main()
