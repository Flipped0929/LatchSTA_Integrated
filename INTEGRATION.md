# 整合记录

## 1. 目的
把两位队友的工作合成一个可追溯、可构建、可引用的仓库，同时不改变任何一方的核心代码。

## 2. 来源
| 轨道 | 仓库 | 分支 | 完整 SHA | 日期 |
|---|---|---|---|---|
| 主线 | BailuFrost/LatchSTA_Code | main | 423e489377b6e32b9f3c3107800a195ed0ee3289 | 2026-11-05 |
| PDS 实验 | zqilin641-jpg/latch_STA_CODE | main | bffc73535b9012207edaad127c29c36cdd5847f2 | 2026-10-26 |

## 3. 方法
- 以 BailuFrost 的 423e489 工作树为基底。
- 把 zqilin 的 PDS实际测量数据/ 原样放到 experiments/pds_fpga/PDS实际测量数据/。
- 把 zqilin 的 tools/pds_howard.cpp 放到 experiments/pds_fpga/tools/。
- 把该工具依赖的旧版头文件与 src/howard.cpp 隔离到 experiments/pds_fpga/upstream/。
- 不做 git merge：两个仓库没有共同祖先；timing_graph 已从 4 参数 Graph 重写为 6 参数 DelayGraph，直接合并会破坏主线。

## 4. 核对结果
| 检查 | 结果 |
|---|---|
| BailuFrost 共同文件 | 2,465 个，逐字节相同 2,465，差异 0 |
| BailuFrost 文件缺失 | 0（整合时核对；随后删除了未跟踪的 build/、.vscode/、.DS_Store） |
| zqilin PDS 文件 | 31 个（PDS实际测量数据/，不含 tools/pds_howard.cpp），逐字节相同 31，差异 0 |
| zqilin pds_howard.cpp | blob 8d1fe9fd046f675a523c6e5f838f789ffd245ad0，与上游一致 |
| PDS CLI 测试 | **未在本机执行**：本机没有 CMake / C++17 编译器 / Boost；文件与上游逐字节一致，待具备 C++17 + Boost 环境验证 |

## 5. 相对上游的改动
只增不改：
- 新增 experiments/pds_fpga/（README、upstream/、tests/、CMakeLists.txt）
- 新增 INTEGRATION.md、docs/report/README.md、docs/upstream/README-BailuFrost.md
- 重写根 README.md
- 删除未跟踪的 build/、.vscode/、.DS_Store
未改动：src/、include/、tests/、examples/、sky130_pdk/、run_tiny_02/、benchmark/、CSTIC/、CMakeLists.txt。

## 6. 已知缺口
- zqilin 报告第 7 节的 phase_optimization 产物不在仓库。
- PDS 原始报告 / 布局布线数据库未完整入库。
- PDS_GRAPH_V1 的生成桥不在仓库。
- PDS 工具使用隔离的旧版头文件；两条线的 API 尚未统一。
- PDS 工具的编译与 CLI 测试未在整理人本机执行（缺 CMake / C++17 编译器 / Boost）；见第 4 节。

## 7. 如何更新
- 上游有新提交时，不要 git pull 或 git merge。
- 重新冻结一个新的上游 SHA，按同样方式导入，另开 commit，并更新本文件第 2 节。
- 已有 tag 不移动、不覆盖。
