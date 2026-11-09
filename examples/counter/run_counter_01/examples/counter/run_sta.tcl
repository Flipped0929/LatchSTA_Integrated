# Fixed SKY130 HD TT, ideal clocks, no SPEF. Both latch polarities and reset are retained.
set case_dir [file dirname [file normalize [info script]]]
set report_dir [file join $case_dir reports]
if {[info exists ::env(COUNTER_REPORT_DIR)]} {
    set report_dir [file normalize $::env(COUNTER_REPORT_DIR)]
    if {[file exists $report_dir]} {error "COUNTER_REPORT_DIR must be a new directory"}
}
if {[file exists [file join $report_dir units.rpt]] || [file exists [file join $report_dir pin_graph]]} {
    error "Existing STA reports are protected; set COUNTER_REPORT_DIR to a new directory"
}
set graph_exporter {}
foreach path [list [file join $case_dir export_pin_graph.tcl] \
                  [file join $case_dir .. tiny_3_latch_circuit export_pin_graph.tcl] \
                  [file join $case_dir .. tiny_sky130 export_pin_graph.tcl]] {
    if {[file isfile $path]} {set graph_exporter $path; break}
}
cd $case_dir
set liberty ../../sky130_pdk/sky130_fd_sc_hd__tt_025C_1v80.lib
foreach path [list $liberty counter_mapped.v counter.sdc $graph_exporter] {
    if {$path eq "" || ![file isfile $path]} {error "Missing counter STA input/exporter: $path"}
}
source $graph_exporter
read_liberty $liberty
read_verilog counter_mapped.v
if {![link_design counter]} {error "Cannot link counter"}
foreach cell {sky130_fd_sc_hd__dlrtn_1 sky130_fd_sc_hd__dlrtp_1} {
    if {[llength [get_lib_cells */$cell]] != 1} {error "Missing or ambiguous library cell: $cell"}
}
foreach port {clk rst_n en} {
    if {[llength [get_ports $port]] != 1} {error "Missing or ambiguous port: $port"}
}
if {[llength [get_ports {count*}]] != 4} {error "Expected four count output bits"}
set latches [all_registers -level_sensitive -cells]
if {[llength $latches] != 8 || [llength [all_registers -edge_triggered -cells]] != 0} {
    error "Expected eight latches and no edge-triggered registers"
}
set latch_rows {}; set negative 0; set positive 0
foreach instance $latches {
    set name [get_full_name $instance]
    if {![regexp {^[A-Za-z_][A-Za-z0-9_$]*$} $name]} {
        error "Expected a flat simple latch instance name: $name"
    }
    set cell [get_property $instance ref_name]
    switch -- $cell {
        sky130_fd_sc_hd__dlrtn_1 {set gate GATE_N; incr negative}
        sky130_fd_sc_hd__dlrtp_1 {set gate GATE; incr positive}
        default {error "Unsupported counter latch cell: $cell"}
    }
    foreach port [list D Q $gate RESET_B] {
        if {[llength [get_pins $name/$port]] != 1} {error "Missing or ambiguous pin: $name/$port"}
    }
    lappend latch_rows [list $name $cell $name/$gate $name/D $name/Q $name/RESET_B]
}
if {$negative != 4 || $positive != 4} {error "Expected four negative and four positive resettable latches"}
read_sdc counter.sdc
file mkdir $report_dir
file copy counter.sdc [file join $report_dir constraints.sdc]
pin_graph::table $report_dir latches {instance cell gate_pin data_pin output_pin reset_pin} $latch_rows
log_begin $report_dir/units.rpt
report_units
log_end
log_begin $report_dir/clocks.rpt
report_clock_properties [get_clocks clk]
log_end
check_setup -verbose > $report_dir/check_setup.rpt
foreach analysis {max min} kind {setup hold} {
    report_checks -path_delay $analysis -format full_clock_expanded \
        -fields {slew capacitance input_pin net} -group_path_count 1000 \
        -endpoint_path_count 1000 -digits 6 > $report_dir/$kind.rpt
}
foreach kind {recovery removal min_pulse_width} name {recovery removal pulse_width} {
    report_check_types -$kind -format end -max_count 1000 -digits 6 > $report_dir/$name.rpt
}
set checks {-max_delay -min_delay -recovery -removal -min_pulse_width -min_period -max_slew -max_capacitance -max_fanout}
report_check_types {*}$checks -format end -max_count 1000 -digits 6 > $report_dir/checks.rpt
report_check_types {*}$checks -violators -format end -max_count 1000 -digits 6 > $report_dir/violations.rpt
foreach row $latch_rows {
    lassign $row name cell gate data output reset
    report_instance $name > $report_dir/${name}_instance.rpt
    log_begin $report_dir/${name}_arrival.rpt
    report_arrival -digits 6 [get_pins $data]
    log_end
    report_net -digits 6 [get_full_name [get_nets -of_objects [get_pins $output]]] \
        > $report_dir/${name}_load.rpt
    foreach from [list $data $gate $reset] label {dq cq reset_q} {
        foreach analysis {min max} {
            log_begin $report_dir/${name}_${label}_${analysis}.rpt
            report_dcalc -from [get_pins $from] -to [get_pins $output] -$analysis -digits 6
            log_end
        }
    }
}
pin_graph::export $report_dir
puts "Counter reports written to $report_dir; inspect setup/hold, recovery/removal, pulse widths and clock phases"
puts "Optimization unsupported: current MCR v3 does not model this mixed-polarity resettable feedback circuit with multiple IOs"
