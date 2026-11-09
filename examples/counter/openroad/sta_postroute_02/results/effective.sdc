###############################################################################
# Created by write_sdc
###############################################################################
current_design counter
###############################################################################
# Timing Constraints
###############################################################################
create_clock -name clk -period 1.649999976158 -waveform {0.824999928474 1.649999856949} [get_ports {clk}]
set_clock_transition 0.059999998659 [get_clocks {clk}]
set_clock_uncertainty 0.049999997020 clk
set_propagated_clock [get_clocks {clk}]
set_clock_latency -source 0.000000000000 [get_clocks {clk}]
set_input_delay 0.199999988079 -clock [get_clocks {clk}] -min -add_delay [get_ports {en}]
set_input_delay 1.000000000000 -clock [get_clocks {clk}] -max -add_delay [get_ports {en}]
set_input_delay 0.199999988079 -clock [get_clocks {clk}] -min -add_delay [get_ports {rst_n}]
set_input_delay 1.000000000000 -clock [get_clocks {clk}] -max -add_delay [get_ports {rst_n}]
set_output_delay -0.049999997020 -clock [get_clocks {clk}] -min -add_delay [get_ports {count[0]}]
set_output_delay 1.000000000000 -clock [get_clocks {clk}] -max -add_delay [get_ports {count[0]}]
set_output_delay -0.049999997020 -clock [get_clocks {clk}] -min -add_delay [get_ports {count[1]}]
set_output_delay 1.000000000000 -clock [get_clocks {clk}] -max -add_delay [get_ports {count[1]}]
set_output_delay -0.049999997020 -clock [get_clocks {clk}] -min -add_delay [get_ports {count[2]}]
set_output_delay 1.000000000000 -clock [get_clocks {clk}] -max -add_delay [get_ports {count[2]}]
set_output_delay -0.049999997020 -clock [get_clocks {clk}] -min -add_delay [get_ports {count[3]}]
set_output_delay 1.000000000000 -clock [get_clocks {clk}] -max -add_delay [get_ports {count[3]}]
###############################################################################
# Environment
###############################################################################
set_load -pin_load 0.009999999776 [get_ports {count[3]}]
set_load -pin_load 0.009999999776 [get_ports {count[2]}]
set_load -pin_load 0.009999999776 [get_ports {count[1]}]
set_load -pin_load 0.009999999776 [get_ports {count[0]}]
set_input_transition 0.059999998659 [get_ports {clk}]
set_input_transition 0.059999998659 [get_ports {en}]
set_input_transition 0.059999998659 [get_ports {rst_n}]
###############################################################################
# Design Rules
###############################################################################
