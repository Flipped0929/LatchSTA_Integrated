set script_dir [file dirname [file normalize [info script]]]
if {[info exists ::env(COUNTER_PNR_RUN)]} {
    set run_dir [file normalize $::env(COUNTER_PNR_RUN)]
} else {
    set run_dir $script_dir/run_03
}
read_db $run_dir/results/08_routed.odb
set platform $::env(HOME)/eda/OpenROAD-flow-scripts-live/flow/platforms/sky130hd
if {[info exists ::env(COUNTER_SKY130_PLATFORM)]} {set platform $::env(COUNTER_SKY130_PLATFORM)}
read_liberty $platform/lib/sky130_fd_sc_hd__tt_025C_1v80.lib
read_sdc $run_dir/results/08_routed.sdc
gui::fit
gui::set_display_controls "*" visible false
gui::set_display_controls "Layers/*" visible true
gui::set_display_controls "Nets/*" visible true
gui::set_display_controls "Instances/*" visible true
gui::set_display_controls "Shape Types/*" visible true
gui::set_display_controls "Misc/Instances/*" visible false
gui::set_display_controls "Misc/Instances/Pins" visible true
gui::set_display_controls "Misc/Instances/Names" visible true
gui::set_display_controls "Misc/Scale bar" visible true
gui::set_display_controls "Misc/Detailed view" visible true
file mkdir $run_dir/images
save_image -area {0 0 60 60} -width 1800 $run_dir/images/layout_with_pdn.png
gui::set_display_controls "Nets/Power" visible false
gui::set_display_controls "Nets/Ground" visible false
gui::set_display_controls "Instances/Physical/*" visible false
save_image -area {0 0 60 60} -width 1800 $run_dir/images/routed_signals.png
gui::set_display_controls "Nets/*" visible false
gui::set_display_controls "Nets/Clock" visible true
gui::set_display_controls "Instances/*" visible false
gui::set_display_controls "Instances/StdCells/Clock tree/*" visible true
gui::set_display_controls "Instances/StdCells/Sequential" visible true
save_image -area {24 22 50 49} -width 1600 $run_dir/images/clock_tree.png
gui::set_display_controls "Nets/*" visible true
gui::set_display_controls "Nets/Power" visible false
gui::set_display_controls "Nets/Ground" visible false
gui::set_display_controls "Instances/*" visible true
gui::set_display_controls "Instances/Physical/*" visible false
gui::fit
