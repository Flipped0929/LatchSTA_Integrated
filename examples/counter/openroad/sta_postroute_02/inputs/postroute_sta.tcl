# Post-route STA for the completed counter. No implementation/constraint repair.
set run_dir [file normalize $::env(COUNTER_POSTSTA_RUN)]
set liberty [file normalize $::env(COUNTER_POSTSTA_LIBERTY)]
set report_dir $run_dir/reports
if {[file exists $report_dir/metrics.tsv]} {error "Refusing to overwrite completed STA results"}
file mkdir $report_dir
set sta_crpr_enabled 1
set sta_crpr_mode same_transition
read_liberty $liberty
read_verilog $run_dir/inputs/counter_sta.v
if {![link_design counter]} {error "Cannot link routed counter netlist"}
if {[llength [get_cells *]] != 22} {error "Expected 18 original cells plus 4 CTS cells"}
set latches [all_registers -level_sensitive -cells]
if {[llength $latches] != 8 || [llength [all_registers -edge_triggered -cells]] != 0} {
    error "Expected 8 latches and no flip-flops"
}
if {[llength [get_ports *]] != 7} {error "Expected 7 functional ports"}
read_sdc $run_dir/inputs/counter_routed.sdc
# set_clock_transition in the original ideal-clock constraints does not provide
# source port slew after propagation. Preserve the 60 ps (20%-80%) source edge.
set_input_transition 0.06 [get_ports clk]
set_propagated_clock [get_clocks clk]
if {[llength [get_clocks *]] != 1 || ![get_property [get_clocks clk] is_propagated]} {
    error "Expected a single propagated clock"
}
if {abs([get_property [get_clocks clk] period]-1.65) > 1e-6} {error "Expected 1.65 ns clock"}
# The SPEF contains wire capacitance only. Add library pin capacitance normally;
# retain the SDC's external 10 fF/bit load and use unit coupling reduction.
read_spef -keep_capacitive_coupling -coupling_reduction_factor 1.0 $run_dir/inputs/counter.nominal.spef
report_parasitic_annotation -report_unannotated > $report_dir/parasitic_annotation.rpt
write_sdc -digits 12 -no_timestamp $run_dir/results/effective.sdc
log_begin $report_dir/units.rpt
report_units
log_end
log_begin $report_dir/clocks.rpt
report_clock_properties [get_clocks clk]
puts "propagated=[get_property [get_clocks clk] is_propagated]"
puts "source_rise_transition_ns=[get_property [get_ports clk] slew_max_rise]"
puts "source_fall_transition_ns=[get_property [get_ports clk] slew_max_fall]"
puts "CRPR_enabled=$sta_crpr_enabled; CRPR_mode=$sta_crpr_mode"
log_end
set constraints_ok [check_setup -verbose > $report_dir/check_setup.rpt]
foreach analysis {max min} label {setup hold} {
    report_checks -path_delay $analysis -format full_clock_expanded \
        -fields {slew capacitance input_pin net fanout} -group_path_count 1000 \
        -endpoint_path_count 1 -sort_by_slack -digits 9 > $report_dir/$label.rpt
    report_checks -path_delay $analysis -format full_clock_expanded \
        -fields {slew capacitance input_pin net fanout} -group_path_count 1 \
        -endpoint_path_count 1 -sort_by_slack -digits 9 > $report_dir/${label}_worst.rpt
    report_checks -path_delay $analysis -slack_max 0 -format full_clock_expanded \
        -fields {slew capacitance input_pin net} -group_path_count 1000 \
        -endpoint_path_count 1 -sort_by_slack -digits 9 > $report_dir/${label}_violations.rpt
    foreach port {en rst_n} {
        report_checks -from [get_ports $port] -path_delay $analysis -format full_clock_expanded \
            -fields {slew capacitance input_pin net} -group_path_count 1000 \
            -endpoint_path_count 1 -digits 9 > $report_dir/${port}_${label}.rpt
    }
}
set checks {-max_delay -min_delay -min_pulse_width -min_period -max_slew -max_capacitance -max_fanout}
report_check_types {*}$checks -format end -max_count 1000 -digits 9 > $report_dir/checks.rpt
report_check_types {*}$checks -violators -format end -max_count 1000 -digits 9 > $report_dir/violations.rpt
foreach option {-min_pulse_width -min_period -max_slew -max_capacitance -max_fanout} label {pulse_width min_period max_slew max_capacitance max_fanout} {
    report_check_types $option -format end -max_count 1000 -digits 9 > $report_dir/$label.rpt
}
log_begin $report_dir/clock_skew.rpt
report_clock_skew -setup -digits 9
report_clock_skew -hold -digits 9
log_end
set clock_fd [open $report_dir/clock_pins.tsv w]
puts $clock_fd "instance\tcell\tclock_pin\tclock_net\trise_slew_ns\tfall_slew_ns"
set endpoints {}
log_begin $report_dir/clock_arrivals.rpt
foreach latch $latches {
    set name [get_full_name $latch]
    set cell [get_property $latch ref_name]
    switch $cell {
        sky130_fd_sc_hd__dlxtn_1 {set gate GATE_N}
        sky130_fd_sc_hd__dlxtp_1 {set gate GATE}
        default {error "Unexpected latch cell: $cell"}
    }
    set pin [get_pins $name/$gate]
    if {[llength [get_property $pin clocks]] != 1} {error "Missing propagated clock at $name/$gate"}
    set net [get_full_name [get_nets -of_objects $pin]]
    puts $clock_fd "$name\t$cell\t$name/$gate\t$net\t[get_property $pin slew_max_rise]\t[get_property $pin slew_max_fall]"
    puts "\n$name/$gate"
    report_arrival -digits 9 $pin
    lappend endpoints [list $name/D [get_pins $name/D] latch]
}
log_end
close $clock_fd
foreach bit {0 1 2 3} {
    set name [format {count[%d]} $bit]
    lappend endpoints [list $name [get_ports $name] output]
}
set ep_fd [open $report_dir/endpoint_slacks.tsv w]
puts $ep_fd "endpoint\tkind\tanalysis\tslack_ns\tstartpoint"
foreach endpoint $endpoints {
    lassign $endpoint name object kind
    foreach analysis {max min} label {setup hold} {
        set paths [find_timing_paths -to $object -path_delay $analysis -group_path_count 1 -endpoint_path_count 1 -sort_by_slack]
        if {[llength $paths] != 1} {error "Missing $label timing path at $name"}
        set path [lindex $paths 0]
        puts $ep_fd "$name\t$kind\t$label\t[get_property $path slack]\t[get_full_name [get_property $path startpoint]]"
    }
}
close $ep_fd
log_begin $report_dir/net_loads.rpt
foreach net [get_nets *] {
    report_net -digits 9 [get_full_name $net]
}
log_end
log_begin $report_dir/summary.rpt
report_worst_slack -max -digits 9
report_worst_slack -min -digits 9
report_tns -max -digits 9
report_tns -min -digits 9
log_end
set fd [open $report_dir/metrics.tsv w]
puts $fd "metric\tvalue"
puts $fd "clock_period_ns\t[get_property [get_clocks clk] period]"
puts $fd "setup_worst_slack_ns\t[sta::worst_slack -max]"
puts $fd "hold_worst_slack_ns\t[sta::worst_slack -min]"
puts $fd "setup_tns_ns\t[sta::total_negative_slack -max]"
puts $fd "hold_tns_ns\t[sta::total_negative_slack -min]"
puts $fd "constraints_ok\t$constraints_ok"
puts $fd "clock_propagated\t[get_property [get_clocks clk] is_propagated]"
puts $fd "clock_source_rise_slew_ns\t[get_property [get_ports clk] slew_max_rise]"
puts $fd "clock_source_fall_slew_ns\t[get_property [get_ports clk] slew_max_fall]"
puts $fd "crpr_enabled\t$sta_crpr_enabled"
puts $fd "crpr_mode\t$sta_crpr_mode"
puts $fd "cells\t[llength [get_cells *]]"
puts $fd "latches\t[llength $latches]"
puts $fd "functional_ports\t[llength [get_ports *]]"
close $fd
if {!$constraints_ok} {error "Constraint sanity checks failed; see check_setup.rpt"}
puts "POST_ROUTE_STA_COMPLETE: $run_dir"
puts "Timing violations, if present, are reported without modifying the design or constraints."
