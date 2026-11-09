# SKY130 latch 小电路教学案例

本目录提供显式实例化标准单元的教学案例。Yosys 导出和 OpenSTA 补跑已完成，
实际运行产物已回传并核对。工具版本为 Yosys 0.68、OpenSTA 3.1.0。
顶层为 `tiny`，端口为 `i_clk`、`i_din`、`o_dout`；之前示例 SDC 的
`clk`、`din`、`dout` 需相应替换。

```text
i_din -> U_INPUT -> L1/Q -- U_LONG_HEAD -> U_LONG_MIDDLE -> U_LONG_TAIL --+
                         +-- U_SHORT ----------------------------------+ -> U_MERGE -> L2
L2/Q -> U_TAIL -> L3 -> U_OUTPUT -> o_dout
```

共有 3 个 `sky130_fd_sc_hd__dlxtp_1`、7 个 `sky130_fd_sc_hd__buf_1` 和
1 个 `sky130_fd_sc_hd__and2_1`。锁存器名称为 `L1/L2/L3`。
所有 GATE 均接 `i_clk`，高电平透明，低电平保持。无复位，仿真初值未知；
同相 latch 可能在一个窗口中连续穿透，不能视为三周期流水线。

## 实例语法

```verilog
sky130_fd_sc_hd__dlxtp_1 L1 (
    .D(input_data),
    .GATE(i_clk),
    .Q(launch_data)
);
```

第一个名字是库单元类型，`L1` 是电路实例名，点号后的名字是库引脚名，
括号中是本电路的信号。没有 `#` 延迟，真实延迟由 Liberty 及工作条件计算。

## Yosys 检查与导出

完整 SKY130 HD `tt_025C_1v80` Liberty 已位于
`../../sky130_pdk/sky130_fd_sc_hd__tt_025C_1v80.lib`。已核对三个目标单元、
信号引脚和 ns/pF 单位；无需再复制库文件或修改脚本路径。

在 WSL/Linux 终端执行：

```bash
# 从克隆后的仓库根目录执行
cd examples/tiny_3_latch_circuit
command -v yosys
command -v sta
yosys -V
sta -version
mkdir -p reports
yosys -l reports/yosys.log -s export.ys
```

Yosys 成功后会生成 `tiny_mapped.v`。确认日志没有 ERROR，实例统计为
三个 latch、七个 BUF、一个 AND2，再运行：

```bash
sta -no_init -no_splash -exit run_sta.tcl > reports/opensta.log 2>&1
```

没有真实运行时，本目录不会创建 `tiny_mapped.v` 或伪造时序报告。
若命令未找到，需先在 Linux 环境安装工具；如果项目复制到了 Linux 自有目录，
保留 `examples/` 和 `sky130_pdk/` 的相对结构，并相应修改 `cd` 路径。

导出脚本包含以下检查，实际可直接使用已准备好的 `export.ys`：

```text
read_liberty -lib -ignore_miss_func -ignore_miss_dir ../../sky130_pdk/sky130_fd_sc_hd__tt_025C_1v80.lib
read_verilog tiny.v
hierarchy -check -top tiny
check -assert
select -assert-count 3 t:sky130_fd_sc_hd__dlxtp_1
select -assert-count 7 t:sky130_fd_sc_hd__buf_1
select -assert-count 1 t:sky130_fd_sc_hd__and2_1
select -assert-count 11 tiny/c:*
select -assert-none tiny/t:$*
select *
stat
write_verilog -noattr -noexpr tiny_mapped.v
```

因为每个实例已经选定库单元，不必执行 ABC。
使用 `read_liberty -lib` 提供外部单元声明；不要用行为仿真模型展开这些测试用门。

随后 OpenSTA 读取同一 Liberty、`tiny_mapped.v` 和使用新端口名的 SDC。
检查 `L1/Q` 到 `L2/D` 的实际长短路径，及各 latch 的 setup/hold。

## OpenSTA 基线与结果

`tiny.sdc` 定义 10 ns 周期、高电平窗口 5--10 ns、输入最小/最大延迟
0.2/1.0 ns、输出最小/最大延迟 -0.05/1.0 ns、输入和时钟 slew 0.05 ns、
输出负载 0.005 pF、零 uncertainty。数值是首轮实验边界，非外部板级测量值。
首版理想时钟、无 SPEF，不包括布局布线互连 RC。

