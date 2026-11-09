#include <cassert>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <sstream>
#include "howard.hpp"
#include "LP.hpp"
#include "sdc_export.hpp"

// Unroll physical half-cycles independently of the constraint-graph cycle coefficients.
static bool unrolledSetup(const DelayGraph &dg, double period)
{
    const auto &io = dg[boost::graph_bundle];
    const auto &counter = *io.counterTiming;
    std::vector<double> previous(boost::num_vertices(dg), 0.0), current(previous);
    for (size_t k = 1; k < previous.size(); ++k)
        if (dg[k].kind == NodeIdx::Kind::Latch)
        {
            if (0.5 * period + 1e-9 < *dg[k].reportedPulseWidth) return false;
            previous[k] = -0.5 * period + dg[k].timing.tcqMax;
        }
    for (int cycle = 0; cycle < 40; ++cycle)
    {
        const double start = cycle * period;
        for (const auto polarity : {NodeIdx::Polarity::Negative, NodeIdx::Polarity::Positive})
            for (size_t k = 1; k < current.size(); ++k)
                if (dg[k].kind == NodeIdx::Kind::Latch && dg[k].polarity == polarity)
                {
                    double arrival = -std::numeric_limits<double>::infinity();
                    const auto paths = boost::in_edges(k, dg);
                    for (auto e = paths.first; e != paths.second; ++e)
                    {
                        const size_t u = boost::source(*e, dg);
                        const double launch = dg[u].kind == NodeIdx::Kind::Input
                            ? start - 0.5 * period + counter.inputs.at(dg[u].name).maxDelay
                            : (polarity == NodeIdx::Polarity::Negative ? previous[u] : current[u]);
                        arrival = std::max(arrival, launch + dg[*e].maxDelay);
                    }
                    const double opening = start + (polarity == NodeIdx::Polarity::Negative ? 0.0 : 0.5 * period);
                    if (arrival + dg[k].timing.tsu + io.setupUncertainty > opening + 0.5 * period + 1e-9) return false;
                    current[k] = std::max(arrival + dg[k].timing.tdqMax, opening + dg[k].timing.tcqMax);
                }
        for (size_t k = 1; k < current.size(); ++k)
            if (dg[k].kind == NodeIdx::Kind::Output)
            {
                const auto paths = boost::in_edges(k, dg);
                for (auto e = paths.first; e != paths.second; ++e)
                    if (current[boost::source(*e, dg)] + dg[*e].maxDelay + counter.outputs.at(dg[k].name).maxDelay
                        + io.setupUncertainty > start + 1.5 * period + 1e-9) return false;
            }
        previous = current;
    }
    return true;
}

static McrResult solve(const DelayGraph &dg, double initial)
{
    Graph graph;
    getMcrGraph(dg, graph, initial);
    Howard howard(graph, boost::num_vertices(graph), initial, 1e-10);
    howard.run();
    const auto result = howard.getResult();
    McrResult lp;
    mcrLP(dg, initial, lp);
    if (result.status != McrStatus::Optimal || lp.status != McrStatus::Optimal)
        std::cerr << "Howard=" << mcrStatusToString(result.status) << ", LP=" << mcrStatusToString(lp.status)
                  << ", Howard period=" << result.period << ", LP period=" << lp.period << '\n';
    assert(result.status == McrStatus::Optimal && lp.status == McrStatus::Optimal);
    assert(std::fabs(result.period - lp.period) < 1e-7);
    assert(mcrScheduleViolation(dg, result.period, result.potential) < kMcrFeasibilityEps);
    assert(mcrPotentialViolation(graph, lp.ratio, lp.potential) < kMcrFeasibilityEps);
    for (double skew : result.skew) assert(std::fabs(skew) < 1e-9);
    auto shifted = result.potential;
    shifted[mcrIndex(1, kMcrSkew)] = 0.1;
    assert(mcrScheduleViolation(dg, result.period, shifted) >= 0.1);
    std::vector<double> infeasible;
    assert(!fillMcrSkew(graph, (initial - result.period + 1e-4) / 2.0,
                        result.period - 1e-4, 1e-10, shifted, infeasible));
    if (dg[boost::graph_bundle].counterTiming)
    {
        assert(unrolledSetup(dg, result.period));
        assert(!unrolledSetup(dg, result.period * 0.99)); // Finite unrolling needs a visible cycle deficit.
    }
    return result;
}

