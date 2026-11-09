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
    if (!rst_n)
        master <= 4'b0000;
    else if (!clk)
        master <= next_count;
end

always @(*) begin
    if (!rst_n)
        slave <= 4'b0000;
    else if (clk)
        slave <= master;
end

assign count = slave;

endmodule
