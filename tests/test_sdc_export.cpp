#include "sdc_export.hpp"
#include "howard.hpp"
#include "LP.hpp"
#include <cassert>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <iterator>
#include <limits>

int main(int argc, char **argv)
{
    assert(argc == 4);
    namespace fs = std::filesystem;
    const fs::path scratch(argv[3]);
    fs::create_directories(scratch);
    DelayGraph dg;
    double initial = 0.0;
    assert(readDelayGraph(argv[1], dg, initial));
    readLatchTiming(argv[2], dg);
    assert(dg[boost::graph_bundle].staConditions);
    for (double duty : {0.5, 0.4})
    {
        Graph graph;
        getMcrGraph(dg, graph, initial, duty);
        Howard solver(graph, boost::num_vertices(graph), initial, 1e-10);
        solver.run();
        const auto howard = solver.getResult();
        McrResult lp;
        mcrLP(dg, initial, lp, duty);
        const auto output = scratch / (duty == 0.5 ? "candidate_howard.sdc" : "candidate_duty40.sdc");
        fs::remove(output);
        exportHowardSdc(output.string(), dg, initial, duty, howard, lp);
        std::ifstream file(output);
        const std::string content((std::istreambuf_iterator<char>(file)), {});
        assert(content.find("solver=Howard") != std::string::npos);
        assert(content.find("set_clock_latency -clock [get_clocks {clk}]") != std::string::npos);
        assert(content.find("set_false_path") == std::string::npos);
        assert(std::fabs(howard.period - 3.541155) < 1e-7);
        bool rejected = false;
        try { exportHowardSdc(output.string(), dg, initial, duty, howard, lp); }
        catch (const std::exception &) { rejected = true; }
        assert(rejected);
        std::ifstream unchanged(output);
        assert(content == std::string((std::istreambuf_iterator<char>(unchanged)), {}));
        const auto invalid = scratch / "rejected.sdc";
        fs::remove(invalid);
        const auto reject = [&](const DelayGraph &badGraph, const McrResult &h, const McrResult &l) {
            bool failed = false;
            try { exportHowardSdc(invalid.string(), badGraph, initial, duty, h, l); }
            catch (const std::exception &) { failed = true; }
            assert(failed && !fs::exists(invalid));
        };
        auto bad = howard;
        bad.status = McrStatus::NumericalError; reject(dg, bad, lp);
        bad = howard; bad.skew[1] += 0.1; reject(dg, bad, lp);
        bad = howard; bad.potential.clear(); reject(dg, bad, lp);
        bad = howard; bad.period = std::numeric_limits<double>::quiet_NaN(); reject(dg, bad, lp);
        bad = lp; bad.status = McrStatus::SolverError; reject(dg, howard, bad);
        bad = lp; bad.period += 0.01; reject(dg, howard, bad);
        auto badGraph = dg;
        badGraph[boost::graph_bundle].staConditions.reset(); reject(badGraph, howard, lp);
        badGraph = dg;
        badGraph[boost::graph_bundle].staConditions->clockName = "bad;exec"; reject(badGraph, howard, lp);
        badGraph = dg;
        badGraph[boost::graph_bundle].staConditions->outputLoad = -1.0; reject(badGraph, howard, lp);
    }
    std::cout << "Howard SDC export and rejection checks passed\n";
}