`run_sta.tcl` 核对库单元、11 个实例、3 个 latch 和 9 个 latch 引脚后，
在 `reports/` 中输出：

- `check_setup.rpt`：缺失时钟、IO 约束、未约束端点等结构性检查。
- `setup.rpt`、`hold.rpt`：最大、最小路径时序报告。
- `units.rpt`、`clocks.rpt`：实际工具单位及波形。
- `pulse_width.rpt`：latch 最小脉宽检查。
- `L1/L2/L3` 的实例、D 引脚到达时间、Q 负载及 D→Q/GATE→Q min/max 延迟计算报告。

先确认日志无错误、约束检查无遗漏，再核对 setup/hold。时序违例是实验结果，
不是解析失败；不要为了“通过”删除 hold 约束。MCR 接入保留路径映射、单独表达
IO 边界并明确周期编号，不能把完整 arrival 或 slack 当组合边延迟。

## 检查状态

OpenSTA 补跑日志无错误或警告，27 份预期报告齐全，`check_setup.rpt` 为空。
setup 报告包含 18 条路径，hold 报告包含 10 条路径，均未报告违例；
hold 最小报告 slack 为 0.302808 ns。部分 latch setup slack 为零且有实际
借时，不表示 10 ns 已是极限周期。修复前的 `opensta.log` 保留为历史记录，
当前验收依据为 `opensta_rerun.log`。

`opensta_baseline.json` 汇总逐实例六参数的报告值包络、Q 负载、当前报告覆盖的
Q→D 组合路径、最短/最长路径引脚映射以及原文件 SHA-256。setup 从借时表中
的带符号贡献恢复为要求值；hold 保留负值；传播延迟分别汇总 min/max 分析中
的 rise/fall。组合段排除源 latch 自身延迟，并以终点和起点 arrival 差交叉核对。

该文件是当前 TT、slew/load 下的基线证据。后文转换器可生成 MCR 输入和
逐实例六参数 JSON，当前入口已支持显式加载这些实例参数；未提供 JSON 时
使用统一常量。v3 已接入下文限定的真实 IO 和周期关系；新增完整引脚图与边界映射
的导出流程见文末。本日已有两轮真实导出归档于仓库根目录 `run_tiny_02/`，
图极值与见证已独立复核；结果范围和后续缺口见 `docs/progress/2026-10-25.md`。
候选调度的既有复核见下文。

技能 formatter 可解析文件；实例数量、最终输出连接及理想布尔抽象已检查。
完整严格门禁在加载外部接口时触发工具自身的 `NameError`，未通过验收。
详细状态见 `reports/validation_status.json`；`reports/gate.json` 为诊断记录。
运行脚本已通过 Tcl 解释器与模拟 STA 命令的语法/控制流检查，包括缺失库单元、
latch 数量不符的拒绝路径；这不等于实际工具运行。见 `reports/script_check.json`。
`reports/input_manifest.json` 记录真实 Liberty、源网表、运行脚本和 SDC 的 SHA-256。
`reports/external_interfaces/sky130_interfaces.v` 仅记录接口事实，不能用于综合、
功能仿真或 STA，也不能替代 Liberty。

`spec/tiny_spec.md` 和波形为行为说明，不是仿真结果。源码双语头中的默认
Description/testbench 路径来自技能格式模板，当前不存在对应 PDF 或 Vivado 工程。

## 转换为 .blif.out 和逐实例六参数 JSON

在项目根目录执行（Python 3.9+，仅使用标准库）：

```bash
python examples/tiny_3_latch_circuit/convert_opensta_reports.py
```

默认读取脚本旁的 `reports/`，生成脚本旁的 `tiny.blif.out` 和
`latch_timing.json`。脚本用自身路径定位默认文件，因此不依赖运行目录。
也可以指定输入和输出位置；输出建议放在报告输入目录之外：

```bash
python examples/tiny_3_latch_circuit/convert_opensta_reports.py \
    --reports examples/tiny_3_latch_circuit/reports \
    --output examples/tiny_3_latch_circuit/tiny.blif.out \
    --json-output examples/tiny_3_latch_circuit/latch_timing.json
```

本案例转换结果为：

