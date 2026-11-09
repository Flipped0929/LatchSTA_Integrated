# 同步复位主从 latch 计数器，单位随 SKY130 Liberty：ns、pF。
# 以下数值均为实验假设，不是板级测量值或已求解的最小周期。
# 使用前先读取 Liberty、counter_mapped.v，并 link_design counter。

# 默认 10 ns、50% 占空比：master 在 0--5 ns 透明，slave 在 5--10 ns 透明。
# 与前仿真的低电平启动相位一致；周期覆盖仅用于 STA，不修改 SPICE 激励。
set counter_period_ns 10.0
if {[info exists ::env(COUNTER_PERIOD_NS)]} {set counter_period_ns $::env(COUNTER_PERIOD_NS)}
if {![string is double -strict $counter_period_ns] ||
    [catch {expr {$counter_period_ns > 0.0 && $counter_period_ns < Inf}} valid_period] || !$valid_period} {
    error "COUNTER_PERIOD_NS must be a finite positive number in ns"
}
create_clock -name clk -period $counter_period_ns \
    -waveform [list [expr {0.5 * $counter_period_ns}] $counter_period_ns] [get_ports clk]
# 单一理想时钟，无逐 latch 偏斜或物理时钟树延迟。
set_clock_latency -source 0.0 [get_clocks clk]
set_clock_latency 0.0 [get_clocks clk]
# 本库 slew 阈值为 20%--80%；线性 100 ps 全摆幅边沿对应 60 ps。
set_clock_transition 0.06 [get_clocks clk]
set_clock_uncertainty -setup 0.05 [get_clocks clk]
set_clock_uncertainty -hold 0.05 [get_clocks clk]

# 外部使能输入相对 clk 上升沿的最早/最晚到达时间。
set_input_delay -clock clk -min 0.2 [get_ports en]
set_input_delay -clock clk -max 1.0 [get_ports en]
set_input_transition 0.06 [get_ports en]

# rst_n 是经组合逻辑进入 master/D 的同步复位，优先于 en。
# 与 en 一样检查其 setup/hold；不设置 false path 或固定为常量。
# 以下是接口预算，不是瞬态激励的 PWL 事件时刻。
set_input_delay -clock clk -min 0.2 [get_ports rst_n]
set_input_delay -clock clk -max 1.0 [get_ports rst_n]
set_input_transition 0.06 [get_ports rst_n]

# 4 位计数输出的外部接口预算及每位负载。
# 输出最小延迟的负号有意保留；这些预算不随周期自动缩放。
set_output_delay -clock clk -max 1.0 [get_ports {count*}]
set_output_delay -clock clk -min -0.05 [get_ports {count*}]
# 对应 counter_tb.sch 每位 10 fF 的外部负载。
set_load 0.010 [get_ports {count*}]

# 首轮采用理想时钟；互连 RC 由后续匹配的 SPEF 提供，不在本文件中虚构。
