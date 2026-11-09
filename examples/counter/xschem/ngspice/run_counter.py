#!/usr/bin/env python3
"""Run and check transistor-level SKY130 counter simulations at three periods."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import time

HERE = Path(__file__).resolve().parent
VDD = 1.8
RISE_NS = 0.1
CYCLES = 128


def controls(n):
    if n < 4:
        return 0, int(n == 3)
    if n < 39:
        return 1, 1
    if n < 47:
        return 1, 0
    if n < 67:
        return 1, 1
    if n < 70:
        return 0, 1
    if n < 74:
        return 1, 0
    if n < 110:
        return 1, 1
    if n < 118:
        return 1, n % 2
    if n < 122:
        return 0, 0
    return 1, 1


def pwl(period, index, delay):
    value = controls(0)[index]
    pairs = [(0.0, VDD * value)]
    for n in range(1, CYCLES):
        new = controls(n)[index]
        if new == value:
            continue
        center = (n - 0.5) * period + delay
        pairs.extend([(center - RISE_NS / 2, VDD * value),
                      (center + RISE_NS / 2, VDD * new)])
        value = new
    return 'PWL(\n+ ' + '\n+ '.join(f'{t:.12g}n {v:.12g}' for t, v in pairs) + ')'


def deck(period, step, delay, model_lib, cells, counter):
    save = ['v(clk)', 'v(rst_n)', 'v(en)', 'i(VDD)']
    save += [f'v(q{i})' for i in range(4)]
    save += [f'v(xdut.master[{i}])' for i in range(4)]
    save += [f'v(xdut._00_[{i}])' for i in range(4)]
    return f'''SKY130 HD counter transistor transient: T={period:g}ns
* TT, 25 C, 1.8 V, 10 fF per output; native cell SPICE, no interconnect PEX.
* Clock 50-percent crossings: rising (n+0.5)*T, falling (n+1)*T.
* Inputs cross 50 percent {delay:g} ns after the preceding rising edge.
.lib "{model_lib}" tt
.include "{cells}"
.include "{counter}"
.temp 25
.option reltol=1e-4 abstol=1e-12 vntol=1e-6
VDD VPWR 0 1.8
VSS VGND 0 0
VCLK clk 0 PULSE(0 1.8 {period / 2 - RISE_NS / 2:.12g}n 100p 100p {period / 2 - RISE_NS:.12g}n {period:.12g}n)
VRST rst_n 0 {pwl(period, 0, delay)}
VEN en 0 {pwl(period, 1, delay)}
XDUT clk rst_n en VPWR VGND q3 q2 q1 q0 counter
C0 q0 0 10f
C1 q1 0 10f
C2 q2 0 10f
C3 q3 0 10f
.save {' '.join(save)}
.control
set num_threads=1
set filetype=binary
tran {step:g}p {(CYCLES + 0.45) * period:.12g}n 0 {step:g}p
write counter.raw
.endc
.end
'''


def run_one(job, ngspice, output):
    name, period, step, text = job
    target = output / name
    target.mkdir()
    started = time.monotonic()
    # Simulate on native storage: HGFS can break in-place raw/netlist writes.
    with tempfile.TemporaryDirectory(prefix=f'counter-spice-{name}-') as temp:
        work = Path(temp)
        (work / 'counter_tb.spice').write_text(text)
        result = subprocess.run([ngspice, '-b', '-o', 'ngspice.log', 'counter_tb.spice'],
                                cwd=work, capture_output=True, text=True)
        (target / 'console.txt').write_text(result.stdout + result.stderr)
        for item in ('counter_tb.spice', 'ngspice.log', 'counter.raw'):
            if (work / item).exists():
                shutil.copyfile(work / item, target / item)
        log = (target / 'ngspice.log').read_text()
        if result.returncode or not (target / 'counter.raw').exists() or re.search(
                r'\berror\b|timestep too small|run simulation.*fail|singular matrix', log, re.I):
            raise RuntimeError(f'{name}: ngspice failed; inspect {target}/ngspice.log')
    return dict(name=name, period_ns=period, max_step_ps=step,
                runtime_seconds=time.monotonic() - started)


def raw_data(path, np):
    data = path.read_bytes()
    header, binary = data.split(b'Binary:\n', 1)
    header = header.decode('ascii')
    assert 'Flags: real' in header and 'Transient Analysis' in header
    nvars = int(re.search(r'No. Variables:\s*(\d+)', header)[1])
    points = int(re.search(r'No. Points:\s*(\d+)', header)[1])
    names = [line.split()[1] for line in header.split('Variables:\n')[1].splitlines() if line.strip()]
    values = np.frombuffer(binary, dtype='<f8').reshape(points, nvars)
    assert len(names) == nvars and names[0] == 'time'
    assert np.isfinite(values).all() and np.all(np.diff(values[:, 0]) > 0)
    return names, values


def analyze(result, output, np):
    target = output / result['name']
    names, values = raw_data(target / 'counter.raw', np)
    t = values[:, 0] * 1e9
    p = result['period_ns']
    clk = values[:, names.index('v(clk)')]
    crossings = np.flatnonzero((clk[:-1] < VDD / 2) & (clk[1:] >= VDD / 2))
    rising = t[crossings] + (VDD / 2 - clk[crossings]) * (
        t[crossings+1] - t[crossings]) / (clk[crossings+1] - clk[crossings])
    assert len(rising) == CYCLES and np.allclose(
        rising, (np.arange(CYCLES) + .5) * p, rtol=0, atol=1e-6), 'Unexpected clock edges'
    control_mismatches = []
    for n in range(CYCLES):
        for index, signal in enumerate(['rst_n', 'en']):
            actual = np.interp((n+.5)*p - .05, t, values[:,names.index(f'v({signal})')])
            desired = controls(n)[index]
            if (desired and actual < .8*VDD) or (not desired and actual > .2*VDD):
                control_mismatches.append(dict(cycle=n, signal=signal, actual_v=float(actual)))
    outputs = values[:, [names.index(f'v(q{i})') for i in range(4)]]
    expected = 0
    rows = []
    delays = []
    failing_windows = []
    for n in range(CYCLES):
        rst, en = controls(n)
        expected = 0 if not rst else (expected + en) % 16
        bits = np.array([(expected >> i) & 1 for i in range(4)])
        samples = []
        pass_samples = True
        for phase in (0.9, 1.4):
            sample_time = (n + phase) * p
            levels = np.array([np.interp(sample_time, t, outputs[:, i]) for i in range(4)])
            valid = (levels <= 0.2 * VDD) | (levels >= 0.8 * VDD)
            observed = int(sum((levels >= 0.8 * VDD) * 2 ** np.arange(4))) if valid.all() else -1
            pass_samples &= bool(valid.all() and observed == expected)
            samples.extend([sample_time, observed, *levels])
        start, stop = (n + 0.9) * p, (n + 1.45) * p
        lo, hi = np.searchsorted(t, [start, stop])
        good = np.where(bits, outputs[lo:hi] >= 0.8 * VDD, outputs[lo:hi] <= 0.2 * VDD)
        stable = bool(good.all())
        if not stable:
            failing_windows.append(n)
        # Delay until all outputs have reached their expected 20/80% regions,
        # and remain there through the end of this cycle's validation window.
        a = np.searchsorted(t, (n + 0.5) * p)
        good_full = np.where(bits, outputs[a:hi] >= 0.8 * VDD, outputs[a:hi] <= 0.2 * VDD).all(axis=1)
        bad = np.flatnonzero(~good_full)
        settled_at = a if not len(bad) else a + bad[-1] + 1
        settling = float(t[settled_at] - (n + 0.5) * p) if settled_at < hi else None
        if settling is not None:
            delays.append(settling)
        rows.append([n, (n + 0.5) * p, rst, en, expected,
                     *samples, int(stable), int(pass_samples and stable), settling])
    columns = ['cycle', 'rising_edge_ns', 'rst_n', 'en', 'expected',
               'high_sample_ns', 'high_observed', 'high_q0_v', 'high_q1_v', 'high_q2_v', 'high_q3_v',
               'low_sample_ns', 'low_observed', 'low_q0_v', 'low_q1_v', 'low_q2_v', 'low_q3_v',
               'stable_window_pass', 'pass', 'settling_to_20_80_ns']
    with (target / 'samples.csv').open('w', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(columns)
        writer.writerows(rows)
    # Preserve complete adaptive-step waveforms in an interoperable compressed CSV.
    with gzip.open(target / 'waveforms.csv.gz', 'wt', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(names)
        writer.writerows(values)
    summary = dict(result, frequency_mhz=1000 / p, cycles_checked=CYCLES,
                   measured_clock_period_ns=float(np.median(np.diff(rising))),
                   clock_rising_edges=len(rising), control_mismatches=control_mismatches,
                   raw_points=len(t), stop_ns=float(t[-1]),
                   failed_cycles=[r[0] for r in rows if not r[-2]],
                   high_sample_mismatches=sum(r[6] != r[4] for r in rows),
                   low_sample_mismatches=sum(r[12] != r[4] for r in rows),
                   unstable_windows=failing_windows,
                   max_settling_to_20_80_ns=max(delays) if delays else None,
                   status='PASS' if all(r[-2] for r in rows) and not control_mismatches else 'FAIL')
    (target / 'summary.json').write_text(json.dumps(summary, indent=2) + '\n')
    return summary, names, values, rows


def plot_results(all_results, output, np):
    os.environ.setdefault('MPLCONFIGDIR', '/tmp/counter-ngspice-matplotlib')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False})
    colors = ['#0072B2', '#009E73', '#D55E00', '#CC79A7']
    for summary, names, data, rows in all_results:
        target = output / summary['name']
        p = summary['period_ns']
        times = data[:, 0] * 1e9
        for filename, start, stop in [('waveforms', 0, 53), ('reset_and_enable', 60, 86)]:
            keep = (times >= start * p) & (times <= stop * p)
            fig, axes = plt.subplots(8, 1, figsize=(16, 12), sharex=True,
                                     gridspec_kw={'height_ratios': [1, 1, 1, 1, 1, 1, 1, 1.6]},
                                     layout='constrained')
            signals = ['clk', 'rst_n', 'en', 'q3', 'q2', 'q1', 'q0']
            for j, signal in enumerate(signals):
                ax = axes[j]
                ax.plot(times[keep], data[keep, names.index(f'v({signal})')],
                        color=colors[(6-j) % 4] if j > 2 else '#4B5563', linewidth=0.9)
                ax.set_ylabel(f'{signal}\n(V)', rotation=0, ha='right', va='center')
                ax.set_yticks([0, 1.8]); ax.set_ylim(-0.16, 1.96)
                ax.grid(alpha=0.18)
            samples = (np.arange(CYCLES) + 0.9) * p
            observed = np.array([r[6] for r in rows])
            expected = np.array([r[4] for r in rows])
            mask = (samples >= start * p) & (samples <= stop * p)
            axes[-1].step(samples[mask], expected[mask], where='mid', color='#111827', alpha=.6, label='Expected')
            axes[-1].plot(samples[mask], observed[mask], '.', color='#0072B2', label='SPICE samples')
            axes[-1].set_ylabel('count\n(decimal)', rotation=0, ha='right', va='center')
            axes[-1].set_yticks([0, 4, 8, 12, 15]); axes[-1].set_ylim(-1, 16)
            axes[-1].set_xlabel('Time (ns)'); axes[-1].grid(alpha=.18)
            axes[-1].legend(loc='upper right', ncols=2)
            for row in rows:
                if not row[-2] and start <= row[0] <= stop:
                    for ax in axes:
                        ax.axvspan((row[0]+.5)*p, (row[0]+1.45)*p, color='red', alpha=.12)
            axes[0].set_title(f'T = {p:g} ns ({1000/p:.3f} MHz) | {summary["status"]} | TT, 1.8 V, 25 C, 10 fF/bit, 100 ps edges', loc='left', pad=12)
            axes[-1].set_xlim(start*p, stop*p)
            fig.savefig(target / f'{filename}.png', dpi=150)
            fig.savefig(target / f'{filename}.svg')
            plt.close(fig)

        # Detail the first 15 -> 0 wrap, including the master state.
        fig, axes = plt.subplots(5, 1, figsize=(12, 9), sharex=True, layout='constrained')
        keep = (times >= 18 * p) & (times <= 21 * p)
        axes[0].plot(times[keep], data[keep, names.index('v(clk)')], color='#4B5563')
        axes[0].set_ylabel('clk (V)')
        for bit in range(4):
            ax = axes[bit+1]
            ax.plot(times[keep], data[keep, names.index(f'v(q{bit})')], color=colors[bit], label=f'count[{bit}]')
            ax.plot(times[keep], data[keep, names.index(f'v(xdut.master[{bit}])')], '--', color='#777777', linewidth=.9, label=f'master[{bit}]')
            ax.axhline(.36, color='#888888', ls=':', lw=.6)
            ax.axhline(1.44, color='#888888', ls=':', lw=.6)
            ax.set_ylabel('Voltage (V)'); ax.legend(loc='upper right', ncols=2)
        for ax in axes:
            ax.set_ylim(-.16,1.96); ax.grid(alpha=.18)
        axes[0].set_title(f'T = {p:g} ns | First 15 -> 0 wrap | Solid: slave output; dashed: master', loc='left')
        axes[-1].set_xlabel('Time (ns)')
        fig.savefig(target/'carry_detail.png', dpi=150)
        fig.savefig(target/'carry_detail.svg')
        plt.close(fig)

    fig, axes = plt.subplots(len(all_results), 1, figsize=(16, 10), sharex=True, layout='constrained')
    axes = np.atleast_1d(axes)
    for ax, (summary, _, _, rows) in zip(axes, all_results):
        n = np.arange(CYCLES)
        expected = [r[4] for r in rows]
        high = [r[6] for r in rows]
        low = [r[12] for r in rows]
        ax.step(n, expected, where='mid', color='#111827', alpha=.5, label='Expected')
        ax.plot(n, high, '.', color='#0072B2', markersize=4, label='SPICE: high-phase samples')
        ax.plot(n, low, '+', color='#009E73', markersize=3, label='SPICE: low-phase samples')
        for r in rows:
            if not r[2]: ax.axvspan(r[0]-.5,r[0]+.5,color='#D55E00',alpha=.10)
            elif not r[3]: ax.axvspan(r[0]-.5,r[0]+.5,color='#999999',alpha=.10)
        ax.set_ylabel('count (decimal)'); ax.set_yticks([0,4,8,12,15]); ax.set_ylim(-1,16)
        ax.grid(alpha=.18)
        ax.set_title(f'T = {summary["period_ns"]:g} ns | {summary["frequency_mhz"]:.3f} MHz | {summary["status"]} | {len(summary["failed_cycles"])} / {CYCLES} failing cycles', loc='left')
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc='outside upper center', ncols=3, frameon=False)
    axes[-1].set_xlabel('Clock cycle (zero based); orange: reset active; gray: enable held low')
    axes[-1].set_xlim(-.5,CYCLES-.5)
    fig.savefig(output/'comparison.png',dpi=160)
    fig.savefig(output/'comparison.svg')
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=HERE/'results')
    parser.add_argument('--pdk-root', type=Path, default=Path.home()/'eda/pdk')
    parser.add_argument('--cell-source', type=Path,
                        default=HERE.parents[4]/'pdk_work/sources/sky130_fd_sc_hd')
    parser.add_argument('--ngspice', default=shutil.which('ngspice'))
    parser.add_argument('--step-ps', type=float, default=5)
    parser.add_argument('--input-delay-ns', type=float, default=1.0)
    parser.add_argument('--periods', type=float, nargs='+', default=[10, 2, 1.65])
    parser.add_argument('--jobs', type=int, default=3)
    parser.add_argument('--no-plots', action='store_true')
    parser.add_argument('--analyze-only', action='store_true',
                        help='Recheck saved raw files and regenerate plots without simulating')
    args = parser.parse_args()
    if args.output.exists() and not args.analyze_only:
        parser.error('Output directory already exists; choose a new --output directory')
    import numpy as np
    output = args.output.resolve()
    if args.analyze_only:
        previous = json.loads((output/'summary.json').read_text())
        results = []
        for item in previous:
            base = {key:item[key] for key in ['name','period_ns','max_step_ps','runtime_seconds']}
            checked = analyze(base, output, np)
            results.append(checked)
            print(json.dumps(checked[0]),flush=True)
        (output/'summary.json').write_text(json.dumps([r[0] for r in results],indent=2)+'\n')
        if not args.no_plots:
            plot_results(results,output,np)
        if any(r[0]['status'] != 'PASS' for r in results):
            raise SystemExit(2)
        return
    output.mkdir(parents=True)
    models = output/'models'
    models.mkdir()
    counter_source = HERE.parent/'simulation/counter.spice'
    net = counter_source.read_text()
    assert '\0' not in net
    (models/'counter.spice').write_text(net)
    cells = []
    provenance = []
    types = sorted(set(re.findall(r'sky130_fd_sc_hd__\w+',net)))
    mos_per_cell = {}
    for typ in types:
        cell = typ.split('__')[1].rsplit('_',1)[0]
        path = args.cell_source/'cells'/cell/f'{typ}.spice'
        text = path.read_text()
        cells.append(text)
        mos_per_cell[typ] = len(re.findall(r'^X\d+\s',text,re.M))
        provenance.append(dict(cell=typ, path=str(path.resolve()), sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    (models/'sky130_hd_used.spice').write_text('\n'.join(cells))
    model_lib = (args.pdk_root/'sky130A/libs.tech/ngspice/sky130.lib.spice').resolve()
    assert model_lib.exists()
    transistors = sum(mos_per_cell[line.split()[-1]] for line in net.splitlines() if line.startswith('x_'))
    manifest = dict(ngspice_version=subprocess.run([args.ngspice,'--version'],capture_output=True,text=True).stdout,
                    pdk_library=str(model_lib), pdk_library_sha256=hashlib.sha256(model_lib.read_bytes()).hexdigest(),
                    source_netlist=str(counter_source), netlist_sha256=hashlib.sha256(counter_source.read_bytes()).hexdigest(),
                    cell_sources=provenance, standard_cell_instances=18, transistor_instances=transistors,
                    corner='tt', temperature_c=25, vdd_v=VDD, output_load_ff_per_bit=10,
                    clock_duty_at_50_percent=0.5, rise_fall_ps=100,
                    input_delay_after_previous_rising_ns=args.input_delay_ns,
                    max_step_ps=args.step_ps, cycles_checked=CYCLES,
                    initialized_by='DC operating point followed by four synchronous reset cycles; no forced state',
                    validation='20/80% levels; samples at rising+0.4T and rising+0.9T; stable through rising+0.95T',
                    parasitics='native cell SPICE MOS models; no interconnect or layout PEX')
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    jobs=[]
    for period in args.periods:
        assert period > 2*RISE_NS and args.step_ps > 0
        assert .05 < args.input_delay_ns < period-.05
        name='T_'+f'{period:g}'.replace('.','p')+'ns'
        jobs.append((name,period,args.step_ps,deck(period,args.step_ps,args.input_delay_ns,
                     model_lib,models/'sky130_hd_used.spice',models/'counter.spice')))
    results=[]
    print(f'Starting {len(jobs)} runs, {transistors} MOS instances, {CYCLES} checked cycles/run',flush=True)
    with ThreadPoolExecutor(max_workers=args.jobs) as executor:
        futures={executor.submit(run_one,job,args.ngspice,output):job[0] for job in jobs}
        for future in as_completed(futures):
            result=future.result()
            analyzed=analyze(result,output,np)
            results.append(analyzed)
            print(json.dumps(analyzed[0]),flush=True)
    results.sort(key=lambda r:-r[0]['period_ns'])
    (output/'summary.json').write_text(json.dumps([r[0] for r in results],indent=2)+'\n')
    if not args.no_plots:
        plot_results(results,output,np)
    print(f'Results: {output}',flush=True)
    if any(r[0]['status']!='PASS' for r in results):
        raise SystemExit(2)


if __name__=='__main__':
    main()
