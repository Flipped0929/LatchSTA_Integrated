module counter (clk,
    en,
    rst_n,
    count);
 input clk;
 input en;
 input rst_n;
 output [3:0] count;

 wire _01_;
 wire _02_;
 wire _03_;
 wire _04_;
 wire _05_;
 wire _06_;
 wire [3:0] _00_;
 wire [3:0] master;
 wire [3:0] slave;

 sky130_fd_sc_hd__tapvpwrvgnd_1 PHY_EDGE_ROW_0_Left_14 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 PHY_EDGE_ROW_0_Right_0 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 PHY_EDGE_ROW_10_Left_24 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 PHY_EDGE_ROW_10_Right_10 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 PHY_EDGE_ROW_11_Left_25 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 PHY_EDGE_ROW_11_Right_11 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 PHY_EDGE_ROW_12_Left_26 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 PHY_EDGE_ROW_12_Right_12 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 PHY_EDGE_ROW_13_Left_27 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 PHY_EDGE_ROW_13_Right_13 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 PHY_EDGE_ROW_1_Left_15 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 PHY_EDGE_ROW_1_Right_1 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 PHY_EDGE_ROW_2_Left_16 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 PHY_EDGE_ROW_2_Right_2 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 PHY_EDGE_ROW_3_Left_17 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 PHY_EDGE_ROW_3_Right_3 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 PHY_EDGE_ROW_4_Left_18 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 PHY_EDGE_ROW_4_Right_4 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 PHY_EDGE_ROW_5_Left_19 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 PHY_EDGE_ROW_5_Right_5 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 PHY_EDGE_ROW_6_Left_20 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 PHY_EDGE_ROW_6_Right_6 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 PHY_EDGE_ROW_7_Left_21 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 PHY_EDGE_ROW_7_Right_7 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 PHY_EDGE_ROW_8_Left_22 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 PHY_EDGE_ROW_8_Right_8 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 PHY_EDGE_ROW_9_Left_23 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 PHY_EDGE_ROW_9_Right_9 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_0_28 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_0_29 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_10_39 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_11_40 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_12_41 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_13_42 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_13_43 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_1_30 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_2_31 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_3_32 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_4_33 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_5_34 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_6_35 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_7_36 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_8_37 ();
 sky130_fd_sc_hd__tapvpwrvgnd_1 TAP_TAPCELL_ROW_9_38 ();
 sky130_fd_sc_hd__o21ai_0 _07_ (.A1(en),
    .A2(slave[0]),
    .B1(rst_n),
    .Y(_01_));
 sky130_fd_sc_hd__a21oi_1 _08_ (.A1(en),
    .A2(slave[0]),
    .B1(_01_),
    .Y(_00_[0]));
 sky130_fd_sc_hd__and3_1 _09_ (.A(en),
    .B(slave[1]),
    .C(slave[0]),
    .X(_02_));
 sky130_fd_sc_hd__o21ai_0 _10_ (.A1(slave[2]),
    .A2(_02_),
    .B1(rst_n),
    .Y(_03_));
 sky130_fd_sc_hd__a21oi_1 _11_ (.A1(slave[2]),
    .A2(_02_),
    .B1(_03_),
    .Y(_00_[2]));
 sky130_fd_sc_hd__a41o_1 _12_ (.A1(slave[2]),
    .A2(en),
    .A3(slave[1]),
    .A4(slave[0]),
    .B1(slave[3]),
    .X(_04_));
 sky130_fd_sc_hd__nand2_1 _13_ (.A(rst_n),
    .B(_04_),
    .Y(_05_));
 sky130_fd_sc_hd__a31oi_1 _14_ (.A1(slave[2]),
    .A2(slave[3]),
    .A3(_02_),
    .B1(_05_),
    .Y(_00_[3]));
 sky130_fd_sc_hd__a21oi_1 _15_ (.A1(en),
    .A2(slave[0]),
    .B1(slave[1]),
    .Y(_06_));
 sky130_fd_sc_hd__nor3b_1 _16_ (.A(_02_),
    .B(_06_),
    .C_N(rst_n),
    .Y(_00_[1]));
 sky130_fd_sc_hd__dlxtn_1 _17_ (.D(_00_[0]),
    .Q(master[0]),
    .GATE_N(clk));
 sky130_fd_sc_hd__dlxtn_1 _18_ (.D(_00_[1]),
    .Q(master[1]),
    .GATE_N(clk));
 sky130_fd_sc_hd__dlxtn_1 _19_ (.D(_00_[2]),
    .Q(master[2]),
    .GATE_N(clk));
 sky130_fd_sc_hd__dlxtn_1 _20_ (.D(_00_[3]),
    .Q(master[3]),
    .GATE_N(clk));
 sky130_fd_sc_hd__dlxtp_1 _21_ (.D(master[0]),
    .Q(slave[0]),
    .GATE(clk));
 sky130_fd_sc_hd__dlxtp_1 _22_ (.D(master[1]),
    .Q(slave[1]),
    .GATE(clk));
 sky130_fd_sc_hd__dlxtp_1 _23_ (.D(master[2]),
    .Q(slave[2]),
    .GATE(clk));
 sky130_fd_sc_hd__dlxtp_1 _24_ (.D(master[3]),
    .Q(slave[3]),
    .GATE(clk));
 assign count[0] = slave[0];
 assign count[1] = slave[1];
 assign count[2] = slave[2];
 assign count[3] = slave[3];
endmodule
