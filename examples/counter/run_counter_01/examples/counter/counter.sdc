# 主从 latch 计数器的示例约束，单位随 SKY130 Liberty：ns、pF。
# 以下数值均为实验假设，不是板级测量值或已求解的最小周期。
# 使用前先读取 Liberty、counter_mapped.v，并 link_design counter。

# 10 ns 周期、50% 占空比：slave 在 0--5 ns 透明，master 在 5--10 ns 透明。
# 改变周期或占空比时，应同时更新波形的上升、下降沿。
create_clock -name clk -period 10.0 -waveform {0.0 5.0} [get_ports clk]
set_clock_transition 0.05 [get_clocks clk]
set_clock_uncertainty -setup 0.05 [get_clocks clk]
set_clock_uncertainty -hold 0.05 [get_clocks clk]

# 外部使能输入相对 clk 上升沿的最早/最晚到达时间。
set_input_delay -clock clk -min 0.2 [get_ports en]
set_input_delay -clock clk -max 1.0 [get_ports en]
set_input_transition 0.05 [get_ports en]

# 本例假设复位释放有与 clk 相关的外部时间预算。
# 不设置 false path 或固定 rst_n=1，以保留库中可用的复位相关检查。
# 真正异步的复位源及释放同步策略需另外验证，此处不证明复位安全。
set_input_delay -clock clk -min 0.2 [get_ports rst_n]
set_input_delay -clock clk -max 1.0 [get_ports rst_n]
set_input_transition 0.05 [get_ports rst_n]

# 4 位计数输出的外部接口预算及每位负载。
# 输出最小延迟的负号有意保留；这些预算不随周期自动缩放。
set_output_delay -clock clk -max 1.0 [get_ports {count*}]
set_output_delay -clock clk -min -0.05 [get_ports {count*}]
set_load 0.005 [get_ports {count*}]

# 首轮采用理想时钟；互连 RC 由后续匹配的 SPEF 提供，不在本文件中虚构。
