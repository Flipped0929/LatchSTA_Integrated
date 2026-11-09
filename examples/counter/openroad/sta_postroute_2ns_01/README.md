# Counter 后布线 STA 结果：2 ns

**分析完成，2 ns 下本次定义的 setup、hold、脉宽和电气限制检查均通过。**
采用现有布线后网表、实际提取的 SPEF、传播时钟和原有 IO 预算。
全局 setup slack 可能因 latch 时间借用显示为 0，输出端口的实际余量另列。

## 汇总

| 检查 | 结果 |
| --- | --- |
| 时钟周期 | 2 ns，波形为 {1 2} |
| Setup 最差 slack | 0.000000000 ns |
| 输出端口最差 setup slack | +0.210795283 ns |
| Setup TNS | 0.000000000 ns |
| Setup 违例端点数 | 0 |
| Hold 最差 slack | +0.035017878 ns |
| Hold TNS | 0.000000000 ns |
| Hold 违例端点数 | 0 |
| 脉宽检查 | PASS，8 个库中定义的检查；最差余量 0.772891879 ns |
| 最大 transition 检查 | PASS，74 个检查 |
| 最大 capacitance 检查 | PASS，22 个检查 |
| Max fanout / 库 min period | 本次库/约束没有相应检查项，不将空报告计为通过 |
| 约束完整性 | 通过，12 个功能端点均有 setup/hold 路径 |
| SPEF 覆盖 | 24 条实际布线网络全部加载，0 条部分缺失 |

## 输出端口结果

| 端点 | Setup slack / ns | Hold slack / ns |
| --- | ---: | ---: |
| `count[0]` | +0.214129 | +0.527387 |
| `count[1]` | +0.238897 | +0.515897 |
| `count[2]` | +0.210795 | +0.530636 |
| `count[3]` | +0.274955 | +0.488590 |

输出端口最差 setup 路径见 [输出临界路径](reports/setup_output_worst.rpt)，
起点为 _23_ (positive level-sensitive latch clocked by clk)，终点为 count[2] (output port clocked by clk)。
报告展开了实际 CTS 时钟树和数据路径。

- 本次源时钟上升沿位于 1 ns。
- 输出临界路径数据到达时间为 1.739204526 ns。
- 外部输出所需时间按 `1.5T - 1.000 - 0.050` 计算，
  实际报告为 1.949999809 ns。
- 输出 setup slack 为 +0.210795283 ns。

最差 hold 路径见 [hold_worst.rpt](reports/hold_worst.rpt)，
起点为 en (input port clocked by clk)，终点为 _17_ (negative level-sensitive latch clocked by clk)，
slack 为 +0.035017878 ns。

## 全部功能端点

| 端点 | Setup slack / ns | Hold slack / ns |
| --- | ---: | ---: |
| `_17_/D` | +0.007562 | +0.035018 |
| `_18_/D` | +0.000000 | +0.129143 |
| `_19_/D` | +0.000000 | +0.110173 |
| `_20_/D` | +0.000000 | +0.082509 |
| `_21_/D` | +0.552740 | +0.214949 |
| `_22_/D` | +0.485956 | +0.202891 |
| `_23_/D` | +0.459152 | +0.204002 |
| `_24_/D` | +0.503504 | +0.215109 |
| `count[0]` | +0.214129 | +0.527387 |
| `count[1]` | +0.238897 | +0.515897 |
| `count[2]` | +0.210795 | +0.530636 |
| `count[3]` | +0.274955 | +0.488590 |

master 数据端出现的 0 setup slack 对应工具的 latch 时间借用表示，
不能把这个数值单独解释成新的最小时钟周期证明。
本次针对所有 8 个 latch 数据端和 4 个输出，均报告了 setup 与 hold，
同步复位 `rst_n` 作为数据输入正常计时，没有 false path 或复位常量化。

## 时钟与寄生核对

8 个 latch 的上升沿插入延迟范围约为
0.262058496–0.274582505 ns，
原始上升沿延迟跨度为 12.524009 ps；
下降沿延迟跨度为 10.269880 ps。
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
- 本次时钟周期为 2 ns，波形为 {1 2}；保留 en/rst_n min/max 0.2/1 ns、
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
python3 openroad/run_postroute_sta.py --period-ns 2 --output openroad/sta_postroute_repeat01
python3 openroad/summarize_postroute_sta.py openroad/sta_postroute_repeat01
```

执行完成与时序通过分别记录：`analysis_integrity=PASS` 表示输入/覆盖/报告核对通过，
本次 `timing_status=PASS` 表示 2 ns 下的时序检查结果。
