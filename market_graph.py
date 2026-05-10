"""
market_graph.py
---------------
Builds the silver futures execution graph that QAOA will optimise.

FINANCIAL CONTEXT
-----------------
Silver futures trade across multiple global venues simultaneously.
An algorithmic trading desk must decide, in microseconds, which sequence
of exchanges to route an order through to minimise:
  - Execution slippage (bid-ask spread eaten by each hop)
  - Latency cost     (slower venues introduce more price drift)
  - Liquidity risk   (thin order books raise impact cost)

We model these as a weighted undirected graph:
  Nodes  = trading venues / liquidity pools
  Edges  = execution pathways, weighted by combined cost score
  Objective = find the partition (Max-Cut) that separates high-cost
              from low-cost execution paths — QAOA's natural problem

WHY MAX-CUT?
------------
The Max-Cut problem asks: partition nodes into two sets S and S̄ such
that the total weight of edges crossing the cut is maximised.
In our financial setting:
  - Set S  = "execute through this venue"
  - Set S̄ = "skip this venue"
  - Cut weight = total cost we are routing AROUND (higher = better avoidance)
QAOA returns a binary string encoding the optimal partition.
"""

import networkx as nx


# ─────────────────────────────────────────────────────────────────────────
# Node metadata
# ─────────────────────────────────────────────────────────────────────────
VENUES = {
    0: {"label": "CME",    "hub": True,  "description": "CME Group (Chicago) — primary futures hub"},
    1: {"label": "LME",    "hub": True,  "description": "London Metal Exchange — metals benchmark"},
    2: {"label": "COMEX",  "hub": False, "description": "COMEX (NY) — high liquidity, high latency"},
    3: {"label": "SGX",    "hub": False, "description": "Singapore Exchange — Asia-Pacific gateway"},
    4: {"label": "TOCOM",  "hub": False, "description": "Tokyo Commodity Exchange — low liquidity"},
    5: {"label": "SHFE",   "hub": False, "description": "Shanghai Futures Exchange — CNY-denominated"},
}

# ─────────────────────────────────────────────────────────────────────────
# Edge cost scores
# Each weight encodes: slippage × latency_penalty × liquidity_risk
# Higher weight = more expensive path = better to include in the cut
# ─────────────────────────────────────────────────────────────────────────
EDGES = [
    # (node_i, node_j, cost_weight)
    (0, 1, 1.2),   # CME  ↔ LME   : moderate — well-arbitraged corridor
    (0, 2, 0.8),   # CME  ↔ COMEX : cheap — co-located, sub-ms latency
    (0, 3, 2.5),   # CME  ↔ SGX   : expensive — cross-Pacific latency
    (1, 2, 1.8),   # LME  ↔ COMEX : moderate-high — transatlantic hop
    (1, 3, 1.4),   # LME  ↔ SGX   : moderate — European-Asian corridor
    (1, 5, 2.1),   # LME  ↔ SHFE  : expensive — regulatory friction + FX
    (2, 4, 3.0),   # COMEX ↔ TOCOM: very expensive — low liquidity at TOCOM
    (3, 4, 1.0),   # SGX  ↔ TOCOM : cheap — geographic proximity
    (3, 5, 1.6),   # SGX  ↔ SHFE  : moderate — intra-Asia, capital controls
    (4, 5, 2.8),   # TOCOM ↔ SHFE : expensive — thin cross-liquidity
]


def build_silver_futures_graph() -> nx.Graph:
    """
    Construct the silver futures execution graph.

    Returns
    -------
    G : nx.Graph
        Weighted undirected graph with node metadata.
    """
    G = nx.Graph()

    for node_id, attrs in VENUES.items():
        G.add_node(node_id, **attrs)

    for u, v, w in EDGES:
        G.add_edge(u, v, weight=w)

    return G


def print_graph_summary(G: nx.Graph) -> None:
    """Print a human-readable summary of the graph."""
    print(f"  Nodes (venues)  : {G.number_of_nodes()}")
    print(f"  Edges (pathways): {G.number_of_edges()}")
    total_w = sum(d['weight'] for _, _, d in G.edges(data=True))
    print(f"  Total cost score: {total_w:.2f}")
    print(f"  Venues:")
    for n in G.nodes():
        hub = "★ hub" if G.nodes[n].get('hub') else "  node"
        print(f"    [{n}] {hub}  {G.nodes[n]['label']:6s} — {G.nodes[n]['description']}")
    print(f"  Edges (u, v, cost):")
    for u, v, d in sorted(G.edges(data=True), key=lambda x: -x[2]['weight']):
        lu = G.nodes[u]['label']
        lv = G.nodes[v]['label']
        print(f"    {lu:6s} ↔ {lv:6s}  cost={d['weight']:.1f}")
