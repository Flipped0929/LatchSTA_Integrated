# Counter MCR Howard + independent LP; fixed scalar timing envelopes; ideal zero skew.
# model=counter_mixed_polarity_feedback_v1; min-delay hold certified by opening-response bounds.
# Reported pulse checks only; independent OpenSTA validation is required.
# period_ns=1.65 frequency_MHz=606.0606060606061
if {[llength [get_ports {clk}]] != 1} {error {Missing clock port}}
create_clock -name {clk} -period 1.63 -waveform {0.815 1.63} [get_ports {clk}]
set_clock_latency -source 0.0 [get_clocks {clk}]
set_clock_latency 0.0 [get_clocks {clk}]
set_clock_transition 0.059999999999999998 [get_clocks {clk}]
set_clock_uncertainty -setup 0.050000000000000003 [get_clocks {clk}]
set_clock_uncertainty -hold 0.050000000000000003 [get_clocks {clk}]
if {[llength [get_ports {en}]] != 1} {error {Missing input port}}
set_input_delay -clock {clk} -min 0.20000000000000001 [get_ports {en}]
set_input_delay -clock {clk} -max 1 [get_ports {en}]
set_input_transition 0.059999999999999998 [get_ports {en}]
if {[llength [get_ports {rst_n}]] != 1} {error {Missing input port}}
set_input_delay -clock {clk} -min 0.20000000000000001 [get_ports {rst_n}]
set_input_delay -clock {clk} -max 1 [get_ports {rst_n}]
set_input_transition 0.059999999999999998 [get_ports {rst_n}]
if {[llength [get_ports {count[0]}]] != 1} {error {Missing output port}}
set_output_delay -clock {clk} -min -0.050000000000000003 [get_ports {count[0]}]
set_output_delay -clock {clk} -max 1 [get_ports {count[0]}]
set_load 0.01 [get_ports {count[0]}]
if {[llength [get_ports {count[1]}]] != 1} {error {Missing output port}}
set_output_delay -clock {clk} -min -0.050000000000000003 [get_ports {count[1]}]
set_output_delay -clock {clk} -max 1 [get_ports {count[1]}]
set_load 0.01 [get_ports {count[1]}]
if {[llength [get_ports {count[2]}]] != 1} {error {Missing output port}}
set_output_delay -clock {clk} -min -0.050000000000000003 [get_ports {count[2]}]
set_output_delay -clock {clk} -max 1 [get_ports {count[2]}]
set_load 0.01 [get_ports {count[2]}]
if {[llength [get_ports {count[3]}]] != 1} {error {Missing output port}}
set_output_delay -clock {clk} -min -0.050000000000000003 [get_ports {count[3]}]
set_output_delay -clock {clk} -max 1 [get_ports {count[3]}]
set_load 0.01 [get_ports {count[3]}]
if {[llength [get_pins {_17_/GATE_N}]] != 1} {error {Missing latch clock pin}}
set_clock_latency -clock [get_clocks {clk}] 0.0 [get_pins {_17_/GATE_N}]
if {[llength [get_pins {_21_/GATE}]] != 1} {error {Missing latch clock pin}}
set_clock_latency -clock [get_clocks {clk}] 0.0 [get_pins {_21_/GATE}]
if {[llength [get_pins {_18_/GATE_N}]] != 1} {error {Missing latch clock pin}}
set_clock_latency -clock [get_clocks {clk}] 0.0 [get_pins {_18_/GATE_N}]
if {[llength [get_pins {_22_/GATE}]] != 1} {error {Missing latch clock pin}}
set_clock_latency -clock [get_clocks {clk}] 0.0 [get_pins {_22_/GATE}]
if {[llength [get_pins {_19_/GATE_N}]] != 1} {error {Missing latch clock pin}}
set_clock_latency -clock [get_clocks {clk}] 0.0 [get_pins {_19_/GATE_N}]
if {[llength [get_pins {_23_/GATE}]] != 1} {error {Missing latch clock pin}}
set_clock_latency -clock [get_clocks {clk}] 0.0 [get_pins {_23_/GATE}]
if {[llength [get_pins {_20_/GATE_N}]] != 1} {error {Missing latch clock pin}}
set_clock_latency -clock [get_clocks {clk}] 0.0 [get_pins {_20_/GATE_N}]
if {[llength [get_pins {_24_/GATE}]] != 1} {error {Missing latch clock pin}}
set_clock_latency -clock [get_clocks {clk}] 0.0 [get_pins {_24_/GATE}]
if {[llength [all_registers -level_sensitive -cells]] != 8} {error {Candidate latch count mismatch}}
