# Physical implementation only. No extract_parasitics, estimate_parasitics,
# read_spef or post-route STA/report_checks calls are made in this flow.
set script_dir [file dirname [file normalize [info script]]]
set project_dir [file dirname $script_dir]
if {![info exists ::env(COUNTER_PNR_RUN)]} {error "Set COUNTER_PNR_RUN to a new output directory"}
set run_dir [file normalize $::env(COUNTER_PNR_RUN)]
if {[file exists $run_dir]} {error "Refusing to overwrite existing run: $run_dir"}
foreach subdir {inputs results reports logs} {file mkdir $run_dir/$subdir}
set platform $::env(HOME)/eda/OpenROAD-flow-scripts-live/flow/platforms/sky130hd
if {[info exists ::env(COUNTER_SKY130_PLATFORM)]} {set platform [file normalize $::env(COUNTER_SKY130_PLATFORM)]}
set tech_lef $platform/lef/sky130_fd_sc_hd.tlef
set cell_lef $platform/lef/sky130_fd_sc_hd_merged.lef
set liberty $platform/lib/sky130_fd_sc_hd__tt_025C_1v80.lib
set input_netlist $project_dir/counter_mapped.v
set input_sdc $project_dir/counter_opt.sdc
foreach path [list $tech_lef $cell_lef $liberty $input_netlist $input_sdc] {
    if {![file isfile $path]} {error "Missing input: $path"}
}
file copy $input_netlist $run_dir/inputs/counter_mapped.v
file copy $input_sdc $run_dir/inputs/counter_opt.sdc
file copy [info script] $run_dir/inputs/flow.tcl
set source_fd [open $run_dir/inputs/sources.tsv w]
puts $source_fd "kind\tpath"
foreach kind {technology_lef cell_lef liberty netlist sdc} path [list $tech_lef $cell_lef $liberty $input_netlist $input_sdc] {
    puts $source_fd "$kind\t$path"
}
close $source_fd
set_thread_count 2

proc power_connect {} {
    add_global_connection -net VDD -inst_pattern {.*} -pin_pattern {^VPWR$} -power
    add_global_connection -net VDD -inst_pattern {.*} -pin_pattern {^VPB$}
    add_global_connection -net VSS -inst_pattern {.*} -pin_pattern {^VGND$} -ground
    add_global_connection -net VSS -inst_pattern {.*} -pin_pattern {^VNB$}
    global_connect
}

proc snapshot {stage} {
    global run_dir
    write_db $run_dir/results/$stage.odb
    write_def $run_dir/results/$stage.def
    write_verilog $run_dir/results/$stage.v
    write_sdc -no_timestamp -digits 12 $run_dir/results/$stage.sdc
}

proc inventory {stage} {
    global run_dir
    set block [ord::get_db_block]
    set inst_fd [open $run_dir/reports/${stage}_instances.tsv w]
    set pin_fd [open $run_dir/reports/${stage}_pins.tsv w]
    puts $inst_fd "instance\tmaster\tx_dbu\ty_dbu\torientation\tstatus"
    puts $pin_fd "instance\tmaster\tpin\tdirection\tsignal_type\tnet"
    foreach inst [$block getInsts] {
        set master [[$inst getMaster] getName]
        lassign [$inst getLocation] x y
        puts $inst_fd "[$inst getName]\t$master\t$x\t$y\t[$inst getOrient]\t[$inst getPlacementStatus]"
        foreach pin [$inst getITerms] {
            set term [$pin getMTerm]
            set net [$pin getNet]
            set net_name ""
            if {$net ne "NULL"} {set net_name [$net getName]}
            puts $pin_fd "[$inst getName]\t$master\t[$term getName]\t[$term getIoType]\t[$term getSigType]\t$net_name"
        }
    }
    close $inst_fd
    close $pin_fd
}

puts "\n===== IMPORT: SKY130 HD + COUNTER + OPTIMIZED SDC ====="
read_lef $tech_lef
read_lef $cell_lef
read_liberty $liberty
read_verilog $run_dir/inputs/counter_mapped.v
link_design counter
read_sdc $run_dir/inputs/counter_opt.sdc
set original_latches [all_registers -level_sensitive -cells]
if {[llength $original_latches] != 8} {error "Expected exactly 8 latches"}
set block [ord::get_db_block]
if {[llength [$block getInsts]] != 18} {error "Expected 18 original standard cells"}
snapshot 01_import
inventory 01_import

puts "\n===== FLOORPLAN + TRACKS + IO + WELL TAPS ====="
# 60 x 60 um block, 86 sites x 14 single-height rows in the core.
initialize_floorplan -die_area {0 0 60 60} -core_area {10.12 10.88 49.68 48.96} -site unithd
source $platform/make_tracks.tcl
set_io_pin_constraint -pin_names {clk} -region bottom:24-36
set_io_pin_constraint -pin_names {en rst_n} -region left:15-45 -group -order
set_io_pin_constraint -pin_names {count[0] count[1] count[2] count[3]} -region right:15-45 -group -order
place_pins -hor_layers met3 -ver_layers met2 -corner_avoidance 8 -min_distance 2
tapcell -distance 14 -tapcell_master sky130_fd_sc_hd__tapvpwrvgnd_1 \
    -endcap_master sky130_fd_sc_hd__tapvpwrvgnd_1
