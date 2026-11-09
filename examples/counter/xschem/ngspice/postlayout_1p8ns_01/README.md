# Counter：1.8 ns 后布局布线 ngspice 功能仿真

本次使用 `openroad/pex_02/inputs/counter_routed.v` 与
`openroad/pex_02/results/counter.nominal.spef`，和既有 1.8 ns 后布线 STA
使用同一份寄生参数。未重新布局布线、提取寄生或修改原始 RTL。
最终结果见本目录 `summary.json` 与下列波形。


**结果：PASS。** 在本次 TT、1.8 V、25°C 和所列激励/负载下，
1.8 ns 周期的 counter 后仿真逻辑功能正确。

| 检查项目 | 2.5 ps 主仿真 | 1.25 ps 复核 |
| --- | ---: | ---: |
| 完整检查周期 | 128 | 128 |
| 总线采样次数 | 256 | 256 |
| 失败周期 / 稳定窗口失败 | 0 / 0 | 0 / 0 |
| 计数状态覆盖 | 0–15 全覆盖 | 0–15 全覆盖 |
| 15→0 回绕 | 5 次 | 5 次 |
| 使能保持周期 | 16 | 16 |
| 同步复位周期 | 11 | 11 |
| 最晚达到并保持预期 20%/80% 电平 | 0.696250 ns | 0.695625 ns |
| 原始时间点数量 | 94,079 | 186,563 |

两组功能结论一致，全部采样电压的最大差异为 **0.058752 mV**；
逐周期稳定时间的最大差异为 **1.875 ps**。全部 8 个 latch 时钟引脚
均收到 128 次上升沿与 128 次下降沿；主仿真的上升沿插入延迟范围
为 **0.194771–0.203894 ns**。

[全部周期波形](overview.png) · [计数及保持](count_and_hold.png) ·
[复位及恢复](reset_and_enable.png) · [15→0 回绕细节](wrap_detail.png) ·
[机器可读结果](summary.json)

## 电路与寄生回标

- SKY130 HD 原生标准单元 SPICE 与 SKY130A BSIM TT 模型，22 个逻辑单元、248 个 MOS。
- 包含原始 18 个单元、3 个 `clkbuf_4` CTS 缓冲器以及 1 个 `clkbuf_1` 时钟负载。
  `clkload0` 的 X 端与布线后 Verilog 一样悬空，保留其真实输入负载。
- 24 个 SPEF 信号/时钟网络，113 个独立电气节点；73 个单元信号引脚与 7 个端口全部回标。
  同一逻辑网络的不同引脚/内部节点通过提取电阻连接，未短接为理想导线。
- 89 个电阻、104 个非零对地电容、166 个非零线间耦合电容；
  对地电容合计 49.866453 fF，去重后耦合电容合计 11.307624 fF。
  SPEF 中互相记录的同一耦合电容只实例化一次，保留真实双节点耦合，零值电容不实例化。
- SPEF 是 `PIN_CAP NONE`；单元引脚本征电容由晶体管模型提供，未重复叠加 Liberty 引脚电容。
- 每位输出额外连接 10 fF 外部负载；电源与衬底使用理想 1.8 V/0 V 连接。

`conversion_audit.json` 记录转换统计、源文件 SHA-256 与检查结果。
转换前逐项校验既有提取归档的哈希，确认来源一致。
`models/node_map.csv` 保存 SPEF 节点到 SPICE 节点及逻辑网络的对应关系。
`models/counter_postroute.spice` 是完整互连 RC 与标准单元连接；
`models/sky130_cells.spice` 保存本次使用的原始单元 SPICE 内容。

本模型覆盖路由互连寄生、CTS 和单元原生晶体管电路；未包含电源网压降、
单元内部版图重新提取的扩散/局部互连寄生、封装模型或随机失配。

## 仿真条件

仿真器为 ngspice 45.2，原始版本输出保存在 `ngspice_version.txt`。
`inputs/spiceinit.reference` 归档本机兼容模式初始化配置；其中默认线程数 2
由各 testbench 中 `set num_threads=1` 覆盖。日志确认器件/实例 `scale=1e-6`。

| 项目 | 设置 |
| --- | --- |
| 周期 / 频率 | 1.8 ns / 555.556 MHz |
| 工艺角 / 电压 / 温度 | TT / 1.8 V / 25°C |
| 时钟占空比 | 源端 50%，按 50% 电压交点计算 |
| 时钟、rst_n、en 全摆幅边沿 | 上升/下降均 100 ps |
| 输入变化 | 在前一个源时钟上升沿后 1 ns 到达 50% 电压 |
| 输出负载 | 每位 10 fF |
| 仿真时长 | 231.21 ns，检查 128 个周期 |
| 最大时间步长 | 2.5 ps 主仿真、1.25 ps 复核 |
| 数值容差 | reltol=1e-4，abstol=1e-12，vntol=1e-6 |
| 初始化 | 自然 DC 工作点；先施加四周期同步复位，无强制计数初值 |

