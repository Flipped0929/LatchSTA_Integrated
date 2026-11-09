# Counter 寄生提取结果

已从 `run_03/results/08_routed.odb` 完成 OpenRCX 布线寄生提取。
结果另存于 **`pex_02/`**，原布局布线数据库未改写。
该提取阶段未进行后布线 STA，也未把 SPEF 注释到 STA 时序引擎。
后续已独立完成的 STA 见 **[`POST_ROUTE_STA.md`](POST_ROUTE_STA.md)**：
1.65 ns 存在 setup 违例；复用相同网表/SPEF 的 2 ns、1.8 ns 检查均通过。
提取阶段文件和记录保持原样。

## 交付文件

| 文件 | 内容 |
| --- | --- |
| [`pex_02/results/counter.nominal.spef`](pex_02/results/counter.nominal.spef) | 24 条信号/时钟网络的互连电阻、接地电容、线间耦合电容及节点坐标 |
| [`pex_02/results/09_extracted.odb`](pex_02/results/09_extracted.odb) | 已保存提取后 RC 对象的完整 OpenDB 数据库 |
| [`pex_02/results/09_extracted.def`](pex_02/results/09_extracted.def) | 提取器整理导线内部编码后写出的 DEF，物理几何保持一致；RC 数值以 SPEF/ODB 为准 |
| [`pex_02/reports/net_parasitics.csv`](pex_02/reports/net_parasitics.csv) | 逐网络的连接数、电阻数、接地/耦合电容和电阻值之和 |
| [`pex_02/reports/coupling_capacitors.csv`](pex_02/reports/coupling_capacitors.csv) | 按物理节点对去重的耦合电容表 |
| [`pex_02/reports/verification.json`](pex_02/reports/verification.json) | 完整核对结果和统计 |
| [`pex_02/reports/geometry_verification.json`](pex_02/reports/geometry_verification.json) | 提取前后实际金属/过孔几何的核对结果 |
| [`pex_02/logs/extraction.log`](pex_02/logs/extraction.log) | 完整 OpenROAD/OpenRCX 提取日志 |
| [`pex_02/manifest.json`](pex_02/manifest.json) | 源数据库、规则、参考网表/SDC、输出文件的路径及 SHA-256 |

匹配的物理网表和 SDC 副本保存为 `pex_02/inputs/counter_routed.v` 和
`counter_routed.sdc`，供以后使用；本轮没有读入该 SDC 或 Liberty 进行时序分析。

## 提取统计

| 项目 | 结果 |
| --- | ---: |
| 提取角 | nominal，规则文件 model index 0 |
| 信号/时钟网络 | 24 / 24 |
| 顶层信号端口 | 7 / 7 |
| 实例引脚与顶层端口连接 | 80 / 80 |
| SPEF 电阻元件 | 89 |
| 接地电容节点 | 113 |
| 唯一耦合电容节点对 | 188，包含 166 对非零及 22 对零值 |
| SPEF 中耦合记录数 | 376；同一个耦合元件在两个相邻网络中各记一次 |
| 接地电容总和 | 49.866453 fF |
| 去重后耦合电容总和 | 11.307624 fF |
| 各网络 `*D_NET` 总电容之和 | 72.481717 fF |

`*D_NET` 总电容包含该网络全部接地电容和关联耦合电容。
跨网络相加时，同一个耦合元件会被计入两次，因此不能把该列的和视为
“接地电容加去重后的耦合电容”。小数尾差来自 SPEF 文本输出精度。
零值耦合项是提取器在 0 fF 阈值设置下导出的记录，检查时保留并单独统计。

日志中的 113 个 RSeg 包括每条网络的一个根部零段；SPEF `*RES` 实际导出
89 个电阻元件。电阻分段不是与 156 个物理过孔一一对应的列表，电阻值中包含过孔贡献。
`resistance_sum_ohm` 仅表示该网络各电阻项的算术和，分支网络不能将其直接当成等效电阻或延时。

## 时钟网络示例

| 网络 | 电阻项 | 接地电容 / fF | 关联耦合电容 / fF | `*D_NET` 总电容 / fF |
| --- | ---: | ---: | ---: | ---: |
| `clk` | 2 | 5.152632 | 0.394250 | 5.546880 |
| `clknet_0_clk` | 5 | 2.947934 | 0.790364 | 3.738300 |
| `clknet_1_0__leaf_clk` | 9 | 3.177775 | 1.429275 | 4.607050 |
| `clknet_1_1__leaf_clk` | 7 | 1.543547 | 0.289142 | 1.832690 |

## 规则和参数

