#include <cassert>
#include <cmath>
#include <iostream>
#include <limits>
#include "howard.hpp"
#include "LP.hpp"

int main(int argc, char **argv)
{
    assert(argc == 3); // tiny.blif.out, latch_timing.json
    DelayGraph dg;
    double initial = 0.0;
    assert(readDelayGraph(argv[1], dg, initial));
    readLatchTiming(argv[2], dg);
    DelayGraph compressed;
    assert(readDelayGraph(argv[1], compressed, initial));
    for (size_t k = 1; k < boost::num_vertices(compressed); ++k)
        for (size_t j = 1; j < boost::num_vertices(dg); ++j)
            if (compressed[k].name == dg[j].name)
            {
                compressed[k].timing = dg[j].timing;
                compressed[k].clockChecks = dg[j].clockChecks;
            }
    dg = std::move(compressed); // Keep the historical kernel regression separate from v3 IO semantics.
    for (double duty : {0.5, 0.4, 0.25, 0.01})
    {
        Graph g;
        getMcrGraph(dg, g, initial, duty);
        Howard howard(g, boost::num_vertices(g), initial, 1e-10);
        howard.run();
        const auto result = howard.getResult();
        McrResult lp;
        mcrLP(dg, initial, lp, duty);
        assert(result.status == McrStatus::Optimal && lp.status == McrStatus::Optimal);
        assert(std::fabs(result.period - lp.period) <= kMcrPeriodEps);
        assert(mcrScheduleViolation(dg, result.period, result.potential, duty) <= kMcrFeasibilityEps);
        assert(mcrPotentialViolation(g, lp.ratio, lp.potential) <= kMcrFeasibilityEps);
        assert(mcrScheduleViolation(dg, lp.period, lp.potential, duty) <= kMcrFeasibilityEps);
        assert(std::fabs(lp.period - mcrPulsePeriodMin(dg, duty)) < 1e-7);
        if (duty == 0.5)
        {
            assert(std::fabs(lp.period - 0.4620274367346939) < 1e-7);
            McrResult defaults;
            mcrLP(dg, initial, defaults);
            assert(defaults.status == McrStatus::Optimal);
            assert(std::fabs(defaults.period - lp.period) < 1e-12);
        }
        std::cout << "duty=" << duty << ", period=" << lp.period << " ns\n";
    }
    DelayGraph legacy = dg;
    for (size_t k = 1; k < boost::num_vertices(legacy); ++k)
        legacy[k].clockChecks = {};
    McrResult oldModel;
    mcrLP(legacy, initial, oldModel);
    assert(oldModel.status == McrStatus::Optimal && std::fabs(oldModel.period - 0.413084) < 1e-7);
    dg[1].clockChecks.minPulseLow = 0.8; // Artificial low-pulse check must dominate at 50%.
    Graph lowGraph;
    getMcrGraph(dg, lowGraph, initial);
    Howard lowHoward(lowGraph, boost::num_vertices(lowGraph), initial, 1e-10);
    lowHoward.run();
    McrResult lowLp;
    mcrLP(dg, initial, lowLp);
    assert(lowLp.status == McrStatus::Optimal && std::fabs(lowLp.period - 1.6) < 1e-7);
    assert(lowHoward.getResult().status == McrStatus::Optimal);
    assert(std::fabs(lowHoward.getResult().period - lowLp.period) < 1e-7);
    for (double duty : {0.0, -0.1, 0.500001, std::numeric_limits<double>::quiet_NaN(),
                        std::numeric_limits<double>::infinity()})
    {
        McrResult lp;
        mcrLP(dg, initial, lp, duty);
        assert(lp.status == McrStatus::InvalidInput);
        assert(!std::isfinite(lp.period));
    }
    dg[1].clockChecks.minPulseHigh = std::numeric_limits<double>::max();
    McrResult overflow;
    mcrLP(dg, initial, overflow, 0.25);
    assert(overflow.status == McrStatus::InvalidInput);
    std::cout << "MCR duty-cycle solver checks passed\n";
}
