if {$argc != 3} {error "Usage: tclsh test_pin_graph.tcl exporter.tcl new_report_dir scenario"}
lassign $argv exporter report_dir scenario
source [file join [file dirname [info script]] pin_graph_mock.tcl]
graph_mock::configure $scenario
source $exporter
pin_graph::export $report_dir
if {![catch {pin_graph::export $report_dir} message] || ![string match {*already exists*} $message]} {
    error "Existing graph output was not protected"
}
if {$::graph_mock::iterators != 0} {error "Leaked graph iterators"}
if {![info exists ::graph_mock::calculated]} {error "Delays were not calculated before export"}
puts "Synthetic graph check completed; NOT a real STA run"