源时钟上升沿在 `(n+0.5)*1.8 ns`；实际 latch 时钟经过 CTS 和互连 RC。
`sink_clocks` 字段逐一记录全部 8 个 latch 时钟引脚的边沿数量、时钟插入延迟、
最小高/低脉宽。电压判断阈值为低电平 ≤0.36 V、高电平 ≥1.44 V。

## 激励与独立参考

每周期独立按 RTL 规则计算参考值：`rst_n=0` 时清零；否则 `en=1`
时模 16 加一；否则保持。参考值只从激励递推，不从模拟输出递推。

| 周期编号（从 0 开始） | rst_n | en | 行为 |
| --- | ---: | ---: | --- |
| 0–3 | 0 | 最后一周期为 1 | 起始清零、复位优先 |
| 4–38 | 1 | 1 | 连续加一，结束为 3 |
| 39–46 | 1 | 0 | 保持 3 |
| 47–66 | 1 | 1 | 连续加一，结束为 7 |
| 67–69 | 0 | 1 | 计数过程中清零 |
| 70–73 | 1 | 0 | 保持 0 |
| 74–109 | 1 | 1 | 连续加一，结束为 4 |
| 110–117 | 1 | 交替 0/1 | 交替保持/加一，结束为 8 |
| 118–121 | 0 | 0 | 使能为 0 时清零 |
| 122–127 | 1 | 1 | 恢复计数，最终为 6 |

每周期分别在源上升沿后 **1.17 ns（0.65T）**、**1.62 ns（0.90T）**
检查总线，另检查上升沿后 **1.17–1.71 ns（0.65T–0.95T）**
的全部保存时间点，必须持续处于参考计数对应的有效电平区间。
插值采样和稳定窗口一起覆盖每周期 2 次总线采样与 1 段稳定区间。
采样位置在运行前固定，以容纳真实 CTS 和晶体管输出传播、转换时间。

这些检查验证给定激励下稳定后的计数功能。采样点不是 SDC 外部接收器的 setup
截止时间，不能据此替代后布线 STA 或证明所有 PVT/输入到达时间下均满足时序。
`max_settling_to_20_80_ns` 是本次原始波形中输出进入并保持在预期 20%/80%
电平区间的最晚时间，相对于源上升沿，单位 ns；不是 STA slack。

## 文件

仓库归档保留原始 `counter.raw`。`waveforms.csv.gz` 可用下述重分析命令生成。

- `summary.json`：两组仿真、功能检查与时间步长收敛结果。
- `overview.png/.svg`：全部 128 个周期，源时钟、两个代表性 latch 时钟、复位、使能、四位输出与参考计数。
- `count_and_hold.png/.svg`：前 53 周期，连续计数及保持。
- `reset_and_enable.png/.svg`：中途复位、保持与恢复计数。
- `wrap_detail.png/.svg`：第一次 15→0 的回绕细节。
- `T_1p8ns_2p5ps/` 与 `T_1p8ns_1p25ps/`：各自的原始仿真结果：
  `counter_tb.spice`、`counter.raw`、`ngspice.log`、`console.txt`、`samples.csv`、
  `waveforms.csv.gz`、`summary.json`。
- `samples.csv`：周期、输入、参考计数、两次模拟采样、稳定窗口结果、20%/80% 电平稳定时间；时间单位 ns。
- `waveforms.csv.gz`：全部自适应时间点与保存信号，时间单位 s、电压 V、电流 A。
- `manifest.json`：生成文件的 SHA-256 与长度。

交互查看原始波形：在任一仿真子目录启动 `ngspice`，执行：

```text
load counter.raw
plot v(clk) v(xdut.ckm[0]) v(xdut.cks[3])
plot v(q3) v(q2) v(q1) v(q0)
```

## 复现

在项目 counter 目录执行，需要本机 SKY130 PDK、ngspice、NumPy 和 Matplotlib。
输出目录必须不存在，以保留历史记录。先在 `/tmp` 原生文件系统仿真，再复制到项目。

```sh
PYTHONPATH=/tmp/counter-plot-deps MPLCONFIGDIR=/tmp/counter-ngspice-matplotlib \
  FONTCONFIG_FILE=/tmp/counter-fonts.conf \
  python3 xschem/ngspice/run_postlayout.py \
  --output xschem/ngspice/postlayout_1p8ns_repeat01
```

对已有两组 `counter.raw` 重新分析、绘图：

```sh
PYTHONPATH=/tmp/counter-plot-deps MPLCONFIGDIR=/tmp/counter-ngspice-matplotlib \
  FONTCONFIG_FILE=/tmp/counter-fonts.conf \
  python3 xschem/ngspice/run_postlayout.py \
  --output xschem/ngspice/postlayout_1p8ns_01 --resume
```

临时绘图库/字体配置路径依赖本机环境，也可使用已有 NumPy/Matplotlib 安装。
