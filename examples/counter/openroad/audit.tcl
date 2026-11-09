set script_dir [file dirname [file normalize [info script]]]
set run_dir [file normalize $::env(COUNTER_PNR_RUN)]
read_db $run_dir/results/08_routed.odb
set fd [open $run_dir/reports/physical_checks.txt w]
check_placement -verbose
puts $fd "placement_legal=PASS"
puts $fd "design_is_routed=[design_is_routed -verbose]"
check_power_grid -net VDD
puts $fd "VDD_connectivity=PASS"
check_power_grid -net VSS
puts $fd "VSS_connectivity=PASS"
report_wire_length -detailed_route -net [get_nets *] -file $run_dir/reports/wire_length_by_net.rpt -verbose
set block [ord::get_db_block]
set rect [$block getDieArea]
puts $fd "die_dbu=[$rect xMin] [$rect yMin] [$rect xMax] [$rect yMax]"
puts $fd "database_units_per_um=[$block getDbUnitsPerMicron]"
puts $fd "instances=[llength [$block getInsts]]"
puts $fd "nets=[llength [$block getNets]]"
puts $fd "ports=[llength [$block getBTerms]]"
puts $fd "rows=[llength [$block getRows]]"
close $fd
set port_fd [open $run_dir/reports/ports.tsv w]
puts $port_fd "port\tdirection\tsignal_type\tnet"
foreach port [$block getBTerms] {
    puts $port_fd "[$port getName]\t[$port getIoType]\t[$port getSigType]\t[[$port getNet] getName]"
}
close $port_fd
puts "FINAL_PHYSICAL_AUDIT_COMPLETE"
