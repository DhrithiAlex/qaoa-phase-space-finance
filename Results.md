# Phase-Space Noise Calibration for QAOA-Based Financial Optimization


 ![](wigner_analysis.png)


<p align="center">
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/Python-3.9%2B-blue?logo=python&logoColor=white" alt="Python"></a>
  <a href="https://pennylane.ai/"><img src="https://img.shields.io/badge/PennyLane-quantum-blueviolet?logo=data:image/svg+xml;base64," alt="PennyLane"></a>
  <img src="https://img.shields.io/badge/QAOA-p%3D1-green" alt="QAOA">
  <img src="https://img.shields.io/badge/ZNE-Richardson-orange" alt="ZNE">
  <img src="https://img.shields.io/badge/Finance-Silver%20Futures-yellow" alt="Finance">
  <img src="https://img.shields.io/badge/License-MIT-lightgrey" alt="License">
</p>

> **A research simulation bridging continuous-variable quantum optics and near-term quantum computing for financial routing optimization.**  
> Inspired by: *"Balanced Homodyne Detection without Coherent State Local Oscillator"* — Master's Thesis, Dhrithi Maria, Universität Paderborn (2026)

---

## Overview

This project applies a theoretical calibration insight from quantum optics — the law-of-total-variance decomposition used in homodyne detection — to the problem of noise mitigation in QAOA circuits running on NISQ hardware.

The core claim: **the mathematical structure of LO noise in balanced homodyne detection is isomorphic to gate decoherence noise in QAOA**, and the same calibration protocol (measuring and subtracting the noise contribution) can recover the true quantum signal in both settings.

The application domain is **silver futures execution routing**: a Max-Cut problem over a 6-node graph of global trading venues, where QAOA determines the optimal partition of exchanges to minimize execution slippage, latency cost, and liquidity risk.

---

## The Core Analogy

| Thesis: CV Quantum Optics | This Project: QAOA Finance |
|---|---|
| LO noise corrupts photocurrent variance | Gate decoherence corrupts the energy landscape |
| `Var(δ̂) = \|⟨b̂⟩\|² · Var_signal + Var_LO` | `E_meas(γ,β) = E_true(γ,β) + λ · E_noise(γ,β)` |
| Vacuum substitution measures `Var_LO` | Wigner-function profiling measures decoherence strength |
| Subtract `Var_LO`, recover `Var_signal` | ZNE extrapolates to `λ=0`, recovers `E_true` |
| `⟨b̂⟩ ≠ 0` is the validity condition | Wigner peak amplitude > 0 is the validity proxy |
| Law of total variance (Chapter 4) | Richardson polynomial extrapolation |
| Certified squeezing via eigenvalues | Certified routing via Max-Cut weight |

---

## What This Simulation Does

1. **Builds a financial graph** — 6 global silver futures venues (CME, LME, COMEX, SGX, TOCOM, SHFE) with edge weights encoding execution cost (slippage × latency × liquidity risk)
2. **Profiles hardware noise** — Wigner-function analysis of a coherent microwave pulse under NISQ decoherence; derives ZNE scale factors from negativity loss `ΔW`
3. **Runs QAOA in three regimes**:
   - **Ideal**: noiseless statevector simulation (ground truth)
   - **Noisy**: depolarising channel per gate at 2.5% error rate (NISQ model)
   - **ZNE-Mitigated**: Wigner-informed Zero-Noise Extrapolation, polynomial fit to `λ=0`
4. **Scans energy landscapes** — 30×30 grid over `(γ, β)` parameter space for all three engines
5. **Optimizes with COBYLA** — 5 random restarts per engine, reports final Max-Cut values
6. **Benchmarks against classical brute-force** — exhaustive `2⁶` bitstring search for comparison
7. **Generates publication-quality figures** — composite 4-row analysis plot + detailed Wigner profiling

---

## Key Results

| Regime | Max-Cut Value | Notes |
|---|---|---|
| Ideal QAOA | ground truth | Noiseless statevector |
| Noisy QAOA | degraded | 2.5% depolarising per gate |
| ZNE-Mitigated | recovered | Wigner-informed Richardson extrapolation |
| Classical Brute-Force | optimal | Exhaustive `2⁶` search |

The landscape recovery metric — `[E_mitig − E_noisy] / [E_ideal − E_noisy] × 100%` — directly parallels the thesis's signal recovery after LO noise subtraction.

---


---


---
## Financial Application

Six global silver futures venues are modelled as a weighted graph:

| Node | Venue | Type |
|---|---|---|
| 0 | CME (Chicago) | Hub |
| 1 | LME (London) | Hub |
| 2 | COMEX (New York) | High liquidity |
| 3 | SGX (Singapore) | Asia-Pacific gateway |
| 4 | TOCOM (Tokyo) | Low liquidity |
| 5 | SHFE (Shanghai) | CNY-denominated |

Edge weights encode a composite cost score (slippage × latency penalty × liquidity risk). The Max-Cut partition separates venues to execute through from venues to skip, maximizing avoided cost.

---

## Honest Limitations

This is a simulation study, not a hardware experiment:

- **p=1 QAOA**: single-layer circuits. Deeper circuits give better approximation ratios but are noisier.
- **Depolarising noise**: simplified independent noise per gate. Real superconducting qubits have correlated errors, crosstalk, and non-Markovian dynamics.
- **ZNE heuristics**: scale factors derived analytically from Wigner analysis. Hardware deployment would use pulse-level gate time stretching.
- **6-node graph**: brute-force classical benchmark is tractable here. Larger graphs require classical heuristics (simulated annealing, Gurobi).
- **Financial model**: illustrative. Production HFT systems use FPGA-based execution at nanosecond timescales; quantum advantage in this domain is a long-term research question.

---
