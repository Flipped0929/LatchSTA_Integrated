module \$_DLATCH_N_ (E, D, Q);
    input E, D;
    output Q;

    sky130_fd_sc_hd__dlxtn_1 _TECHMAP_REPLACE_ (
        .GATE_N(E), .D(D), .Q(Q)
    );
endmodule

module \$_DLATCH_P_ (E, D, Q);
    input E, D;
    output Q;

    sky130_fd_sc_hd__dlxtp_1 _TECHMAP_REPLACE_ (
        .GATE(E), .D(D), .Q(Q)
    );
endmodule