power_connect
snapshot 02_floorplan

puts "\n===== POWER DELIVERY NETWORK ====="
set_voltage_domain -name CORE -power VDD -ground VSS
define_pdn_grid -name core_grid -voltage_domains CORE -pins {met5}
add_pdn_ring -grid core_grid -layers {met4 met5} -widths {1.6 1.6} \
    -spacings {1.7 1.7} -core_offsets {2.4 2.4}
add_pdn_stripe -grid core_grid -layer met1 -width 0.48 -pitch 5.44 -offset 0 -followpins -extend_to_core_ring
add_pdn_stripe -grid core_grid -layer met4 -width 1.6 -pitch 20 -offset 4 -snap_to_grid -extend_to_core_ring
add_pdn_stripe -grid core_grid -layer met5 -width 1.6 -pitch 20 -offset 4 -snap_to_grid -extend_to_core_ring
add_pdn_connect -grid core_grid -layers {met1 met4}
add_pdn_connect -grid core_grid -layers {met4 met5}
pdngen -failed_via_report $run_dir/reports/pdn_failed_vias.rpt
check_power_grid -net VDD -error_file $run_dir/reports/pdn_vdd.rpt
check_power_grid -net VSS -error_file $run_dir/reports/pdn_vss.rpt
snapshot 03_pdn

puts "\n===== GLOBAL AND DETAILED PLACEMENT ====="
# Default mode is wirelength/density driven; omit -timing_driven and
# -routability_driven so no timing or design RC estimation is requested.
global_placement -density 0.45
detailed_placement -report_file_name $run_dir/reports/placement.json
check_placement -verbose -report_file_name $run_dir/reports/placement_check.json
report_design_area
snapshot 04_placed
inventory 04_placed

puts "\n===== CLOCK TREE SYNTHESIS ====="
# Per-unit RC lookup is needed to characterize/build the CTS buffers.
# This does not run design parasitic estimation or extraction.
source $platform/setRC.tcl
clock_tree_synthesis -buf_list {sky130_fd_sc_hd__clkbuf_1 sky130_fd_sc_hd__clkbuf_2 sky130_fd_sc_hd__clkbuf_4} \
    -root_buf sky130_fd_sc_hd__clkbuf_4 -tree_buf sky130_fd_sc_hd__clkbuf_2 \
    -sink_clustering_enable -sink_clustering_size 4 -sink_clustering_max_diameter 20 \
    -balance_levels -obstruction_aware
detailed_placement -report_file_name $run_dir/reports/cts_placement.json
check_placement -verbose -report_file_name $run_dir/reports/cts_placement_check.json
power_connect
# Retain the original SDC snapshot. The physical SDC uses propagated clocks,
# removing the original zero ideal network/pin latencies for a later STA run.
set clock_pins {}
foreach n {17 18 19 20} {lappend clock_pins [get_pins _${n}_/GATE_N]}
foreach n {21 22 23 24} {lappend clock_pins [get_pins _${n}_/GATE]}
unset_clock_latency -clock [get_clocks clk] $clock_pins
unset_clock_latency [get_clocks clk]
set_propagated_clock [get_clocks clk]
report_cts -out_file $run_dir/reports/cts.rpt
snapshot 05_cts
inventory 05_cts

puts "\n===== FILLER PLACEMENT ====="
filler_placement -prefix FILL_ {sky130_fd_sc_hd__fill_8 sky130_fd_sc_hd__fill_4 sky130_fd_sc_hd__fill_2 sky130_fd_sc_hd__fill_1}
power_connect
check_placement -verbose -report_file_name $run_dir/reports/filler_placement_check.json
check_power_grid -net VDD -error_file $run_dir/reports/final_pdn_vdd.rpt
check_power_grid -net VSS -error_file $run_dir/reports/final_pdn_vss.rpt
snapshot 06_filled

puts "\n===== GLOBAL ROUTING ====="
set_global_routing_layer_adjustment met1-met5 0.2
set_routing_layers -signal met1-met5 -clock met3-met5
global_route -guide_file $run_dir/results/counter.guide -congestion_iterations 50 \
    -congestion_report_file $run_dir/reports/congestion.rpt -verbose
snapshot 07_global_route

puts "\n===== DETAILED ROUTING ====="
detailed_route -output_drc $run_dir/reports/detailed_route_drc.rpt \
    -output_maze $run_dir/logs/maze.log \
    -output_guide_coverage $run_dir/reports/guide_coverage.csv \
    -drc_report_iter_step 5 -droute_end_iter 64 -or_seed 42 -verbose 1
if {![design_is_routed -verbose]} {error "Final design contains unrouted signal nets"}
report_wire_length -detailed_route -summary -file $run_dir/reports/wire_length.rpt
snapshot 08_routed
inventory 08_routed
write_verilog -include_pwr_gnd $run_dir/results/counter_routed_power.v
write_verilog -remove_cells {sky130_fd_sc_hd__fill* sky130_fd_sc_hd__tapvpwrvgnd*} \
    $run_dir/results/counter_routed.v
puts "\nPHYSICAL_IMPLEMENTATION_COMPLETE: $run_dir"
puts "Parasitic extraction: NOT RUN. Post-route STA: NOT RUN."
