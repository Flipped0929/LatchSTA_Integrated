# Synchronous-reset counter: SKY130 HD TT, ideal zero-skew clock, no SPEF.

# COUNTER_SDC and COUNTER_REPORT_DIR must be set,such as:
# COUNTER_SDC="$PWD/counter_opt.sdc" COUNTER_REPORT_DIR="$PWD/reports_169" sta -no_init -no_splash -exit run_sta.tcl

set case_dir [file dirname [file normalize [info script]]]
set report_dir [file join $case_dir reports]
if {[info exists ::env(COUNTER_REPORT_DIR)]} {
    set report_dir [file normalize $::env(COUNTER_REPORT_DIR)]
    if {[file exists $report_dir]} {error "COUNTER_REPORT_DIR must be a new directory"}
}
if {[file exists [file join $report_dir units.rpt]] || [file exists [file join $report_dir pin_graph]]} {
    error "Existing STA reports are protected; set COUNTER_REPORT_DIR to a new directory"
}
set sdc_file [file join $case_dir counter.sdc]
if {[info exists ::env(COUNTER_SDC)]} {set sdc_file [file normalize $::env(COUNTER_SDC)]}
cd $case_dir
set liberty ../../sky130_pdk/sky130_fd_sc_hd__tt_025C_1v80.lib
foreach path [list $liberty counter_mapped.v $sdc_file] {
    if {![file isfile $path]} {error "Missing counter STA input: $path"}
}
read_liberty $liberty
read_verilog counter_mapped.v
if {![link_design counter]} {error "Cannot link counter"}
foreach cell {sky130_fd_sc_hd__dlxtn_1 sky130_fd_sc_hd__dlxtp_1} {
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
        sky130_fd_sc_hd__dlxtn_1 {set gate GATE_N; incr negative}
        sky130_fd_sc_hd__dlxtp_1 {set gate GATE; incr positive}
        default {error "Unsupported counter latch cell: $cell"}
    }
    foreach port [list D Q $gate] {
        if {[llength [get_pins $name/$port]] != 1} {error "Missing or ambiguous pin: $name/$port"}
    }
    set gate_net [get_full_name [get_nets -of_objects [get_pins $name/$gate]]]
    if {$gate_net ne "clk"} {error "Expected direct shared clk at $name/$gate, found $gate_net"}
    lappend latch_rows [list $name $cell $name/$gate $name/D $name/Q]
}
if {$negative != 4 || $positive != 4} {error "Expected four master dlxtn and four slave dlxtp latches"}
read_sdc $sdc_file
if {[llength [get_clocks *]] != 1 || [llength [get_clocks clk]] != 1} {error "Expected one shared clock clk"}
file mkdir $report_dir
file copy $sdc_file [file join $report_dir constraints.sdc]
set mapping [open [file join $report_dir latches.tsv] w]
puts $mapping "instance\tcell\tgate_pin\tdata_pin\toutput_pin"
foreach row $latch_rows {puts $mapping [join $row \t]}
close $mapping
# Archive the evaluated period too: constraints.sdc alone does not record environment overrides.
write_sdc [file join $report_dir effective.sdc]
log_begin $report_dir/units.rpt
report_units
log_end
log_begin $report_dir/clocks.rpt
report_clock_properties [get_clocks clk]
log_end
set constraints_ok [check_setup -verbose > $report_dir/check_setup.rpt]
foreach analysis {max min} kind {setup hold} {
    report_checks -path_delay $analysis -format full_clock_expanded \
        -fields {slew capacitance input_pin net} -group_path_count 1000 \
        -endpoint_path_count 1000 -digits 6 > $report_dir/$kind.rpt
}
foreach port {en rst_n} {
    foreach analysis {max min} kind {setup hold} {
        report_checks -from [get_ports $port] -path_delay $analysis -format full_clock_expanded \
            -fields {slew capacitance input_pin net} -group_path_count 1000 \
            -endpoint_path_count 1000 -digits 6 > $report_dir/${port}_${kind}.rpt
    }
}
report_check_types -min_pulse_width -format end -max_count 1000 -digits 6 > $report_dir/pulse_width.rpt
set checks {-max_delay -min_delay -min_pulse_width -min_period -max_slew -max_capacitance -max_fanout}
report_check_types {*}$checks -format end -max_count 1000 -digits 6 > $report_dir/checks.rpt
report_check_types {*}$checks -violators -format end -max_count 1000 -digits 6 > $report_dir/violations.rpt
foreach row $latch_rows {
    lassign $row name cell gate data output
    report_instance $name > $report_dir/${name}_instance.rpt
    log_begin $report_dir/${name}_arrival.rpt
    report_arrival -digits 6 [get_pins $data]
    log_end
    report_net -digits 6 [get_full_name [get_nets -of_objects [get_pins $output]]] \
        > $report_dir/${name}_load.rpt
    foreach from [list $data $gate] label {dq cq} {
        foreach analysis {min max} {
            log_begin $report_dir/${name}_${label}_${analysis}.rpt
            report_dcalc -from [get_pins $from] -to [get_pins $output] -$analysis -digits 6
            log_end
        }
    }
}
puts "Counter reports written to $report_dir; inspect setup/hold, synchronous reset paths, pulse widths and clock phases"
puts "Analysis only: ideal zero skew; the requested clock period is not a maximum-frequency certificate"
if {!$constraints_ok} {error "Incomplete timing constraints or invalid structure; see $report_dir/check_setup.rpt"}
