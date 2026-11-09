# FPGA Latch-based Timing Analysis Tool

本项目是一款针对 FPGA 设计的时序分析与优化工具。主要功能是通过解析基于寄存器（Register-based）的时序报告，建立锁存器（Latch）时序模型。利用锁存器特有的时序借用（Time Borrowing）特性，并结合椭球法（Ellipsoid Method）优化算法，计算设计在引入锁存器后能够达到的最高运行频率。

---

## 一、 环境配置说明

### 1. 包管理 (Conda)
推荐使用 Conda 管理编译环境。

*   **安装 Conda 与依赖：**
    ```bash
    # 下载并安装 Miniconda
    wget "http://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh" -O miniconda.sh
    export CONDA_PREFIX=~/miniconda3
    bash miniconda.sh -b -p $CONDA_PREFIX

    # 安装必要的开发库
    conda install pkg-config
    conda install -c conda-forge \
        cmake ninja bison flex \
        cppcheck valgrind doxygen \
        xtensor-fftw xtensor-blas xtensor \
        openblas boost catch2 benchmark gfortran
    ```

### 2. 外部依赖库
*   **GLPK (GNU Linear Programming Kit)**: 
    *   需从 [官网](http://www.gnu.org/software/glpk/) 下载安装。
    *   编译时 CMake 会自动通过 `find_package` 或手动指定的路径链接 `-lglpk`。
*   **LEDA**: 
    *   需从 [官网](http://www.algorithmic-solutions.com/) 下载免费版。
    *   编译选项需包含：`-I$LEDAROOT/incl -L$LEDAROOT -lleda -lX11 -lm`。

---

## 二、 编译指南

请在项目根目录下执行以下命令进行构建：

```bash
# 1. 创建并进入构建目录
mkdir -p build && cd build

# 2. 运行 CMake 配置
cmake ..

# 3. 编译（使用 8 线程并行）
make -j8
```

## 三、 使用说明

程序编译完成后生成 `main` 可执行文件，运行格式如下：

```bash
./main <input_file> <iterations> <ellipsoid_radius> [latch_timing.json] [--read-only] [--no-skew] [--duty-cycle fraction] [--export-sdc new_file.sdc]
```

参数说明：
input_file: 输入的网表或时序报告文件路径（如 ../benchmark/s27.blif.out）。
iterations: 算法优化迭代次数（如 1 或 100）。
ellipsoid_radius: 椭球法搜索的初始半径（如 100）。
latch_timing.json: 可选的逐实例六参数文件，按实例名称匹配，单位 ns。
省略时保留统一常量；指定时用于 MCR 的 Howard、YTO、LP 和可行性检查。
ELL 使用独立旧模型；加载 v3 真实 IO 时跳过 ELL。
--duty-cycle: MCR 高电平占空比，范围 (0, 0.5]；v1/v2 默认 0.5，v3 默认取自 SDC。
每次运行固定一个占空比，透明窗口为 [s_k+(1-duty)*T, s_k+T]。
JSON 加载真实 latch 的六项参数、v2 起的脉宽检查及 v3 的 IO 约束；端口与零参考点的六参数为零。
此选项同时用于 Howard、YTO、LP 和原式验证；ELL 不使用该占空比。

`--no-skew` 暂停时钟偏斜优化，在 MCR 约束图、独立 LP 和原式验证中固定所有
`s_k=0`；保留固定占空比、setup/hold、脉宽及已加载的 IO 约束。
程序输出该模型的最小周期和最高频率 `1000/T(ns)` MHz，不打印偏斜调度；
跳过不支持零偏斜约束的独立 ELL 模型。省略此开关仍执行原有偏斜优化。
可与 `--export-sdc` 合用，导出的 latch latency 为零并标注零偏斜模式。

```bash
./main <supported_input.out> 1 100 <latch_timing.json> --no-skew
```

counter 通过专门的 schema 4 模型支持双极性反馈、独立 IO 和零偏斜求解；
必须保留 TimingModel 标记及配套 JSON，不可按统一正极性 v3 无环输入处理。

counter 的 schema 4 时序交换文件现已支持读取：保留正负极性、窗口、反馈边及
独立 IO 预算。先调用 `readDelayGraph` 读取带 `TimingModel` 标记的 `.blif.out`，
再调用 `readLatchTiming` 加载配套 JSON。`--read-only` 加载后打印图规模并退出，
可用于检查 counter 输入；此模式不求频率，也不导出 SDC。求解时使用 `--no-skew`，
保持 50% 占空比，并通过逐边保守 hold 检查。当前数据得到模型最小周期 1.584538 ns、
最高频率 631.098780843 MHz。`--export-sdc` 支持此模式，恢复 GATE/GATE_N 及独立 IO，
所有 latency 为零。也提供仅依赖 Boost 头文件、GLPK 的 `counter_solver` 入口。
构建、导出、模型定义、回归及 OpenSTA 候选复核命令见 `examples/counter/README.md`。

零偏斜回归（人工参数，非 counter 表征数据）：

```bash
g++ -std=c++17 -Iinclude tests/test_mcr_no_skew.cpp src/timing_graph.cpp \
  src/howard.cpp src/LP.cpp -lglpk -o test_mcr_no_skew
./test_mcr_no_skew
```

逐实例 JSON v2 还包含 `clock_checks_ns.min_pulse_width_high/low`，单位 ns。
数值表示库要求，`null` 表示已检查该库弧但没有对应检查；v2 必须显式提供两项。
MCR 将周期下界设为所有实例的 `max(high/duty, low/(1-duty))`，图、LP 和原式验证一致。
v1 和未提供 JSON 的旧输入仍可运行，但没有脉宽约束；程序打印实例覆盖数量和周期下界。
改变工艺角或时钟 transition 后应重新提取；此模型仍假设理想时钟、固定占空比。

JSON v3 还加载 `io_constraints`：单输入/单输出、同一理想时钟上升沿参考、
显式 min/max IO delay 和 setup/hold uncertainty。输入由本周期上升沿发射，
输出 setup/hold 分别使用下一/本周期上升沿；无反馈数据路径按同次事务传播，不再逐边减 T。
加载器将压缩输入中合并的 IO 拆成真实输入端口、真实输出端口和独立零参考点。
v3 默认占空比取自 SDC 波形；`--duty-cycle` 可覆盖，保持下降沿为 T。
反馈、其他周期映射或多个端口不在此首版范围内，会拒绝输入。
Latch 发射路径的 hold 使用开启响应下界作保守检查，不把可行势变量当作物理最早到达时间。
v1/v2 继续保留旧合并 IO 和路径周期关系；ELL 在 v3 模式下跳过。

`--export-sdc new_file.sdc` 导出同次 Howard 求解的周期和全部 latch 偏移。
需要重新生成的 v3 JSON，包含 `sta_conditions`（时钟端口、clock/input transition、output load）。
Howard 和 LP 均须为 Optimal、通过图及原式检查，并在周期容差内一致；不导出回退求解器的结果。
输出必须是尚不存在的 `.sdc` 文件，父目录须已存在。导出保留 IO、工况和 uncertainty，
以各 latch GATE 引脚的理想 network latency 表达偏移；注释记录周期、占空比和透明窗口。
仅支持扁平简单实例名及 D/GATE/Q 接口，尚不表示实际时钟树实现或 OpenSTA 验证通过。
新增源文件后需重新运行 CMake 配置，再构建。案例完整命令见 `examples/tiny_3_latch_circuit/README.md`。

运行示例：
```bash
./main ../benchmark/s27.blif.out 1 100
```


## 四、 目录结构说明
src/: 项目核心源代码目录 (.cpp)。
include/: 项目头文件目录 (.h)。
benchmark/: 存放标准测试数据集。
benchmark_rslt/: 存放参考测试结果数据。
CSTIC/:专门用于对基于寄存器的时序报告进行解析，重点分析在锁存器依赖环境下FPGA 设计能够达到的时序提升空间。
cmake/: 包含 CMake 构建系统的相关配置文件。

## 2026-10-25 进展与案例

- [当日推进记录与验证边界](docs/progress/2026-10-25.md)。
- [三锁存器全流程、完整引脚图与绘图](examples/tiny_3_latch_circuit/README.md)，真实运行归档见 [run_tiny_02](run_tiny_02/)。
- [同步复位 counter 案例](examples/counter/README.md)：零偏斜求解、OpenROAD 布局布线和 1.80 ns 后仿真验证。
- [回归测试说明](tests/README.md)。
