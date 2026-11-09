# Counter 后布线 STA

最新已完成 **1.8 ns** 后布线 STA，完整结果见
**[sta_postroute_1p8ns_01/README.md](sta_postroute_1p8ns_01/README.md)**。

使用布线后网表、OpenRCX nominal SPEF 和 SKY130 HD TT/25°C/1.8 V Liberty，
时钟周期为 1.8 ns，波形为 `{0.9 1.8}`，保留原 IO 预算、10 fF 输出负载和 0.05 ns uncertainty，
开启传播时钟与 CRPR，并为根时钟端口明确补充 0.06 ns 源边沿。

| 检查 | 结果 |
| --- | --- |
| 全局 Setup 最差 slack | **0.000000 ns**，latch 时间借用端点；无负 slack |
| 输出端口最差 Setup slack | **+0.010795 ns**，`count[2]`，约 10.795 ps |
| Setup TNS | 0.000000 ns |
| Setup 违例端点数 | 0 |
| Hold 最差 slack | **+0.035018 ns**，通过 |
| 时钟脉宽 | 8 项通过，最差余量 +0.672892 ns |
| Transition / capacitance | 库中定义的检查均通过 |
| 约束与寄生覆盖 | 检查通过；12 个功能端点、24 条布线网络 |

输出端口最差 setup 路径由 `_23_` 的传播时钟路径及 Q→`count[2]` 构成。
数据到达约 1.639205 ns，输出预算要求约 1.650000 ns，余量约 10.795 ps。

[最差输出 setup](sta_postroute_1p8ns_01/reports/setup_output_worst.rpt) ·
[最差 hold](sta_postroute_1p8ns_01/reports/hold_worst.rpt) ·
[逐端点 CSV](sta_postroute_1p8ns_01/reports/endpoint_slacks.csv) ·
[完整机器汇总](sta_postroute_1p8ns_01/reports/summary.json) ·
[有效 SDC](sta_postroute_1p8ns_01/results/effective.sdc)

此次复用相同物理网表和 SPEF，仅修改本次 STA 的时钟周期/波形，未重做布局布线或寄生提取。
新旧有效 SDC 除 `create_clock` 行外一致，见
[对照记录](sta_postroute_1p8ns_01/reports/comparison_with_previous_runs.json)。
原始 `counter_opt.sdc` 和所有历史运行文件保留。

| 周期 | 最差输出 Setup slack / ns | 总体时序结果 |
| --- | ---: | --- |
| [1.65 ns](sta_postroute_02/README.md) | -0.139205 | FAIL，4 个输出 setup 违例 |
| [1.8 ns](sta_postroute_1p8ns_01/README.md) | +0.010795 | PASS |
| [2 ns](sta_postroute_2ns_01/README.md) | +0.210795 | PASS |

上述运行使用相同网表、SPEF、Liberty 和其他有效约束，只改变时钟周期/波形。
本次没有搜索新的最小时钟周期，不将 latch 端点显示的 0 slack 解释为极限频率证明。

重跑任意指定周期的示例：

```sh
python3 openroad/run_postroute_sta.py --period-ns 1.8 --output openroad/sta_postroute_1p8ns_repeat01
python3 openroad/summarize_postroute_sta.py openroad/sta_postroute_1p8ns_repeat01
```