```text
INPUT L1 0.083593 0.074577
L1 L2 0.336778 0.177533
L2 L3 0.072031 0.070218
L3 OUTPUT 0.095645 0.088638
```

每行第三列为最大组合延迟，第四列为最小组合延迟，单位 ns。
输入段从顶层输入端口开始，内部段从源 latch/Q 开始，输出段从末级 Q 开始；
源点行的延迟不计入组合段。到达时间差用于交叉核对逐段增量之和。
latch 内部延迟、时钟项、借时项和外部 IO delay 均不计入 .blif.out。
同一对边界之间的不同分支及 rise/fall 路径按最大值/最小值合并。

JSON 的 `nodes` 列表以 `instance` 对应 latch 名称，`parameters_ns` 包含
`tsu`、`thd`、`tdqMin`、`tdqMax`、`tcqMin`、`tcqMax`。setup 从报告贡献中
恢复符号后取最大要求，hold 保留符号后取最大要求；DQ/CQ 分别使用 min
分析的 rise/fall 最小值和 max 分析的 rise/fall 最大值。
`edges` 保留最长/最短路径见证，`paths` 保留原始端口和引脚序列、带符号的
外部 IO delay 报告贡献，`source_sha256` 记录输入报告哈希。

`clock_checks_ns` 另存 GATE 最小高/低脉宽要求，不属于六参数。
转换器复用 `../../sky130_pdk/extract_latch_timing.py`，读取同目录下的 common/cell
Liberty JSON，以 setup/hold 报告中的逐实例 GATE slew 做一维插值，并与
`pulse_width.rpt` 已列出的检查交叉核对。`pulse_width_sources` 保存库表哈希。
因此复制本案例到另一环境时，应同时复制 `sky130_pdk/` 下的提取脚本和两份库 JSON，
并保留 `examples/` 与 `sky130_pdk/` 的目录关系。`--pdk` 可指定库 JSON 所在目录。
首版只接受同一实例在报告中具有一个固定 GATE slew；多 slew、其他单元或工艺角会报错。

当前三个实例的高脉宽要求均为 `0.23101371836734697 ns`，库中没有低脉宽表，
所以低项显式为 `null`；各实例分别查询库表，并非从最坏一条报告推断其他实例。
v2 要求每个实例都具有显式高/低字段。旧 v1 仍兼容，但不包含脉宽检查。
MCR 将 `T >= max(high/duty, low/(1-duty))` 同时用于图、LP 和结果验证。
50% 占空比下脉宽下界为 `0.46202743673469394 ns`。这是 v2 旧 IO 模型的最优周期，
不是下述 v3 真实 IO 模型的最优周期；未含脉宽的更早基线为 `0.413084 ns`。

脚本会拒绝缺失 min/max 路径、缺失六参数来源、非有限数值、异常延迟排序、
错误单位、未完成的补跑日志、非空 check_setup 报告及输入文件覆盖。
输出在完成解析与验证后写入，使用同目录临时文件替换避免单文件截断。

支持范围限定为现有 OpenSTA 文本布局、单时钟和扁平的高电平 D/GATE/Q latch。
只转换报告实际覆盖的路径；扩大电路后，报告数量上限可能漏掉连接或极值，
需改用完整图导出验证覆盖。JSON 的路径 IO 项保留报告贡献，`io_constraints` 保存下文限定的 SDC 模型。
通过可选的第四个参数显式加载逐实例 JSON。v3 会拆分 INPUT/OUTPUT；v1/v2 保留旧占位模型：

```bash
./main examples/tiny_3_latch_circuit/tiny.blif.out 1 100 examples/tiny_3_latch_circuit/latch_timing.json
```

本例 SDC 高电平占空比为 0.5。可在命令末尾指定 (0, 0.5] 内的值，例如：

```bash
./main examples/tiny_3_latch_circuit/tiny.blif.out 1 100 examples/tiny_3_latch_circuit/latch_timing.json --duty-cycle 0.4
```

每次求解固定该占空比，透明窗口为 `[s_k+(1-duty)*T, s_k+T]`。
v3 默认占空比取自 SDC 波形，v1/v2 默认仍为 0.5；实验改变占空比后，
独立 STA 验证也需使用对应波形。端口和参考点的六参数为零，L1/L2/L3 使用 JSON 值。
最小脉宽已加入优化模型；求解器打印脉宽覆盖数量和周期下界。
v3 真实 IO 支持范围见下文；模型通过不等于独立 STA 验收。

