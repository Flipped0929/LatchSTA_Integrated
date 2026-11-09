# Tcl/SDC control-flow fixture only; all timing output is explicitly synthetic.
if {$argc != 3} {error "Usage: tclsh test_counter_sta.tcl runner.tcl new_report_dir scenario"}
lassign $argv runner destination scenario
namespace eval counter_mock {variable rows {}; variable calls {}; variable logging {}; variable log_open 0}
for {set i 0} {$i < 8} {incr i} {
    set name [expr {$i < 4 ? "master_$i" : "slave_$i"}]
    set cell [expr {$i < 4 ? "sky130_fd_sc_hd__dlxtn_1" : "sky130_fd_sc_hd__dlxtp_1"}]
    dict set counter_mock::rows $name $cell
}
if {$scenario eq "wrong_cell"} {dict set counter_mock::rows master_0 unsupported_latch}
proc assert {condition} {
    if {![uplevel 1 [list expr $condition]]} {error "Assertion failed: $condition"}
}
proc get_full_name {value} {return $value}
proc get_property {instance property} {
    assert {$property eq "ref_name"}
    return [dict get $::counter_mock::rows $instance]
}
proc all_registers {args} {
    if {[lsearch -exact $args -edge_triggered] >= 0} {return {}}
    return [dict keys $::counter_mock::rows]
}
proc get_lib_cells {pattern} {return mock_lib_cell}
proc get_ports {pattern} {
    if {$pattern eq "count*"} {return {{count[0]} {count[1]} {count[2]} {count[3]}}}
    if {$pattern in {clk rst_n en}} {return [list $pattern]}
    return {}
}
proc get_pins {name} {
    if {$::scenario eq "missing_pin" && $name eq "master_0/GATE_N"} {return {}}
    lassign [split $name /] instance port
    if {![dict exists $::counter_mock::rows $instance]} {return {}}
    set gate [expr {[string match master* $instance] ? "GATE_N" : "GATE"}]
    if {$port in [list D Q $gate]} {return [list $name]}
    return {}
}
proc get_clocks {name} {assert {$name in {clk *}}; return clk}
proc get_nets {args} {return clk}
proc read_liberty {path} {assert {[file isfile $path]}}
proc read_verilog {path} {assert {[file isfile $path]}}
proc link_design {name} {assert {$name eq "counter"}; return 1}
proc write_sdc {path} {file copy [file join [file dirname $path] constraints.sdc] $path}
proc create_clock {args} {set ::counter_mock::clock $args}
foreach command {set_clock_latency set_clock_transition set_clock_uncertainty set_input_delay set_input_transition set_output_delay set_load} {
    proc $command {args} {dict lappend ::counter_mock::calls [lindex [info level 0] 0] $args}
}
proc set_false_path {args} {error "Reset timing must not be hidden"}
proc set_case_analysis {args} {error "Reset must not be forced inactive"}
proc read_sdc {path} {uplevel #0 [list source $path]}
proc log_begin {path} {
    assert {!$::counter_mock::log_open}
    set ::counter_mock::log_open 1
    set f [open $path w]; puts $f "MOCK ONLY; NOT STA EVIDENCE"; close $f
}
proc log_end {} {assert {$::counter_mock::log_open}; set ::counter_mock::log_open 0}
foreach command {report_units report_clock_properties report_arrival} {proc $command {args} {}}
proc report_dcalc {args} {dict lappend ::counter_mock::calls dcalc $args}
proc redirected {args} {
    set idx [lsearch -exact $args >]
    assert {$idx >= 0}
    set f [open [lindex $args [expr {$idx+1}]] w]
    puts $f "MOCK ONLY; NOT STA EVIDENCE"; close $f
}
foreach command {check_setup report_checks report_check_types report_instance report_net} {
    proc $command {args} {
        dict lappend ::counter_mock::calls [lindex [info level 0] 0] $args
        redirected {*}$args
        return 1
    }
}
set ::env(COUNTER_REPORT_DIR) [file normalize $destination]
set status [catch {source [file normalize $runner]} message]
if {$scenario ne "normal"} {
    assert {$status != 0}
    if {$scenario eq "missing_pin"} {assert {[string match {*Missing or ambiguous pin*} $message]}}
    if {$scenario eq "wrong_cell"} {assert {[string match {*Unsupported counter latch cell*} $message]}}
    assert {![file exists [file join $destination units.rpt]]}
    puts "Counter rejection fixture passed; no STA was executed"
    exit
}
if {$status} {error $message}
assert {[llength [glob -directory $destination *.rpt]] == 68}
assert {[file isfile [file join $destination latches.tsv]]}
assert {!$::counter_mock::log_open}
assert {[dict size $::counter_mock::rows] == 8}
set clock $::counter_mock::clock
assert {[lindex $clock [expr {[lsearch -exact $clock -waveform]+1}]] eq "5.0 10.0"}
set cq 0; set dq 0
foreach args [dict get $::counter_mock::calls dcalc] {
    set from [lindex $args [expr {[lsearch -exact $args -from]+1}]]
    if {[string match */GATE* $from]} {incr cq}
    if {[string match */D $from]} {incr dq}
}
assert {$cq == 16 && $dq == 16}
assert {[catch {source $runner} message] && [string match {*must be a new directory*} $message]}
puts "Counter phases, synchronous reset reports and overwrite protection passed; no STA was executed"
