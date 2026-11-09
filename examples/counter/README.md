# SKY130 同步复位主从 latch 计数器

当前电路是 4 位模 16 计数器。master 为四个 `dlxtn_1`，slave 为四个
`dlxtp_1`；八个 latch 共用 `clk`。`rst_n` 低有效，通过组合逻辑同步清零
master 数据，优先于 `en`。不使用异步复位引脚。


当前完成了同步复位 counter 从零偏斜求解到带寄生后仿真的验证。以下数值均为指定实验工况下的结果。

| 阶段 | 结果 |
| --- | --- |
| [理想时钟模型求解](solver_validation/regenerated_solver.log) | Howard 和 LP 一致，最小周期 1.584538 ns |
| [原理图及前仿真](xschem/ngspice/RESULTS.md) | 10、2.00、1.65 ns 均通过 |
| [布局布线](openroad/README.md)与[寄生提取](openroad/EXTRACTION.md) | 八个 latch 均接入 CTS，24 条信号/时钟网布通并提取 RC |
| [同一版图后布线 STA](openroad/POST_ROUTE_STA.md) | 1.65 ns 输出 setup 未通过；1.80、2.00 ns 通过 |
| [1.80 ns 后仿真](xschem/ngspice/postlayout_1p8ns_01/README.md) | TT、nominal RC，2.5 ps 和 1.25 ps 步长各检查 128 个周期，均通过 |

**1.80 ns / 555.56 MHz** 是当前同时通过后布线 STA 和后仿真的最快已验证工作点。
相对 10 ns 实验基线，周期缩短 82%。1.584538 ns 是理想零偏斜模型的结果。
`run_counter_01/` 与 `reports_yosys/yosys_async_legacy.log` 保存早期异步复位实验，供追溯。
归档的日志、输入副本和 SPICE testbench 保留实验机器的路径。重跑请使用各阶段的脚本生成新目录。
后仿真脚本支持 `COUNTER_SKY130_CELL_SOURCE` 指向含 `cells/` 的 SKY130 HD 源码目录，
以及 `COUNTER_SKY130_NGSPICE_LIB` 指向 SKY130A 的 `sky130.lib.spice`。
标准单元模型的上游许可见 [SKY130 库许可证](../../sky130_pdk/LICENSE.upstream)。

## 直接运行 OpenSTA

从仓库根目录 `code/` 执行，需匹配的 SKY130 TT Liberty 和 OpenSTA：

```sh
COUNTER_REPORT_DIR="$PWD/examples/counter/reports_sync_01" \
sta -no_init -no_splash -exit examples/counter/run_sta.tcl
```

输出目录必须不存在。默认周期为 10 ns，可指定待验证周期：

```sh
COUNTER_PERIOD_NS=8.0 \
COUNTER_REPORT_DIR="$PWD/examples/counter/reports_sync_8ns" \
sta -no_init -no_splash -exit examples/counter/run_sta.tcl
```

这是在给定周期下检查时序，不会自动寻找最高频率。
改变周期后应同时审查 setup、hold、脉宽和全部端点；不能仅根据 setup slack
将周期相减而认定得到 latch 电路的最高频率。

## 当前约束

`counter.sdc` 使用单一理想零偏斜时钟，50% 占空比；默认 master 在 0--5 ns
透明、slave 在 5--10 ns 透明。TT、1.8 V、25°C；每位输出负载为 0.010 pF，
对应前仿真的 10 fF。库 slew 阈值为 20%--80%，故线性 100 ps 全摆幅边沿
按 0.06 ns transition 建模。时钟相位忽略前仿真有限边沿的 50 ps 阈值偏移，
不用于逐皮秒对齐瞬态波形。

输入 en、rst_n 的 min/max delay 为 0.2/1.0 ns；输出 min/max delay 为
-0.05/1.0 ns；setup/hold uncertainty 均为 0.05 ns。这些仍是实验接口预算，
不是对 PWL 激励事件的直接换算。复位按同步数据路径执行 setup/hold 检查，
不固定 rst_n、不加 false path，也不生成不适用的 recovery/removal 报告。

无 SPEF、无物理时钟树；修改 COUNTER_PERIOD_NS 不会修改 SPICE 激励。

## 输出与完整流程

`run_sta.tcl` 校验八个 latch 的型号、引脚及共享 clk 连接，输出：

