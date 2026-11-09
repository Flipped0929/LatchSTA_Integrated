#include <cassert>
#include <cmath>
#include <iostream>
#include "howard.hpp"
#include "LP.hpp"

static McrResult solve(DelayGraph &dg, double duty)
{
    constexpr double initial = 30.0;
    Graph graph;
    getMcrGraph(dg, graph, initial, duty);
    Howard howard(graph, boost::num_vertices(graph), initial, 1e-10);
    howard.run();
    const auto result = howard.getResult();
    McrResult lp;
    mcrLP(dg, initial, lp, duty);
    assert(result.status == McrStatus::Optimal && lp.status == McrStatus::Optimal);
    assert(std::fabs(result.period - lp.period) < kMcrPeriodEps);
    assert(mcrScheduleViolation(dg, result.period, result.potential, duty) < kMcrFeasibilityEps);
    assert(mcrPotentialViolation(graph, lp.ratio, lp.potential) < kMcrFeasibilityEps);
    if (!dg[boost::graph_bundle].optimizeSkew)
        for (double skew : result.skew)
            assert(std::fabs(skew) < kMcrFeasibilityEps);
    return result;
}

int main()
{
    DelayGraph dg;
    for (size_t k = 0; k < 3; ++k)
        boost::add_vertex(NodeIdx{k, {}, "node" + std::to_string(k)}, dg);
    boost::add_edge(1, 2, EdgeDelay{10.0, 10.0}, dg);
    boost::add_edge(2, 1, EdgeDelay{0.5, 0.5}, dg);
    assert(dg[boost::graph_bundle].optimizeSkew);
    const auto optimized = solve(dg, 0.5);
    dg[boost::graph_bundle].optimizeSkew = false;
    const auto fixed = solve(dg, 0.5);
    assert(fixed.period > optimized.period + 0.1);
    assert(std::fabs(fixed.period - 10.0 / 1.5) < kMcrPeriodEps);

    // A schedule valid in optimized mode must be rejected when its nonzero offsets are forbidden.
    assert(mcrScheduleViolation(dg, optimized.period, optimized.potential, 0.5) > kMcrFeasibilityEps);
    auto shifted = fixed.potential;
    for (size_t variable = 0; variable < kMcrVarsPerNode; ++variable)
        shifted[kMcrVarsPerNode + variable] += 0.2;
    assert(mcrScheduleViolation(dg, fixed.period, shifted, 0.5) >= 0.2 - kMcrFeasibilityEps);

    dg[1].clockChecks = {true, 5.0, 1.0};
    const auto pulse = solve(dg, 0.25);
    assert(std::fabs(pulse.period - 20.0) < kMcrPeriodEps);

    DelayGraph realIo;
    boost::add_vertex(NodeIdx{0, {}, "reference"}, realIo);
    boost::add_vertex(NodeIdx{1, {}, "din", {}, NodeIdx::Kind::Input}, realIo);
    boost::add_vertex(NodeIdx{2, {0.1, 0.05, 0.1, 0.2, 0.1, 0.2}, "latch"}, realIo);
    boost::add_vertex(NodeIdx{3, {}, "dout", {}, NodeIdx::Kind::Output}, realIo);
    boost::add_edge(1, 2, EdgeDelay{0.2, 0.1}, realIo);
    boost::add_edge(2, 3, EdgeDelay{0.3, 0.1}, realIo);
    auto &io = realIo[boost::graph_bundle];
    io.enabled = true;
    io.inputPort = "din";
    io.outputPort = "dout";
    io.inputMin = 0.1;
    io.inputMax = 0.4;
    io.outputMin = -0.1;
    io.outputMax = 0.2;
    io.optimizeSkew = false;
    // The input-to-latch closing constraint is T/2 + 0.4 + 0.2 + 0.1 <= T.
    assert(std::fabs(solve(realIo, 0.5).period - 1.4) < kMcrPeriodEps);
    std::cout << "zero-skew regression passed: optimized=" << optimized.period
              << " ns, zero-skew=" << fixed.period << " ns, pulse-bound=" << pulse.period << " ns\n";
}
