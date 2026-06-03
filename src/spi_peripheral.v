`default_nettype none

module spi_peripheral (
    input wire rst_n,
    input wire clk,

    input wire CS,
    input wire SCLK,
    input wire COPI,
    output wire CIPO,

    output reg [7:0] en_reg_out_7_0,
    output reg [7:0] en_reg_out_15_8,
    output reg [7:0] en_reg_pwm_7_0,
    output reg [7:0] en_reg_pwm_15_8,
    output reg [7:0] pwm_duty_cycle
);
    //No CIPO in this design
    assign CIPO = 1'bz;

    //For dealing with peripheral input
    reg sclk_ff_1, sclk_ff_2;
    reg copi_ff_1, copi_ff_2;

    //For keeping track of how much data has come in
    reg [3:0] counter;
    reg activate_counter;

    reg [14:0] buffer;

    always @(posedge clk or negedge rst_n) begin
        //Resetting mechanism
        if(!rst_n) begin
            en_reg_out_7_0  <= 8'h0;
            en_reg_out_15_8 <= 8'h0;
            en_reg_pwm_7_0  <= 8'h0;
            en_reg_pwm_15_8 <= 8'h0;
            pwm_duty_cycle  <= 8'h0;

            sclk_ff_1 <= 1'b0;
            sclk_ff_2 <= 1'b0;

            counter <= 4'b0000;
            activate_counter <= 1'b1;

            buffer <= 15'h0;

        end else if(!CS) begin
            //Feeding sclk through 2 ff's for edge detection
            sclk_ff_1 <= SCLK;
            sclk_ff_2 <= sclk_ff_1;

            //Feeding copi through 2 ff's so copi is in timing with sclk
            copi_ff_1 <= COPI;
            copi_ff_2 <= copi_ff_1;

            //Checking if sclk is posedge
            if((sclk_ff_1 == 0) & (sclk_ff_2 == 1)) begin
                if(activate_counter == 1) begin
                    //Adding to counter and preventing continual adding
                    counter <= counter + 1;
                    activate_counter <= 1'b0;

                    //Adding data to buffer
                    buffer <= {buffer[14:0], copi_ff_2};
                end else ;
            end else ;

            //I have two design choices with where to put this
            //if statement, if I put it in the above if block
            //if would mean 1 additional rising edge would be
            //needed to update the registers, as I don't belive
            //this is going to always happen I chose to put the
            //if statement outside of this statment but this
            //means that if any other module wants to update
            //the reg's it could very quickly be over rided.
            //Since no other module uses these reg's I will put
            //the if statement below the above one
            if(counter == 4'b1111) begin
                if(buffer[14] == 1'b1) begin
                    case(buffer[13:7])
                        7'h0: en_reg_out_7_0  <= {buffer[6:0],copi_ff_2};
                        7'h1: en_reg_out_15_8 <= {buffer[6:0],copi_ff_2};
                        7'h2: en_reg_pwm_7_0  <= {buffer[6:0],copi_ff_2};
                        7'h3: en_reg_pwm_15_8 <= {buffer[6:0],copi_ff_2};
                        7'h4: pwm_duty_cycle <= {buffer[6:0],copi_ff_2};
                        default: ;
                    endcase
                end
            end

            //Checking if sclk is negedge
            if ((sclk_ff_1 == 1) & (sclk_ff_2 == 0)) begin
                activate_counter <= 1'b1;
            end
        end
    end
endmodule