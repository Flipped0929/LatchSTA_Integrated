# Routed-geometry OpenRCX extraction only. No STA library/SDC loading,
# timing-parasitic annotation, timing reports, timing repair or RC scaling.
set script_dir [file dirname [file normalize [info script]]]
set input_run $script_dir/run_03
if {[info exists ::env(COUNTER_RCX_INPUT)]} {set input_run [file normalize $::env(COUNTER_RCX_INPUT)]}
if {![info exists ::env(COUNTER_RCX_RUN)]} {error "Set COUNTER_RCX_RUN to a new output directory"}
set output_run [file normalize $::env(COUNTER_RCX_RUN)]
if {[file exists $output_run]} {error "Refusing to overwrite existing output: $output_run"}
set rules $::env(HOME)/eda/OpenROAD-flow-scripts-live/flow/platforms/sky130hd/rcx_patterns.rules
if {[info exists ::env(COUNTER_RCX_RULES)]} {set rules [file normalize $::env(COUNTER_RCX_RULES)]}
set input_db $input_run/results/08_routed.odb
foreach path [list $input_db $rules $input_run/results/counter_routed.v $input_run/results/08_routed.sdc] {
    if {![file isfile $path]} {error "Missing extraction input: $path"}
}
foreach dir {inputs results reports logs} {file mkdir $output_run/$dir}
file copy [info script] $output_run/inputs/extract.tcl
# Tcl file copy preserves a symlink rather than its contents. The ORFS HD
# rules path is a symlink, and HGFS does not support creating that symlink.
set rule_src [open $rules rb]
set rule_dst [open $output_run/inputs/sky130hd_rcx_patterns.rules wb]
fcopy $rule_src $rule_dst
close $rule_src
close $rule_dst
file copy $input_run/results/counter_routed.v $output_run/inputs/counter_routed.v
file copy $input_run/results/08_routed.sdc $output_run/inputs/counter_routed.sdc
set fd [open $output_run/inputs/sources.tsv w]
puts $fd "kind\tpath"
puts $fd "routed_odb\t$input_db"
puts $fd "extraction_rules\t$rules"
puts $fd "netlist\t$input_run/results/counter_routed.v"
puts $fd "sdc_reference_only\t$input_run/results/08_routed.sdc"
close $fd
set_thread_count 2
read_db $input_db
if {![design_is_routed -verbose]} {error "Input database contains unrouted signal nets"}
set block [ord::get_db_block]
if {[$block getName] ne "counter"} {error "Unexpected top design"}
set fd [open $output_run/reports/routing_layers.tsv w]
puts $fd "level\tname\tdirection"
set levels {}
foreach layer [[ord::get_db_tech] getLayers] {
    set level [$layer getRoutingLevel]
    if {$level > 0} {
        lappend levels $level
        puts $fd "$level\t[$layer getName]\t[$layer getDirection]"
    }
}
close $fd
if {[lsort -integer $levels] ne {1 2 3 4 5 6}} {error "Expected the SKY130 6-layer interconnect stack"}
set fd [open $output_run/reports/expected_connections.tsv w]
puts $fd "net\tkind\tinstance\tpin\tdirection"
set signal_nets 0
foreach net [$block getNets] {
    if {[$net getSigType] in {POWER GROUND}} {continue}
    incr signal_nets
    foreach pin [$net getITerms] {
        puts $fd "[$net getName]\tinstance\t[[$pin getInst] getName]\t[[$pin getMTerm] getName]\t[[$pin getMTerm] getIoType]"
    }
    foreach port [$net getBTerms] {
        puts $fd "[$net getName]\tport\t\t[$port getName]\t[$port getIoType]"
    }
}
close $fd
if {$signal_nets != 24} {error "Expected 24 signal/clock nets"}
write_def $output_run/inputs/before_extract.def
cd $output_run/logs
puts "\n===== OPENRCX NOMINAL EXTRACTION ====="
define_process_corner -ext_model_index 0 nominal
# A zero threshold retains modeled positive inter-net coupling capacitors.
# Keep via resistors separate from wire resistors. Use the default 50-ohm
# series wire-resistance merge limit and explicitly record the search context.
extract_parasitics -ext_model_file $output_run/inputs/sky130hd_rcx_patterns.rules \
    -max_res 50 -coupling_threshold 0.0 -cc_model 10 -context_depth 5 -no_merge_via_res
write_spef -coordinates $output_run/results/counter.nominal.spef
write_db $output_run/results/09_extracted.odb
write_def $output_run/results/09_extracted.def
set fd [open $output_run/reports/extraction_status.txt w]
puts $fd "design=counter"
puts $fd "corner=nominal"
puts $fd "routed_signal_clock_nets=$signal_nets"
puts $fd "rule_layers=6"
puts $fd "coupling_threshold_ff=0.0"
puts $fd "max_series_resistance_ohm=50"
puts $fd "coupling_context_tracks=10"
puts $fd "context_depth=5"
puts $fd "merge_via_resistance=false"
puts $fd "post_route_sta=NOT RUN"
puts $fd "sta_spef_annotation=NOT RUN"
close $fd
puts "\nPARASITIC_EXTRACTION_COMPLETE: $output_run"
puts "Post-route STA and timing-parasitic annotation: NOT RUN."
