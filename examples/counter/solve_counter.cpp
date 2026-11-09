#include <cmath>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include "howard.hpp"
#include "LP.hpp"
#include "sdc_export.hpp"

int main(int argc, char **argv)
{
    try
    {
        if (argc != 4)
            throw std::invalid_argument("Usage: counter_solver input.blif.out timing.json new_output.sdc");
        DelayGraph dg;
        double initial = 0.0;
        if (!readDelayGraph(argv[1], dg, initial))
            return 1;
        readLatchTiming(argv[2], dg);
        dg[boost::graph_bundle].optimizeSkew = false;
        Graph graph;
        getMcrGraph(dg, graph, initial, 0.5);
        Howard solver(graph, boost::num_vertices(graph), initial, 1e-10);
        solver.run();
        const auto result = solver.getResult();
        McrResult lp;
        mcrLP(dg, initial, lp, 0.5);
        exportHowardSdc(argv[3], dg, initial, 0.5, result, lp);
        std::cout << std::setprecision(12)
                  << "Zero-skew model minimum period = " << result.period << " ns\n"
                  << "Model maximum clock frequency = " << 1000.0 / result.period << " MHz\n"
                  << "Exported SDC: " << argv[3] << "\n"
                  << "Fixed scalar envelopes; reported pulse checks; independent OpenSTA validation required.\n";
        return 0;
    }
    catch (const std::exception &error)
    {
        std::cerr << "Error: " << error.what() << '\n';
        return 1;
    }
}
