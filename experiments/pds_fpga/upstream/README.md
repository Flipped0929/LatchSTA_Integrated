# upstream：PDS 适配器的旧版依赖

这些文件原样复制自 `zqilin641-jpg/latch_STA_CODE` @
`bffc73535b9012207edaad127c29c36cdd5847f2`：

| 文件 | 上游路径 | blob SHA-1 |
|---|---|---|
| `howard.hpp` | `include/howard.hpp` | `6b51d9048de15eb04cbbc625426fdaf7ac5a6e66` |
| `timing_graph.hpp` | `include/timing_graph.hpp` | `55adb4c26592c53b5a494df15ff554050db25419` |
| `solver_status.hpp` | `include/solver_status.hpp` | `c0dfd3c5585f3fcc252a2bddf2dfbd16aa799d5d` |
| `strOperation.hpp` | `include/strOperation.hpp` | `c03bf10550bcd26eafe6589ad4f8c0fd21f60234` |
| `howard.cpp` | `src/howard.cpp` | `a90c7eca006ea99a0536f39150699478e4470b74` |

## 为什么单独放一份

主线 `include/timing_graph.hpp`、`include/howard.hpp` 已被改造成
`DelayGraph` / `McrStatus` 体系：

- `NodeProperties` 只有 `nodeIndex` 一个字段；
- `ArcProperties` 只有 `mode / weight / delay` 三个字段；
- 没有 `HowardStatus`、`statusName`、`HowardResult`。

而 `tools/pds_howard.cpp` 使用 zqilin 旧 API：

- `NodeProperties{nodeIndex, latchName, timingVariable}`；
- `ArcProperties{mode, weight, delay, constraintType}`；
- `HowardStatus::Converged`、`statusName()`、`result.cycleResidual`。

直接编译会报“initializer 过多 / 未定义标识符”。把旧头文件隔离在 `upstream/`，
既能让 PDS 工具原样可复现，又不污染主线。

## 注意

- 这些头文件**只**供 `pds_howard` 使用，不要加到主线的 include 路径。
- 如果以后要统一两条线的 API，应改写 `pds_howard.cpp` 并同步更新
  `tests/test_pds_graph_cli.py`，而不是让主线回退到旧 API。
