`default_nettype none

module Two_FF_Synchronizer #(parameter width = 1) (  
    input wire clk,
    input wire [width-1:0] async_in,
    output reg [width-1:0] ff1,
    output wire [width-1:0] sync_out
);

//reg [width-1:0] ff1;
reg [width-1:0] ff2;

always @(posedge clk) begin
    ff1 <= async_in;
    ff2 <= ff1;
end

assign sync_out = ff2;

endmodule

