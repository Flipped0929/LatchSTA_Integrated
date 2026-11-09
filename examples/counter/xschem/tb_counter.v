`timescale 1ns/1ps
module tb_counter;
  reg clk = 1, rst_n = 0, en = 0;
  supply1 VPWR;
  supply0 VGND;
  wire [3:0] count, mapped_count, rtl_count;
  reg [3:0] expected = 0;
  reg valid = 0;
  integer cycles = 0;
  integer state, reset_case, enable_case, k;
  counter dut (.clk(clk), .rst_n(rst_n), .en(en), .count(count), .VPWR(VPWR), .VGND(VGND));
  counter_mapped ref_mapped (.clk(clk), .rst_n(rst_n), .en(en), .count(mapped_count));
  counter_rtl ref_rtl (.clk(clk), .rst_n(rst_n), .en(en), .count(rtl_count));

  task check;
    begin
      if (count !== expected || mapped_count !== expected || rtl_count !== expected)
        $fatal(1, "cycle=%0d clk=%b rst_n=%b en=%b expected=%h schematic=%h mapped=%h rtl=%h",
               cycles, clk, rst_n, en, expected, count, mapped_count, rtl_count);
    end
  endtask

  task step(input reg reset_value, input reg enable_value);
    begin
      // Inputs change in the high phase, away from the closing edge of master.
      rst_n = reset_value;
      en = enable_value;
      #3;
      if (valid) check;
      clk = 0;
      #5;
      if (valid) check; // Slave must hold throughout the low phase.
      expected = !reset_value ? 4'd0 : expected + enable_value;
      clk = 1;
      #5;
      cycles = cycles + 1;
      valid = 1;
      check;
    end
  endtask

  initial begin
    #1;
    step(0, 0);
    // Cover every output state with all four (rst_n, en) combinations.
    for (state = 0; state < 16; state = state + 1)
      for (reset_case = 0; reset_case < 2; reset_case = reset_case + 1)
        for (enable_case = 0; enable_case < 2; enable_case = enable_case + 1) begin
          step(0, 0);
          for (k = 0; k < state; k = k + 1) step(1, 1);
          step(reset_case, enable_case);
        end
    // Several wraps, consecutive holds, and reset priority while enabled.
    repeat (40) step(1, 1);
    repeat (5) step(1, 0);
    step(0, 1);
    step(1, 0);
    $display("PASS: %0d cycles; all 64 state/control cases; wrap, hold, reset priority and latch phases", cycles);
    $finish;
  end
endmodule