路径相对于运行目录。JSON 按实例名称匹配，不依赖 `.blif.out` 的行顺序；
缺失、重复、未知实例或无效参数会报错。省略 JSON 参数时保留原来的统一常量。
逐实例参数用于 MCR 的 Howard、YTO、LP 和可行性检查；ELL 仍为独立旧模型。
v3 已接入以下受限 SDC IO 模型；其他 IO/时钟关系仍需扩展和独立验证。

## v3 真实 IO 与周期关系

`run_sta.tcl` 保存本次 STA 实际读取的 SDC 为 `reports/constraints.sdc`。
转换器只读取该快照中明确支持的单时钟、单数据输入/输出命令，拒绝未知命令、
缺失 min/max、重复项、错误波形和与报告不一致的 IO delay/uncertainty。
历史报告目录的快照由原 `input_manifest.json` 中的 SDC 哈希核对后归档，没有重跑或改写时序报告。

`io_constraints` 保存真实端口名、带符号的 IO delay、uncertainty 和周期关系。
本例输入 min/max 为 0.2/1.0 ns，输出为 -0.05/1.0 ns，不确定性为零。
令 `r=(1-duty)*T`，输入到达区间为 `[r+Imin,r+Imax]`；输出最晚要求为
`r+T-Omax-Usetup`，最早要求为 `r-Omin+Uhold`。因此在原 10 ns、50% 波形下，
输入端口到达为 5.2/6.0 ns，输出 setup/hold 要求为 14.0/5.05 ns。
输出 min 为负值时，保持要求必须取相反符号，不能直接将 -0.05 加入最早到达。

C++ v3 模式具有三个 latch、独立输入与输出节点，以及单独的零参考节点；
端口和参考点不再套用 latch 透明窗、DQ/CQ 或脉宽约束。所有数据路径均为同次事务、
cycle shift=0，输入发射为本周期上升沿，输出 setup/hold 捕获为下一/本周期上升沿。
首版要求连接输入和输出的无反馈 DAG；反馈、多端口、多时钟、下降沿参考或其他 SDC 例外会被拒绝。

最早离开时间的松弛变量不能直接作为物理 hold 证据。因此 latch 发射的路径另加保守检查：
使用 `opening+min(tcqMin,tdqMin)+pathMin` 作为最早响应下界，检查接收侧上一关闭沿
或输出同周期捕获沿的保持要求。这是充分条件，可能拒绝实际可行调度；不宣称完整精确的 STA 模型。
图、独立 LP 及原式验证都包含这些边界、周期关系和保守 hold 条件。ELL 因不支持此 IO 模型而跳过。

当前案例在 50%、40%、25% 占空比下，模型最优周期为 `3.541155 ns`。
该值由 `Imax + 全路径组合最大延迟 + 三个 DQ 最大延迟 + Omax` 给出独立下界，
不是从此前 0.462027 ns 做频率收益比较。模型仍使用路径包络、固定工况和理想时钟，
可按下文导出候选调度并运行独立 STA。用户已提供 `reports_howard_01/`：
10 条 setup 和 10 条 hold 路径均为 MET，最差 slack 分别为 0.000000/0.974505 ns，
已列出的 L1 高脉宽检查为 MET，三项 ideal network latency 与 Howard 输出一致。
这是当前工况下所提供报告层面的可行性结果；本次完整日志、逐实例脉宽明细和实际时钟实现仍待补充。
完整复核及结论范围见 `howard_validation_review.md`。

## 导出 Howard 调度并交给 OpenSTA

转换器同时保存 `sta_conditions`，含时钟端口、clock/input transition 和输出负载。
旧 v3 JSON 未包含此项时，仍可求解，但不能导出；先用原始基线报告重新运行转换器。
导出不会自动加周期余量，也不会修改六参数或 IO 预算。

本仓库根目录直接对应原工作区的 `code` 目录。同步源码到虚拟机后，从仓库的 `build/` 执行：

