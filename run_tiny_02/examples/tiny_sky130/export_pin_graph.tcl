# OpenSTA 3.1 graph export. Values are the frozen graph-based analysis (GBA)
# delays/slews; they are not path-based recharacterization or Boolean sensitization.
namespace eval pin_graph {}

proc pin_graph::number {value context} {
    if {![string is double -strict $value] ||
        [catch {expr {double($value) > -Inf && double($value) < Inf}} finite] || !$finite} {
        error "Non-finite or unavailable $context: $value"
    }
    return [format %.17g $value]
}

proc pin_graph::seconds_ns {value context} {
    number $value $context
    return [number [expr {$value * 1e9}] $context]
}

proc pin_graph::table {directory name header rows} {
    set stream [open [file join $directory $name.tsv] {WRONLY CREAT EXCL}]
    try {
        fconfigure $stream -encoding utf-8 -translation lf
        foreach row [linsert $rows 0 $header] {
            set fields {}
            foreach value $row {
                lappend fields "\"[string map [list \" \"\"] $value]\""
            }
            puts $stream [join $fields \t]
        }
    } finally {
        close $stream
    }
}

# Cut at sequential boundaries before sorting: latch feedback is allowed,
# but a combinational loop must not disappear behind OpenSTA's loop breaking.
proc pin_graph::topological {vertices edges} {
    set degree {}; set outgoing {}
    foreach v $vertices {dict set degree $v 0; dict set outgoing $v {}}
    foreach e $edges {
        lassign $e id from to
        dict incr degree $to
        dict lappend outgoing $from $to
    }
    set ready {}
    foreach v $vertices {if {[dict get $degree $v] == 0} {lappend ready $v}}
    set order {}
    for {set i 0} {$i < [llength $ready]} {incr i} {
        set v [lindex $ready $i]
        lappend order $v
        foreach to [dict get $outgoing $v] {
            dict incr degree $to -1
            if {[dict get $degree $to] == 0} {lappend ready $to}
        }
    }
    if {[llength $order] != [llength $vertices]} {
        error "Combinational cycle in complete graph; boundary extraction is not valid"
    }
    return $order
}

