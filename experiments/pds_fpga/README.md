# FPGA / PDS 实验线

本目录是 zqilin641-jpg 的 FPGA/PDS 实验工作，原样导入自
\zqilin641-jpg/latch_STA_CODE\ @ \ffc73535b9012207edaad127c29c36cdd5847f2\。
导入时逐字节核对，未做修改。

## 1. 内容

| 路径 | 说明 |
|---|---|
| \PDS实际测量数据/PDS时序分析实验报告_润色版.docx\ | **最终报告底稿**（8 节） |
| \PDS实际测量数据/ff_and_latch/\ | FF / latch 同功能 RTL、\.fdc\、PDS tcl、ModelSim 脚本 |
| \PDS实际测量数据/time_borrow/\ | 时间借用三案例：baseline / borrow / overflow |
| \PDS实际测量数据/备份/\ | 旧版报告，仅存档，**不要引用** |
| \PDS实际测量数据/实验阶段一.docx\、\工作记录.docx\ | 过程材料 |
| \	ools/pds_howard.cpp\ | \PDS_GRAPH_V1\ → Howard 最小周期 |
| \upstream/\ | 该工具依赖的 zqilin 旧版头文件与 \howard.cpp\（见第 4 节） |
| \	ests/test_pds_graph_cli.py\ | PDS 图 CLI 的解析测试 |

## 2. 复现前提

- Pango Design Suite（PDS）
- ModelSim
- Windows + PowerShell
- 脚本中的绝对路径（如 \E:\pds\...\）需要按本机修改

具体命令见：

- \PDS实际测量数据/ff_and_latch/README.md\
- \PDS实际测量数据/time_borrow/README.md\

## 3. 结果与边界

- FF 固定相位最小通过点 15 ns；latch 20 ns。
- 相位优化后 FF 14.100 ns；latch 16.000 ns。
- 时间借用可见、可报告；但**没有 latch 比 FF 更快的证据**。
- 不是上板实测；没有 SDF；每个点分别 P&R。
- 报告第 7 节的 \phase_optimization\ 产物（\solve.py\、\erify.py\、\lp_solution.json\ 等）
  **不在仓库**，属于“本地证据，未入库”。

## 4. PDS_GRAPH_V1 求解器

\	ools/pds_howard.cpp\ 读取如下文本图：

\\\	ext
PDS_GRAPH_V1 <n> <m> <t0>
<u> <v> <weight> <transit> <edge_id>
...
\\\

- \
\：节点数；\m\：边数；\	0\：初始周期上界（ns）
- \weight\：约束边权重；\	ransit\：透明窗口 / 传输时间
- \edge_id\：数字字符串，输出临界环时原样返回

它使用 zqilin 旧版的 \HowardStatus\ / \HowardResult\ / \ArcProperties.constraintType\，
与主线 \include/\ 的新 API（\McrStatus\、三字段 \ArcProperties\）不兼容。
因此 \upstream/\ 保留了一套独立的旧版头文件和 \howard.cpp\，只服务这个工具，
**不参与主线构建**。

构建（在仓库根目录执行）：

\\\ash
cmake -S experiments/pds_fpga -B build_pds -DCMAKE_BUILD_TYPE=Release
cmake --build build_pds -j
python -I experiments/pds_fpga/tests/test_pds_graph_cli.py build_pds/pds_howard
\\\

预期最后一行：

\\\	ext
PDS graph CLI: analytic cycle, invalid input, unsupported-cycle reporting PASS
\\\

依赖：C++17 编译器 + Boost 头文件（只用到 Boost.Graph，不需要链接 Boost 库）。

## 5. 缺口

- PDS 原始报告 / 布局布线数据库未完整入库。
- \PDS_GRAPH_V1\ 的生成桥不在仓库，只有格式定义和测试。
- 第 7 节相位优化产物未入库。
