`default_nettype none

module spi_peripheral (
    input rst_n,
    input clk,

    input CS,
    input SCLK,
    input COPI,
    output CIPO,

    output reg [7:0] en_reg_out_7_0,
    output reg [7:0] en_reg_out_15_8,
    output reg [7:0] en_reg_pwm_7_0,
    output reg [7:0] en_reg_pwm_15_8,
    output reg [7:0] pwm_duty_cycle
);

//No CIPO in this design
assign CIPO = 1'bz;

//For connection between clk ff and SCLK tffs
reg cross_domain_wire;

//tffs output
reg sync_out;
reg ff1_out;

Two_FF_Synchronizer #(.width(1)) tff (
    .clk(SCLK),
    .rst_n(rst_n),
    .async_in(cross_domain_wire),
    .ff1(ff1_out),
    .sync_out(sync_out)
);

//SPI is in mode 0
//CPOL = 0 -> idle state low
//CPHA = 0 -> sample on first edge
//Rising edge data sample
reg [15:0] buffer;
reg [3:0] counter;

reg [7:0] temp_en_reg_out_7_0;
reg [7:0] temp_en_reg_out_15_8;
reg [7:0] temp_en_reg_pwm_7_0;
reg [7:0] temp_en_reg_pwm_15_8;
reg [7:0] temp_pwm_duty_cycle;

always @(posedge SCLK) begin
    //If the chip select is on and the rst_n is off
    if((!CS) && (rst_n)) begin
        buffer <= {buffer[14:0], sync_out};
        counter <= counter + 1;
        
        if(counter == 4'b1111) begin
            //Checking if it is a write packet
            if(buffer[12] == 1'b1) begin
                case(buffer[11:5])
                    7'h00: temp_en_reg_out_7_0 <= {buffer[4:0], sync_out, ff1_out, cross_domain_wire};
                    7'h01: temp_en_reg_out_15_8 <= {buffer[4:0], sync_out, ff1_out, cross_domain_wire};
                    7'h02: temp_en_reg_pwm_7_0 <= {buffer[4:0], sync_out, ff1_out, cross_domain_wire};
                    7'h03: temp_en_reg_pwm_15_8 <= {buffer[4:0], sync_out, ff1_out, cross_domain_wire};
                    7'h04: temp_pwm_duty_cycle <= {buffer[4:0], sync_out, ff1_out, cross_domain_wire};
                endcase
            end
            counter <= 4'b0;
        end
    end

     //If CS is 1 or High Z
     if (CS) begin
        counter <= 4'b0000;
    end
end

always @(posedge clk or negedge rst_n) begin
    //Reset mechanism
    if(!rst_n) begin
        counter <= 4'b0000;
        buffer <= 16'h00;
        cross_domain_wire <= 1'b0;

        en_reg_out_7_0 <= {8{1'b0}};
        en_reg_out_15_8 <= {8{1'b0}};
        en_reg_pwm_7_0 <= {8{1'b0}};
        en_reg_pwm_15_8 <= {8{1'b0}};
        pwm_duty_cycle <= {8{1'b0}};
    end
    else begin
        //First ff set in clock domain crossing
        cross_domain_wire <= COPI;

        en_reg_out_7_0 <= temp_en_reg_out_7_0;
        en_reg_out_15_8 <= temp_en_reg_out_15_8;
        en_reg_pwm_7_0 <= temp_en_reg_pwm_7_0;
        en_reg_pwm_15_8 <= temp_en_reg_pwm_15_8;
        pwm_duty_cycle <= temp_pwm_duty_cycle;
    end
end

endmodule