proc pin_graph::extract {order combinational samples launches captures} {
    set outgoing {}
    foreach e $combinational {
        lassign $e id from to
        dict lappend outgoing $from $id
    }
    set paths {}; set envelopes {}; set path_count 0
    # Keep transition states separate through reconvergence and inverting arcs.
    # shortcut: witnesses copy path lists; use predecessor arrays for large designs.
    dict for {condition arcs} $samples {
        lassign $condition scene analysis
        dict for {source source_name} $launches {
            foreach source_rf {rise fall} {
                set best [dict create [list $source $source_rf] [list 0.0 [list $source] {} {}]]
                foreach v $order {
                    foreach rf {rise fall} {
                        set key [list $v $rf]
                        if {![dict exists $best $key]} {continue}
                        lassign [dict get $best $key] delay vertices edge_ids arc_ids
                        if {$v ne $source && [dict exists $captures $v]} {
                            set target_name [dict get $captures $v]
                            set path_id p[incr path_count]
                            lappend paths [list $path_id $source_name $target_name $scene $analysis \
                                $source_rf $rf [number $delay path_sum] [join $vertices ,] \
                                [join $edge_ids ,] [join $arc_ids ,]]
                            set pair [list $source_name $target_name $scene]
                            if {![dict exists $envelopes $pair $analysis] ||
                                ($analysis eq "min" && $delay < [lindex [dict get $envelopes $pair $analysis] 0]) ||
                                ($analysis eq "max" && $delay > [lindex [dict get $envelopes $pair $analysis] 0])} {
                                dict set envelopes $pair $analysis [list $delay $path_id]
                            }
                            continue
                        }
                        if {![dict exists $outgoing $v]} {continue}
                        foreach edge_id [dict get $outgoing $v] {
                            if {![dict exists $arcs $edge_id]} {continue}
                            foreach arc [dict get $arcs $edge_id] {
                                lassign $arc arc_id from_rf to_rf to arc_delay
                                if {$from_rf ne $rf} {continue}
                                set value [expr {$delay + $arc_delay}]
                                number $value path_sum
                                set next [list $to $to_rf]
                                if {![dict exists $best $next] ||
                                    ($analysis eq "min" && $value < [lindex [dict get $best $next] 0]) ||
                                    ($analysis eq "max" && $value > [lindex [dict get $best $next] 0])} {
                                    dict set best $next [list $value [concat $vertices [list $to]] \
                                        [concat $edge_ids [list $edge_id]] [concat $arc_ids [list $arc_id]]]
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    set compressed {}; set edge_count 0
    foreach pair [lsort [dict keys $envelopes]] {
        if {![dict exists $envelopes $pair min] || ![dict exists $envelopes $pair max]} {
            error "Missing min/max analysis for boundary pair $pair"
        }
        lassign [dict get $envelopes $pair min] minimum min_path
        lassign [dict get $envelopes $pair max] maximum max_path
        if {$minimum > $maximum + 1e-9} {error "min exceeds max for boundary pair $pair"}
        lappend compressed [concat [list b[incr edge_count]] $pair \
            [list [number $minimum boundary_min] [number $maximum boundary_max] $min_path $max_path]]
    }
    if {![llength $compressed]} {error "No active adjacent Latch/IO boundary paths"}
    return [list $paths $compressed]
}

proc pin_graph::export {report_dir} {
    set destination [file join $report_dir pin_graph]
    if {[file exists $destination]} {error "Pin graph output already exists: $destination"}
    foreach command {vertex_iterator network_leaf_instances find_port_pins_matching find_delays \
                     scenes edge_disable_reason timing_arc_disabled time_ui_sta} {
        if {![llength [info commands ::sta::$command]]} {
            error "OpenSTA 3.1 graph API required: sta::$command is missing"
        }
    }
    sta::find_delays
    set scenes [sta::scenes]
    if {![llength $scenes]} {error "No OpenSTA analysis scenes"}

    # Collect network pins as well as graph vertices, including unconnected pins.
    set network_pins {}
    foreach pin [sta::find_port_pins_matching * 0 0] {
        dict set network_pins [get_full_name $pin] $pin
    }
    foreach instance [sta::network_leaf_instances] {
        set iter [$instance pin_iterator]
        try {
            while {[$iter has_next]} {
                set pin [$iter next]
                if {![$pin is_pwr_gnd]} {dict set network_pins [get_full_name $pin] $pin}
            }
        } finally {$iter finish}
    }
    set clock_sources {}
    foreach clock [get_clocks *] {
        foreach pin [$clock sources] {dict set clock_sources [get_full_name $pin] 1}
    }
    set boundaries {}
    foreach {option role} {-data_pins latch_d -output_pins latch_q -clock_pins latch_clock} {
        foreach pin [all_registers -level_sensitive $option] {
            dict set boundaries [get_full_name $pin] [list [get_full_name [$pin instance]] $role]
        }
    }
    if {[llength [all_registers -edge_triggered -cells]]} {
        error "Boundary extraction supports Latch/IO, not edge-triggered cells"
    }
    set pins {}; set pin_ids {}; set pin_count 0
    foreach name [lsort [dict keys $network_pins]] {
        set pin [dict get $network_pins $name]
        set id n[incr pin_count]
        dict set pin_ids $name $id
        set instance {}; set cell {}; set library {}; set boundary {}; set boundary_role {}
        set direction [get_property $pin direction]
        if {[$pin is_top_level_port]} {
            if {[dict exists $clock_sources $name]} {
                set boundary_role clock_source
            } elseif {$direction in {input output}} {
                set boundary $name; set boundary_role $direction
            } else {error "Unsupported bidirectional top-level port $name"}
        } else {
            set inst [$pin instance]
            set instance [get_full_name $inst]
            set cell [get_property $inst ref_name]
            set lib_cell [$inst liberty_cell]
            if {$lib_cell eq "NULL"} {error "Missing Liberty cell for $instance"}
            set library [get_full_name [get_property $lib_cell library]]
            if {[dict exists $boundaries $name]} {
                lassign [dict get $boundaries $name] boundary boundary_role
            }
        }
        set net [$pin net]
        if {$net eq "NULL"} {set net {}} else {set net [get_full_name $net]}
        lappend pins [list $id $name $direction $instance $cell $library [$pin port_name] \
            $net $boundary $boundary_role]
    }
    set vertex_objects {}; set iter [sta::vertex_iterator]
    try {
        while {[$iter has_next]} {
            set v [$iter next]
            set name [get_full_name [$v pin]]
            if {![dict exists $pin_ids $name]} {error "Graph pin is missing from network: $name"}
            dict set vertex_objects [list $name [$v is_bidirect_driver]] $v
        }
    } finally {$iter finish}
    set vertices {}; set vertex_ids {}; set vertex_by_id {}; set launches {}; set captures {}
    set vertex_count 0
    foreach key [lsort [dict keys $vertex_objects]] {
        lassign $key name bidirect
        set v [dict get $vertex_objects $key]
        set id v[incr vertex_count]
        dict set vertex_ids $v $id
        dict set vertex_by_id $id $v
        lappend vertices [list $id [dict get $pin_ids $name] $bidirect]
        set role {}; set boundary {}
        if {[dict exists $boundaries $name]} {lassign [dict get $boundaries $name] boundary role}
        set pin [dict get $network_pins $name]
        if {[$pin is_top_level_port] && ![dict exists $clock_sources $name]} {
            set role [get_property $pin direction]; set boundary $name
        }
        if {$role in {input latch_q}} {dict set launches $id $boundary}
        if {$role in {output latch_d}} {dict set captures $id $boundary}
    }
    # Stable IDs use names/roles/conditions, never SWIG pointer values.
    set edge_objects {}
    dict for {id v} $vertex_by_id {
        set iter [$v out_edge_iterator]
        try {
            while {[$iter has_next]} {
                set edge [$iter next]
                set key [list $id [dict get $vertex_ids [$edge to]] [$edge role] \
                    [$edge cond] [$edge mode_name] [$edge mode_value]]
                if {[dict exists $edge_objects $key]} {error "Indistinguishable parallel timing edges: $key"}
                dict set edge_objects $key $edge
            }
        } finally {$iter finish}
    }
    set edges {}; set combinational {}; set delays {}; set slews {}; set samples {}
    set edge_count 0; set arc_count 0
    foreach scene $scenes {
        set scene_name [get_full_name $scene]
        foreach analysis {min max} {
            dict set samples [list $scene_name $analysis] {}
            dict for {id v} $vertex_by_id {
                foreach rf {rise fall} {
                    # The scene-specific string is in user units, not internal seconds.
                    set value [$v slew_scenes_string $rf [list $scene] $analysis 0 12]
                    set value [seconds_ns [sta::time_ui_sta $value] "slew $id/$scene_name/$analysis/$rf"]
                    dict set slews [list $id $scene_name $analysis $rf] $value
                }
            }
        }
    }
    foreach key [lsort [dict keys $edge_objects]] {
        lassign $key from to role cond mode_name mode_value
        set edge [dict get $edge_objects $key]
        set id e[incr edge_count]
        set kind [expr {$role eq "wire" ? "net" : "cell"}]
        set disabled [sta::edge_disable_reason $edge]
        lappend edges [list $id $from $to $kind $role $cond $mode_name $mode_value $disabled]
        set is_comb [expr {$role in {wire combinational}}]
        if {$is_comb} {lappend combinational [list $id $from $to]}
        set timing_arcs [$edge timing_arcs]
        if {![llength $timing_arcs]} {error "Timing edge has no arcs: $key"}
        foreach arc $timing_arcs {
            set arc_id a[incr arc_count]
            set from_rf [$arc from_edge_name]; set to_rf [$arc to_edge_name]
            if {$from_rf ni {rise fall} || $to_rf ni {rise fall}} {
                error "Unsupported transition on $id: $from_rf -> $to_rf"
            }
            foreach scene $scenes {
                set scene_name [get_full_name $scene]
                foreach analysis {min max} {
                    set status calculated; set value {}
                    if {$disabled ne "" || [sta::timing_arc_disabled $edge $arc]} {
                        set status disabled
                    } elseif {($role in {setup {latch setup}} && $analysis eq "min") ||
                              ($role in {hold {latch hold}} && $analysis eq "max")} {
                        set status not_applicable
                    } else {
                        set value [seconds_ns [$edge arc_delay $arc $scene $analysis] \
                            "arc $id/$arc_id/$scene_name/$analysis"]
                    }
                    lappend delays [list $arc_id $id $from_rf $to_rf $scene_name $analysis $status $value \
                        [dict get $slews [list $from $scene_name $analysis $from_rf]] \
                        [dict get $slews [list $to $scene_name $analysis $to_rf]]]
                    if {$is_comb && $status eq "calculated"} {
                        set condition [list $scene_name $analysis]
                        set active [dict get $samples $condition]
                        dict lappend active $id [list $arc_id $from_rf $to_rf $to $value]
                        dict set samples $condition $active
                    }
                }
            }
        }
    }
    set order [topological [dict keys $vertex_by_id] $combinational]
    lassign [extract $order $combinational $samples $launches $captures] paths compressed
    set slew_rows {}
    dict for {key value} $slews {lappend slew_rows [concat $key [list $value]]}
    set manifest [list [list schema_version 1] [list time_unit ns] \
        [list analysis_scope {all sta::scenes in the current mode, min/max, rise/fall}] \
        [list delay_semantics {stored GBA arc delay at the analyzed operating point}] \
        [list slew_semantics {stored vertex slew; not an individual incoming arc's output slew}] \
        [list boundary_semantics {adjacent Latch Q / data input to Latch D / data output; no latch, clock or external IO delay}] \
        [list path_semantics {transition-consistent extrema of frozen active combinational arcs; not Boolean-sensitized PBA}] \
        [list pins [llength $pins]] [list vertices [llength $vertices]] \
        [list edges [llength $edges]] [list arcs $arc_count] [list boundary_edges [llength $compressed]]]
    set staging [file join $report_dir .pin_graph_[pid]_[clock clicks]]
    file mkdir $staging
    table $staging pins {pin_id name direction instance cell library port net boundary boundary_role} $pins
    table $staging vertices {vertex_id pin_id bidirect_driver} $vertices
    table $staging edges {edge_id from_vertex to_vertex kind role condition mode_name mode_value disabled_reason} $edges
    table $staging arc_delays {arc_id edge_id from_rf to_rf scene analysis status delay_ns from_vertex_slew_ns to_vertex_slew_ns} $delays
    table $staging slews {vertex_id scene analysis rf slew_ns} $slew_rows
    table $staging boundary_paths {path_id source target scene analysis from_rf to_rf delay_ns vertex_ids edge_ids arc_ids} $paths
    table $staging boundary_edges {boundary_edge_id source target scene min_delay_ns max_delay_ns min_path_id max_path_id} $compressed
    table $staging manifest {key value} $manifest
    # Publish only a complete export; an interrupted run retains a clearly temporary directory.
    file rename $staging $destination
    puts "Complete pin graph written to $destination ([llength $pins] pins, [llength $edges] edges, [llength $compressed] boundary edges)"
    return $destination
}
