#!/usr/bin/env python3
"""Validate STA provenance/coverage and summarize timing; violations remain visible."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import re

HERE=Path(__file__).resolve().parent
NUM=r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?'
ROUNDING_NS=1e-6


def tsv(path):
    with path.open() as f:return list(csv.DictReader(f,delimiter='\t'))


def check_rows(path):
    result=[]
    pattern=re.compile(r'^(.+?)\s+('+NUM+r')\s+('+NUM+r')\s+('+NUM+r')\s+\((MET|VIOLATED)\)\s*$')
    for line in path.read_text().splitlines():
        match=pattern.match(line)
        if match:
            name,limit,actual,slack,status=match.groups()
            result.append(dict(object=name.strip(),limit=float(limit),actual=float(actual),slack=float(slack),reported_status=status))
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run',nargs='?',type=Path,default=HERE/'sta_postroute_02')
    args=parser.parse_args()
    run=args.run.resolve(); reports=run/'reports'
    manifest=json.loads((run/'manifest.json').read_text())
    for entry in manifest['files']:
        path=Path(entry['path'])
        if not path.is_absolute():path=run/path
        assert hashlib.sha256(path.read_bytes()).hexdigest()==entry['sha256'], f'Changed STA input/output: {path}'
    log=(run/'logs/opensta.log').read_text()
    assert 'POST_ROUTE_STA_COMPLETE' in log and not re.search(r'^Error|^Warning',log,re.M)
    metrics={r['metric']:r['value'] for r in tsv(reports/'metrics.tsv')}
    assert metrics['constraints_ok']=='1' and not (reports/'check_setup.rpt').read_text().strip()
    assert metrics['clock_propagated']=='1' and metrics['crpr_enabled']=='1' and metrics['crpr_mode']=='same_transition'
    expected_period=float(manifest.get('clock_period_ns',1.65))
    assert abs(float(metrics['clock_period_ns'])-expected_period)<1e-6
    assert float(metrics['clock_source_rise_slew_ns'])==float(metrics['clock_source_fall_slew_ns'])==.06
    assert int(metrics['cells'])==22 and int(metrics['latches'])==8 and int(metrics['functional_ports'])==7
    annotation=(reports/'parasitic_annotation.rpt').read_text()
    assert re.fullmatch(r'Found 1 unannotated drivers\.\s+clkload0/X\s+Found 0 partially unannotated drivers\.\s*',annotation)
    # All real routed nets must have wire capacitance loaded from SPEF.
    pex=Path(manifest['pex_source'])
    with (pex/'reports/net_parasitics.csv').open() as f:
        expected_caps={r['net']:float(r['d_net_total_ff'])/1000 for r in csv.DictReader(f)}
    net_caps={}
    for block in (reports/'net_loads.rpt').read_text().split('Net ')[1:]:
        name=block.splitlines()[0].strip()
        wire=re.search(r'Wire capacitance: ([^\n]+)',block)
        assert wire, name
        values=[float(v) for v in re.findall(r'\d+\.\d+',wire[1])]
        assert values and all(math.isclose(v,expected_caps[name],rel_tol=1e-5,abs_tol=1e-9) for v in values), name
        if name in net_caps: assert net_caps[name]==values
        net_caps[name]=values
    assert set(net_caps)==set(expected_caps) and len(net_caps)==24
    for bit in range(4):
        assert re.search(r'count\['+str(bit)+r'\] output port pin 0\.010000000',(reports/'net_loads.rpt').read_text())
    endpoints=tsv(reports/'endpoint_slacks.tsv')
    expected_endpoints={f'_{i}_/D' for i in range(17,25)} | {f'count[{i}]' for i in range(4)}
    assert len(endpoints)==24 and {r['endpoint'] for r in endpoints}==expected_endpoints
    for endpoint in expected_endpoints:
        assert {r['analysis'] for r in endpoints if r['endpoint']==endpoint}=={'setup','hold'}
    for row in endpoints:row['slack_ns']=float(row['slack_ns'])
    setup=[r for r in endpoints if r['analysis']=='setup']
    hold=[r for r in endpoints if r['analysis']=='hold']
    setup_fail=[r for r in setup if r['slack_ns'] < -ROUNDING_NS]
    hold_fail=[r for r in hold if r['slack_ns'] < -ROUNDING_NS]
    assert math.isclose(min(r['slack_ns'] for r in setup),float(metrics['setup_worst_slack_ns']),abs_tol=ROUNDING_NS)
    assert math.isclose(min(r['slack_ns'] for r in hold),float(metrics['hold_worst_slack_ns']),abs_tol=ROUNDING_NS)
    assert math.isclose(sum(min(0,r['slack_ns']) for r in setup),float(metrics['setup_tns_ns']),abs_tol=3*ROUNDING_NS)
    assert math.isclose(sum(min(0,r['slack_ns']) for r in hold),float(metrics['hold_tns_ns']),abs_tol=3*ROUNDING_NS)
    check_data={label:check_rows(reports/(label+'.rpt')) for label in ['pulse_width','min_period','max_slew','max_capacitance','max_fanout']}
    assert len(check_data['pulse_width'])==8
    check_summary={label:dict(status=('N/A' if not rows else 'FAIL' if any(r['slack'] < -ROUNDING_NS for r in rows) else 'PASS'),
                                    count=len(rows),violations=sum(r['slack'] < -ROUNDING_NS for r in rows),
                                    worst_slack=min((r['slack'] for r in rows),default=None))
                   for label,rows in check_data.items()}
    clocks=tsv(reports/'clock_pins.tsv')
    assert len(clocks)==8 and len({r['clock_net'] for r in clocks})==2
    waveform=re.search(r'-waveform\s+\{([^}]+)\}',(run/'results/effective.sdc').read_text())
    rise_source,fall_source=map(float,waveform[1].split())
    arrivals=(reports/'clock_arrivals.rpt').read_text()
    clock_latency=[]
    for row in clocks:
        pin=row['clock_pin']
        block=arrivals.split('\n'+pin+'\n',1)[1].split('\n\n',1)[0]
        rising=float(re.search(r'\(clk \^\) r ('+NUM+r'):',block)[1])-rise_source
        falling=float(re.search(r'\(clk v\).* f ('+NUM+r'):',block)[1])-fall_source
        assert rising>0 and falling>0
        clock_latency.append(dict(clock_pin=pin,rise_latency_ns=rising,fall_latency_ns=falling,
                                  rise_slew_ns=float(row['rise_slew_ns']),fall_slew_ns=float(row['fall_slew_ns'])))
    with (reports/'clock_latencies.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(clock_latency[0]));writer.writeheader();writer.writerows(clock_latency)
    worst_setup=(reports/'setup_worst.rpt').read_text()
    worst_hold=(reports/'hold_worst.rpt').read_text()
    def worst_path(text):
        start=re.search(r'^Startpoint: (.+)',text,re.M)[1]
        end=re.search(r'^Endpoint: (.+)',text,re.M)[1]
        slack=float(re.search(r'^\s*('+NUM+r')\s+slack \(',text,re.M)[1])
        arrival=float(re.search(r'^\s*('+NUM+r')\s+data arrival time',text,re.M)[1])
        required=float(re.search(r'^\s*('+NUM+r')\s+data required time',text,re.M)[1])
        return dict(startpoint=start,endpoint=end,arrival_ns=arrival,required_ns=required,slack_ns=slack)
    output_worst_file=reports/'setup_output_worst.rpt'
    output_worst=worst_path(output_worst_file.read_text()) if output_worst_file.exists() else worst_path(worst_setup)
    summary=dict(analysis_completed=True,analysis_integrity='PASS',timing_status='FAIL' if setup_fail or hold_fail or any(r['status']=='FAIL' for r in check_summary.values()) else 'PASS',
                 sta_version=manifest['sta_version'],library_corner=manifest['library_corner'],rc_corner=manifest['rc_corner'],
                 period_ns=float(metrics['clock_period_ns']),source_transition_ns=.06,
                 propagated_clock=True,crpr_enabled=True,crpr_mode='same_transition',coupling_reduction_factor=1.0,
                 setup_worst_slack_ns=float(metrics['setup_worst_slack_ns']),setup_tns_ns=float(metrics['setup_tns_ns']),
                 hold_worst_slack_ns=float(metrics['hold_worst_slack_ns']),hold_tns_ns=float(metrics['hold_tns_ns']),
                 setup_violating_endpoints=setup_fail,hold_violating_endpoints=hold_fail,
                 constrained_endpoints=len(expected_endpoints),annotated_routed_nets=24,partially_unannotated_drivers=0,
                 expected_unannotated_open_driver='clkload0/X',constraints_complete=True,
                 checks=check_summary,worst_setup=worst_path(worst_setup),worst_hold=worst_path(worst_hold),
                 worst_output_setup=output_worst,output_setup_worst_slack_ns=output_worst['slack_ns'],
                 raw_rising_clock_latency_min_ns=min(r['rise_latency_ns'] for r in clock_latency),
                 raw_rising_clock_latency_max_ns=max(r['rise_latency_ns'] for r in clock_latency),
                 raw_rising_clock_latency_spread_ns=max(r['rise_latency_ns'] for r in clock_latency)-min(r['rise_latency_ns'] for r in clock_latency),
                 raw_falling_clock_latency_spread_ns=max(r['fall_latency_ns'] for r in clock_latency)-min(r['fall_latency_ns'] for r in clock_latency),
                 numeric_rounding_tolerance_ns=ROUNDING_NS,implementation_modified=False,minimum_period_search='NOT RUN')
    (reports/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    with (reports/'endpoint_slacks.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(endpoints[0]));writer.writeheader();writer.writerows(endpoints)
    endpoint_md=[]
    for endpoint in sorted(expected_endpoints):
        s=next(r['slack_ns'] for r in setup if r['endpoint']==endpoint)
        h=next(r['slack_ns'] for r in hold if r['endpoint']==endpoint)
        endpoint_md.append(f'| `{endpoint}` | {s:+.6f} | {h:+.6f} |')
    period=summary['period_ns']
    verdict=(f"分析完成，{period:g} ns 下本次定义的 setup、hold、脉宽和电气限制检查均通过。"
             if summary['timing_status']=='PASS'
             else f"分析完成，{period:g} ns 下存在时序或电气限制违例，见下表和详细报告。")
    output_report_name='setup_output_worst.rpt' if output_worst_file.exists() else 'setup_worst.rpt'
    report=f'''# Counter 后布线 STA 结果：{period:g} ns

**{verdict}**
采用现有布线后网表、实际提取的 SPEF、传播时钟和原有 IO 预算。
全局 setup slack 可能因 latch 时间借用显示为 0，输出端口的实际余量另列。

## 汇总

| 检查 | 结果 |
| --- | --- |
| 时钟周期 | {period:g} ns，波形为 {{{period/2:g} {period:g}}} |
| Setup 最差 slack | {summary['setup_worst_slack_ns']:.9f} ns |
| 输出端口最差 setup slack | {summary['output_setup_worst_slack_ns']:+.9f} ns |
| Setup TNS | {summary['setup_tns_ns']:.9f} ns |
| Setup 违例端点数 | {len(setup_fail)} |
| Hold 最差 slack | {summary['hold_worst_slack_ns']:+.9f} ns |
| Hold TNS | {summary['hold_tns_ns']:.9f} ns |
| Hold 违例端点数 | {len(hold_fail)} |
| 脉宽检查 | {check_summary['pulse_width']['status']}，8 个库中定义的检查；最差余量 {check_summary['pulse_width']['worst_slack']:.9f} ns |
| 最大 transition 检查 | {check_summary['max_slew']['status']}，{check_summary['max_slew']['count']} 个检查 |
| 最大 capacitance 检查 | {check_summary['max_capacitance']['status']}，{check_summary['max_capacitance']['count']} 个检查 |
| Max fanout / 库 min period | 本次库/约束没有相应检查项，不将空报告计为通过 |
| 约束完整性 | 通过，12 个功能端点均有 setup/hold 路径 |
| SPEF 覆盖 | 24 条实际布线网络全部加载，0 条部分缺失 |

## 输出端口结果

| 端点 | Setup slack / ns | Hold slack / ns |
| --- | ---: | ---: |
'''+'\n'.join(row for row in endpoint_md if row.startswith('| `count['))+f'''

输出端口最差 setup 路径见 [输出临界路径](reports/{output_report_name})，
起点为 {output_worst['startpoint']}，终点为 {output_worst['endpoint']}。
报告展开了实际 CTS 时钟树和数据路径。

- 本次源时钟上升沿位于 {period/2:g} ns。
- 输出临界路径数据到达时间为 {output_worst['arrival_ns']:.9f} ns。
- 外部输出所需时间按 `1.5T - 1.000 - 0.050` 计算，
  实际报告为 {output_worst['required_ns']:.9f} ns。
- 输出 setup slack 为 {output_worst['slack_ns']:+.9f} ns。

最差 hold 路径见 [hold_worst.rpt](reports/hold_worst.rpt)，
起点为 {summary['worst_hold']['startpoint']}，终点为 {summary['worst_hold']['endpoint']}，
slack 为 {summary['hold_worst_slack_ns']:+.9f} ns。

## 全部功能端点

| 端点 | Setup slack / ns | Hold slack / ns |
| --- | ---: | ---: |
'''+'\n'.join(endpoint_md)+f'''

master 数据端出现的 0 setup slack 对应工具的 latch 时间借用表示，
不能把这个数值单独解释成新的最小时钟周期证明。
本次针对所有 8 个 latch 数据端和 4 个输出，均报告了 setup 与 hold，
同步复位 `rst_n` 作为数据输入正常计时，没有 false path 或复位常量化。

## 时钟与寄生核对

8 个 latch 的上升沿插入延迟范围约为
{summary['raw_rising_clock_latency_min_ns']:.9f}–{summary['raw_rising_clock_latency_max_ns']:.9f} ns，
原始上升沿延迟跨度为 {summary['raw_rising_clock_latency_spread_ns']*1000:.6f} ps；
下降沿延迟跨度为 {summary['raw_falling_clock_latency_spread_ns']*1000:.6f} ps。
完整时钟信息见 [clock_latencies.csv](reports/clock_latencies.csv) 和
[clock_skew.rpt](reports/clock_skew.rpt)。后者是工具针对路径配对的报告，
还包含 uncertainty/CRPR，不能把其输出直接当成原始插入延迟跨度。

SPEF 中 24 条网络的 `*D_NET` 电容分别与 OpenSTA `report_net` 的 wire capacitance
核对一致，Liberty 引脚电容正常加入，每位输出原有 10 fF 外部负载也仍然存在。
寄生注释报告仅列出 `clkload0/X` 为未注释 driver：它是 CTS 平衡负载的有意悬空输出，
没有相连导线；其 A 引脚所在的叶时钟网已完整注释。

## 分析输入和补充设置

- OpenSTA {manifest['sta_version']}；Liberty TT、25°C、1.8 V；RC 为平台 nominal 提取角。
- 网表来自 PNR，22 个单元（18 个原始单元、3 个时钟缓冲器、1 个平衡负载），未改任何实例或信号连接。
- 仅在 `inputs/counter_sta.v` 中移除两个未连接的顶层电源端口 VDD/VSS，
  避免将电源端口误当作无约束数据 IO；原始网表副本完整保留。
- 本次时钟周期为 {period:g} ns，波形为 {{{period/2:g} {period:g}}}；保留 en/rst_n min/max 0.2/1 ns、
  输出 min/max -0.05/1 ns、0.05 ns uncertainty、输出 10 fF 负载。
- 对传播时钟根端口补充 `set_input_transition 0.06 [get_ports clk]`。
  原 SDC 只有 `set_clock_transition`，直接加载时根端口实测 slew 为 0；
  此补充延续原先线性全摆幅 100 ps 对应 20%–80% 的 60 ps 源边沿设置。
- CRPR 开启，模式 `same_transition`；SPEF 保留耦合，reduction factor 为 1.0。
- 本次为单一 Liberty/RC 角的常规 STA，不包含多 PVT、OCV 或串扰 aggressor 切换场景分析。

本次只分析，没有修改物理实现、修复 setup/hold 或放宽原 IO 预算，
也未搜索新的最小时钟周期。该电路包含混合极性 latch 及时间借用，
不通过简单的 `周期减 slack` 或不适用于 latch 的最小周期命令宣称新的 Fmax。

## 文件和复现

- [有效约束](results/effective.sdc)、[最差 setup](reports/setup_worst.rpt)、[最差 hold](reports/hold_worst.rpt)。
- [完整 setup 报告](reports/setup.rpt)、[完整 hold 报告](reports/hold.rpt)、[全部违规检查](reports/violations.rpt)。
- [脉宽报告](reports/pulse_width.rpt)、[寄生注释检查](reports/parasitic_annotation.rpt)、[机器可读汇总](reports/summary.json)。
- [逐端点 CSV](reports/endpoint_slacks.csv)、[运行日志](logs/opensta.log)、[输入输出哈希](manifest.json)。

在 counter 目录用新输出目录重跑：

```sh
python3 openroad/run_postroute_sta.py --period-ns {period:g} --output openroad/sta_postroute_repeat01
python3 openroad/summarize_postroute_sta.py openroad/sta_postroute_repeat01
```

执行完成与时序通过分别记录：`analysis_integrity=PASS` 表示输入/覆盖/报告核对通过，
本次 `timing_status={summary['timing_status']}` 表示 {period:g} ns 下的时序检查结果。
'''
    (run/'README.md').write_text(report)
    print(json.dumps({k:summary[k] for k in ['analysis_completed','analysis_integrity','timing_status','period_ns','setup_worst_slack_ns','setup_tns_ns','hold_worst_slack_ns','hold_tns_ns','annotated_routed_nets','checks']},indent=2))


if __name__=='__main__':
    main()
