# Synthetic SWIG-shaped graph, not OpenSTA timing evidence.
namespace eval graph_mock {
    variable objects {}; variable serial 0; variable pins {}; variable instances {}
    variable scene_list {S_tt}; variable iterators 0; variable scenario normal
}
proc graph_mock::make {type properties} {
    variable objects; variable serial
    set id M[incr serial]
    dict set objects $id [dict merge [dict create type $type] $properties]
    interp alias {} ::$id {} graph_mock::dispatch $id
    return $id
}
proc graph_mock::dispatch {id method args} {
    variable objects; variable iterators; variable scenario
    set data [dict get $objects $id]
    switch -- $method {
        has_next {return [expr {[llength [dict get $data items]] > 0}]}
        next {
            set items [dict get $data items]
            dict set objects $id items [lrange $items 1 end]
            return [lindex $items 0]
        }
        finish {dict unset objects $id; rename ::$id {}; incr iterators -1; return}
        pin_iterator {return [graph_mock::iterator [dict get $data pins]]}
        out_edge_iterator {return [graph_mock::iterator [dict get $data edges]]}
        slew_scenes_string {
            lassign $args rf scenes analysis variance digits
            if {$scenario eq "missing_slew"} {return Inf}
            set scale [expr {[lindex $scenes 0] eq "S_slow" ? 2.0 : 1.0}]
            set units [expr {$scenario eq "units_ps" ? 1000.0 : 1.0}]
            return [expr {($rf eq "rise" ? 0.05 : 0.06) * $scale * ($analysis eq "min" ? 1 : 1.1) * $units}]
        }
        arc_delay {
            lassign $args arc scene analysis
            if {$scenario eq "nonfinite" && [dict get $data role] eq "combinational"} {return Inf}
            set value [dict get $objects $arc $analysis]
            return [expr {$value * 1e-9 * ($scene eq "S_slow" ? 2.0 : 1.0)}]
        }
        default {
            if {[llength $args]} {error "Unexpected mock args: $id $method $args"}
            if {![dict exists $data $method]} {error "Unknown mock API: [dict get $data type].$method"}
            return [dict get $data $method]
        }
    }
}
proc graph_mock::iterator {items} {
    variable iterators; incr iterators
    return [make iterator [dict create items $items]]
}
proc graph_mock::pin {name direction {instance {}}} {
    variable objects; variable pins
    set port [lindex [split $name /] end]
    set pin [make pin [dict create full_name $name direction $direction instance $instance \
        port_name $port net NULL is_pwr_gnd 0 is_top_level_port [expr {$instance eq ""}]]]
    set vertex [make vertex [dict create pin $pin is_bidirect_driver 0 edges {}]]
    dict set objects $pin vertices [list $vertex]
    dict set pins $name $pin
    if {$instance ne ""} {
        set data [dict get $objects $instance]
        dict lappend data pins $pin
        dict set objects $instance $data
    }
    return $pin
}
proc graph_mock::edge {from to role {rise {0 0}} {fall {0 0}} {invert 0}} {
    variable pins; variable objects
    set from [lindex [dict get $objects [dict get $pins $from] vertices] 0]
    set to [lindex [dict get $objects [dict get $pins $to] vertices] 0]
    set arcs {}
    foreach rf {rise fall} values [list $rise $fall] {
        set to_rf $rf
        if {$invert} {set to_rf [expr {$rf eq "rise" ? "fall" : "rise"}]}
        lassign $values minimum maximum
        lappend arcs [make arc [dict create from_edge_name $rf to_edge_name $to_rf min $minimum max $maximum]]
    }
    set edge [make edge [dict create from $from to $to role $role cond {} mode_name {} mode_value {} \
        timing_arcs $arcs disabled {}]]
    set data [dict get $objects $from]
    dict lappend data edges $edge
    dict set objects $from $data
    return $edge
}
proc get_full_name {object} {
    if {[dict exists $::graph_mock::objects $object full_name]} {
        return [dict get $::graph_mock::objects $object full_name]
    }
    return $object
}
proc get_property {object property} {return [dict get $::graph_mock::objects $object $property]}
proc get_clocks {pattern} {
    if {$pattern ni {clk *}} {error "Unexpected mock clock pattern $pattern"}
    return clk
}
proc clk {method} {
    if {$method ne "sources"} {error "Unexpected mock clock method $method"}
    return [list [dict get $::graph_mock::pins i_clk]]
}
proc all_registers {args} {
    if {[lsearch -exact $args -edge_triggered] >= 0} {return {}}
    set result {}
    foreach name {L1 L2 L3} {
        if {[lsearch -exact $args -data_pins] >= 0} {set suffix /D
        } elseif {[lsearch -exact $args -output_pins] >= 0} {set suffix /Q
        } elseif {[lsearch -exact $args -clock_pins] >= 0} {set suffix /GATE
        } else {lappend result [dict get $::graph_mock::instances $name]; continue}
        lappend result [dict get $::graph_mock::pins $name$suffix]
    }
    return $result
}
namespace eval sta {}
proc sta::find_delays {} {set ::graph_mock::calculated 1}
proc sta::time_ui_sta {value} {
    return [expr {$value * ($::graph_mock::scenario eq "units_ps" ? 1e-12 : 1e-9)}]
}
proc sta::scenes {} {return $::graph_mock::scene_list}
proc sta::network_leaf_instances {} {return [dict values $::graph_mock::instances]}
proc sta::find_port_pins_matching {pattern regexp nocase} {
    return [lmap name {i_clk i_din o_dout} {dict get $::graph_mock::pins $name}]
}
proc sta::vertex_iterator {} {
    set vertices {}
    dict for {name pin} $::graph_mock::pins {
        lappend vertices {*}[dict get $::graph_mock::objects $pin vertices]
    }
    return [graph_mock::iterator $vertices]
}
proc sta::edge_disable_reason {edge} {return [dict get $::graph_mock::objects $edge disabled]}
proc sta::timing_arc_disabled {edge arc} {return 0}

