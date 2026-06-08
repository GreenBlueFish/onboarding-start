# SPDX-FileCopyrightText: © 2024 Tiny Tapeout
# SPDX-License-Identifier: Apache-2.0

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge
from cocotb.triggers import ClockCycles
from cocotb.types import LogicArray
from cocotb.utils import get_sim_time

async def await_half_sclk(dut):
    """Wait for the SCLK signal to go high or low."""
    start_time = cocotb.utils.get_sim_time(units="ns")
    while True:
        await ClockCycles(dut.clk, 1)
        # Wait for half of the SCLK period (10 us)
        if (start_time + 100*100*0.5) < cocotb.utils.get_sim_time(units="ns"):
            break
    return

def ui_in_logicarray(ncs, bit, sclk):
    """Setup the ui_in value as a LogicArray."""
    return LogicArray(f"00000{ncs}{bit}{sclk}")

async def send_spi_transaction(dut, r_w, address, data):
    """
    Send an SPI transaction with format:
    - 1 bit for Read/Write
    - 7 bits for address
    - 8 bits for data
    
    Parameters:
    - r_w: boolean, True for write, False for read
    - address: int, 7-bit address (0-127)
    - data: LogicArray or int, 8-bit data
    """
    # Convert data to int if it's a LogicArray
    if isinstance(data, LogicArray):
        data_int = int(data)
    else:
        data_int = data
    # Validate inputs
    if address < 0 or address > 127:
        raise ValueError("Address must be 7-bit (0-127)")
    if data_int < 0 or data_int > 255:
        raise ValueError("Data must be 8-bit (0-255)")
    # Combine RW and address into first byte
    first_byte = (int(r_w) << 7) | address
    # Start transaction - pull CS low
    sclk = 0
    ncs = 0
    bit = 0
    # Set initial state with CS low
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    await ClockCycles(dut.clk, 1)
    # Send first byte (RW + Address)
    for i in range(8):
        bit = (first_byte >> (7-i)) & 0x1
        # SCLK low, set COPI
        sclk = 0
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
        # SCLK high, keep COPI
        sclk = 1
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
    # Send second byte (Data)
    for i in range(8):
        bit = (data_int >> (7-i)) & 0x1
        # SCLK low, set COPI
        sclk = 0
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
        # SCLK high, keep COPI
        sclk = 1
        dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
        await await_half_sclk(dut)
    # End transaction - return CS high
    sclk = 0
    ncs = 1
    bit = 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    await ClockCycles(dut.clk, 600)
    return ui_in_logicarray(ncs, bit, sclk)

async def pwm_signal_info(dut):
    # Wait for bit 0 to go low first, so we start from a known state
    initial_time = get_sim_time(units="ns")
    while dut.uo_out.value == 1:
        await RisingEdge(dut.clk)  
        if(get_sim_time(units="ns") >= float(initial_time + 1000000)):
            return 0,0,0,100

    # Wait for first rising edge on bit 0 of uo_out
    initial_time = get_sim_time(units="ns")
    while dut.uo_out.value == 0:
        await RisingEdge(dut.clk)
        if(get_sim_time(units="ns") >= float(initial_time + 1000000)):
            return 0,0,0,0
    rising_edge_time_1 = get_sim_time(units="ns")

    # Wait for falling edge on bit 0
    while dut.uo_out.value == 1:
        await RisingEdge(dut.clk)
    falling_edge_time = get_sim_time(units="ns")

    # Wait for second rising edge on bit 0
    while dut.uo_out.value == 0:
        await RisingEdge(dut.clk)
    rising_edge_time_2 = get_sim_time(units="ns")

    period = rising_edge_time_2 - rising_edge_time_1
    frequency = 1e9 / period
    high_time = falling_edge_time - rising_edge_time_1
    duty_cycle = (high_time / period) * 100

    return period, frequency, high_time, duty_cycle

@cocotb.test()
async def test_spi(dut):
    dut._log.info("Start SPI test")

    # Set the clock period to 100 ns (10 MHz)
    clock = Clock(dut.clk, 100, units="ns")
    cocotb.start_soon(clock.start())

    # Reset
    dut._log.info("Reset")
    dut.ena.value = 1
    ncs = 1
    bit = 0
    sclk = 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)

    dut._log.info("Test project behavior")
    dut._log.info("Write transaction, address 0x00, data 0xF0")
    ui_in_val = await send_spi_transaction(dut, 1, 0x00, 0xF0)  # Write transaction
    assert dut.uo_out.value == 0xF0, f"Expected 0xF0, got {dut.uo_out.value}"
    await ClockCycles(dut.clk, 1000) 

    dut._log.info("Write transaction, address 0x01, data 0xCC")
    ui_in_val = await send_spi_transaction(dut, 1, 0x01, 0xCC)  # Write transaction
    assert dut.uio_out.value == 0xCC, f"Expected 0xCC, got {dut.uio_out.value}"
    await ClockCycles(dut.clk, 100)

    dut._log.info("Write transaction, address 0x30 (invalid), data 0xAA")
    ui_in_val = await send_spi_transaction(dut, 1, 0x30, 0xAA)
    await ClockCycles(dut.clk, 100)

    dut._log.info("Read transaction (invalid), address 0x00, data 0xBE")
    ui_in_val = await send_spi_transaction(dut, 0, 0x30, 0xBE)
    assert dut.uo_out.value == 0xF0, f"Expected 0xF0, got {dut.uo_out.value}"
    await ClockCycles(dut.clk, 100)
    
    dut._log.info("Read transaction (invalid), address 0x41 (invalid), data 0xEF")
    ui_in_val = await send_spi_transaction(dut, 0, 0x41, 0xEF)
    await ClockCycles(dut.clk, 100)

    dut._log.info("Write transaction, address 0x02, data 0xFF")
    ui_in_val = await send_spi_transaction(dut, 1, 0x02, 0xFF)  # Write transaction
    await ClockCycles(dut.clk, 100)

    dut._log.info("Write transaction, address 0x04, data 0xCF")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0xCF)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("Write transaction, address 0x04, data 0xFF")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0xFF)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("Write transaction, address 0x04, data 0x00")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0x00)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("Write transaction, address 0x04, data 0x01")
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0x01)  # Write transaction
    await ClockCycles(dut.clk, 30000)

    dut._log.info("SPI test completed successfully")

