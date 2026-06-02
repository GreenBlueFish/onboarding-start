`default_nettype none

module Two_FF_Synchronizer(  
    input wire clk,
    input wire async_in,
    output wire sync_out
);

reg ff1;
reg ff2;

always @(posedge clk) begin
    ff1 <= async_in;
    ff2 <= ff1;
end

assign sync_out = ff2;

endmodule

