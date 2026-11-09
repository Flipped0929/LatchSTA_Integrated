# OpenDB geometry/RC inspection only; does not load or invoke STA.
set audit_db $::env(COUNTER_RCX_AUDIT_DB)
set audit_prefix $::env(COUNTER_RCX_AUDIT_PREFIX)
read_db $audit_db
set block [ord::get_db_block]
set geom_fd [open ${audit_prefix}_geometry.tsv w]
puts $geom_fd "net\tkind\tlayer\tvia\txmin\tymin\txmax\tymax"
set rc_fd [open ${audit_prefix}_rc.tsv w]
puts $rc_fd "net\trsegs\tcap_nodes\tresistance_sum_ohm\tground_cap_sum_ff"
set itr [odb::new_dbWirePathItr]
set path [odb::new_dbWirePath]
set shape [odb::new_dbWirePathShape]
foreach net [$block getNets] {
    if {[$net getSigType] in {POWER GROUND}} {continue}
    set wire [$net getWire]
    if {$wire eq "NULL"} {error "Missing routed wire for [$net getName]"}
    odb::dbWirePathItr_begin $itr $wire
    while {[odb::dbWirePathItr_getNextPath $itr $path]} {
        while {[odb::dbWirePathItr_getNextShape $itr $shape]} {
            set geom [odb::dbWirePathShape_shape_get $shape]
            set layer [odb::dbShape_getTechLayer $geom]
            set via [odb::dbShape_getTechVia $geom]
            set block_via [odb::dbShape_getVia $geom]
            set layer_name ""
            set via_name ""
            if {$layer ne "NULL"} {set layer_name [odb::dbTechLayer_getName $layer]}
            if {$via ne "NULL"} {set via_name [odb::dbTechVia_getName $via]}
            if {$block_via ne "NULL"} {set via_name [odb::dbVia_getName $block_via]}
            set kind segment
            if {[odb::dbShape_isVia $geom]} {set kind via}
            puts $geom_fd "[$net getName]\t$kind\t$layer_name\t$via_name\t[odb::dbShape_xMin $geom]\t[odb::dbShape_yMin $geom]\t[odb::dbShape_xMax $geom]\t[odb::dbShape_yMax $geom]"
        }
    }
    set cap 0.0
    set resistance 0.0
    foreach rseg [$net getRSegs] {
        set resistance [expr {$resistance + [$rseg getResistance 0]}]
        set cap [expr {$cap + [$rseg getGroundCapacitance 0]}]
    }
    puts $rc_fd "[$net getName]\t[llength [$net getRSegs]]\t[llength [$net getCapNodes]]\t$resistance\t$cap"
}
close $geom_fd
close $rc_fd
odb::delete_dbWirePathItr $itr
odb::delete_dbWirePath $path
odb::delete_dbWirePathShape $shape
puts "OPENDB_GEOMETRY_AND_RC_AUDIT_COMPLETE: $audit_prefix"