@cocotb.test()
async def test_pwm_freq(dut):
    # debugging code
    # for name in dir(dut):
    #    print(name)

    # Set the clock period to 100 ns (10 MHz)
    clock = Clock(dut.clk, 100, units="ns")
    cocotb.start_soon(clock.start())

    # Reset
    dut._log.info("Reset")
    dut.ena.value = 1
    ncs = 1
    bit = 0
    sclk = 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)

    # Write your test here
    dut._log.info("PWM Frequency test")
    
    # setting the PWM duty cycle reg to 128 to 
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0x1A)
    await ClockCycles(dut.clk, 100)

    # setting the 1st bit of the en_reg_pwm_7_0 to a 1
    ui_in_val = await send_spi_transaction(dut, 1, 0x02, 0x01)
    await ClockCycles(dut.clk, 100)

    # setting the 1st bit of the en_reg_out_7_0 to a 1
    ui_in_val = await send_spi_transaction(dut, 1, 0x00, 0x01)
    await ClockCycles(dut.clk, 100)

    # testing a few different duty cycles to see if changes the frequency (I know the duty cycle has no influence over the frequency but I may as well make the test)

    # duty cycle = 10
    for i in range(10):
        period, frequency, high_time, duty_cycle = await pwm_signal_info(dut)
        assert 2970 <= frequency <= 3030
        await ClockCycles(dut.clk, 10)

    # duty cycle = 50
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0x80)
    await ClockCycles(dut.clk, 100)
    for i in range(10):
        period, frequency, high_time, duty_cycle = await pwm_signal_info(dut)
        assert 2970 <= frequency <= 3030
        await ClockCycles(dut.clk, 10)

    # duty cycle = 90
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0xE7)
    await ClockCycles(dut.clk, 100)
    for i in range(10):
        period, frequency, high_time, duty_cycle = await pwm_signal_info(dut)
        assert 2970 <= frequency <= 3030
        await ClockCycles(dut.clk, 10)

    dut._log.info("PWM Frequency test completed successfully")

@cocotb.test()
async def test_pwm_duty(dut):
    # Set the clock period to 100 ns (10 MHz)
    clock = Clock(dut.clk, 100, units="ns")
    cocotb.start_soon(clock.start())

    # Reset
    dut._log.info("Reset")
    dut.ena.value = 1
    ncs = 1
    bit = 0
    sclk = 0
    dut.ui_in.value = ui_in_logicarray(ncs, bit, sclk)
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 5)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 5)

    # Write your test here
    dut._log.info("PWM Duty Cycle test")

    # setting the PWM duty cycle reg to 128 to 
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0x00)
    await ClockCycles(dut.clk, 100)

    # setting the 1st bit of the en_reg_pwm_7_0 to a 1
    ui_in_val = await send_spi_transaction(dut, 1, 0x02, 0x01)
    await ClockCycles(dut.clk, 100)

    # setting the 1st bit of the en_reg_out_7_0 to a 1
    ui_in_val = await send_spi_transaction(dut, 1, 0x00, 0x01)
    await ClockCycles(dut.clk, 100)

    # duty cycle = 0
    for i in range(10):
        period, frequency, high_time, duty_cycle = await pwm_signal_info(dut)
        assert duty_cycle == 0, "expected 0"
        await ClockCycles(dut.clk, 10)

    # duty cycle = 50
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0x80)
    await ClockCycles(dut.clk, 100)
    for i in range(10):
        period, frequency, high_time, duty_cycle = await pwm_signal_info(dut)
        assert duty_cycle == 50, "expected 50"
        await ClockCycles(dut.clk, 10)

    # duty cylce = 100
    ui_in_val = await send_spi_transaction(dut, 1, 0x04, 0xFF)
    await ClockCycles(dut.clk, 100)
    for i in range(10):
        period, frequency, high_time, duty_cycle = await pwm_signal_info(dut)
        assert duty_cycle == 100, "expected 100"
        await ClockCycles(dut.clk, 10)

    dut._log.info("PWM Duty Cycle test completed successfully")