- `constraints.sdc` 原约束快照及 `effective.sdc` 实际求值后的约束。
- `latches.tsv` 实例、型号和 D/Q/GATE 或 GATE_N 映射。
- units、clocks、check_setup、setup、hold、pulse_width、checks、violations 报告。
- en、rst_n 各自的 setup/hold 路径报告。
- 每实例的 instance、arrival、load 和 DQ/CQ min/max 报告。

该 STA 入口不依赖其他案例的引脚图导出器。

需要重新综合并归档完整流程时，从 `code/` 执行：

```sh
COUNTER_PERIOD_NS=10.0 sh examples/counter/run_flow.sh ./run_counter_sync_01
```

输出目录必须是新目录且父目录已存在；需 Yosys、OpenSTA、Python 3、sha256sum。
此入口已同步改为检查当前同步复位报告，不再要求 reset→Q、recovery/removal
或 pin_graph 文件。原有运行目录和历史报告保持原样，不能视为当前网表的结果。

此综合/STA 归档入口不自动调用优化器，记录 optimization not_run。
最高频率求解与 SDC 导出使用下文的 schema 4 零偏斜入口。
Xschem 原理图和功能仿真见 `xschem/README.md`。

## 转换现有 OpenSTA 报告

当前归档目录为 `reports_opensta_10ns/`。从 `code/` 执行：

```sh
python examples/counter/reports_to_blif.py
```

默认生成 `counter.blif.out` 和 `counter_timing.json`，拒绝覆盖已有输出。
重新转换时使用 `--output <新文件.blif.out> --json-output <新文件.json>`；
`--reports` 可指定其他报告目录。转换器直接解析 `effective.sdc`，不执行 Tcl，
不依赖已删除案例的 Python 模块，也不修改报告。

本轮转换保留 26 条组合边、160 条 max/min 路径见证、8 个 latch 的逐实例
六参数、正负透明极性、窗口比例和报告脉宽要求，以及独立的 en、rst_n、
四个 count 输出预算。边延迟不包含源 latch 的 CQ/DQ 或外部 IO delay。
零组合延迟的 master→slave、slave→输出连线有意保留。
报告引脚连接及边覆盖会与 `counter_mapped.v` 对照，并保存来源文件 SHA-256。

### C++ 时序图读取

读取器支持 `.blif.out` 的 `TimingModel counter_mixed_polarity_feedback_v1` 标记，
保留全部 26 条组合边（含 8 条零延迟边）和独立端点，不合并 IO，也不删除反馈。
随后加载配套 schema 4 JSON，将端点识别为 8 个 latch、2 个输入、4 个输出；
加上索引 0 的独立参考点，共 15 个顶点。

```cpp
DelayGraph graph;
double maxCombinationalDelay = 0.0;
if (!readDelayGraph("examples/counter/counter.blif.out", graph, maxCombinationalDelay))
    throw std::runtime_error("Cannot read counter paths");
readLatchTiming("examples/counter/counter_timing.json", graph);
```

第一步仅加载拓扑与延时，端点类型暂为 `NodeIdx::Kind::Unknown`；第二步按名称匹配
并核对 JSON 的全部边及 min/max 延时。失败时不修改已有图。JSON 中每个端点必须
恰好分类一次，负延时、无穷值、重复边、错误极性/窗口或不匹配的配套文件都会报错。
IO 预算允许 SDC 的有符号值，组合路径延时仍要求 `0 <= min <= max`。

`NodeIdx` 保存逐实例六参数、`polarity`、`windowFraction` 和 `reportedPulseWidth`；
后者仅表示报告中的高电平（正极性）或低电平（负极性）要求，不代表完整 Liberty
检查覆盖。图属性 `counterTiming` 保存时钟波形、transition 和逐端口预算/负载；
setup/hold uncertainty 保存在图属性的同名字段。

也可通过主程序只读取并打印图规模，不执行优化（从 `code/` 运行）：

```sh
./main examples/counter/counter.blif.out 1 100 examples/counter/counter_timing.json --read-only
```

输出应包含 `vertices=15`、`edges=26`、`latches=8`、`inputs=2`、`outputs=4`，
最大组合延时为 `0.410682 ns`；这不是最小周期。`1 100` 沿用原命令行的必填占位参数。

读取与兼容性回归：

