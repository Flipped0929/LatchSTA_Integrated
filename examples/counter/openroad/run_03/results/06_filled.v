module counter (clk,
    en,
    rst_n,
    count,
    VDD,
    VSS);
 input clk;
 input en;
 input rst_n;
 output [3:0] count;
 inout VDD;
 inout VSS;

 wire _01_;
 wire _02_;
 wire _03_;
 wire _04_;
 wire _05_;
 wire _06_;
 wire clknet_0_clk;
 wire clknet_1_0__leaf_clk;
 wire clknet_1_1__leaf_clk;
 wire [3:0] _00_;
 wire [3:0] master;
 wire [3:0] slave;

 sky130_fd_sc_hd__fill_8 FILL_0_1 ();
 sky130_fd_sc_hd__fill_8 FILL_0_17 ();
 sky130_fd_sc_hd__fill_4 FILL_0_25 ();
 sky130_fd_sc_hd__fill_1 FILL_0_29 ();
 sky130_fd_sc_hd__fill_8 FILL_0_31 ();
 sky130_fd_sc_hd__fill_8 FILL_0_39 ();
 sky130_fd_sc_hd__fill_8 FILL_0_47 ();
 sky130_fd_sc_hd__fill_4 FILL_0_55 ();
 sky130_fd_sc_hd__fill_1 FILL_0_59 ();
 sky130_fd_sc_hd__fill_8 FILL_0_61 ();
 sky130_fd_sc_hd__fill_8 FILL_0_69 ();
 sky130_fd_sc_hd__fill_8 FILL_0_77 ();
 sky130_fd_sc_hd__fill_8 FILL_0_9 ();
 sky130_fd_sc_hd__fill_8 FILL_10_1 ();
 sky130_fd_sc_hd__fill_8 FILL_10_17 ();
 sky130_fd_sc_hd__fill_4 FILL_10_25 ();
 sky130_fd_sc_hd__fill_1 FILL_10_29 ();
 sky130_fd_sc_hd__fill_8 FILL_10_31 ();
 sky130_fd_sc_hd__fill_4 FILL_10_39 ();
 sky130_fd_sc_hd__fill_2 FILL_10_43 ();
 sky130_fd_sc_hd__fill_1 FILL_10_45 ();
 sky130_fd_sc_hd__fill_2 FILL_10_82 ();
 sky130_fd_sc_hd__fill_1 FILL_10_84 ();
 sky130_fd_sc_hd__fill_8 FILL_10_9 ();
 sky130_fd_sc_hd__fill_8 FILL_11_1 ();
 sky130_fd_sc_hd__fill_8 FILL_11_17 ();
 sky130_fd_sc_hd__fill_8 FILL_11_25 ();
 sky130_fd_sc_hd__fill_8 FILL_11_33 ();
 sky130_fd_sc_hd__fill_4 FILL_11_41 ();
 sky130_fd_sc_hd__fill_2 FILL_11_45 ();
 sky130_fd_sc_hd__fill_1 FILL_11_47 ();
 sky130_fd_sc_hd__fill_2 FILL_11_61 ();
 sky130_fd_sc_hd__fill_8 FILL_11_75 ();
 sky130_fd_sc_hd__fill_2 FILL_11_83 ();
 sky130_fd_sc_hd__fill_8 FILL_11_9 ();
 sky130_fd_sc_hd__fill_8 FILL_12_1 ();
 sky130_fd_sc_hd__fill_8 FILL_12_17 ();
 sky130_fd_sc_hd__fill_4 FILL_12_25 ();
 sky130_fd_sc_hd__fill_1 FILL_12_29 ();
 sky130_fd_sc_hd__fill_8 FILL_12_31 ();
 sky130_fd_sc_hd__fill_8 FILL_12_39 ();
 sky130_fd_sc_hd__fill_8 FILL_12_47 ();
 sky130_fd_sc_hd__fill_2 FILL_12_55 ();
 sky130_fd_sc_hd__fill_1 FILL_12_57 ();
 sky130_fd_sc_hd__fill_8 FILL_12_70 ();
 sky130_fd_sc_hd__fill_4 FILL_12_78 ();
 sky130_fd_sc_hd__fill_2 FILL_12_82 ();
 sky130_fd_sc_hd__fill_1 FILL_12_84 ();
 sky130_fd_sc_hd__fill_8 FILL_12_9 ();
 sky130_fd_sc_hd__fill_8 FILL_13_1 ();
 sky130_fd_sc_hd__fill_8 FILL_13_17 ();
 sky130_fd_sc_hd__fill_4 FILL_13_25 ();
 sky130_fd_sc_hd__fill_1 FILL_13_29 ();
 sky130_fd_sc_hd__fill_8 FILL_13_31 ();
 sky130_fd_sc_hd__fill_8 FILL_13_39 ();
 sky130_fd_sc_hd__fill_4 FILL_13_47 ();
 sky130_fd_sc_hd__fill_2 FILL_13_51 ();
 sky130_fd_sc_hd__fill_1 FILL_13_53 ();
 sky130_fd_sc_hd__fill_8 FILL_13_61 ();
 sky130_fd_sc_hd__fill_8 FILL_13_69 ();
 sky130_fd_sc_hd__fill_8 FILL_13_77 ();
 sky130_fd_sc_hd__fill_8 FILL_13_9 ();
 sky130_fd_sc_hd__fill_8 FILL_1_1 ();
 sky130_fd_sc_hd__fill_8 FILL_1_17 ();
 sky130_fd_sc_hd__fill_8 FILL_1_25 ();
 sky130_fd_sc_hd__fill_8 FILL_1_33 ();
 sky130_fd_sc_hd__fill_8 FILL_1_41 ();
 sky130_fd_sc_hd__fill_8 FILL_1_49 ();
 sky130_fd_sc_hd__fill_2 FILL_1_57 ();
 sky130_fd_sc_hd__fill_1 FILL_1_59 ();
 sky130_fd_sc_hd__fill_8 FILL_1_61 ();
 sky130_fd_sc_hd__fill_8 FILL_1_69 ();
 sky130_fd_sc_hd__fill_8 FILL_1_77 ();
 sky130_fd_sc_hd__fill_8 FILL_1_9 ();
 sky130_fd_sc_hd__fill_8 FILL_2_1 ();
 sky130_fd_sc_hd__fill_8 FILL_2_17 ();
 sky130_fd_sc_hd__fill_4 FILL_2_25 ();
 sky130_fd_sc_hd__fill_1 FILL_2_29 ();
 sky130_fd_sc_hd__fill_8 FILL_2_31 ();
 sky130_fd_sc_hd__fill_8 FILL_2_39 ();
 sky130_fd_sc_hd__fill_8 FILL_2_47 ();
 sky130_fd_sc_hd__fill_8 FILL_2_55 ();
 sky130_fd_sc_hd__fill_8 FILL_2_63 ();
 sky130_fd_sc_hd__fill_8 FILL_2_71 ();
 sky130_fd_sc_hd__fill_4 FILL_2_79 ();
 sky130_fd_sc_hd__fill_2 FILL_2_83 ();
 sky130_fd_sc_hd__fill_8 FILL_2_9 ();
 sky130_fd_sc_hd__fill_8 FILL_3_1 ();
 sky130_fd_sc_hd__fill_8 FILL_3_17 ();
 sky130_fd_sc_hd__fill_8 FILL_3_25 ();
 sky130_fd_sc_hd__fill_8 FILL_3_33 ();
 sky130_fd_sc_hd__fill_8 FILL_3_41 ();
 sky130_fd_sc_hd__fill_8 FILL_3_49 ();
 sky130_fd_sc_hd__fill_2 FILL_3_57 ();
 sky130_fd_sc_hd__fill_1 FILL_3_59 ();
 sky130_fd_sc_hd__fill_8 FILL_3_61 ();
 sky130_fd_sc_hd__fill_8 FILL_3_69 ();
 sky130_fd_sc_hd__fill_8 FILL_3_77 ();
 sky130_fd_sc_hd__fill_8 FILL_3_9 ();
 sky130_fd_sc_hd__fill_8 FILL_4_1 ();
 sky130_fd_sc_hd__fill_8 FILL_4_17 ();
 sky130_fd_sc_hd__fill_4 FILL_4_25 ();
 sky130_fd_sc_hd__fill_1 FILL_4_29 ();
 sky130_fd_sc_hd__fill_8 FILL_4_31 ();
 sky130_fd_sc_hd__fill_8 FILL_4_39 ();
 sky130_fd_sc_hd__fill_8 FILL_4_47 ();
 sky130_fd_sc_hd__fill_8 FILL_4_55 ();
 sky130_fd_sc_hd__fill_8 FILL_4_63 ();
 sky130_fd_sc_hd__fill_8 FILL_4_71 ();
 sky130_fd_sc_hd__fill_4 FILL_4_79 ();
 sky130_fd_sc_hd__fill_2 FILL_4_83 ();
 sky130_fd_sc_hd__fill_8 FILL_4_9 ();
 sky130_fd_sc_hd__fill_8 FILL_5_1 ();
 sky130_fd_sc_hd__fill_8 FILL_5_17 ();
 sky130_fd_sc_hd__fill_8 FILL_5_25 ();
 sky130_fd_sc_hd__fill_8 FILL_5_33 ();
 sky130_fd_sc_hd__fill_8 FILL_5_41 ();
 sky130_fd_sc_hd__fill_8 FILL_5_49 ();
 sky130_fd_sc_hd__fill_2 FILL_5_57 ();
 sky130_fd_sc_hd__fill_1 FILL_5_59 ();
 sky130_fd_sc_hd__fill_4 FILL_5_61 ();
 sky130_fd_sc_hd__fill_1 FILL_5_65 ();
 sky130_fd_sc_hd__fill_8 FILL_5_72 ();
 sky130_fd_sc_hd__fill_4 FILL_5_80 ();
 sky130_fd_sc_hd__fill_1 FILL_5_84 ();
 sky130_fd_sc_hd__fill_8 FILL_5_9 ();
 sky130_fd_sc_hd__fill_8 FILL_6_1 ();
 sky130_fd_sc_hd__fill_8 FILL_6_17 ();
 sky130_fd_sc_hd__fill_4 FILL_6_25 ();
 sky130_fd_sc_hd__fill_1 FILL_6_29 ();
 sky130_fd_sc_hd__fill_8 FILL_6_31 ();
 sky130_fd_sc_hd__fill_8 FILL_6_39 ();
 sky130_fd_sc_hd__fill_4 FILL_6_47 ();
 sky130_fd_sc_hd__fill_8 FILL_6_75 ();
 sky130_fd_sc_hd__fill_2 FILL_6_83 ();
 sky130_fd_sc_hd__fill_8 FILL_6_9 ();
 sky130_fd_sc_hd__fill_8 FILL_7_1 ();
 sky130_fd_sc_hd__fill_8 FILL_7_17 ();
 sky130_fd_sc_hd__fill_8 FILL_7_25 ();
 sky130_fd_sc_hd__fill_8 FILL_7_33 ();
 sky130_fd_sc_hd__fill_8 FILL_7_41 ();
 sky130_fd_sc_hd__fill_2 FILL_7_49 ();
 sky130_fd_sc_hd__fill_1 FILL_7_65 ();
 sky130_fd_sc_hd__fill_8 FILL_7_69 ();
 sky130_fd_sc_hd__fill_8 FILL_7_77 ();
 sky130_fd_sc_hd__fill_8 FILL_7_9 ();
 sky130_fd_sc_hd__fill_8 FILL_8_1 ();
 sky130_fd_sc_hd__fill_8 FILL_8_17 ();
 sky130_fd_sc_hd__fill_4 FILL_8_25 ();
 sky130_fd_sc_hd__fill_1 FILL_8_29 ();
 sky130_fd_sc_hd__fill_8 FILL_8_31 ();
 sky130_fd_sc_hd__fill_8 FILL_8_39 ();
 sky130_fd_sc_hd__fill_4 FILL_8_47 ();
 sky130_fd_sc_hd__fill_2 FILL_8_51 ();
 sky130_fd_sc_hd__fill_1 FILL_8_53 ();
 sky130_fd_sc_hd__fill_2 FILL_8_60 ();
 sky130_fd_sc_hd__fill_1 FILL_8_62 ();
 sky130_fd_sc_hd__fill_8 FILL_8_71 ();
 sky130_fd_sc_hd__fill_4 FILL_8_79 ();
 sky130_fd_sc_hd__fill_2 FILL_8_83 ();
 sky130_fd_sc_hd__fill_8 FILL_8_9 ();
 sky130_fd_sc_hd__fill_8 FILL_9_1 ();
 sky130_fd_sc_hd__fill_8 FILL_9_17 ();
 sky130_fd_sc_hd__fill_8 FILL_9_25 ();
 sky130_fd_sc_hd__fill_8 FILL_9_33 ();
 sky130_fd_sc_hd__fill_8 FILL_9_41 ();
 sky130_fd_sc_hd__fill_1 FILL_9_49 ();
 sky130_fd_sc_hd__fill_8 FILL_9_77 ();
 sky130_fd_sc_hd__fill_8 FILL_9_9 ();
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
    .GATE_N(clknet_1_0__leaf_clk));
 sky130_fd_sc_hd__dlxtn_1 _18_ (.D(_00_[1]),
    .Q(master[1]),
    .GATE_N(clknet_1_1__leaf_clk));
 sky130_fd_sc_hd__dlxtn_1 _19_ (.D(_00_[2]),
    .Q(master[2]),
    .GATE_N(clknet_1_1__leaf_clk));
 sky130_fd_sc_hd__dlxtn_1 _20_ (.D(_00_[3]),
    .Q(master[3]),
    .GATE_N(clknet_1_1__leaf_clk));
 sky130_fd_sc_hd__dlxtp_1 _21_ (.D(master[0]),
    .Q(slave[0]),
    .GATE(clknet_1_0__leaf_clk));
 sky130_fd_sc_hd__dlxtp_1 _22_ (.D(master[1]),
    .Q(slave[1]),
    .GATE(clknet_1_0__leaf_clk));
 sky130_fd_sc_hd__dlxtp_1 _23_ (.D(master[2]),
    .Q(slave[2]),
    .GATE(clknet_1_0__leaf_clk));
 sky130_fd_sc_hd__dlxtp_1 _24_ (.D(master[3]),
    .Q(slave[3]),
    .GATE(clknet_1_1__leaf_clk));
 sky130_fd_sc_hd__clkbuf_4 clkbuf_0_clk (.A(clk),
    .X(clknet_0_clk));
 sky130_fd_sc_hd__clkbuf_4 clkbuf_1_0__f_clk (.A(clknet_0_clk),
    .X(clknet_1_0__leaf_clk));
 sky130_fd_sc_hd__clkbuf_4 clkbuf_1_1__f_clk (.A(clknet_0_clk),
    .X(clknet_1_1__leaf_clk));
 sky130_fd_sc_hd__clkbuf_1 clkload0 (.A(clknet_1_0__leaf_clk));
 assign count[0] = slave[0];
 assign count[1] = slave[1];
 assign count[2] = slave[2];
 assign count[3] = slave[3];
endmodule
