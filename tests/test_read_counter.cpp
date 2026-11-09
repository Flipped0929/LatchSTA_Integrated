#include <cassert>
#include <chrono>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <map>
#include <boost/property_tree/json_parser.hpp>
#include "timing_graph.hpp"
#include "LP.hpp"

using boost::property_tree::ptree;

int main()
{
    namespace fs = std::filesystem;
    const auto scratch = fs::temp_directory_path() /
        ("test_read_counter_" + std::to_string(std::chrono::steady_clock::now().time_since_epoch().count()));
    assert(fs::create_directory(scratch));
    const auto input = scratch / "input.out", json = scratch / "timing.json";
    const string counterFile = "examples/counter/counter.blif.out";
    const string timingFile = "examples/counter/counter_timing.json";
    DelayGraph dg;
    double initial = -1.0;
    assert(readDelayGraph(counterFile, dg, initial));
    assert(validDelayGraph(dg, initial));
    assert(boost::num_vertices(dg) == 15 && boost::num_edges(dg) == 26);
    assert(fabs(initial - 0.410682) < 1e-12);
    for (size_t k = 1; k < boost::num_vertices(dg); ++k)
        assert(dg[k].kind == NodeIdx::Kind::Unknown);
    const DelayGraph raw = dg;
    readLatchTiming(timingFile, dg);
    assert(validDelayGraph(dg, initial));
    assert(boost::degree(0, dg) == 0);
    map<string, size_t> indices;
    size_t latches = 0, inputs = 0, outputs = 0;
    for (size_t k = 1; k < boost::num_vertices(dg); ++k)
    {
        assert(indices.emplace(dg[k].name, k).second);
        latches += dg[k].kind == NodeIdx::Kind::Latch;
        inputs += dg[k].kind == NodeIdx::Kind::Input;
        outputs += dg[k].kind == NodeIdx::Kind::Output;
    }
    assert(latches == 8 && inputs == 2 && outputs == 4);
    ptree source;
    boost::property_tree::read_json(timingFile, source);
    for (const auto &entry : source.get_child("nodes"))
    {
        const auto &p = entry.second;
        const auto &node = dg[indices.at(p.get<string>("instance"))];
        assert(node.polarity == (p.get<string>("polarity") == "negative"
            ? NodeIdx::Polarity::Negative : NodeIdx::Polarity::Positive));
        const auto &window = p.get_child("window_fraction");
        assert(node.windowFraction.first == window.front().second.get_value<double>());
        assert(node.windowFraction.second == window.back().second.get_value<double>());
        assert(node.timing.tsu == p.get<double>("parameters_ns.tsu"));
        assert(node.timing.thd == p.get<double>("parameters_ns.thd"));
        assert(node.timing.tdqMin == p.get<double>("parameters_ns.tdqMin"));
        assert(node.timing.tdqMax == p.get<double>("parameters_ns.tdqMax"));
        assert(node.timing.tcqMin == p.get<double>("parameters_ns.tcqMin"));
        assert(node.timing.tcqMax == p.get<double>("parameters_ns.tcqMax"));
        assert(node.reportedPulseWidth == p.get<double>("reported_pulse_check.required_ns"));
        assert(!node.clockChecks.characterized); // Reports do not prove complete Liberty coverage.
    }
    size_t zeroEdges = 0;
    for (const auto &entry : source.get_child("edges"))
    {
        const auto &p = entry.second;
        const auto e = boost::edge(indices.at(p.get<string>("source")), indices.at(p.get<string>("target")), dg);
        assert(e.second);
        assert(dg[e.first].minDelay == p.get<double>("min_delay_ns"));
        assert(dg[e.first].maxDelay == p.get<double>("max_delay_ns"));
        zeroEdges += dg[e.first].maxDelay == 0.0;
    }
    assert(zeroEdges == 8);
    assert(boost::edge(indices.at("_17_"), indices.at("_21_"), dg).second);
    assert(boost::edge(indices.at("_21_"), indices.at("_17_"), dg).second);
    const auto &io = dg[boost::graph_bundle];
    const auto &counter = *io.counterTiming;
    assert(io.timingModel == "counter_mixed_polarity_feedback_v1" && !io.enabled);
    assert(counter.clockName == "clk" && counter.clockPort == "clk");
    assert(counter.period == 10.0 && counter.rise == 5.0 && counter.fall == 10.0);
    assert(counter.skew == 0.0 && counter.clockTransition == 0.06);
    assert(io.dutyCycle == 0.5 && io.setupUncertainty == 0.05 && io.holdUncertainty == 0.05);
    for (const auto &port : counter.inputs)
        assert(port.second.minDelay == 0.2 && port.second.maxDelay == 1.0 && port.second.transition == 0.06);
    for (const auto &port : counter.outputs)
        assert(port.second.minDelay == -0.05 && port.second.maxDelay == 1.0 && port.second.load == 0.01);
    readLatchTiming(timingFile, dg); // Reload without reindexing or merging ports.
    assert(validDelayGraph(dg, initial) && boost::num_edges(dg) == 26);

    const auto rejectJson = [&](const ptree &bad) {
        boost::property_tree::write_json(json.string(), bad);
        bool rejected = false;
        try { readLatchTiming(json.string(), dg); }
        catch (const std::exception &) { rejected = true; }
        assert(rejected && validDelayGraph(dg, initial));
        assert(boost::num_vertices(dg) == 15 && boost::num_edges(dg) == 26);
        assert(dg[indices.at("_17_")].timing.tsu == 0.161291);
        assert(dg[boost::graph_bundle].counterTiming->inputs.at("en").maxDelay == 1.0);
    };
    for (const auto &change : std::vector<std::pair<string, string>>{
        {"schema_version", "3"}, {"units.time", "ps"}, {"timing_model", "unknown"},
        {"clock.period_ns", "0"}, {"clock.rise_ns", "nan"}, {"clock_skew_ns", "0.1"},
        {"io_constraints.inputs.en.min_delay_ns", "2"}, {"io_constraints.outputs.count[0].load_pf", "-1"}})
    {
        auto bad = source;
        bad.put(change.first, change.second);
        rejectJson(bad);
    }
    for (const auto &change : std::vector<std::pair<string, string>>{
        {"instance", "missing"}, {"polarity", "other"}, {"parameters_ns.tdqMin", "100"},
        {"parameters_ns.tsu", "nan"}, {"reported_pulse_check.level", "high"},
        {"reported_pulse_check.required_ns", "-1"}})
    {
        auto bad = source;
        bad.get_child("nodes").front().second.put(change.first, change.second);
        rejectJson(bad);
    }
    auto bad = source;
    bad.get_child("nodes").front().second.get_child("window_fraction").front().second.put_value(0.5);
    rejectJson(bad);
    bad = source;
    bad.get_child("nodes").push_back(bad.get_child("nodes").front());
    rejectJson(bad);
    bad = source;
    bad.get_child("nodes").pop_front();
    rejectJson(bad);
    bad = source;
    bad.get_child("edges").front().second.put("max_delay_ns", 1.0);
    rejectJson(bad);
    bad = source;
    bad.get_child("edges").pop_front();
    rejectJson(bad);
    bad = source;
    bad.get_child("edges").back().second = bad.get_child("edges").front().second;
    rejectJson(bad);
    bad = source;
    bad.get_child("nodes").front().second.put("parameters_ns.tsu", 999.0);
    bad.get_child("edges").back().second.put("source", "missing");
    rejectJson(bad); // Late failure must not commit the earlier latch change.
    bad = source;
    bad.get_child("io_constraints.outputs").erase("count[3]");
    rejectJson(bad);

    const auto rejectOut = [&](const string &text) {
        { std::ofstream stream(input); stream << text; }
        DelayGraph probe = dg;
        double t = initial;
        assert(!readDelayGraph(input.string(), probe, t));
        assert(boost::num_vertices(probe) == 0 && t == 0.0);
    };
    const string marker = "TimingModel counter_mixed_polarity_feedback_v1\n";
    rejectOut("TimingModel unknown\na b 1 0\n");
    rejectOut(marker + marker + "a b 1 0\n");
    rejectOut("a b 1 0\n" + marker);
    rejectOut("INPUT OUTPUT 1 0\n" + marker);
    rejectOut(marker + "a b nan 0\n");
    rejectOut(marker + "a b 0 1\n");
    rejectOut(marker + "a b 1 -1\n");
    rejectOut(marker + "a b 1\n");
    rejectOut(marker + "a b 1 0\na b 2 0\n");
    rejectOut(marker + "IO b 1 0\n");
    rejectOut(marker);

    Graph graph;
    for (const auto &probe : {raw, dg})
    {
        bool rejected = false;
        try { getMcrGraph(probe, graph, initial); }
        catch (const std::invalid_argument &) { rejected = true; }
        assert(rejected && boost::num_vertices(graph) == 0);
        McrResult result;
        mcrLP(probe, initial, result);
        assert(result.status == McrStatus::InvalidInput);
        assert(std::isinf(mcrPulsePeriodMin(probe, 0.5)));
        assert(std::isinf(mcrScheduleViolation(probe, 10.0, std::vector<double>(75))));
    }
    bool rejected = false;
    try { getEllGraph(counterFile, graph, initial); }
    catch (const std::invalid_argument &) { rejected = true; }
    assert(rejected);
    double period = 0.0, width = 0.0;
    rejected = false;
    try { ellLP(counterFile, period, width); }
    catch (const std::invalid_argument &) { rejected = true; }
    assert(rejected);

    DelayGraph legacy;
    assert(readDelayGraph("examples/tiny_3_latch_circuit/tiny.blif.out", legacy, initial));
    readLatchTiming("examples/tiny_3_latch_circuit/latch_timing.json", legacy);
    assert(validDelayGraph(legacy, initial) && legacy[boost::graph_bundle].enabled);
    getMcrGraph(legacy, graph, initial);
    assert(readDelayGraph("benchmark/s27.blif.out", legacy, initial));
    assert(validDelayGraph(legacy, initial));
    getMcrGraph(legacy, graph, initial);
    // Explicit RSLT entry point keeps the historical reversed min/max column order.
    { std::ofstream stream(input); stream << "DFF1 DFF2 0.1 0.3\n"; }
    assert(getRsltDelayGraph(input.string(), legacy, initial));
    assert(initial == 0.3 && boost::num_edges(legacy) == 1);
    { std::ofstream stream(input); stream << "INPUT L 0.3 0.1\nL OUTPUT 0.2 0.1\nINPUT L 0.4 0.2\n"; }
    assert(readDelayGraph(input.string(), legacy, initial));
    assert(boost::num_vertices(legacy) == 2 && boost::num_edges(legacy) == 2 && initial == 0.4);
    const auto merged = boost::edge(0, 1, legacy);
    assert(merged.second && legacy[merged.first].minDelay == 0.1 && legacy[merged.first].maxDelay == 0.4);
    ptree oldJson, oldNode, oldNodes;
    oldJson.put("units.time", "ns");
    oldNode.put("instance", "L");
    oldNode.add_child("parameters_ns", source.get_child("nodes").front().second.get_child("parameters_ns"));
    for (int schema : {1, 2})
    {
        oldJson.put("schema_version", schema);
        if (schema == 2)
        {
            oldNode.put("clock_checks_ns.min_pulse_width_high", 0.2);
            oldNode.put("clock_checks_ns.min_pulse_width_low", "null");
        }
        oldNodes.clear();
        oldNodes.push_back({"", oldNode});
        oldJson.put_child("nodes", oldNodes);
        boost::property_tree::write_json(json.string(), oldJson);
        readLatchTiming(json.string(), legacy);
        assert(validDelayGraph(legacy, initial) && legacy[1].timing.tsu == 0.161291);
        assert(legacy[1].clockChecks.characterized == (schema == 2));
    }
    fs::remove(input);
    fs::remove(json);
    fs::remove(scratch);
    std::cout << "counter reader passed: 8 latches, 2 inputs, 4 outputs, 26 edges (8 zero-delay); legacy regression passed\n";
}
