"""Render OpenSTA pin_graph TSV exports to PNG and SVG (matplotlib, networkx)."""

import argparse
import csv
import math
from collections import defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import FancyBboxPatch
import networkx as nx


WIRE, CELL, LATCH, CLOCK, CHECK = "#718096", "#2563a6", "#c47717", "#188c92", "#ae4b80"


def table(directory, name, columns):
    with (directory / (name + ".tsv")).open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream, delimiter="\t")
        if not set(columns) <= set(reader.fieldnames or []):
            raise ValueError(f"{name}.tsv: missing required columns")
        rows = list(reader)
    if any(None in row or any(row[c] is None for c in columns) for row in rows):
        raise ValueError(f"{name}.tsv: malformed row")
    return rows


def indexed(rows, key):
    result = {row[key]: row for row in rows}
    if len(result) != len(rows) or "" in result:
        raise ValueError(f"Empty or duplicate {key}")
    return result


def load_graphs(directory):
    manifest = dict((r["key"], r["value"]) for r in table(directory, "manifest", ["key", "value"]))
    if manifest.get("schema_version") != "1" or manifest.get("time_unit") != "ns":
        raise ValueError("Expected pin graph schema 1 and ns time units")
    pins = indexed(table(directory, "pins", ["pin_id", "name", "direction", "instance", "port", "boundary", "boundary_role"]), "pin_id")
    vertices = indexed(table(directory, "vertices", ["vertex_id", "pin_id", "bidirect_driver"]), "vertex_id")
    edges = indexed(table(directory, "edges", ["edge_id", "from_vertex", "to_vertex", "kind", "role", "disabled_reason"]), "edge_id")
    graph = nx.MultiDiGraph()
    represented = set()
    for vertex, row in vertices.items():
        if row["pin_id"] not in pins:
            raise ValueError(f"Unknown pin in {vertex}")
        pin = pins[row["pin_id"]]
        graph.add_node(vertex, **pin, label=pin["port"] + (" [driver]" if row["bidirect_driver"] == "1" else ""))
        represented.add(row["pin_id"])
    # Keep pins without timing vertices, including unconnected/internal library pins.
    for pin_id, pin in pins.items():
        if pin_id not in represented:
            graph.add_node("pin:" + pin_id, **pin, label=pin["port"] + " [no vertex]")
    for edge_id, row in edges.items():
        if row["from_vertex"] not in vertices or row["to_vertex"] not in vertices:
            raise ValueError(f"Unknown vertex in {edge_id}")
        graph.add_edge(row["from_vertex"], row["to_vertex"], key=edge_id, **row)
    boundary = nx.MultiDiGraph()
    known = {p["boundary"] for p in pins.values() if p["boundary"]}
    rows = indexed(table(directory, "boundary_edges", ["boundary_edge_id", "source", "target", "scene", "min_delay_ns", "max_delay_ns"]), "boundary_edge_id")
    for edge_id, row in rows.items():
        lo, hi = float(row["min_delay_ns"]), float(row["max_delay_ns"])
        if not (math.isfinite(lo) and math.isfinite(hi) and 0 <= lo <= hi):
            raise ValueError(f"Invalid delay range in {edge_id}")
        if row["source"] not in known or row["target"] not in known:
            raise ValueError(f"Unknown boundary in {edge_id}")
        boundary.add_edge(row["source"], row["target"], key=edge_id, **row)
    if not graph or not boundary:
        raise ValueError("Empty pin or boundary graph")
    return graph, boundary, len(pins), len(vertices)


def layers(graph):
    """Arrange SCCs in forward layers; retain cycles for drawing."""
    condensed = nx.condensation(graph, scc=sorted(nx.strongly_connected_components(graph), key=lambda s: sorted(s)))
    level = {}
    for component in nx.topological_sort(condensed):
        level[component] = max((level[p] + 1 for p in condensed.predecessors(component)), default=0)
    return {node: level[component] for node, component in condensed.graph["mapping"].items()}


