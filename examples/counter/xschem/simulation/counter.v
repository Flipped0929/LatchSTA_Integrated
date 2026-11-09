// sch_path: /mnt/hgfs/LatchSTA_Code/code/examples/counter/xschem/counter.sch
module counter
(
  output wire [3:0] count,
  inout wire VPWR,
  inout wire VGND,
  input wire clk,
  input wire rst_n,
  input wire en
);
wire [3:0] master ;
wire [3:0] _00_ ;
wire _01_ ;
wire _02_ ;
wire _03_ ;
wire _04_ ;
wire _05_ ;
wire _06_ ;

sky130_fd_sc_hd__o21ai_0
x_07_ ( 
 .A1( en ),
 .A2( count[0] ),
 .B1( rst_n ),
 .Y( _01_ )
);


sky130_fd_sc_hd__a21oi_1
x_08_ ( 
 .A1( en ),
 .A2( count[0] ),
 .B1( _01_ ),
 .Y( _00_[0] )
);


sky130_fd_sc_hd__and3_1
x_09_ ( 
 .A( en ),
 .B( count[1] ),
 .C( count[0] ),
 .X( _02_ )
);


sky130_fd_sc_hd__o21ai_0
x_10_ ( 
 .A1( count[2] ),
 .A2( _02_ ),
 .B1( rst_n ),
 .Y( _03_ )
);


sky130_fd_sc_hd__a21oi_1
x_11_ ( 
 .A1( count[2] ),
 .A2( _02_ ),
 .B1( _03_ ),
 .Y( _00_[2] )
);


sky130_fd_sc_hd__a41o_1
x_12_ ( 
 .A1( count[2] ),
 .A2( en ),
 .A3( count[1] ),
 .A4( count[0] ),
 .B1( count[3] ),
 .X( _04_ )
);


sky130_fd_sc_hd__nand2_1
x_13_ ( 
 .A( rst_n ),
 .B( _04_ ),
 .Y( _05_ )
);


sky130_fd_sc_hd__a31oi_1
x_14_ ( 
 .A1( count[2] ),
 .A2( count[3] ),
 .A3( _02_ ),
 .B1( _05_ ),
 .Y( _00_[3] )
);


sky130_fd_sc_hd__a21oi_1
x_15_ ( 
 .A1( en ),
 .A2( count[0] ),
 .B1( count[1] ),
 .Y( _06_ )
);


sky130_fd_sc_hd__nor3b_1
x_16_ ( 
 .A( _02_ ),
 .B( _06_ ),
 .C_N( rst_n ),
 .Y( _00_[1] )
);


sky130_fd_sc_hd__dlxtn_1
x_17_ ( 
 .D( _00_[0] ),
 .GATE_N( clk ),
 .Q( master[0] )
);


sky130_fd_sc_hd__dlxtn_1
x_18_ ( 
 .D( _00_[1] ),
 .GATE_N( clk ),
 .Q( master[1] )
);


sky130_fd_sc_hd__dlxtn_1
x_19_ ( 
 .D( _00_[2] ),
 .GATE_N( clk ),
 .Q( master[2] )
);


sky130_fd_sc_hd__dlxtn_1
x_20_ ( 
 .D( _00_[3] ),
 .GATE_N( clk ),
 .Q( master[3] )
);


sky130_fd_sc_hd__dlxtp_1
x_21_ ( 
 .D( master[0] ),
 .GATE( clk ),
 .Q( count[0] )
);


sky130_fd_sc_hd__dlxtp_1
x_22_ ( 
 .D( master[1] ),
 .GATE( clk ),
 .Q( count[1] )
);


sky130_fd_sc_hd__dlxtp_1
x_23_ ( 
 .D( master[2] ),
 .GATE( clk ),
 .Q( count[2] )
);


sky130_fd_sc_hd__dlxtp_1
x_24_ ( 
 .D( master[3] ),
 .GATE( clk ),
 .Q( count[3] )
);

endmodule
