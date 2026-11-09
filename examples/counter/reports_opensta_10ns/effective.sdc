###############################################################################
# Created by write_sdc
# Thu Nov  5 16:04:52 2026
###############################################################################
current_design counter
###############################################################################
# Timing Constraints
###############################################################################
create_clock -name clk -period 10.0000 -waveform {5.0000 10.0000} [get_ports {clk}]
set_clock_transition 0.0600 [get_clocks {clk}]
set_clock_uncertainty 0.0500 clk
set_clock_latency 0.0000 [get_clocks {clk}]
set_clock_latency -source 0.0000 [get_clocks {clk}]
set_input_delay 0.2000 -clock [get_clocks {clk}] -min -add_delay [get_ports {en}]
set_input_delay 1.0000 -clock [get_clocks {clk}] -max -add_delay [get_ports {en}]
set_input_delay 0.2000 -clock [get_clocks {clk}] -min -add_delay [get_ports {rst_n}]
set_input_delay 1.0000 -clock [get_clocks {clk}] -max -add_delay [get_ports {rst_n}]
set_output_delay -0.0500 -clock [get_clocks {clk}] -min -add_delay [get_ports {count[0]}]
set_output_delay 1.0000 -clock [get_clocks {clk}] -max -add_delay [get_ports {count[0]}]
set_output_delay -0.0500 -clock [get_clocks {clk}] -min -add_delay [get_ports {count[1]}]
set_output_delay 1.0000 -clock [get_clocks {clk}] -max -add_delay [get_ports {count[1]}]
set_output_delay -0.0500 -clock [get_clocks {clk}] -min -add_delay [get_ports {count[2]}]
set_output_delay 1.0000 -clock [get_clocks {clk}] -max -add_delay [get_ports {count[2]}]
set_output_delay -0.0500 -clock [get_clocks {clk}] -min -add_delay [get_ports {count[3]}]
set_output_delay 1.0000 -clock [get_clocks {clk}] -max -add_delay [get_ports {count[3]}]
###############################################################################
# Environment
###############################################################################
set_load -pin_load 0.0100 [get_ports {count[3]}]
set_load -pin_load 0.0100 [get_ports {count[2]}]
set_load -pin_load 0.0100 [get_ports {count[1]}]
set_load -pin_load 0.0100 [get_ports {count[0]}]
set_input_transition 0.0600 [get_ports {rst_n}]
set_input_transition 0.0600 [get_ports {en}]
###############################################################################
# Design Rules
###############################################################################