def pin_layout(graph):
    groups = defaultdict(list)
    group_of = {}
    clocks = set()
    for node, pin in graph.nodes(data=True):
        group = pin["instance"] or pin["name"]
        groups[group].append(node)
        group_of[node] = group
        if pin["boundary_role"] == "clock_source":
            clocks.add(group)
    data = nx.DiGraph()
    data.add_nodes_from(sorted(set(groups) - clocks))
    for u, v, edge in graph.edges(data=True):
        if (not edge["disabled_reason"] and edge["role"] in {"wire", "combinational", "Latch D to Q"}
                and group_of[u] != group_of[v] and group_of[u] not in clocks and group_of[v] not in clocks):
            data.add_edge(group_of[u], group_of[v])
    ranks = layers(data)
    centers = {}
    for rank in sorted(set(ranks.values())):
        batch = sorted((g for g in data if ranks[g] == rank), key=lambda g: (
            sum(centers[p][1] for p in data.predecessors(g) if p in centers), g))
        for i, group in enumerate(batch):
            centers[group] = (rank * 3.1, (len(batch) - 1 - 2 * i) * 2.0)
    for i, group in enumerate(sorted(clocks)):
        centers[group] = (i * 3.1, 4.2)
    positions, boxes = {}, []
    for group, nodes in groups.items():
        x, y = centers[group]
        if len(nodes) == 1 and not graph.nodes[nodes[0]]["instance"]:
            positions[nodes[0]] = (x, y)
            continue
        by_direction = defaultdict(list)
        for node in nodes:
            by_direction[graph.nodes[node]["direction"]].append(node)
        for direction, members in by_direction.items():
            for i, node in enumerate(sorted(members, key=lambda n: (graph.nodes[n]["port"], n))):
                if direction == "internal":
                    positions[node] = (x + (i - (len(members) - 1) / 2) * 0.9, y - 1.6)
                else:
                    positions[node] = (x + (0.65 if direction == "output" else -0.65),
                                       y + (len(members) - 1 - 2 * i) * 0.48)
        boxes.append((group, nodes))
    return positions, boxes


def edge_style(edge):
    if edge["disabled_reason"]:
        return "#bdc2ca", "dotted", 1.0
    role = edge["role"]
    if role in {"setup", "hold", "width"}:
        return CHECK, "dashed" if role == "hold" else "dotted", 1.0
    if role == "Latch En to Q":
        return CLOCK, "dashed", 1.2
    if role == "Latch D to Q":
        return LATCH, "solid", 1.6
    return (WIRE, "solid", 1.0) if edge["kind"] == "net" else (CELL, "solid", 1.5)


def draw_pins(graph, pins, vertices):
    positions, boxes = pin_layout(graph)
    extent = max(x for x, _ in positions.values()) - min(x for x, _ in positions.values())
    fig, ax = plt.subplots(figsize=(min(32, max(12, extent * 0.65 + 3)), 9))
    for group, nodes in boxes:
        xs, ys = zip(*(positions[n] for n in nodes))
        ax.add_patch(FancyBboxPatch((min(xs) - 0.52, min(ys) - 0.5), max(xs) - min(xs) + 1.04,
                                   max(ys) - min(ys) + 1.2, boxstyle="round,pad=0.06", linewidth=0.8,
                                   facecolor="#f5f7fa", edgecolor="#d4dae3", zorder=0))
        ax.text((min(xs) + max(xs)) / 2, max(ys) + 0.48, group, fontsize=8.5,
                ha="center", va="center", fontweight="bold", color="#28374d")
    for u, v, key, edge in graph.edges(keys=True, data=True):
        color, style, width = edge_style(edge)
        parallel = list(graph[u][v])
        radius = (parallel.index(key) - (len(parallel) - 1) / 2) * 0.48
        if graph.nodes[u]["boundary_role"] == "clock_source":
            color, style, radius = CLOCK, "dashed", -0.25
        nx.draw_networkx_edges(graph, positions, edgelist=[(u, v)], ax=ax, node_size=510,
                               edge_color=color, style=style, width=width, arrowsize=12,
                               connectionstyle=f"arc3,rad={radius}", alpha=0.85)
    colors = []
    for _, pin in graph.nodes(data=True):
        role = pin["boundary_role"]
        colors.append("#d6eef0" if role in {"clock_source", "latch_clock"} else
                      "#ffedc9" if role.startswith("latch_") else
                      "#dcebe0" if role in {"input", "output"} else
                      "#e5e7eb" if pin["direction"] == "internal" else "#ffffff")
    nx.draw_networkx_nodes(graph, positions, ax=ax, node_size=510, node_color=colors,
                           edgecolors="#66758a", linewidths=0.8)
    nx.draw_networkx_labels(graph, positions, labels={n: p["label"] for n, p in graph.nodes(data=True)},
                            ax=ax, font_size=7.5, font_color="#223044")
    handles = [Line2D([], [], color=c, linestyle=s, label=label, lw=1.8) for c, s, label in
               [(WIRE, "solid", "Net / wire"), (CELL, "solid", "Combinational cell"),
                (LATCH, "solid", "Latch D to Q"), (CLOCK, "dashed", "Clock / enable to Q"),
                (CHECK, "dotted", "Setup / hold / pulse check")]]
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.025), ncol=5, frameon=False, fontsize=9)
    ax.set_title(f"Complete pin graph  |  {pins} pins, {vertices} vertices, {graph.number_of_edges()} edges",
                 fontsize=15, fontweight="bold", loc="left", pad=20)
    ax.margins(x=0.035, y=0.16)
    ax.set_axis_off()
    fig.text(0.5, 0.025, "Structure view; check arcs are not data-flow edges. Internal / unconnected pins are retained.",
             ha="center", fontsize=9, color="#66758a")
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    return fig


