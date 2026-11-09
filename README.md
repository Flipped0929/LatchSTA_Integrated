# Latch STA：C++ 时序工具 + FPGA/PDS 实验

本仓库整合两条 latch 时序验证路线。它不是两个仓库的 `git merge`
（两边没有共同 git 祖先），而是：

- **主线**：BailuFrost 的 C++ STA 工具与 SKY130 物理实现验证，整棵工作树原样保留。
- **旁路**：zqilin641-jpg 的 FPGA/PDS 实验，原样放在 `experiments/pds_fpga/`。

整合方法、核对结果和已知缺口见 [`INTEGRATION.md`](INTEGRATION.md)。

## 来源版本

| 轨道 | 仓库 | commit |
|---|---|---|
| 主线 | `BailuFrost/LatchSTA_Code` | `423e489377b6e32b9f3c3107800a195ed0ee3289` |
| PDS 实验 | `zqilin641-jpg/latch_STA_CODE` | `bffc73535b9012207edaad127c29c36cdd5847f2` |

## 目录

```text
.
├─ src/ include/ tests/            主线 C++ 工具（新 6 参数 / DelayGraph）
├─ examples/                       三锁存器、counter 全流程
├─ run_tiny_02/                    三锁存器真实运行归档
├─ sky130_pdk/                     Liberty/SPICE 提取与六参数 JSON
├─ test_result_pdk/ test_result_css/
├─ benchmark/ CSTIC/               共同底座
├─ experiments/pds_fpga/           PDS 实验线（上游快照 + 求解器 + 测试）
├─ docs/
│  ├─ upstream/                    上游原始 README
│  ├─ progress/                    进度记录
│  └─ report/                      报告入口
└─ INTEGRATION.md                  整合记录
```

## 快速开始

### 主线 C++ 工具

依赖：C++17、LEDA 7.x、GLPK、OpenBLAS、gfortran。
完整环境与 CLI 参数见 [`docs/upstream/README-BailuFrost.md`](docs/upstream/README-BailuFrost.md)。

```bash
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j
./build/main benchmark/s27.blif.out 1 100
```

### PDS 实验

见 [`experiments/pds_fpga/README.md`](experiments/pds_fpga/README.md)。
需要 Pango PDS + ModelSim + Windows/PowerShell。

### PDS 图求解器

```bash
cmake -S experiments/pds_fpga -B build_pds -DCMAKE_BUILD_TYPE=Release
cmake --build build_pds -j
python -I experiments/pds_fpga/tests/test_pds_graph_cli.py build_pds/pds_howard
```

## 文档

| 文件 | 用途 |
|---|---|
| `INTEGRATION.md` | 来源、合并方法、核对结果、缺口 |
| `experiments/pds_fpga/README.md` | PDS 实验入口 |
| `docs/upstream/README-BailuFrost.md` | 主线原始 README（完整 CLI） |
| `docs/report/README.md` | 报告位置与引用规则 |
| `docs/progress/2026-10-25.md` | BailuFrost 当日进度 |

## 结果与边界

- PDS 线：时间借用和相位优化可见；**没有 latch 比 FF 更快的证据**。
- SKY130 线：模型下界 1.584538 ns；最快已验证点 1.80 ns / 555.56 MHz。
- 两条线的工具、工艺、抽象层级不同，**数字不可直接比较**。
- 没有上板实测（E1）；最高证据等级是后布局 ngspice 功能仿真（E2）。

## 许可

`sky130_pdk/LICENSE.upstream` 随附。PDS 实验材料来自 zqilin641-jpg，
引用时请注明来源与 commit。