static DelayGraph artificial()
{
    DelayGraph dg;
    for (size_t k = 0; k < 5; ++k)
        boost::add_vertex(NodeIdx{k, {}, std::vector<string>{"IO", "M", "S", "en", "count[0]"}[k]}, dg);
    for (size_t k : {1, 2})
    {
        dg[k].timing = {0.1, 0.05, 0.2, 0.3, 0.2, 0.4};
        dg[k].reportedPulseWidth = 0.1;
    }
    dg[1].polarity = NodeIdx::Polarity::Negative;
    dg[1].windowFraction = {0.0, 0.5};
    dg[3].kind = NodeIdx::Kind::Input;
    dg[4].kind = NodeIdx::Kind::Output;
    boost::add_edge(1, 2, EdgeDelay{0.0, 0.0}, dg);
    boost::add_edge(2, 1, EdgeDelay{0.1, 0.1}, dg);
    boost::add_edge(3, 1, EdgeDelay{0.2, 0.1}, dg);
    boost::add_edge(2, 4, EdgeDelay{0.0, 0.0}, dg);
    auto &io = dg[boost::graph_bundle];
    io.timingModel = "counter_mixed_polarity_feedback_v1";
    io.optimizeSkew = false;
    io.setupUncertainty = io.holdUncertainty = 0.05;
    io.counterTiming = IoConstraints::CounterTiming{"clk", "clk", 10.0, 5.0, 10.0, 0.0, 0.06,
        {{"en", {0.2, 1.0, 0.06, 0.0}}}, {{"count[0]", {-0.05, 1.0, 0.0, 0.01}}}};
    assert(validCounterMcr(dg, 0.5));
    return dg;
}

int main(int argc, char **argv)
{
    auto fixture = artificial();
    assert(std::fabs(solve(fixture, 5.0).period - 1.45) < 1e-7); // CQ + external output budget.
    fixture[boost::graph_bundle].counterTiming->outputs.at("count[0]").maxDelay = 0.5;
    assert(std::fabs(solve(fixture, 5.0).period - 1.35) < 1e-7); // Input -> master setup.
    fixture[1].reportedPulseWidth = 1.0;
    assert(std::fabs(solve(fixture, 5.0).period - 2.0) < 1e-7);
    fixture[1].reportedPulseWidth = 0.1;
    fixture[boost::edge(2, 1, fixture).first].maxDelay = 3.0;
    assert(std::fabs(solve(fixture, 5.0).period - 3.6) < 1e-7); // Two DQ arcs + feedback combinational delay.
    fixture = artificial();
    fixture[2].timing.thd = 1.0;
    assert(!validCounterMcr(fixture, 0.5));
    fixture = artificial();
    fixture[boost::graph_bundle].counterTiming->outputs.at("count[0]").minDelay = -1.0;
    assert(!validCounterMcr(fixture, 0.5));
    fixture = artificial();
    boost::add_edge(1, 1, EdgeDelay{0.1, 0.1}, fixture);
    assert(!validCounterMcr(fixture, 0.5));

    DelayGraph dg;
    double initial = 0.0;
    assert(readDelayGraph("examples/counter/counter.blif.out", dg, initial));
    readLatchTiming("examples/counter/counter_timing.json", dg);
    assert(!validCounterMcr(dg, 0.5)); // Skew optimization is intentionally unsupported.
    dg[boost::graph_bundle].optimizeSkew = false;
    assert(!validCounterMcr(dg, 0.4));
    const auto result = solve(dg, initial);
    assert(std::fabs(result.period - 1.584538) < 1e-7);
    // Independent active-path bound: en -> master[2] -> slave[2] -> output, across two periods.
    const double bound = (1.0 + 0.367006 + 0.329435 + 0.422635 + 1.0 + 0.05) / 2.0;
    assert(std::fabs(result.period - bound) < 1e-7);
    McrResult lp;
    mcrLP(dg, initial, lp);
    if (argc == 2)
    {
        exportHowardSdc(argv[1], dg, initial, 0.5, result, lp);
        std::ifstream stream(argv[1]);
        std::stringstream contents;
        contents << stream.rdbuf();
        const auto text = contents.str();
        assert(text.find("_17_/GATE_N") != string::npos && text.find("_21_/GATE}") != string::npos);
        assert(text.find("{count[3]}") != string::npos && text.find("{rst_n}") != string::npos);
        bool rejected = false;
        try { exportHowardSdc(argv[1], dg, initial, 0.5, result, lp); }
        catch (const std::invalid_argument &) { rejected = true; }
        assert(rejected);
        auto corrupted = result;
        corrupted.skew[1] = 0.1;
        rejected = false;
        const string invalidPath = string(argv[1]) + ".invalid.sdc";
        try { exportHowardSdc(invalidPath, dg, initial, 0.5, corrupted, lp); }
        catch (const std::invalid_argument &) { rejected = true; }
        assert(rejected && !std::filesystem::exists(invalidPath));
        DelayGraph legacy;
        double legacyInitial = 0.0;
        assert(readDelayGraph("examples/tiny_3_latch_circuit/tiny.blif.out", legacy, legacyInitial));
        readLatchTiming("examples/tiny_3_latch_circuit/latch_timing.json", legacy);
        legacy[boost::graph_bundle].optimizeSkew = false;
        const auto legacyResult = solve(legacy, legacyInitial);
        McrResult legacyLp;
        mcrLP(legacy, legacyInitial, legacyLp);
        exportHowardSdc(string(argv[1]) + ".legacy.sdc", legacy, legacyInitial, 0.5, legacyResult, legacyLp);
    }
    std::cout << "counter solver passed: T=" << result.period << " ns, f=" << 1000.0 / result.period
              << " MHz; independent LP, active-path bound and infeasibility checks passed\n";
}
