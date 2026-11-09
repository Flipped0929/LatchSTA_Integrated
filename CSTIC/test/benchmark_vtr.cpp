/**
 * @file benchmark_vtr.cpp
 * @brief 找到对应的函数并执行
 * @details
 * @author kxzhu
 * @version 1.0
 * @date 2021-08-16
*/

#include "benchmark_vtr.h"
#include "benchmark.h"
#include <cstdlib>
#include <fstream>



using namespace std;


bool benchmark_vtr(const string& s)
{
    string command = "mkdir " + s;
    system(command.c_str());
    string command = "cd " + s;
    string command = "~/Documents/vtr-verilog-to-routing-8.0.0/vpr/vpr ~/Documents/vtr-verilog-to-routing-8.0.0/vtr_flow/arch/timing/k6_frac_N10_mem32K_40nm.xml ~/Documents/vtr-verilog-to-routing-8.0.0/vtr_flow/benchmarks/blif/" + s + "--timing_report_detail aggregated";
    system(command.c_str());
    char outfile[255];
    sprintf(outfile, "%s.blif.out", s);
    benchmarkConversion("report_timing.hold.rpt","hold.out");
    benchmarkConversion("report_timing.setup.rpt","setup.out");
    printrsltfile("setup.out","hold.out",outfile);
    return ture;
}