## Project Structure

```
qaoa-phase-space-finance/
│
├── simulation.py          # Main entry point — run this
├── market_graph.py        # 6-node silver futures execution graph
├── wigner_calibrate.py    # Wigner-function noise profiler (Layer 1 calibration)
├── qaoa_engine.py         # QAOA circuit engine (ideal / noisy / ZNE)
├── landscape.py           # Energy landscape scanner + ZNECalibrator
├── zne_calibration.py     # Re-export shim for ZNECalibrator
│
├── assets/
│   ├── wigner_analysis.png    # Wigner noise profiling figure
│   └── full_analysis.png      # Main composite figure (generated at runtime)
│
├── results/               # Runtime output directory (auto-created)
│
├── docs/
│   └── thesis_analogy_map.md  # Full reference map: thesis → simulation
│
├── requirements.txt
├── .gitignore
└── README.md
```

---

## Module Architecture

```
simulation.py
    │
    ├── market_graph.py        build_silver_futures_graph()
    │                              → nx.Graph (6 nodes, 10 edges, weighted)
    │
    ├── wigner_calibrate.py    WignerNoiseProfiler.run()
    │                              → noise_report { noise_scale, zne_scales, delta_negativity }
    │
    ├── qaoa_engine.py         QAOAEngine(G, noise_level, zne_scales)
    │       │                      → .cost(γ, β)              # COBYLA objective
    │       │                      → .get_best_bitstring()    # decode partition
    │       │                      → .evaluate_cut()          # Max-Cut weight
    │       │
    │       └── PennyLane      default.qubit  (ideal statevector)
    │                          default.mixed  (density matrix + DepolarizingChannel)
    │
    └── landscape.py           LandscapeScanner.scan(engine, γ_grid, β_grid)
                                   → 2D ndarray energy landscape
                               ZNECalibrator.extrapolate(scales, values)
                                   → float  (Richardson λ→0 limit)
```
