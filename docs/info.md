<!---

This file is used to generate your project datasheet. Please fill in the information below and delete any unused
sections.

You can also include images in this folder and reference them in the markdown. Each image must be less than
512 kb in size, and the combined size of all images must be less than 1 MB.
-->

## How it works

Explain how your project works
The project takes in input signals which are used to write to registers. These registers then are used to modify output signals and the pwm peripheral duty cycle

## How to test

Explain how to use your project
Cocotb is used for all testing. I enter in input signals through dut.input_name.value and then run clock cycles and see if the output is the correct result using the assert function


## External hardware

List external hardware used in your project (e.g. PMOD, LED display, etc), if any
No external hardware is used. I did however make a two ff sychronizer for the project for cross domain clocking