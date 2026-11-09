#include <cassert>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <boost/property_tree/json_parser.hpp>
#include "timing_graph.hpp"

int main(int argc, char **argv)
{
    assert(argc == 4); // tiny.blif.out, latch_timing.json, scratch directory
    namespace fs = std::filesystem;
    using boost::property_tree::ptree;
    const fs::path scratch = argv[3];
    fs::create_directories(scratch);
    ptree legacyInput;
    boost::property_tree::read_json(argv[2], legacyInput);
    legacyInput.put("schema_version", 2);
    legacyInput.erase("io_constraints");
    const string timingPath = (scratch / "timing_v2.json").string();
    boost::property_tree::write_json(timingPath, legacyInput);
    DelayGraph dg;
    double initial = 0.0;
    assert(readDelayGraph(argv[1], dg, initial));
    readLatchTiming(timingPath, dg);
    const map<string, LatchTiming> expected{
        {"L1", {0.19198, -0.015695, 0.218371, 0.327392, 0.273814, 0.315624}},
        {"L2", {0.192707, -0.018286, 0.21217, 0.313652, 0.264169, 0.300269}},
        {"L3", {0.191975, -0.015689, 0.20878, 0.312064, 0.264169, 0.300269}}};
    const auto verify = [&] {
        assert(boost::num_vertices(dg) == 4);
        for (size_t k = 0; k < boost::num_vertices(dg); ++k)
        {
            const auto &t = dg[k].timing;
            const auto e = k == kIoNodeIdx ? LatchTiming{} : expected.at(dg[k].name);
            assert(fabs(t.tsu - e.tsu) < 1e-12 && fabs(t.thd - e.thd) < 1e-12);
            assert(fabs(t.tdqMin - e.tdqMin) < 1e-12 && fabs(t.tdqMax - e.tdqMax) < 1e-12);
            assert(fabs(t.tcqMin - e.tcqMin) < 1e-12 && fabs(t.tcqMax - e.tcqMax) < 1e-12);
            const auto &checks = dg[k].clockChecks;
            assert(checks.characterized == (k != kIoNodeIdx));
            if (k != kIoNodeIdx)
            {
                assert(checks.minPulseHigh && fabs(*checks.minPulseHigh - 0.23101371836734694) < 1e-12);
                assert(!checks.minPulseLow);
            }
        }
    };
    verify();
    Graph g;
    getMcrGraph(dg, g, initial);
    for (size_t k = 1; k < boost::num_vertices(dg); ++k)
    {
        const auto dq = boost::edge(mcrIndex(k, kMcrLatestD), mcrIndex(k, kMcrLatestA), g);
        const auto cq = boost::edge(mcrIndex(k, kMcrD), mcrIndex(k, kMcrSkew), g);
        assert(dq.second && fabs(g[dq.first].weight + dg[k].timing.tdqMax) < 1e-12);
        assert(cq.second && fabs(g[cq.first].weight + dg[k].timing.tcqMin + initial / 2) < 1e-12);
    }

    for (double duty : {0.5, 0.4, 0.25, 0.01})
    {
        getMcrGraph(dg, g, initial, duty);
        for (size_t k = 0; k < boost::num_vertices(dg); ++k)
            for (const auto variable : {kMcrD, kMcrLatestD})
            {
                const auto cq = boost::edge(mcrIndex(k, variable), mcrIndex(k, kMcrSkew), g);
                const double delay = variable == kMcrD ? dg[k].timing.tcqMin : dg[k].timing.tcqMax;
                assert(cq.second && fabs(g[cq.first].weight + delay + (1.0 - duty) * initial) < 1e-12);
                assert(fabs(g[cq.first].delay + 2.0 * (1.0 - duty)) < 1e-12);
            }
    }
    DelayGraph isolated;
    boost::add_vertex(NodeIdx{kIoNodeIdx, {}, "IO"}, isolated);
    boost::add_vertex(NodeIdx{1, LatchTiming{0.1, 0.0, 0.1, 0.2, 0.1, 0.2}, "L1"}, isolated);
    vector<double> potential(kMcrVarsPerNode * 2, 0.0);
    potential[mcrIndex(0, kMcrD)] = potential[mcrIndex(0, kMcrLatestD)] = 1.0;
    potential[mcrIndex(1, kMcrA)] = potential[mcrIndex(1, kMcrLatestA)] = 0.1;
    potential[mcrIndex(1, kMcrD)] = 0.6;
    potential[mcrIndex(1, kMcrLatestD)] = 0.7;
    assert(mcrScheduleViolation(isolated, 1.0, potential) < 1e-12);
    assert(fabs(mcrScheduleViolation(isolated, 1.0, potential, 0.25) - 0.25) < 1e-12);
    potential[mcrIndex(1, kMcrD)] = 0.85;
    potential[mcrIndex(1, kMcrLatestD)] = 0.95;
    assert(mcrScheduleViolation(isolated, 1.0, potential, 0.25) < 1e-12);
    isolated[1].clockChecks.characterized = true;
    isolated[1].clockChecks.minPulseHigh = 0.3;
    isolated[1].clockChecks.minPulseLow = 0.8;
    assert(fabs(mcrPulsePeriodMin(isolated, 0.25) - 1.2) < 1e-12);
    assert(fabs(mcrPulsePeriodMin(isolated, 0.5) - 1.6) < 1e-12);
    assert(fabs(mcrScheduleViolation(isolated, 1.0, potential, 0.25) - 0.2) < 1e-12);
    for (size_t k = 0; k < 2; ++k)
        potential[mcrIndex(k, kMcrD)] = potential[mcrIndex(k, kMcrLatestD)] = 2.0;
    assert(mcrScheduleViolation(isolated, 1.2, potential, 0.25) < 1e-12);
    assert(mcrScheduleViolation(isolated, 1.21, potential, 0.25) < 1e-12);
    getMcrGraph(isolated, g, 1.0, 0.25);
    const auto pulseEdge = boost::edge(mcrIndex(0, kMcrSkew), mcrIndex(0, kMcrSkew), g);
    assert(pulseEdge.second && fabs(g[pulseEdge.first].weight + 0.2) < 1e-12);
    assert(fabs(g[pulseEdge.first].delay - 2.0) < 1e-12);
    isolated[1].clockChecks.minPulseHigh = numeric_limits<double>::max();
    assert(isinf(mcrPulsePeriodMin(isolated, 0.25)));
    bool overflowRejected = false;
    try { getMcrGraph(isolated, g, 1.0, 0.25); }
    catch (const std::invalid_argument &) { overflowRejected = true; }
    assert(overflowRejected);
    for (double duty : {0.0, -0.1, 0.500001, numeric_limits<double>::quiet_NaN(),
                        numeric_limits<double>::infinity()})
    {
        bool rejectedDuty = false;
        try { getMcrGraph(dg, g, initial, duty); }
        catch (const std::invalid_argument &) { rejectedDuty = true; }
        assert(rejectedDuty);
        assert(isinf(mcrScheduleViolation(isolated, 1.0, potential, duty)));
    }

    const fs::path reordered = scratch / "reordered.out";
    {
        std::ofstream out(reordered);
        out << "L2 L3 0.072031 0.070218\nL3 OUTPUT 0.095645 0.088638\n"
               "L1 L2 0.336778 0.177533\nINPUT L1 0.083593 0.074577\n";
    }
    assert(readDelayGraph(reordered.string(), dg, initial));
    assert(dg[1].name == "L2" && dg[3].name == "L1");
    readLatchTiming(timingPath, dg);
    verify();

    ptree original;
    boost::property_tree::read_json(timingPath, original);
    const fs::path invalid = scratch / "invalid.json";
    const auto reject = [&](const ptree &data) {
        boost::property_tree::write_json(invalid.string(), data);
        bool rejected = false;
        try { readLatchTiming(invalid.string(), dg); }
        catch (const std::exception &) { rejected = true; }
        assert(rejected);
        verify(); // Failed loads must preserve the previous timing.
    };
    auto data = original;
    data.put("units.time", "ps");
    reject(data);
    data = original;
    data.put("schema_version", 4);
    reject(data);
    data = original;
    data.get_child("nodes").pop_back();
    reject(data);
    data = original;
    data.get_child("nodes").push_back(*data.get_child("nodes").begin());
    reject(data);
    data = original;
    data.get_child("nodes").front().second.put("instance", "UNKNOWN");
    reject(data);
    data = original;
    data.get_child("nodes").front().second.get_child("parameters_ns").erase("tsu");
    reject(data);
    for (const string value : {"-1", "1", "nan", "1e999"})
    {
        data = original;
        data.get_child("nodes").front().second.put("parameters_ns.tdqMin", value);
        reject(data);
    }
    data = original;
    data.get_child("nodes").front().second.put("parameters_ns.tcqMax", 0.0);
    reject(data);
    for (const string value : {"-1", "nan", "1e999", "abc"})
    {
        data = original;
        data.get_child("nodes").front().second.put("clock_checks_ns.min_pulse_width_high", value);
        reject(data);
    }
    data = original;
    data.get_child("nodes").front().second.erase("clock_checks_ns");
    reject(data);
    data = original;
    data.get_child("nodes").front().second.get_child("clock_checks_ns").erase("min_pulse_width_low");
    reject(data);
    data = original;
    data.get_child("nodes").front().second.add("clock_checks_ns.min_pulse_width_high", 0.2);
    reject(data);
    bool rejected = false;
    try { readLatchTiming((scratch / "missing.json").string(), dg); }
    catch (const std::exception &) { rejected = true; }
    assert(rejected);
    verify();
    data = original;
    data.put("schema_version", 1);
    reject(data); // v1 must not silently ignore pulse-width fields.
    for (auto &entry : data.get_child("nodes"))
        entry.second.erase("clock_checks_ns");
    const fs::path legacy = scratch / "legacy_v1.json";
    boost::property_tree::write_json(legacy.string(), data);
    readLatchTiming(legacy.string(), dg);
    assert(mcrPulsePeriodMin(dg, 0.5) == 0.0);
    for (size_t k = 1; k < boost::num_vertices(dg); ++k)
        assert(!dg[k].clockChecks.characterized && !dg[k].clockChecks.minPulseHigh && !dg[k].clockChecks.minPulseLow);
    readLatchTiming(timingPath, dg);
    verify();
    std::cout << "Per-instance latch timing, duty-cycle and pulse-width checks passed\n";
}
