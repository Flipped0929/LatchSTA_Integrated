module counter (
    input wire clk,
    input wire rst_n,
    input wire en,
    output wire [3:0] count
);

reg [3:0] master;
reg [3:0] slave;

wire [3:0] next_count;

assign next_count = en ? (slave + 4'd1) : slave;

always @(*) begin
    if(!clk)
        master <= next_count & {4{rst_n}};
end

always @(*) begin
    if(clk)
        slave <= master;
end

assign count = slave;

endmodule