def draw_boundaries(graph):
    ranks = layers(graph)
    positions = {}
    for rank in sorted(set(ranks.values())):
        nodes = sorted(n for n in graph if ranks[n] == rank)
        for i, node in enumerate(nodes):
            positions[node] = (rank * 3.3, (len(nodes) - 1 - 2 * i) * 1.8)
    fig, ax = plt.subplots(figsize=(max(10, min(26, len(set(ranks.values())) * 2.5)), 4.5))
    nx.draw_networkx_nodes(graph, positions, ax=ax, node_shape="s", node_size=2500,
                           node_color="#e5eff9", edgecolors=CELL, linewidths=1.2)
    nx.draw_networkx_labels(graph, positions, ax=ax, font_size=11, font_weight="bold")
    for u, v, key, edge in graph.edges(keys=True, data=True):
        parallel = list(graph[u][v])
        radius = (parallel.index(key) - (len(parallel) - 1) / 2) * 0.4
        nx.draw_networkx_edges(graph, positions, edgelist=[(u, v)], ax=ax, node_size=2500,
                               node_shape="s", edge_color=CELL, width=1.7, arrowsize=20,
                               connectionstyle=f"arc3,rad={radius}")
        x = (positions[u][0] + positions[v][0]) / 2
        y = (positions[u][1] + positions[v][1]) / 2 + 0.38 + radius * 2
        label = (f"{edge['boundary_edge_id']} / {edge['scene']}\n"
                 f"Dmin {float(edge['min_delay_ns']):.6f} ns\nDmax {float(edge['max_delay_ns']):.6f} ns")
        ax.text(x, y, label, ha="center", va="bottom", fontsize=9, color="#28374d",
                bbox=dict(facecolor="white", edgecolor="none", alpha=0.92, pad=3))
    ax.set_title("Latch / IO boundary graph", fontsize=15, fontweight="bold", loc="left", pad=18)
    xs, ys = zip(*positions.values())
    ax.set_xlim(min(xs) - 1.2, max(xs) + 1.2)
    ax.set_ylim(min(ys) - 1.0, max(ys) + 1.5)
    ax.set_axis_off()
    fig.text(0.5, 0.045, "Frozen GBA combinational-delay extrema; latch internal delay, clock latency and external IO delay are excluded.",
             ha="center", fontsize=9, color="#66758a")
    fig.tight_layout(rect=(0, 0.1, 1, 1))
    return fig


def render(directory, output):
    graph, boundary, pins, vertices = load_graphs(directory)
    # shortcut: static layouts target small circuits; use tiled/interactive views for large netlists.
    output.mkdir(parents=True, exist_ok=False)
    for name, figure in (("pin_graph", draw_pins(graph, pins, vertices)), ("boundary_graph", draw_boundaries(boundary))):
        try:
            for suffix in ("png", "svg"):
                figure.savefig(output / f"{name}.{suffix}", dpi=180, facecolor="white", bbox_inches="tight")
        finally:
            plt.close(figure)
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pin_graph", type=Path, help="Directory containing OpenSTA pin_graph TSV files")
    parser.add_argument("--output-dir", type=Path, help="New output directory; default: beside pin_graph, named figures")
    args = parser.parse_args()
    try:
        output = render(args.pin_graph, args.output_dir or args.pin_graph.parent / "figures")
    except (OSError, ValueError, nx.NetworkXException) as error:
        parser.exit(1, f"Rendering failed: {error}\n")
    print(f"Saved pin_graph.png/.svg and boundary_graph.png/.svg to {output}")