```bash
python3 ../examples/tiny_3_latch_circuit/convert_opensta_reports.py
cmake ..
cmake --build . -j2
./main ../examples/tiny_3_latch_circuit/tiny.blif.out 1 100 \
  ../examples/tiny_3_latch_circuit/latch_timing.json \
  --export-sdc ../examples/tiny_3_latch_circuit/candidate_howard_repro.sdc

cd ../examples/tiny_3_latch_circuit
MCR_SDC="$PWD/candidate_howard_repro.sdc" \
MCR_REPORT_DIR="$PWD/reports_howard_repro_01" \
sta -no_init -no_splash -exit run_sta.tcl
```

`cmake ..` 让已有构建目录发现新增的导出源文件。`--duty-cycle 0.4` 可与
`--export-sdc` 同时使用，两项顺序不限；SDC 使用本次实际求解的占空比。
Howard 和 LP 必须均为有效 Optimal，图约束及原式残差不超过 `1e-7 ns`，
周期差不超过 `1e-4 ns`。导出只使用 Howard 的完整调度，不混用 LP/YTO 偏移。
文件已有、Howard 失败或缺失工况时会报错，不覆盖文件或静默导出其他求解器的结果。
需要再次运行时，为 SDC 和验证报告选新的名称。
仓库已归档的 `candidate_howard.sdc` 和 `reports_howard_01/` 是本次结果证据，复现命令使用其他名称。

导出的基准时钟保持 IO 参考不变，latch GATE 引脚的 ideal network latency 为各自 `s_k`，
上升/下降沿及 min/max 使用相同延迟。注释列出 `T`、占空比、LP 对照周期、
各实例的偏移和透明窗口，端口/引脚缺失时 SDC 会报错。
只支持当前单时钟、简单扁平实例名和 GATE 接口，不能用于任意时钟结构。

指定候选模式时，`MCR_SDC` 和 `MCR_REPORT_DIR` 必须成对提供；报告目录必须尚不存在。
脚本读取路径相对于启动目录解析，随后保存该候选 SDC 快照到新目录，并生成 27 份时序报告。
无这两个环境变量时，仍执行原 `tiny.sdc` / `reports/` 的基线流程。

验收时检查 OpenSTA 日志、`check_setup.rpt`、`setup.rpt`、`hold.rpt` 和 `pulse_width.rpt`。
完整时钟路径中的 latency、透明边沿、输入发射及输出捕获周期必须与模型一致；
仅有正 slack 或工具退出码为零不够。保留全部真实 IO 约束，不能通过 false path 或
异步时钟分组排除违例。由于固定六参数和路径包络近似，STA 结果可能与求解器不同；
应据实际报告定位差异。候选报告不应直接送回原基线转换器（其中的 clock latency 不在其 SDC 子集内）。

回归测试包括当前四条边、六参数、IO/latch 延迟排除、负 hold、错误报告和
文件保护。运行：

```bash
python -m unittest discover -s examples/tiny_3_latch_circuit -p 'test_convert_opensta_reports.py' -v
```

## 完整引脚图、弧数据和边界映射导出

`run_sta.tcl` 在原有 27 份报告全部输出后，加载同目录的
`export_pin_graph.tcl`，显式执行 `sta::find_delays`，直接遍历 OpenSTA 的网络引脚、
全部图顶点、连线边和单元时序弧。它不读取 `report_checks` 的有限路径列表来构图。
复制工程时须同时复制这两个 Tcl 文件；仓库外层 `examples/` 与 `code/examples/`
各保留一份相同的脚本。

导出目录为本轮报告目录下的 `pin_graph/`，已有目录会拒绝覆盖。
所有文件为 UTF-8、带表头、双引号转义的 TSV，可用 Python 标准库
`csv.DictReader(stream, delimiter="\t")` 读取。时间统一为 ns。

| 文件 | 内容 |
|---|---|
| `pins.tsv` | 所有顶层端口和叶单元信号引脚，包括未连接引脚；记录实例、库单元、库、引脚方向、网络名及 Latch/IO 边界角色 |
| `vertices.tsv` | OpenSTA 图顶点与引脚 ID 的映射；双向引脚的 load/driver 顶点分别保存；无图顶点的网络引脚仍保留在 pins 表 |
| `edges.tsv` | 全部图边，含 net/cell 类型、时序角色、条件、mode 和禁用原因；latch 内部弧、时钟和检查弧也保留 |
| `arc_delays.tsv` | 每条 rise/fall 时序弧在当前 mode 下所有 `sta::scenes` 的 min/max 存储延迟，以及源/目标顶点 slew |
| `slews.tsv` | 每个顶点、scene、min/max、rise/fall 的存储 slew |
| `boundary_paths.tsv` | 相邻 Latch/数据 IO 边界之间按 scene、min/max、起终翻转方向区分的极值路径，以及顶点/边/弧 ID 序列 |
| `boundary_edges.tsv` | 每个边界对、每个 scene 的 Dmin/Dmax 包络，分别指向最短和最长路径 ID |
| `manifest.tsv` | 格式版本、单位、分析语义和图规模 |