```sh
g++ -std=c++17 -Iinclude tests/test_read_counter.cpp src/timing_graph.cpp src/LP.cpp \
  -lglpk -o test_read_counter
./test_read_counter
```

### 零偏斜最高频率与 SDC 导出

现支持共享理想时钟、50% 占空比、零偏斜的 schema 4 counter。输出文件必须不存在。
完整主程序沿用原参数（从 `code/` 执行）：

```sh
./main examples/counter/counter.blif.out 1 100 examples/counter/counter_timing.json \
  --no-skew --export-sdc examples/counter/counter_zero_skew.sdc
```

也可只编译所需的 Boost 头文件与 GLPK 入口，无需 ELL/YTO 的 xtensor、LEDA、BLAS：

```sh
g++ -std=c++17 -O2 -Iinclude examples/counter/solve_counter.cpp \
  src/timing_graph.cpp src/howard.cpp src/LP.cpp src/sdc_export.cpp -lglpk -o counter_solver
./counter_solver examples/counter/counter.blif.out examples/counter/counter_timing.json \
  examples/counter/counter_zero_skew.sdc
```

CMake 的完整依赖环境也提供 `counter_solver` target。独立入口固定零偏斜，不打印偏斜调度。
当前数据的模型最小周期为 **1.584538 ns**，最高频率为 **631.098780843 MHz**。
Howard 和独立 LP 均须 Optimal、通过图及原式检查、周期一致，才能导出 SDC。

事件定义为 master[k] 在 `[kT,kT+T/2]` 透明，slave[k] 在 `[kT+T/2,(k+1)T]`
透明。master[k]→slave[k] 的周期差为 0；slave[k]→master[k+1] 和上升沿
input[k]→master[k+1] 的周期差为 1。输出 setup 相对 `(k+1.5)T` 的上升沿。
最晚传播使用 `A_j >= D_i + max_delay - cycle_shift*T`，逐 latch 使用
`D_i >= max(A_i+tdqMax, opening_i+tcqMax)` 和关闭沿 setup 界限。

当前临界约束可独立核算：en→_19_→_23_→count[2] 的输入预算、组合延时、两级
DQ、输出预算和 uncertainty 合计 `3.169076 ns`，跨越两个周期，因此
`T >= 3.169076/2 = 1.584538 ns`。在该周期存在通过全部模型约束的解。

最短路径使用 `min(tcqMin,tdqMin)` 的开启响应下界，逐边检查 hold；输入使用各自
min IO 预算，输出保留有符号 output min delay。不能通过此保守 hold 证明的输入
会被拒绝，不宣称其物理电路必然不可行。势变量中的 a/d 为已证明的最早到达下界，
不声称是精确波形。脉宽约束包含报告的对应极性要求，不声称覆盖未报告的 Liberty 弧。

导出的 SDC 保留全部端口 min/max delay、transition、load、uncertainty 和
50% 波形，时钟 source/network 及每个 GATE/GATE_N latency 均为零。
此最优值基于固定工况的标量延时包络，不等于已通过物理实现或多 PVT 签核。
ELL、偏斜优化、非 50% 波形及同极性反馈均未开放；不可删除 TimingModel 或降级 schema。

用导出的文件重新运行 OpenSTA（报告目录必须新建，候选文件周期不受 COUNTER_PERIOD_NS 覆盖）：

```sh
COUNTER_SDC="$PWD/examples/counter/counter_zero_skew.sdc" \
COUNTER_REPORT_DIR="$PWD/examples/counter/reports_zero_skew_candidate" \
sta -no_init -no_splash -exit examples/counter/run_sta.tcl
```

应同时检查 setup、hold、pulse_width、check_setup 及全部端点；不把借用路径的零 setup
slack 单独当作失败或最优证明。求解与导出回归（人工输入、反馈/IO/脉宽主导、缩短周期
不可行、零偏斜、实际 counter 和文件保护）：

```sh
g++ -std=c++17 -Iinclude tests/test_counter_solver.cpp src/timing_graph.cpp \
  src/howard.cpp src/LP.cpp src/sdc_export.cpp -lglpk -o test_counter_solver
./test_counter_solver new_test_candidate.sdc
tclsh tests/test_counter_sdc.tcl new_test_candidate.sdc
```

Tcl 回归使用 mock 命令，只验证语法与约束往返，不代替实际 OpenSTA。