使用 OpenROAD `26Q2-1164-g08f67ee5ec` 的 OpenRCX，基于已详细布线的 OpenDB 几何提取。
规则使用 ORFS SKY130 HD 平台配置指定的：

```text
$HOME/eda/OpenROAD-flow-scripts-live/flow/platforms/sky130hd/rcx_patterns.rules
```

该平台路径是指向 `../sky130hs/rcx_patterns.rules` 的原有符号链接。
本轮按 SKY130 HD 平台的默认配置使用它，并保存了解引用后的规则内容及哈希。
规则的 6 层与数据库的 `li1, met1, met2, met3, met4, met5` 对应。
RC 的 `nominal` 名称表示此规则文件的第 0 个提取模型，不等于对器件进行完整 PVT/失配扫描。

实际调用：

```tcl
define_process_corner -ext_model_index 0 nominal
extract_parasitics -ext_model_file <保存的规则文件> \
    -max_res 50 -coupling_threshold 0.0 \
    -cc_model 10 -context_depth 5 -no_merge_via_res
write_spef -coordinates <输出 SPEF>
write_db <输出 ODB>
```

参数语义参见 [OpenRCX 官方文档](https://openroad.readthedocs.io/en/latest/main/src/rcx/README.html#extract-parasitics)：
串联电阻合并阈值为 50 Ω，线间耦合转接地的阈值为 0 fF，横向考虑 10 个 track，
垂向 context depth 为 5，并使用 `-no_merge_via_res` 选项。
未使用 `-lef_rc` 进行粗略替代，也没有调用 `adjust_rc` 缩放结果。

## 已完成的检查

- 全部 24 个 `*D_NET` 与布线数据库逐一对应，7 个信号端口和 80 个连接端点完整匹配。
- 各网络的电阻图连通，端口、引脚及内部 RC 节点均在同一电阻网络中。
- 全部电阻/电容值有限且非负；零值条目允许保留。
- 188 对耦合记录在两个网络中的端点与数值相互一致，未将重复记录算作两个元件。
- 每网络的接地电容、总电容和电阻统计与 SPEF 及重新打开的提取后 ODB 一致。
- 提取前后的 156 个过孔形状完全一致；54 个“网络×金属层”组合的金属矩形并集精确一致。
- 实例放置、IO、行和电源网络的 DEF 部分保持一致，原始 ODB 的 SHA-256 仍与布局布线阶段的 manifest 一致。
- 提取日志无错误或警告，未执行后布线 STA 或 STA SPEF 注释。

OpenRCX 会为 RC 网络重排并拆分导线编码，所以 DEF 文本不再逐字相同，
金属矩形分段数由 163 变为 171；按实际矩形并集检查，物理金属没有增加、删除或移动。

## 结果范围

这是基于平台规则和 LEF/DEF/OpenDB 模型的信号/时钟互连寄生提取，
不是晶体管级全版图场求解或 foundry 签核提取。
VDD/VSS 的物理几何作为环境存在，本 SPEF 不包含独立的电源网 RC/IR-drop 分析。
SPEF 标头为 `PIN_CAP NONE`，不含 Liberty 中的单元引脚电容，
也不含 SDC 中每位输出的 10 fF 外部负载；这两部分应在后续使用相应库/约束时处理。

该提取阶段不输出 setup/hold、skew、slack 或后布线最高频率；
后续 STA 对 1.65 ns 的分析结果见本页开头的独立报告链接。

## 重新执行

在 counter 项目目录使用新的输出目录：

```sh
sh openroad/extract.sh openroad/pex_repeat01
COUNTER_RCX_AUDIT_DB="$PWD/openroad/run_03/results/08_routed.odb" \
COUNTER_RCX_AUDIT_PREFIX="$PWD/openroad/pex_repeat01/reports/before" \
  openroad -no_init -exit openroad/extract_audit.tcl
COUNTER_RCX_AUDIT_DB="$PWD/openroad/pex_repeat01/results/09_extracted.odb" \
COUNTER_RCX_AUDIT_PREFIX="$PWD/openroad/pex_repeat01/reports/after" \
  openroad -no_init -exit openroad/extract_audit.tcl
python3 openroad/verify_extraction.py openroad/pex_repeat01
```

`extract.sh` 不给参数时自动使用带时间戳的目录，拒绝覆盖已有结果。
`COUNTER_RCX_INPUT` 可指定其他布局布线运行目录，`COUNTER_RCX_RULES` 可指定规则文件。
提取脚本只加载物理数据库；检查脚本只读取 OpenDB/SPEF 数据，不调用时序分析。
