# SKY130 四位 latch 计数器原理图

`counter.sch` 是可直接编辑的 xschem 标准单元级原理图，根据上一层目录的
`counter_mapped.v` 搭建。使用本机 SKY130A PDK 的 `sky130_stdcells` 符号库，
单元系列为 `sky130_fd_sc_hd`。

## 打开

在 counter 项目目录执行：

```sh
sh xschem/open.sh
```

也可以直接执行：

```sh
xschem --rcfile ./xschem/xschemrc ./xschem/counter.sch
```

配置默认使用 `$HOME/eda/pdk/sky130A`，支持通过 `PDK_ROOT` 指定其他安装根目录。
启动脚本会进入原理图目录并加载项目配置。`counter.svg` 和 `counter.png` 可直接预览。

## 电路连接与读图

图中每行对应一位，信号由左至右经过组合逻辑、master latch、slave latch，
输出为 `count[3:0]`。相同网络标签表示电气连接，计数反馈通过标签接回组合逻辑。

| 网表实例 | SKY130 单元 | 数量 |
| --- | --- | ---: |
| `_07_`、`_10_` | `o21ai_0` | 2 |
| `_08_`、`_11_`、`_15_` | `a21oi_1` | 3 |
| `_09_` | `and3_1` | 1 |
| `_12_` | `a41o_1` | 1 |
| `_13_` | `nand2_1` | 1 |
| `_14_` | `a31oi_1` | 1 |
| `_16_` | `nor3b_1` | 1 |
| `_17_` 至 `_20_` | `dlxtn_1`，master | 4 |
| `_21_` 至 `_24_` | `dlxtp_1`，slave | 4 |

共 18 个标准单元。原理图实例名前增加 `x`，例如 `_07_` 对应 `x_07_`，
以便直接生成合法 SPICE 子电路实例。Yosys 中的 `assign count = slave`
通过统一网络名实现，`slave[i]` 在图中记为 `count[i]`。

八个 latch 的 `GATE_N` / `GATE` 均接同一 `clk`。master 在低电平透明，
slave 在高电平透明。`rst_n` 为低有效的数据通路同步清零，优先于 `en`；
`en=1` 时模 16 加一，`en=0` 时保持。

电源端口 `VPWR` 接 1.8 V，`VGND` 接 0 V。每个标准单元的实例属性明确设置
`VPB=VPWR`、`VNB=VGND`，以及对应的 `VPWR`、`VGND` 电源连接。
这些隐式电源引脚会写入 SPICE 网表。

## 已完成的核对

- xschem 导出 SPICE 和 Verilog 均通过 ERC，无错误或悬空网络警告。
- 从实际导出的网表逐实例核对全部 18 个单元及其信号引脚。
- SPICE 中逐一核对电源、阱连接和顶层 9 个标量端口。
- 使用本仓库 SKY130 官方功能模型进行 Icarus Verilog 仿真，
  原理图导出网表、`counter_mapped.v` 和 `counter.v` 在 656 个周期内一致。
  覆盖全部 64 种计数状态/复位/使能组合、连续回绕、保持、复位优先级，
  并检查高电平改变输入以及低电平期间输出保持。
- 已在 xschem 中加载并检查 SVG/PNG 排版。

功能仿真使用零延时数字模型。导出的 SPICE 文件是标准单元级子电路，
未附加晶体管模型、激励或瞬态仿真结果。

10 ns、2 ns、1.65 ns 的晶体管级 ngspice 仿真另见
[`ngspice/README.md`](ngspice/README.md)，结果及波形保存在该目录下。

## 修改后重新导出和检查

在 counter 项目目录执行：

```sh
xschem -r -q --rcfile ./xschem/xschemrc \
  --script ./xschem/export.tcl ./xschem/counter.sch
python3 xschem/verify.py --simulate
```

`export.tcl` 更新 `counter.svg`、`simulation/counter.spice`、
`simulation/counter.v` 和 `simulation/erc.txt`。它先在 `/tmp` 中导出网表再复制，
以避免 HGFS 共享目录内网表后处理产生 NUL 字节。
PNG 是交付时保存的预览，重新导出只更新 SVG。

`verify.py` 默认从项目根目录下的 `pdk_work/sources/sky130_fd_sc_hd`
读取功能模型；可通过 `--cell-source <路径>` 改用其他 SKY130 单元源码目录。
省略 `--simulate` 可只检查网表和 ERC。
