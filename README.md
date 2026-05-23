# Phase-Space Noise Calibration for QAOA in Financial Optimization

<p align="center">
  <img src="assets/wigner_analysis.png" alt="Wigner Function Analysis" width="800"/>
</p>

<p align="center">
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.9%2B-blue?logo=python&logoColor=white" alt="Python"></a>
  <a href="https://pennylane.ai/"><img src="https://img.shields.io/badge/PennyLane-Quantum-blueviolet" alt="PennyLane"></a>
  <a href="https://github.com/DhrithiAlex/qaoa-phase-space-finance/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-MIT-lightgrey" alt="MIT License"></a>
  <img src="https://img.shields.io/badge/QAOA-p%3D1-green" alt="QAOA">
  <img src="https://img.shields.io/badge/ZNE-Mitigation-orange" alt="Zero Noise Extrapolation">
  <img src="https://img.shields.io/badge/Domain-Finance%20%7C%20Quantum-yellow" alt="Finance + Quantum">
</p>

> Bridging continuous-variable quantum optics and near-term quantum algorithms for robust financial portfolio routing optimization.

**Inspired by** *Balanced Homodyne Detection without Coherent State Local Oscillator* — Master's Thesis, Dhrithi Maria, Universität Paderborn (2026).

---

## ✨ Overview

This project demonstrates how insights from quantum optics (law-of-total-variance in homodyne detection) can be applied to mitigate noise in **QAOA** circuits for a real-world financial optimization problem: optimal execution routing across global silver futures venues.

The core claim: **the mathematical structure of LO noise in balanced homodyne detection is isomorphic to gate decoherence noise in QAOA**, and the same calibration protocol (measuring and subtracting the noise contribution) can recover the true quantum signal in both settings.

The application domain is **silver futures execution routing**: a Max-Cut problem over a 6-node graph of global trading venues, where QAOA determines the optimal partition of exchanges to minimize execution slippage, latency cost, and liquidity risk.

**Key Innovation**: Wigner-function-based noise profiling → informed **Zero-Noise Extrapolation (ZNE)** for recovering clean energy landscapes on noisy quantum hardware.

---

## 🎯 Features

- Realistic 6-node Max-Cut graph for silver futures venues (CME, LME, COMEX, etc.)
- Full QAOA pipeline (ideal, noisy, ZNE-mitigated)
- Wigner function noise calibration
- Energy landscape visualization + optimization
- Publication-ready figures
- Reproducible results with detailed benchmarks

---

## 🚀 Quick Start

```bash
# Clone the repo
git clone https://github.com/DhrithiAlex/qaoa-phase-space-finance.git
cd qaoa-phase-space-finance

# Create virtual environment
python -m venv venv
source venv/bin/activate    # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the full simulation
python simulation.py
