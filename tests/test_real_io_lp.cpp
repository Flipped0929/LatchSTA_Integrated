#include <cassert>
#include <cmath>
#include <iostream>
#include "howard.hpp"
#include "LP.hpp"

static double compare(const DelayGraph &dg, double initial, double duty)
{
    Graph g;
    getMcrGraph(dg, g, initial, duty);
    Howard how(g, boost::num_vertices(g), initial, 1e-10);
    how.run();
    const auto graph = how.getResult();
    McrResult lp;
    mcrLP(dg, initial, lp, duty);
    assert(lp.status == McrStatus::Optimal && graph.status == McrStatus::Optimal);
    assert(std::fabs(lp.period - graph.period) < 1e-7);
    assert(mcrPotentialViolation(g, lp.ratio, lp.potential) <= kMcrFeasibilityEps);
    assert(mcrScheduleViolation(dg, lp.period, lp.potential, duty) <= kMcrFeasibilityEps);
    std::cout << "LP/Howard IO duty=" << duty << " period=" << lp.period << " ns\n";
    return lp.period;
}

int main(int argc, char **argv)
{
    assert(argc == 3);
    DelayGraph dg;
    double initial = 0;
    assert(readDelayGraph(argv[1], dg, initial));
    readLatchTiming(argv[2], dg);
    assert(dg[boost::graph_bundle].enabled);
    const auto original = dg;
    for (double duty : {0.5, 0.4, 0.25, 0.01})
        assert(std::fabs(compare(dg, initial, duty) - std::max(3.541155, mcrPulsePeriodMin(dg, duty))) < 1e-7);
    dg[boost::graph_bundle].inputMax += 0.5;
    assert(std::fabs(compare(dg, initial, 0.5) - 4.041155) < 1e-7);
    dg = original;
    dg[boost::graph_bundle].outputMax += 0.5;
    assert(std::fabs(compare(dg, initial, 0.5) - 4.041155) < 1e-7);
    dg = original;
    dg[boost::graph_bundle].setupUncertainty = 0.2;
    assert(std::fabs(compare(dg, initial, 0.5) - 3.741155) < 1e-7);
    dg = original;
    dg[boost::graph_bundle].outputMin = -100.0;
    assert(compare(dg, initial, 0.5) > 90.0);
    dg = original;
    dg[boost::graph_bundle].holdUncertainty = 10.0;
    assert(compare(dg, initial, 0.5) > 19.0);
    dg = original;
    dg[boost::graph_bundle].inputMin = 2.0;
    McrResult invalid;
    mcrLP(dg, initial, invalid);
    assert(invalid.status == McrStatus::InvalidInput);
    std::cout << "Real IO independent LP comparisons passed\n";
}
