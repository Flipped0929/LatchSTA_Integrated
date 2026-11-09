# Run after loading counter.sch. Use a native temporary directory because
# xschem's in-place netlist postprocessing can leave holes on VMware HGFS.
set project_dir [file dirname [xschem get schname]]
set export_tmp [file join /tmp counter-xschem-export-[pid]]
file mkdir $export_tmp
file mkdir [file join $project_dir simulation]
set local_netlist_dir 0
set netlist_dir $export_tmp
set export_log {}
foreach export_type {spice verilog} export_name {counter.spice counter.v} {
    xschem set netlist_type $export_type
    set export_messages [xschem netlist -messages [file join $export_tmp $export_name]]
    puts "$export_type ERC: $export_messages"
    append export_log "$export_type ERC:\n$export_messages\n"
    set export_file [file join $export_tmp $export_name]
    if {![file exists $export_file] || [file size $export_file] == 0} {
        error "Netlist export failed: $export_file"
    }
    file copy -force $export_file [file join $project_dir simulation $export_name]
}
xschem set netlist_type spice
xschem print svg [file join $export_tmp counter.svg] 2400 2150
file copy -force [file join $export_tmp counter.svg] [file join $project_dir counter.svg]
set export_fd [open [file join $project_dir simulation erc.txt] w]
puts $export_fd $export_log
close $export_fd
puts "Exported counter.svg and simulation/counter.{spice,v}"
