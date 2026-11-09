# Counter 晶体管级 ngspice 仿真

最新 **1.8 ns 后布局布线仿真** 使用真实 CTS 与已提取的 SPEF RC，见
[postlayout_1p8ns_01/README.md](postlayout_1p8ns_01/README.md)、
[结果汇总](postlayout_1p8ns_01/summary.json)和
[完整波形](postlayout_1p8ns_01/overview.png)。
复现脚本为 `run_postlayout.py`；以下内容保留原有三种周期的综合后仿真记录。

本目录使用 xschem 实际导出的 `../simulation/counter.spice` 作为 DUT，
展开 SKY130 HD 的 18 个标准单元，共 214 个 MOS 管。
标准单元 SPICE 来自项目 `pdk_work/sources/sky130_fd_sc_hd/cells/`，
器件模型使用本机 SKY130A 的 ngspice TT 库。未使用数字行为模型代替晶体管。

完成后的结果汇总见 [RESULTS.md](RESULTS.md)，
三种周期对比图见 [results/comparison.png](results/comparison.png)。

## 工况与激励

| 项目 | 设置 |
| --- | --- |
| 时钟周期 | 10 ns、2 ns、1.65 ns |
| 工艺角 / 电压 / 温度 | TT / 1.8 V / 25°C |
| 输出负载 | 每位 10 fF，和 `counter.sdc` 的 0.010 pF 一致 |
| 占空比 | 按 50% 电压交点计为 50% |
| 时钟、使能、复位上升/下降时间 | 全摆幅 100 ps，对应线性边沿 20%–80% 的 60 ps |
| 输入变化时间 | 在前一个时钟上升沿后 1 ns 到达 50% 电压 |
| 最大积分步长 | 主仿真 5 ps；1.65 ns 另以 2.5 ps 复算 |
| 数值容差 | `reltol=1e-4, abstol=1e-12, vntol=1e-6` |
| 初始化 | 自然 DC 工作点，不强制 count 初值；开始施加四周期同步复位 |
| 仿真长度 | 每组 128.45 个周期，完整检查 128 次计数更新 |

时钟初始为低，50% 电压上升交点位于 `(n+0.5)T`，下降交点位于 `(n+1)T`。
`PULSE` 的延迟和高电平平顶时间已补偿 100 ps 边沿，因此改变周期不会改变实际占空比。
使能与复位的 1 ns 延迟是固定绝对时间，不随周期缩放，采用现有 SDC 的最大输入延迟预算。

三种周期使用同一组逻辑序列。以下周期编号从 0 开始：

| 周期 | rst_n | en | 预期行为 |
| --- | ---: | ---: | --- |
| 0–2 | 0 | 0 | 起始清零 |
| 3 | 0 | 1 | 复位优先于使能 |
| 4–38 | 1 | 1 | 连续 35 次加一，包含回绕，结束为 3 |
| 39–46 | 1 | 0 | 保持 3 |
| 47–66 | 1 | 1 | 连续 20 次加一，结束为 7 |
| 67–69 | 0 | 1 | 在使能有效时同步清零 |
| 70–73 | 1 | 0 | 保持 0 |
| 74–109 | 1 | 1 | 连续 36 次加一，结束为 4 |
| 110–117 | 1 | 交替 0/1 | 保持与加一交替，结束为 8 |
| 118–121 | 0 | 0 | 使能无效时同步清零 |
| 122–127 | 1 | 1 | 重新计数，最后一次检查为 6 |

## 检查方法

每个上升沿按 `rst_n=0 -> 0`，否则 `en=1 -> (count+1) mod 16`，
否则保持，独立计算参考计数。不是用仿真输出递推参考值。

每周期在上升沿后 `0.4T`（高电平相）和 `0.9T`（低电平相）分别检查四位输出，
并检查从上升沿后 `0.4T` 到 `0.95T` 的完整保存波形区间。
每一位低电平必须不高于 0.36 V，高电平必须不低于 1.44 V；
中间电平、错计数和保持区间内越出有效电平范围均视为失败。
因此每组包含 256 次总线采样和 128 段稳定区间检查。
另从原始波形核对实际时钟上升沿、周期和每周期的使能/复位电平。

`max_settling_to_20_80_ns` 是相对上升沿，输出总线进入并持续保持在
预期 20%/80% 电平区间的最长观测时间；它是本次波形统计，不是 STA slack。

## 输出文件

仓库归档保留原始 `counter.raw`。`waveforms.csv.gz` 可用下述重分析命令生成。

每个 `results/T_*ns/` 子目录包含：

- `counter_tb.spice`：实际使用的激励、电源、负载和分析命令。
- `counter.raw`：ngspice 原始二进制瞬态波形。
- `ngspice.log` / `console.txt`：仿真器日志和控制台输出。
- `waveforms.csv.gz`：完整自适应时间点的波形，时间单位 s、电压 V、电流 A。
- `samples.csv`：逐周期的参考值、两次实测值、四位电压、稳定区间检查和通过标志；时间单位 ns。
- `summary.json`：机器可读的检查结果。
- `waveforms.png/.svg`：前 53 周期的模拟电压波形和计数对照。
- `reset_and_enable.png/.svg`：中途复位与恢复计数的局部波形。
- `carry_detail.png/.svg`：第一次 15→0 回绕的局部波形，包含 master 内部节点。

`results/models/` 保存 DUT 网表与原始标准单元 SPICE 内容。
`manifest.json` 记录模型路径、源文件 SHA-256、仿真器版本及参数。
`results_step2p5ps/` 保存 1.65 ns 的步长复算结果。

ngspice 交互读取原始结果的示例：

```text
load counter.raw
plot v(clk) v(rst_n) v(en)
plot v(q0) v(q1) v(q2) v(q3)
```

## 重新运行

需要 Python 的 NumPy、Matplotlib 和本机 `ngspice`。在 counter 目录执行：

```sh
python3 xschem/ngspice/run_counter.py --output xschem/ngspice/results_repeat01
```

本次使用的绘图依赖安装在临时目录，可在该目录仍存在时这样运行：

```sh
PYTHONPATH=/tmp/counter-plot-deps python3 xschem/ngspice/run_counter.py \
  --output xschem/ngspice/results_repeat01
```

输出目录必须不存在，避免覆盖历史结果。支持 `--pdk-root`、`--cell-source`、
`--ngspice`、`--periods`、`--step-ps`、`--input-delay-ns` 和 `--jobs`。
只重新核对已有原始波形并生成图表：

```sh
PYTHONPATH=/tmp/counter-plot-deps python3 xschem/ngspice/run_counter.py \
  --output xschem/ngspice/results --analyze-only
```

仿真先在 `/tmp` 原生文件系统中执行，再复制到项目目录，避免 HGFS 的原地写入问题。

## 结论范围

这是 TT、1.8 V、25°C、理想共用时钟及所列负载/输入序列下的晶体管级功能验证。
使用原始单元 SPICE 和器件模型电容，没有加入版图提取的扩散面积/互连寄生、
物理时钟树或随机失配。输入采用最大到达时间的一个确定实例，未遍历 SDC 的全部
输入到达范围、时钟不确定度或输出接口预算；本次验证也不是极限频率搜索或全 PVT 签核。
