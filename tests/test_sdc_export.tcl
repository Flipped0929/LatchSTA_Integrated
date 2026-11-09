# Tcl syntax/control-flow test with mocked STA commands; this is NOT timing validation.
if {$argc != 3} {error "Usage: tclsh test_sdc_export.tcl candidate.sdc run_sta.tcl new_report_dir"}
lassign $argv candidate runner destination
set candidate [file normalize $candidate]
set runner [file normalize $runner]
set destination [file normalize $destination]
if {[file exists $destination]} {error "Test needs a new report directory"}
proc assert {condition} {
    if {![uplevel 1 [list expr $condition]]} {error "Assertion failed: $condition"}
}
proc contents {path} {set f [open $path rb]; set data [read $f]; close $f; return $data}
proc get_ports {name} {
    if {$name in {i_clk i_din o_dout}} {return [list $name]}
    return {}
}
proc get_pins {name} {
    if {[info exists ::missing_gate] && $name eq "L2/GATE"} {return {}}
    if {[regexp {^L[123]/(D|GATE|Q)$} $name]} {return [list $name]}
    return {}
}
proc get_clocks {name} {assert {$name eq "clk"}; return [list $name]}
proc all_registers {args} {return {L1 L2 L3}}
proc get_cells {args} {return {L1 L2 L3 B1 B2 B3 B4 B5 B6 B7 AND}}
proc get_lib_cells {args} {return {mock_lib_cell}}
proc read_liberty {args} {}
proc read_verilog {args} {}
proc link_design {args} {return 1}
proc create_clock {args} {set ::clock_args $args}
proc set_clock_latency {args} {
    assert {[llength $args] == 4 && [lindex $args 0] eq "-clock" && [lindex $args 1] eq "clk"}
    dict set ::latencies [lindex $args 3] [lindex $args 2]
}
proc set_input_delay {args} {dict set ::io_delays input [lindex $args 2] [lindex $args 3]}
proc set_output_delay {args} {dict set ::io_delays output [lindex $args 2] [lindex $args 3]}
proc set_clock_transition {args} {set ::clock_transition [lindex $args 0]}
proc set_input_transition {args} {set ::input_transition [lindex $args 0]}
proc set_load {args} {set ::output_load [lindex $args 0]}
proc set_clock_uncertainty {args} {dict set ::uncertainty [lindex $args 0] [lindex $args 1]}
proc read_sdc {path} {set ::loaded_sdc $path; uplevel #0 [list source $path]}
proc log_begin {path} {
    assert {![info exists ::logging]}
    set ::logging $path
    set f [open $path w]; puts $f "MOCK COMMANDS ONLY, NOT A TIMING REPORT"; close $f
}
proc log_end {} {assert {[info exists ::logging]}; unset ::logging}
proc redirected {args} {
    set idx [lsearch -exact $args >]
    if {$idx >= 0} {
        set f [open [lindex $args [expr {$idx + 1}]] w]
        puts $f "MOCK COMMANDS ONLY, NOT A TIMING REPORT"; close $f
    }
}
foreach command {check_setup report_checks report_check_types report_instance report_net} {
    proc $command {args} {redirected {*}$args}
}
foreach command {report_units report_clock_properties report_arrival report_dcalc} {
    proc $command {args} {}
}
proc get_nets {args} {return mock_net}
proc get_full_name {value} {return $value}
set original_baseline [contents [file join [file dirname $runner] tiny.sdc]]
set ::env(MCR_SDC) $candidate
set ::env(MCR_REPORT_DIR) $destination
source [file join [file dirname [info script]] pin_graph_mock.tcl]
source $runner
assert {$::loaded_sdc eq $candidate}
assert {[contents [file join $destination constraints.sdc]] eq [contents $candidate]}
assert {[llength [glob -directory $destination *.rpt]] == 27}
assert {[file isfile [file join $destination pin_graph boundary_edges.tsv]]}
assert {![info exists ::logging]}
set period [lindex $::clock_args [expr {[lsearch -exact $::clock_args -period] + 1}]]
set wave [lindex $::clock_args [expr {[lsearch -exact $::clock_args -waveform] + 1}]]
assert {abs($period - 3.541155) < 1e-7 && abs([lindex $wave 1] - $period) < 1e-12}
assert {abs($::clock_transition - 0.05) < 1e-12 && abs($::input_transition - 0.05) < 1e-12}
assert {abs($::output_load - 0.005) < 1e-12}
assert {[dict get $::io_delays input -min] == 0.2 && [dict get $::io_delays input -max] == 1.0}
assert {[dict get $::io_delays output -min] == -0.05 && [dict get $::io_delays output -max] == 1.0}
assert {[dict get $::uncertainty -setup] == 0.0 && [dict get $::uncertainty -hold] == 0.0}
assert {[dict size $::latencies] == 3}
foreach line [split [contents $candidate] \n] {
    if {[regexp {^# \{(L[123])\} skew_ns=(\S+) opening_ns=(\S+) closing_ns=(\S+)} $line -> instance skew opening closing]} {
        assert {abs([dict get $::latencies $instance/GATE] - $skew) < 1e-12}
        assert {abs($opening - $skew - [lindex $wave 0]) < 1e-12}
        assert {abs($closing - $skew - $period) < 1e-12}
    }
}
assert {[catch {source $runner} message] && [string match {*previous reports are protected*} $message]}
unset ::env(MCR_REPORT_DIR)
assert {[catch {source $runner} message] && [string match {*requires MCR_SDC and MCR_REPORT_DIR*} $message]}
set ::env(MCR_REPORT_DIR) $destination
set ::env(MCR_SDC) [file join [file dirname $runner] tiny.sdc]
assert {[catch {source $runner} message] && [string match {*baseline and previous reports are protected*} $message]}
set ::missing_gate 1
assert {[catch {source $candidate} message] && [string match {*Missing latch GATE pin*} $message]}
assert {$original_baseline eq [contents [file join [file dirname $runner] tiny.sdc]]}
puts "Candidate SDC and runner Tcl checks passed; no real STA was executed"
