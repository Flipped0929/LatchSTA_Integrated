# Syntax and constraint round-trip test with mocked STA commands; not an OpenSTA run.
if {$argc != 1} {error "Usage: tclsh test_counter_sdc.tcl candidate.sdc"}
set ports {clk en rst_n {count[0]} {count[1]} {count[2]} {count[3]}}
set pins {_17_/GATE_N _18_/GATE_N _19_/GATE_N _20_/GATE_N _21_/GATE _22_/GATE _23_/GATE _24_/GATE}
proc get_ports {name} {
    if {$name ni $::ports} {error "Unknown port: $name"}
    return [list $name]
}
proc get_pins {name} {
    if {$name ni $::pins} {error "Unknown clock pin: $name"}
    return [list $name]
}
proc get_clocks {name} {
    if {$name ne "clk"} {error "Unknown clock: $name"}
    return [list $name]
}
proc all_registers {args} {return {_17_ _18_ _19_ _20_ _21_ _22_ _23_ _24_}}
proc create_clock {args} {
    set ::period [lindex $args 3]
    set waveform [lindex $args 5]
    if {abs($::period-1.584538)>1e-7 || abs([lindex $waveform 0]-0.5*$::period)>1e-12 ||
        abs([lindex $waveform 1]-$::period)>1e-12 || [lindex $args 6] ne "clk"} {error "Incorrect waveform"}
}
set latencies 0
proc set_clock_latency {args} {
    if {[lindex $args end-1] != 0.0} {error "Nonzero clock latency"}
    incr ::latencies
}
proc set_clock_transition {value clock} {
    if {$value != 0.06} {error "Clock transition changed"}
}
proc set_clock_uncertainty {kind value clock} {
    if {$value != 0.05} {error "Clock uncertainty changed"}
    dict set ::uncertainties $kind $value
}
proc set_input_delay {args} {
    dict set ::inputs [lindex [lindex $args end] 0] [lindex $args 2] [lindex $args 3]
}
proc set_output_delay {args} {
    dict set ::outputs [lindex [lindex $args end] 0] [lindex $args 2] [lindex $args 3]
}
proc set_input_transition {value port} {
    if {$value != 0.06} {error "Input transition changed"}
    lappend ::slews $port
}
proc set_load {value port} {
    if {$value != 0.01} {error "Output load changed"}
    lappend ::loads $port
}
source [lindex $argv 0]
if {$latencies != 10 || [dict size $inputs] != 2 || [dict size $outputs] != 4 ||
    [llength $slews] != 2 || [llength $loads] != 4 || [dict size $uncertainties] != 2} {error "Missing constraints"}
foreach port {en rst_n} {
    if {[dict get $inputs $port -min] != 0.2 || [dict get $inputs $port -max] != 1.0} {error "Input budget changed"}
}
foreach port {{count[0]} {count[1]} {count[2]} {count[3]}} {
    if {[dict get $outputs $port -min] != -0.05 || [dict get $outputs $port -max] != 1.0} {error "Output budget changed"}
}
puts "counter SDC syntax, waveform, zero latencies and all IO constraints passed (mocked STA)"
