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
