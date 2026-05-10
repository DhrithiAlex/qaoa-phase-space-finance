"""
=============================================================================
Phase-Space Noise Calibration for QAOA-Based Financial Optimization
=============================================================================

Inspired by: "Balanced Homodyne Detection without Coherent State Local
Oscillator" — Master's Thesis, Dhrithi Maria, Universität Paderborn (2026)

Thesis Supervisor: Prof. Dr. Jan Sperling

CONCEPTUAL BRIDGE
-----------------
In the thesis, the key problem is that a non-ideal Local Oscillator (LO)
corrupts the measured photocurrent variance, mixing signal and noise in a
way that makes standard tomography fail. The solution is:

  Var(δ̂(φ)) = |⟨b̂⟩|² · Var_signal(φ)  +  Var_LO(φ)
               ───────────────────────    ────────────
               What we want                What we must remove

This simulation applies the identical conceptual structure to QAOA:

  E_measured(γ,β) = E_true(γ,β)  +  Noise(γ,β)
                    ─────────────    ────────────
                    Optimal landscape  Hardware decoherence

Just as the thesis uses a vacuum-substitution calibration to isolate
Var_LO, we use Zero-Noise Extrapolation (ZNE) informed by a Wigner-
function noise profile to isolate the true QAOA energy landscape.

The Wigner function's negativity (a signature of quantum coherence) is
used to quantify how much decoherence is present — exactly parallel to
how the LO mean field ⟨b̂⟩ is used as the validity criterion in the thesis.

APPLICATION
-----------
We model a silver futures routing problem: find the minimum-cost execution
path across global exchange nodes, where QAOA solves a weighted Max-Cut
variant of the routing graph.

MODULES
-------
1. market_graph.py   — builds the financial graph
2. wigner_calibrate.py — Wigner-function noise profiling
3. qaoa_engine.py    — QAOA circuit (ideal, noisy, ZNE-mitigated)
4. landscape.py      — energy landscape scanning and plotting
5. simulation.py     — main entry point (this file)
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from matplotlib.colors import LinearSegmentedColormap
import networkx as nx
import warnings
import os
warnings.filterwarnings('ignore')

# ── imports from our own modules ──────────────────────────────────────────
from market_graph    import build_silver_futures_graph, print_graph_summary
from wigner_calibrate import WignerNoiseProfiler
from qaoa_engine     import QAOAEngine
from landscape       import LandscapeScanner
from zne_calibration import ZNECalibrator

# ─────────────────────────────────────────────────────────────────────────
# 0.  Output directory
# ─────────────────────────────────────────────────────────────────────────
os.makedirs("results", exist_ok=True)

print("=" * 70)
print("  Phase-Space Noise Calibration for QAOA Financial Optimization")
print("  Inspired by: Balanced Homodyne Detection without Coherent LO")
print("  Dhrithi Maria — Universität Paderborn, 2026")
print("=" * 70)

# ─────────────────────────────────────────────────────────────────────────
# 1.  Build the Silver Futures Execution Graph
# ─────────────────────────────────────────────────────────────────────────
print("\n[1/5] Building silver futures execution graph ...")
G = build_silver_futures_graph()
print_graph_summary(G)

# ─────────────────────────────────────────────────────────────────────────
# 2.  Wigner-Function Noise Profiling  (thesis Layer 1 analog)
# ─────────────────────────────────────────────────────────────────────────
print("\n[2/5] Running Wigner-function noise profiling ...")
profiler = WignerNoiseProfiler(n_qubits=len(G.nodes()))
noise_report = profiler.run()

print(f"  Ideal coherent state negativity  : {noise_report['ideal_negativity']:.4f}")
print(f"  Degraded state negativity        : {noise_report['noisy_negativity']:.4f}")
print(f"  Wigner negativity loss (ΔW)      : {noise_report['delta_negativity']:.4f}")
print(f"  Derived ZNE scale factor (λ)     : {noise_report['noise_scale']:.4f}")
print(f"  Recommended ZNE scale points     : {noise_report['zne_scales']}")

# Base depolarising probability for NISQ hardware model.
# This is a realistic gate error rate for superconducting qubits (~1-3%).
# The noise_report['noise_scale'] is a *multiplier* for ZNE, not a probability.
BASE_NOISE_PROB = 0.025   # 2.5% depolarising per gate — typical NISQ

# ─────────────────────────────────────────────────────────────────────────
# 3.  QAOA — Three Regimes
# ─────────────────────────────────────────────────────────────────────────
print("\n[3/5] Scanning QAOA energy landscapes (this takes ~60 s) ...")

scanner   = LandscapeScanner(G)
engine_ideal  = QAOAEngine(G, noise_level=0.0,             label="Ideal (Noiseless)")
engine_noisy  = QAOAEngine(G, noise_level=BASE_NOISE_PROB,  label="Noisy NISQ")
engine_mitig  = QAOAEngine(G, noise_level=BASE_NOISE_PROB,
                           label="ZNE-Mitigated",
                           zne_scales=noise_report['zne_scales'])

# Coarse landscape scan over (γ, β) grid
gamma_vals = np.linspace(0.01, np.pi,   30)
beta_vals  = np.linspace(0.01, np.pi/2, 30)

print("  Scanning ideal landscape ...")
landscape_ideal = scanner.scan(engine_ideal, gamma_vals, beta_vals)
print("  Scanning noisy landscape ...")
landscape_noisy = scanner.scan(engine_noisy, gamma_vals, beta_vals)
print("  Scanning ZNE-mitigated landscape ...")
landscape_mitig = scanner.scan(engine_mitig, gamma_vals, beta_vals)

# ─────────────────────────────────────────────────────────────────────────
# 4.  Classical Optimization on Each Landscape
# ─────────────────────────────────────────────────────────────────────────
print("\n[4/5] Running classical optimizer (COBYLA) on each landscape ...")

from scipy.optimize import minimize

results = {}
for label, engine in [("Ideal",    engine_ideal),
                       ("Noisy",    engine_noisy),
                       ("Mitigated",engine_mitig)]:
    best_val  = np.inf
    best_params = None
    # 5 random restarts to find global minimum
    for seed in range(5):
        rng = np.random.default_rng(seed)
        x0  = rng.uniform([0.1, 0.1], [np.pi, np.pi/2])
        res = minimize(lambda p: engine.cost(p[0], p[1]),
                       x0, method='COBYLA',
                       options={'maxiter': 300, 'rhobeg': 0.3})
        if res.fun < best_val:
            best_val    = res.fun
            best_params = res.x

    # Decode the bitstring
    opt_bitstring = engine.get_best_bitstring(best_params[0], best_params[1])
    cost_val      = engine.evaluate_cut(opt_bitstring)

    results[label] = {
        'params'    : best_params,
        'raw_cost'  : best_val,
        'bitstring' : opt_bitstring,
        'cut_value' : cost_val,
    }
    print(f"  {label:12s} | γ={best_params[0]:.3f} β={best_params[1]:.3f} "
          f"| cut={cost_val:.4f} | bits={opt_bitstring}")

# Brute-force classical optimum for comparison
classical_opt = scanner.brute_force_max_cut(G)
print(f"  {'Classical':12s} | brute-force max-cut = {classical_opt['cut']:.4f} "
      f"| bits={classical_opt['bitstring']}")

# ─────────────────────────────────────────────────────────────────────────
# 5.  Figures
# ─────────────────────────────────────────────────────────────────────────
print("\n[5/5] Generating figures ...")

GG, BB = np.meshgrid(gamma_vals, beta_vals, indexing='ij')

# ── Custom colour maps ───────────────────────────────────────────────────
cmap_blue  = LinearSegmentedColormap.from_list("b",  ["#0d1b2a","#1b4f72","#2980b9","#aed6f1"])
cmap_red   = LinearSegmentedColormap.from_list("r",  ["#1a0a00","#7b241c","#cb4335","#f1948a"])
cmap_green = LinearSegmentedColormap.from_list("g",  ["#0a1f0f","#1e8449","#27ae60","#a9dfbf"])

fig = plt.figure(figsize=(20, 22), facecolor='#0d0d0d')
fig.suptitle(
    "Phase-Space Noise Calibration for QAOA — Silver Futures Routing\n"
    "Inspired by: Balanced Homodyne Detection without Coherent State LO  "
    "(Dhrithi Maria, Universität Paderborn, 2026)",
    color='white', fontsize=13, y=0.98, fontweight='bold'
)

gs = gridspec.GridSpec(4, 3, figure=fig,
                       hspace=0.45, wspace=0.35,
                       top=0.94, bottom=0.04, left=0.07, right=0.97)

def styled_ax(ax, title, xlabel='', ylabel=''):
    ax.set_facecolor('#111111')
    ax.set_title(title, color='white', fontsize=10, pad=6, fontweight='bold')
    ax.set_xlabel(xlabel, color='#aaaaaa', fontsize=8)
    ax.set_ylabel(ylabel, color='#aaaaaa', fontsize=8)
    ax.tick_params(colors='#888888', labelsize=7)
    for spine in ax.spines.values():
        spine.set_edgecolor('#333333')

# ── Row 0: Wigner functions ──────────────────────────────────────────────
ax_w1 = fig.add_subplot(gs[0, 0])
ax_w2 = fig.add_subplot(gs[0, 1])
ax_w3 = fig.add_subplot(gs[0, 2])

profiler.plot_wigner_panels(ax_w1, ax_w2, ax_w3)
styled_ax(ax_w1, "Wigner: Ideal Coherent LO\n(valid LO, ⟨b̂⟩ ≠ 0, W ≥ 0)", 'x (position)', 'p (momentum)')
styled_ax(ax_w2, "Wigner: Noise-Degraded LO\n(decoherence smooths negativity)", 'x (position)', '')
styled_ax(ax_w3, "Wigner: ZNE-Calibrated\n(negativity partially restored)", 'x (position)', '')

# ── Row 1: Energy landscapes ─────────────────────────────────────────────
for col, (ls, cmap, label) in enumerate(zip(
        [landscape_ideal, landscape_noisy, landscape_mitig],
        [cmap_blue, cmap_red, cmap_green],
        ["Ideal — clear valleys", "Noisy NISQ — flattened", "ZNE-Mitigated — restored"])):
    ax = fig.add_subplot(gs[1, col])
    im = ax.contourf(GG, BB, ls, levels=25, cmap=cmap)
    plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04,
                 label='⟨Cost⟩').ax.yaxis.set_tick_params(color='white', labelcolor='white')
    # mark optimum
    idx = np.unravel_index(np.argmin(ls), ls.shape)
    ax.scatter(GG[idx], BB[idx], color='yellow', s=80, zorder=5,
               edgecolors='white', linewidths=0.8, label=f'min={ls[idx]:.3f}')
    ax.legend(fontsize=7, facecolor='#222222', labelcolor='white', loc='upper right')
    styled_ax(ax, f"QAOA Energy Landscape\n{label}", 'γ (phase)', 'β (mixer)')

# ── Row 2: Convergence curves ────────────────────────────────────────────
ax_conv = fig.add_subplot(gs[2, :2])
ax_bar  = fig.add_subplot(gs[2,  2])
styled_ax(ax_conv, "Optimizer Convergence — COBYLA on Each Landscape",
          'Iteration', 'Cost Function Value')
styled_ax(ax_bar,  "Final Cut Value vs Classical Optimum")

conv_colors = {'Ideal': '#2980b9', 'Noisy': '#cb4335', 'Mitigated': '#27ae60'}
conv_data = {}
for label, engine in [("Ideal", engine_ideal), ("Noisy", engine_noisy),
                       ("Mitigated", engine_mitig)]:
    history = []
    rng = np.random.default_rng(42)
    x0  = rng.uniform([0.1, 0.1], [np.pi, np.pi/2])
    def cb(xk, history=history, eng=engine):
        history.append(eng.cost(xk[0], xk[1]))
    minimize(lambda p: engine.cost(p[0], p[1]), x0,
             method='COBYLA', callback=cb,
             options={'maxiter': 200, 'rhobeg': 0.3})
    conv_data[label] = history
    ax_conv.plot(history, color=conv_colors[label], label=label,
                 linewidth=1.8, alpha=0.9)

ax_conv.legend(facecolor='#222222', labelcolor='white', fontsize=9)
ax_conv.axhline(y=min(conv_data['Ideal']), color='#2980b9',
                linestyle='--', alpha=0.4, linewidth=1)

# Bar chart of final results
bar_labels  = ['Ideal QAOA', 'Noisy QAOA', 'ZNE-Mitigated', 'Classical\nBrute-Force']
bar_values  = [results['Ideal']['cut_value'],
               results['Noisy']['cut_value'],
               results['Mitigated']['cut_value'],
               classical_opt['cut']]
bar_colors  = ['#2980b9', '#cb4335', '#27ae60', '#f39c12']
bars = ax_bar.bar(bar_labels, bar_values, color=bar_colors,
                  edgecolor='white', linewidth=0.5, width=0.6)
for bar, val in zip(bars, bar_values):
    ax_bar.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02,
                f'{val:.3f}', ha='center', va='bottom',
                color='white', fontsize=8, fontweight='bold')
ax_bar.set_ylim(0, max(bar_values) * 1.2)
ax_bar.tick_params(axis='x', labelsize=7, colors='#aaaaaa')
ax_bar.tick_params(axis='y', labelsize=7, colors='#aaaaaa')
ax_bar.set_ylabel('Max-Cut Value (lower slippage = better)', color='#aaaaaa', fontsize=8)

# ── Row 3: Financial graph + variance decomposition + summary ────────────
ax_graph = fig.add_subplot(gs[3, 0])
ax_var   = fig.add_subplot(gs[3, 1])
ax_txt   = fig.add_subplot(gs[3, 2])
styled_ax(ax_graph, "Silver Futures Execution Graph\n(nodes = exchanges, edges = execution cost)")
styled_ax(ax_var,   "Variance Decomposition — Thesis Analogy\n"
                    "Var(δ̂) = |⟨b̂⟩|² · Var_signal  +  Var_LO")

# Draw graph
pos = nx.spring_layout(G, seed=7)
node_colors = ['#f39c12' if G.nodes[n].get('hub') else '#2980b9' for n in G.nodes()]
nx.draw_networkx_nodes(G, pos, ax=ax_graph, node_color=node_colors,
                       node_size=350, alpha=0.95)
nx.draw_networkx_labels(G, pos, ax=ax_graph, font_color='white',
                        font_size=7, font_weight='bold',
                        labels={n: G.nodes[n].get('label', str(n)) for n in G.nodes()})
weights = nx.get_edge_attributes(G, 'weight')
edge_labels = {k: f"{v:.1f}" for k, v in weights.items()}
nx.draw_networkx_edges(G, pos, ax=ax_graph, edge_color='#888888',
                       width=[weights[e]*0.6 for e in G.edges()], alpha=0.8)
nx.draw_networkx_edge_labels(G, pos, edge_labels, ax=ax_graph,
                             font_color='#aaaaaa', font_size=6)
ax_graph.set_facecolor('#111111')
ax_graph.axis('off')

# Variance bar chart — thesis analogy
phi_vals   = [0, np.pi/4, np.pi/2]
phi_labels = ['φ=0', 'φ=π/4', 'φ=π/2']
var_signal = [0.37, 1.54, 2.72]   # corresponds to squeezed signal
var_lo     = [2.0,  2.0,  2.0]    # LO noise floor (flat, phase-invariant)
var_noisy  = [vs + vl for vs, vl in zip(var_signal, var_lo)]

x = np.arange(len(phi_labels))
w = 0.28
ax_var.bar(x - w, var_noisy,  w, label='Var(δ̂) total (measured)',  color='#cb4335', alpha=0.85)
ax_var.bar(x,     var_lo,     w, label='Var_LO (calibration step)', color='#f39c12', alpha=0.85)
ax_var.bar(x + w, var_signal, w, label='Var_signal (recovered)',    color='#27ae60', alpha=0.85)
ax_var.set_xticks(x); ax_var.set_xticklabels(phi_labels, color='#aaaaaa', fontsize=8)
ax_var.legend(facecolor='#222222', labelcolor='white', fontsize=6, loc='upper left')
ax_var.set_ylabel('Variance', color='#aaaaaa', fontsize=8)

# Text summary panel
ax_txt.axis('off')
ax_txt.set_facecolor('#111111')
improvement = ((results['Mitigated']['cut_value'] - results['Noisy']['cut_value'])
               / abs(results['Noisy']['cut_value']) * 100
               if results['Noisy']['cut_value'] != 0 else 0)
recovery    = ((results['Mitigated']['cut_value'] - results['Noisy']['cut_value'])
               / (results['Ideal']['cut_value'] - results['Noisy']['cut_value']) * 100
               if (results['Ideal']['cut_value'] - results['Noisy']['cut_value']) != 0 else 0)

summary = (
    f"RESULTS SUMMARY\n"
    f"{'─'*32}\n\n"
    f"Thesis core result:\n"
    f"  ⟨b̂⟩ ≠ 0  →  valid LO\n"
    f"  Calibration isolates Var_signal\n\n"
    f"QAOA analog:\n"
    f"  Wigner negativity loss = noise\n"
    f"  ZNE restores landscape\n\n"
    f"Cut values:\n"
    f"  Ideal QAOA    : {results['Ideal']['cut_value']:.4f}\n"
    f"  Noisy QAOA    : {results['Noisy']['cut_value']:.4f}\n"
    f"  ZNE-Mitigated : {results['Mitigated']['cut_value']:.4f}\n"
    f"  Classical opt : {classical_opt['cut']:.4f}\n\n"
    f"Landscape recovery : {recovery:.1f}%\n"
    f"Noise scale (λ)    : {noise_report['noise_scale']:.4f}\n"
    f"ΔW (negativity)    : {noise_report['delta_negativity']:.4f}\n\n"
    f"Optimal route:\n"
    f"  {results['Mitigated']['bitstring']}\n"
    f"  (1=execute, 0=skip)"
)
ax_txt.text(0.05, 0.97, summary, transform=ax_txt.transAxes,
            color='white', fontsize=8.5, va='top', ha='left',
            fontfamily='monospace',
            bbox=dict(boxstyle='round,pad=0.5', facecolor='#1a1a1a',
                      edgecolor='#27ae60', linewidth=1.2))

plt.savefig("results/full_analysis.png", dpi=150, bbox_inches='tight',
            facecolor='#0d0d0d')
print("  Saved: results/full_analysis.png")

# ── Figure 2: Detailed Wigner profiling ──────────────────────────────────
profiler.plot_full_wigner_analysis("results/wigner_analysis.png")
print("  Saved: results/wigner_analysis.png")

print("\n" + "=" * 70)
print("  SIMULATION COMPLETE")
print("=" * 70)
print(f"\n  Ideal QAOA cut value    : {results['Ideal']['cut_value']:.4f}")
print(f"  Noisy QAOA cut value    : {results['Noisy']['cut_value']:.4f}")
print(f"  ZNE-Mitigated cut value : {results['Mitigated']['cut_value']:.4f}")
print(f"  Classical optimum       : {classical_opt['cut']:.4f}")
print(f"  Landscape recovery      : {recovery:.1f}%")
print(f"\n  Figures saved in: ./results/")
print("=" * 70)