foreach scene {S_tt S_slow} {
    dict set ::graph_mock::objects $scene [dict create type scene full_name $scene]
}
foreach name {i_clk i_din o_dout} direction {input input output} {graph_mock::pin $name $direction}
set lib [graph_mock::make library [dict create full_name mock_tt]]
foreach name {L1 L2 L3 U_INPUT U_LONG_HEAD U_LONG_MIDDLE U_LONG_TAIL U_SHORT U_MERGE U_TAIL U_OUTPUT} {
    set cell [graph_mock::make liberty_cell [dict create library $lib]]
    set inst [graph_mock::make instance [dict create full_name $name ref_name mock_$name liberty_cell $cell pins {}]]
    dict set ::graph_mock::instances $name $inst
    if {[string match L* $name]} {
        foreach port {D GATE Q} direction {input input output} {graph_mock::pin $name/$port $direction $inst}
        graph_mock::edge $name/D $name/Q {Latch D to Q} {100 110} {101 111}
        graph_mock::edge $name/GATE $name/Q {Latch En to Q} {200 210} {201 211}
        graph_mock::edge $name/GATE $name/D setup {0.2 0.2} {0.21 0.21}
        graph_mock::edge $name/GATE $name/D hold {-0.02 -0.02} {-0.01 -0.01}
    } else {
        set ports {A X}; set directions {input output}
        if {$name eq "U_MERGE"} {set ports {A B X}; set directions {input input output}}
        foreach port $ports direction $directions {graph_mock::pin $name/$port $direction $inst}
    }
}
foreach {from to} {
    i_clk L1/GATE i_clk L2/GATE i_clk L3/GATE
    i_din U_INPUT/A U_INPUT/X L1/D
    L1/Q U_LONG_HEAD/A U_LONG_HEAD/X U_LONG_MIDDLE/A
    U_LONG_MIDDLE/X U_LONG_TAIL/A U_LONG_TAIL/X U_MERGE/A
    L1/Q U_SHORT/A U_SHORT/X U_MERGE/B U_MERGE/X L2/D
    L2/Q U_TAIL/A U_TAIL/X L3/D L3/Q U_OUTPUT/A U_OUTPUT/X o_dout
} {graph_mock::edge $from $to wire}
foreach {name rise fall} {
    U_INPUT {0.01 0.03} {0.02 0.04}
    U_LONG_HEAD {0.10 0.20} {0.11 0.21}
    U_LONG_MIDDLE {0.12 0.22} {0.13 0.23}
    U_LONG_TAIL {0.14 0.24} {0.15 0.25}
    U_SHORT {0.03 0.07} {0.04 0.08}
    U_TAIL {0.01 0.03} {0.02 0.04}
    U_OUTPUT {0.01 0.03} {0.02 0.04}
} {graph_mock::edge $name/A $name/X combinational $rise $fall}
graph_mock::edge U_MERGE/A U_MERGE/X combinational {0.16 0.26} {0.17 0.27}
graph_mock::edge U_MERGE/B U_MERGE/X combinational {0.05 0.09} {0.06 0.10}

proc graph_mock::configure {scenario} {
    set ::graph_mock::scenario $scenario
    switch -- $scenario {
        normal - nonfinite - missing_slew - units_ps {}
        scenes {set ::graph_mock::scene_list {S_tt S_slow}}
        cycle {graph_mock::edge U_LONG_MIDDLE/X U_LONG_HEAD/A wire}
        feedback {graph_mock::edge U_OUTPUT/X L1/D wire}
        disconnected {graph_mock::pin U_INPUT/UNCONNECTED input [dict get $::graph_mock::instances U_INPUT]}
        no_vertex {
            set pin [graph_mock::pin U_INPUT/UNCONNECTED input [dict get $::graph_mock::instances U_INPUT]]
            dict set ::graph_mock::objects $pin vertices {}
        }
        empty_arcs {
            dict for {id object} $::graph_mock::objects {
                if {[dict get $object type] eq "edge" && [dict get $object role] eq "combinational"} {
                    dict set ::graph_mock::objects $id timing_arcs {}
                    break
                }
            }
        }
        invert - disabled - net_delay {
            dict for {id object} $::graph_mock::objects {
                if {[dict get $object type] ne "edge"} {continue}
                set from_pin [[dict get $object from] pin]
                set name [get_full_name $from_pin]
                if {$scenario eq "disabled" && $name eq "U_SHORT/A"} {
                    dict set ::graph_mock::objects $id disabled constraint
                }
                if {$scenario eq "invert" && $name eq "U_SHORT/A"} {
                    foreach arc [dict get $object timing_arcs] {
                        set rf [$arc from_edge_name]
                        dict set ::graph_mock::objects $arc to_edge_name [expr {$rf eq "rise" ? "fall" : "rise"}]
                    }
                }
                if {$scenario eq "net_delay" && [dict get $object role] eq "wire"} {
                    foreach arc [dict get $object timing_arcs] {
                        dict set ::graph_mock::objects $arc min 0.001
                        dict set ::graph_mock::objects $arc max 0.003
                    }
                }
            }
        }
        default {error "Unknown mock scenario $scenario"}
    }
}
