# Fixed TT, ideal clock, no SPEF: cell loads include connected input capacitance.
set case_dir [file dirname [file normalize [info script]]]
set sdc_path [file join $case_dir tiny.sdc]
set report_dir [file join $case_dir reports]
if {[info exists ::env(MCR_SDC)] || [info exists ::env(MCR_REPORT_DIR)]} {
    if {![info exists ::env(MCR_SDC)] || ![info exists ::env(MCR_REPORT_DIR)] ||
        $::env(MCR_SDC) eq "" || $::env(MCR_REPORT_DIR) eq ""} {
        error "Candidate validation requires MCR_SDC and MCR_REPORT_DIR"
    }
    set sdc_path [file normalize $::env(MCR_SDC)]
    set report_dir [file normalize $::env(MCR_REPORT_DIR)]
    if {![file isfile $sdc_path] || $sdc_path eq [file join $case_dir tiny.sdc] || [file exists $report_dir]} {
        error "Use an existing candidate SDC and a new report directory; baseline and previous reports are protected"
    }
}
if {[file exists [file join $report_dir pin_graph]]} {
    error "Use a new report directory; existing pin graph and reports are protected"
}
cd [file dirname [file normalize [info script]]]
set liberty ../../sky130_pdk/sky130_fd_sc_hd__tt_025C_1v80.lib
set graph_exporter [file join $case_dir export_pin_graph.tcl]
if {![file isfile $liberty] || ![file isfile tiny_mapped.v] || ![file isfile $graph_exporter]} {
    error "Missing Liberty, tiny_mapped.v or export_pin_graph.tcl; copy the exporter and run Yosys export.ys first"
}

read_liberty $liberty
read_verilog tiny_mapped.v
if {![link_design tiny]} {
    error "Cannot link tiny"
}
foreach cell {sky130_fd_sc_hd__dlxtp_1 sky130_fd_sc_hd__buf_1 sky130_fd_sc_hd__and2_1} {
    if {[llength [get_lib_cells */$cell]] != 1} {
        error "Missing or ambiguous library cell: $cell"
    }
}
if {[llength [get_cells *]] != 11 ||
    [llength [all_registers -level_sensitive -cells]] != 3} {
    error "Expected eleven instances including three latches"
}
foreach pin {L1/D L1/GATE L1/Q L2/D L2/GATE L2/Q L3/D L3/GATE L3/Q} {
    if {[llength [get_pins $pin]] != 1} {
        error "Missing or ambiguous latch pin: $pin"
    }
}

read_sdc $sdc_path
file mkdir $report_dir
file copy -force $sdc_path [file join $report_dir constraints.sdc]
log_begin ${report_dir}/units.rpt
report_units
log_end
log_begin ${report_dir}/clocks.rpt
report_clock_properties [get_clocks clk]
log_end
check_setup -verbose > ${report_dir}/check_setup.rpt

report_checks -path_delay max -format full_clock_expanded \
    -fields {slew capacitance input_pin net} \
    -group_path_count 100 -endpoint_path_count 100 -digits 6 \
    > ${report_dir}/setup.rpt
report_checks -path_delay min -format full_clock_expanded \
    -fields {slew capacitance input_pin net} \
    -group_path_count 100 -endpoint_path_count 100 -digits 6 \
    > ${report_dir}/hold.rpt
report_check_types -min_pulse_width -digits 6 > ${report_dir}/pulse_width.rpt

foreach latch {L1 L2 L3} {
    report_instance $latch > ${report_dir}/${latch}_instance.rpt
    log_begin ${report_dir}/${latch}_arrival.rpt
    report_arrival -digits 6 [get_pins $latch/D]
    log_end
    report_net -digits 6 [get_full_name [get_nets -of_objects [get_pins $latch/Q]]] \
        > ${report_dir}/${latch}_load.rpt
    log_begin ${report_dir}/${latch}_dq_min.rpt
    report_dcalc -from [get_pins $latch/D] -to [get_pins $latch/Q] -min -digits 6
    log_end
    log_begin ${report_dir}/${latch}_dq_max.rpt
    report_dcalc -from [get_pins $latch/D] -to [get_pins $latch/Q] -max -digits 6
    log_end
    log_begin ${report_dir}/${latch}_cq_min.rpt
    report_dcalc -from [get_pins $latch/GATE] -to [get_pins $latch/Q] -min -digits 6
    log_end
    log_begin ${report_dir}/${latch}_cq_max.rpt
    report_dcalc -from [get_pins $latch/GATE] -to [get_pins $latch/Q] -max -digits 6
    log_end
}
source $graph_exporter
pin_graph::export $report_dir
puts "Reports written to $report_dir; inspect setup, hold, clock edge mapping and pulse width"
