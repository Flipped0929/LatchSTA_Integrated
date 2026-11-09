# Counter 后布线 STA 结果

**分析完成，但 1.65 ns 不满足当前输出接口的 setup 约束。**
采用布线后网表、实际提取的 SPEF、传播时钟和原有 IO 预算，
四个 `count` 输出均有 setup 违例；hold、已定义的时钟脉宽和电气限制检查通过。

## 汇总

| 检查 | 结果 |
| --- | --- |
| 时钟周期 | 1.65 ns |
| Setup 最差 slack | -0.139204652 ns |
| Setup TNS | -0.461223517 ns |
| Setup 违例端点数 | 4 |
| Hold 最差 slack | +0.035017767 ns |
| Hold TNS | 0.000000000 ns |
| Hold 违例端点数 | 0 |
| 脉宽检查 | PASS，8 个库中定义的检查；最差余量 0.597891867 ns |
| 最大 transition 检查 | PASS，74 个检查 |
| 最大 capacitance 检查 | PASS，22 个检查 |
| Max fanout / 库 min period | 本次库/约束没有相应检查项，不将空报告计为通过 |
| 约束完整性 | 通过，12 个功能端点均有 setup/hold 路径 |
| SPEF 覆盖 | 24 条实际布线网络全部加载，0 条部分缺失 |

## 输出 setup 违例

| 端点 | Setup slack / ns | Hold slack / ns |
| --- | ---: | ---: |
| `count[0]` | -0.135871 | +0.527387 |
| `count[1]` | -0.111103 | +0.515897 |
| `count[2]` | -0.139205 | +0.530636 |
| `count[3]` | -0.075045 | +0.488589 |

最差 setup 路径见 [setup_worst.rpt](reports/setup_worst.rpt)：
`clk → clkbuf_0_clk → clkbuf_1_0__f_clk → _23_/GATE → _23_/Q → count[2]`。

- 实际上升沿出现在约 0.825 ns。
- 时钟到 `_23_/GATE` 的插入延迟约 0.274583 ns，到达约 1.099582 ns。
- latch 的 clock→Q 延迟约 0.464231 ns，Q→输出线延迟约 0.000391 ns。
- `count[2]` 数据到达时间为 1.564204454 ns。
- 外部输出所需时间为 `2.475 - 1.000 - 0.050 ≈ 1.425 ns`，
  实际报告为 1.424999833 ns。
- 两者相减得到 -0.139204651 ns 的 setup slack。

本次违例位于输出接口预算，不表示已观察到计数逻辑错误。
之前 ngspice 的功能仿真和前布局 STA 未包含这次物理 CTS 与提取互连的完整组合，
因此此前功能通过/理想时钟模型无违例，不能替代本次输出接口时序检查。

最差 hold 路径为 `en → _08_/A1 → _08_/Y → _17_/D`，
见 [hold_worst.rpt](reports/hold_worst.rpt)，slack 为 +0.035017767 ns。

## 全部功能端点

| 端点 | Setup slack / ns | Hold slack / ns |
| --- | ---: | ---: |
| `_17_/D` | +0.000000 | +0.035018 |
| `_18_/D` | +0.000000 | +0.129143 |
| `_19_/D` | +0.000000 | +0.110173 |
| `_20_/D` | +0.000000 | +0.082509 |
| `_21_/D` | +0.327312 | +0.214949 |
| `_22_/D` | +0.135956 | +0.202891 |
| `_23_/D` | +0.109152 | +0.204002 |
| `_24_/D` | +0.153504 | +0.215109 |
| `count[0]` | -0.135871 | +0.527387 |
| `count[1]` | -0.111103 | +0.515897 |
| `count[2]` | -0.139205 | +0.530636 |
| `count[3]` | -0.075045 | +0.488589 |

master 数据端出现的 0 setup slack 对应工具的 latch 时间借用表示，
不能把这个数值单独解释成新的最小时钟周期证明。
本次针对所有 8 个 latch 数据端和 4 个输出，均报告了 setup 与 hold，
同步复位 `rst_n` 作为数据输入正常计时，没有 false path 或复位常量化。

## 时钟与寄生核对

8 个 latch 的上升沿插入延迟范围约为
0.262058378–0.274582506 ns，
原始上升沿延迟跨度为 12.524128 ps；
下降沿延迟跨度为 10.270000 ps。
完整时钟信息见 [clock_latencies.csv](reports/clock_latencies.csv) 和
[clock_skew.rpt](reports/clock_skew.rpt)。后者是工具针对路径配对的报告，
还包含 uncertainty/CRPR，不能把其输出直接当成原始插入延迟跨度。

SPEF 中 24 条网络的 `*D_NET` 电容分别与 OpenSTA `report_net` 的 wire capacitance
核对一致，Liberty 引脚电容正常加入，每位输出原有 10 fF 外部负载也仍然存在。
寄生注释报告仅列出 `clkload0/X` 为未注释 driver：它是 CTS 平衡负载的有意悬空输出，
没有相连导线；其 A 引脚所在的叶时钟网已完整注释。

## 分析输入和补充设置

- OpenSTA 3.1.0；Liberty TT、25°C、1.8 V；RC 为平台 nominal 提取角。
- 网表来自 PNR，22 个单元（18 个原始单元、3 个时钟缓冲器、1 个平衡负载），未改任何实例或信号连接。
- 仅在 `inputs/counter_sta.v` 中移除两个未连接的顶层电源端口 VDD/VSS，
  避免将电源端口误当作无约束数据 IO；原始网表副本完整保留。
- 使用原物理 SDC 的 1.65 ns 周期、50% 波形、en/rst_n min/max 0.2/1 ns、
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
python3 openroad/run_postroute_sta.py --output openroad/sta_postroute_repeat01
python3 openroad/summarize_postroute_sta.py openroad/sta_postroute_repeat01
```

执行完成与时序通过分别记录：`analysis_integrity=PASS` 表示输入/覆盖/报告核对通过，
`timing_status=FAIL` 表示当前 1.65 ns 下存在实际时序违例。
