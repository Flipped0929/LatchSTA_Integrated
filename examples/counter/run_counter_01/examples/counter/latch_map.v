// Yosys technology mapping only; keep the internal-cell port names unchanged.
module \$_DLATCH_NN0_ (E, R, D, Q);
    input E;
    input R;
    input D;
    output Q;

    sky130_fd_sc_hd__dlrtn_1 _TECHMAP_REPLACE_ (
        .GATE_N(E),
        .RESET_B(R),
        .D(D),
        .Q(Q)
    );
endmodule

module \$_DLATCH_PN0_ (E, R, D, Q);
    input E;
    input R;
    input D;
    output Q;

    sky130_fd_sc_hd__dlrtp_1 _TECHMAP_REPLACE_ (
        .GATE(E),
        .RESET_B(R),
        .D(D),
        .Q(Q)
    );
endmodule
