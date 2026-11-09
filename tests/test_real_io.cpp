#include <cassert>
#include <cmath>
#include <filesystem>
#include <iostream>
#include <boost/property_tree/json_parser.hpp>
#include "howard.hpp"

static McrResult solve(const DelayGraph &dg, double initial, double duty)
{
    Graph g;
    getMcrGraph(dg, g, initial, duty);
    Howard how(g, boost::num_vertices(g), initial, 1e-10);
    how.run();
    auto result = how.getResult();
    assert(result.status == McrStatus::Optimal);
    assert(mcrScheduleViolation(dg, result.period, result.potential, duty) <= kMcrFeasibilityEps);
    assert(mcrPotentialViolation(g, result.ratio, result.potential) <= kMcrFeasibilityEps);
    return result;
}

int main(int argc, char **argv)
{
    assert(argc == 4); // tiny.blif.out, schema-v3 JSON, scratch directory
    DelayGraph dg;
    double initial = 0.0;
    assert(readDelayGraph(argv[1], dg, initial));
    readLatchTiming(argv[2], dg);
    assert(boost::num_vertices(dg) == 6 && boost::degree(0, dg) == 0);
    assert(dg[4].kind == NodeIdx::Kind::Input && dg[4].name == "i_din");
    assert(dg[5].kind == NodeIdx::Kind::Output && dg[5].name == "o_dout");
    const auto original = dg;
    const auto &io = dg[boost::graph_bundle];
    assert(io.enabled && io.inputMin == 0.2 && io.inputMax == 1.0 && io.outputMin == -0.05 && io.outputMax == 1.0);
    // Every max path is data-limited at this solution: sum input budget, cell/comb delays and output budget.
    const double expected = 1.0 + 0.083593 + 0.327392 + 0.336778 + 0.313652 + 0.072031 + 0.312064 + 0.095645 + 1.0;
    McrResult baseline;
    for (double duty : {0.5, 0.4, 0.25})
    {
        auto result = solve(dg, initial, duty);
        assert(std::fabs(result.period - expected) < 1e-7);
        if (duty == 0.5) baseline = result;
        std::cout << "IO duty=" << duty << " period=" << result.period << " ns\n";
    }
    auto corrupted = baseline.potential;
    corrupted[mcrIndex(4, kMcrLatestD)] += 0.1;
    assert(mcrScheduleViolation(dg, baseline.period, corrupted) > 0.09);
    dg[boost::graph_bundle].inputMax += 0.5;
    assert(mcrScheduleViolation(dg, baseline.period, baseline.potential) > 0.49);
    assert(std::fabs(solve(dg, initial, 0.5).period - expected - 0.5) < 1e-7);
    dg = original;
    dg[boost::graph_bundle].outputMax += 0.5;
    assert(std::fabs(solve(dg, initial, 0.5).period - expected - 0.5) < 1e-7);
    dg = original;
    dg[boost::graph_bundle].setupUncertainty = 0.2;
    assert(std::fabs(solve(dg, initial, 0.5).period - expected - 0.2) < 1e-7);
    dg = original;
    dg[boost::graph_bundle].outputMin = -100.0;
    assert(mcrScheduleViolation(dg, baseline.period, baseline.potential) > 90.0);
    assert(solve(dg, initial, 0.5).period > 90.0);
    dg = original;
    Graph g;
    getMcrGraph(dg, g, initial);
    std::vector<double> skew, potential;
    assert(!fillMcrSkew(g, (initial - (expected - 1e-4)) / 2, expected - 1e-4, 1e-10, skew, potential));
    assert(fillMcrSkew(g, (initial - 10.0) / 2, 10.0, 1e-10, skew, potential));
    assert(mcrScheduleViolation(dg, 10.0, potential) <= kMcrFeasibilityEps);
    const double launch = 5.0;
    assert(std::fabs(potential[mcrIndex(4, kMcrD)] - (launch + 0.2)) < 1e-7);
    assert(std::fabs(potential[mcrIndex(4, kMcrLatestD)] - (launch + 1.0)) < 1e-7);
    assert(potential[mcrIndex(5, kMcrLatestA)] <= 14.0 + 1e-7);
    assert(potential[mcrIndex(5, kMcrA)] >= 5.05 - 1e-7);
    boost::add_edge(3, 1, EdgeDelay{0.1, 0.05}, dg);
    assert(!validDelayGraph(dg, initial));
    dg = original;
    namespace fs = std::filesystem;
    fs::create_directories(argv[3]);
    const auto invalid = fs::path(argv[3]) / "invalid_io.json";
    boost::property_tree::ptree json;
    boost::property_tree::read_json(argv[2], json);
    const auto reject = [&](const boost::property_tree::ptree &bad) {
        boost::property_tree::write_json(invalid.string(), bad);
        bool rejected = false;
        try { readLatchTiming(invalid.string(), dg); }
        catch (const std::exception &) { rejected = true; }
        assert(rejected && dg[boost::graph_bundle].outputMin == -0.05);
        assert(mcrScheduleViolation(dg, baseline.period, baseline.potential) <= kMcrFeasibilityEps);
    };
    for (const std::string key : {"input.min_delay_ns", "output.max_delay_ns", "setup_uncertainty_ns"})
    {
        auto bad = json;
        bad.put("io_constraints." + key, "nan");
        reject(bad);
    }
    auto bad = json;
    bad.get_child("io_constraints").erase("output"); reject(bad);
    bad = json; bad.put("io_constraints.path_cycle_shift", 1); reject(bad);
    bad = json; bad.put("io_constraints.output.port", "UNKNOWN"); reject(bad);
    bad = json; bad.put("schema_version", 2); reject(bad);
    bad = json; bad.get_child("edges").front().second.put("max_delay_ns", 99.0); reject(bad);
    bad = json; bad.get_child("edges").pop_back(); reject(bad);
    bad = json; bad.put("sta_conditions.output_load_pf", -0.1); reject(bad);
    bad = json; bad.put("sta_conditions.clock_transition_ns", 0.1); reject(bad);
    bad = json; bad.put("units.capacitance", "fF"); reject(bad);
    readLatchTiming(argv[2], dg); // Repeated v3 loads retain split-port semantics.
    assert(boost::num_vertices(dg) == 6 && mcrScheduleViolation(dg, baseline.period, baseline.potential) <= kMcrFeasibilityEps);
    assert(readDelayGraph(argv[1], dg, initial));
    assert(!dg[boost::graph_bundle].enabled && boost::num_vertices(dg) == 4);
    readLatchTiming(argv[2], dg);
    assert(mcrScheduleViolation(dg, baseline.period, baseline.potential) <= kMcrFeasibilityEps);
    assert(!readDelayGraph((fs::path(argv[3]) / "missing.out").string(), dg, initial));
    assert(!dg[boost::graph_bundle].enabled && boost::num_vertices(dg) == 0);
    std::cout << "Separate real IO constraints and failure checks passed\n";
}