ID 根据引脚名、顶点类型和时序边属性排序生成，不保存易变的 SWIG 指针。
同一份图导出的多个文件使用一致的 ID；不同拓扑之间不保证 ID 不变。
一个 pin 可以对应多个 vertex，或者没有 vertex，不能把两张表直接等同。

`arc_delays.tsv` 的 `status` 为 `calculated`、`disabled` 或 `not_applicable`。
禁用弧及 setup/min、hold/max 不适用项保留结构并留空延迟，不填伪造的零值。
非有限数值、缺失接口、无法区分的平行边或没有时序弧的边会报错。
`from_vertex_slew_ns`、`to_vertex_slew_ns` 是图中该顶点的 GBA slew，
不是每条输入弧单独计算的输出 slew，不能当作逐路径重新表征结果。

边界提取从顶层数据输入或 latch Q 开始，到遇到的第一个 latch D 或顶层数据输出
为止。时钟源端口不作为数据输入，且只沿 `wire`、`combinational` 活动弧传播。
因此 DQ/CQ、setup/hold 检查、时钟 latency、外部 IO delay 都不会加进组合延迟。
起点 arrival 置零，使用图中已经计算的弧延迟求和。
rise/fall 在反相、非单调弧和分支重汇合处分别维护；最短与最长见证独立保存。
压缩后可以出现 latch 反馈边，但纯组合环会明确报错，不能靠 STA 的断环边静默消失。

这里得到的是**当前工况下固定 GBA 弧权重的结构极值**，没有做逐路径 slew/load
重新计算或布尔可敏化分析；条件与禁用信息保存在图中。当前 runner 仍限定本例的
单时钟、扁平 D/GATE/Q latch 和无 SPEF 工况；顶层双向端口和 FF 边界会拒绝。
输出先写临时目录，全部完成后才发布为 `pin_graph/`；失败可能留下
`.pin_graph_*` 临时目录，不能将其当作成功结果。
这些新文件暂不替换原报告转换器生成的 JSON 或现有求解器输入。

使用已有 Howard 候选运行一轮，并为本轮指定尚不存在的报告目录：

```bash
cd examples/tiny_3_latch_circuit
MCR_SDC="$PWD/candidate_howard.sdc" \
MCR_REPORT_DIR="$PWD/reports_graph_01" \
sta -no_init -no_splash -exit run_sta.tcl > opensta_graph_01.log 2>&1
```

检查日志中同时出现 `Complete pin graph written to` 和最后的
`Reports written to`。当前电路应有 `i_din→L1`、`L1→L2`、`L2→L3`、
`L3→o_dout` 四组边界连接；仍需用真实执行输出核对延迟和见证。
原有基线和候选报告没有因新增脚本而被重写。

接口依据为 OpenSTA 3.1 的官方
[Graph.i](https://github.com/The-OpenROAD-Project/OpenSTA/blob/150bc0dbd103cbc97c0f85f63c4c8338826121fd/graph/Graph.i)、
[DelayCalc.i](https://github.com/The-OpenROAD-Project/OpenSTA/blob/150bc0dbd103cbc97c0f85f63c4c8338826121fd/dcalc/DelayCalc.i)
及相关网络/Liberty SWIG 接口；其他版本缺少所需接口时会报错。

## 一次执行 Yosys、STA、优化与候选验证

配置好 Linux/WSL 中的 Yosys、当前 exporter 所需的 OpenSTA、Python 3.9+，
并构建支持 `--export-sdc` 的 `main` 后，在仓库根目录执行：

```sh
sh examples/tiny_3_latch_circuit/run_flow.sh ./build/main ./run_tiny_01
```

第二个参数必须是尚不存在的目录，且其父目录已经存在。相对路径从调用目录解析。
脚本不需要可执行位；再次运行请指定新目录名。求解器须先构建，脚本不自动配置 Conda 或编译依赖。

脚本复制本轮需要的源网表、初始 SDC、Yosys/Tcl/Python 脚本、完整 Liberty 和库表，
在新目录内依次执行：Yosys 检查与网表导出 → OpenSTA 基线报告与引脚图 →
报告转换和检查 → Howard/LP 求解及候选 SDC 导出 → 新 OpenSTA 进程验证候选。
继承的 `MCR_SDC`/`MCR_REPORT_DIR` 不影响本轮基线。原案例及历史报告不会被覆盖。

运行目录保存 `tool_versions.txt`、源码 Git 状态（可用时）、求解器路径/参数/哈希、
执行脚本与输入副本及 `inputs.sha256`；末尾再检查输入和求解器哈希。
五阶段日志位于 `logs/` 及案例的 `reports/`。案例路径为运行目录中的
`examples/tiny_3_latch_circuit/`，其中包含基线 `reports/`、生成的 `tiny.blif.out`、
`latch_timing.json`、`candidate_howard.sdc` 和候选 `reports_candidate/`。
两轮报告各包含本轮的 `pin_graph/` 导出。

`baseline_check.json` 和 `candidate_check.json` 记录已报告的路径数、最差 setup/hold slack、
已列出的脉宽数量和引脚。退出码非零表示本轮未完成或未通过，保留中间产物供排查。
检查器拒绝工具日志错误/警告、未完成输出、非空 `check_setup`、缺失图文件、
缺失/违例路径、边界对覆盖变化及缺失/违例脉宽；不能仅以 `sta` 退出码零判定通过。

成功状态 `reported_checks_passed` 仅表示所报告检查通过。最坏脉宽摘要可能只列一个实例，
固定数量的路径报告也不是任意电路的完整签核；仍需核对时钟沿、latency、周期映射和模型范围。
此入口继续使用已有报告转换器生成求解器输入，新增完整引脚图另行归档，尚未取代转换器。
当前 Yosys 脚本适用于显式实例化标准单元的 tiny，未提供任意行为级 RTL 的综合映射流程。

检查器测试仅使用归档报告与明确标记的 mock 图/日志，不执行 STA：

```sh
python3 -m unittest discover -s tests -p test_flow_reports.py -v
```

## 将引脚图渲染为 PNG / SVG

`render_pin_graph.py` 使用 Matplotlib 和 NetworkX，直接读取完整图导出的 TSV，
不修改原始数据，也不重新进行时序分析。首次使用缺少依赖时安装：

```sh
python3 -m pip install matplotlib networkx
```

在仓库根目录，以本轮候选结果为例：

```sh
python3 examples/tiny_3_latch_circuit/render_pin_graph.py \
  run_tiny_02/examples/tiny_sky130/reports_candidate/pin_graph
```

默认在同轮 `reports_candidate/figures/` 新建目录，输出：

- `pin_graph.png`、`pin_graph.svg`：完整引脚结构图，按单元实例分组，区分连线、
  组合弧、Latch DQ、时钟/CQ 和检查弧，保留孤立内部引脚及没有图顶点的网络引脚。
- `boundary_graph.png`、`boundary_graph.svg`：压缩的 Latch/IO 边界图，标注 scene、
  Dmin/Dmax（ns）和边 ID；数值直接来自 `boundary_edges.tsv`。

基线图将输入改为 `reports/pin_graph` 即可。已有输出目录会拒绝覆盖；重新渲染可指定新目录：

```sh
python3 examples/tiny_3_latch_circuit/render_pin_graph.py \
  run_tiny_02/examples/tiny_sky130/reports_candidate/pin_graph \
  --output-dir run_tiny_02/figures_candidate_v2
```

图片用于检查图结构和已导出的组合延迟，不表示 setup/hold 已通过，也不将边界 Dmax
当作全路径 slack。完整图的 setup/hold/width 边是检查关系，不是数据传播连接。
脚本读取 schema 1 / ns 的图，适合当前小电路；大规模网表应分块查看或采用交互工具。
无需 Graphviz、OpenSTA 或求解器即可渲染已有 TSV。

渲染与输入校验测试：

```sh
python3 -m unittest discover -s tests -p test_render_pin_graph.py -v
```
