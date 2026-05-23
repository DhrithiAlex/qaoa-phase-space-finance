# Thesis Analogy Map: CV Quantum Optics → QAOA Finance

This document provides a detailed mapping between the theoretical framework of  
*"Balanced Homodyne Detection without Coherent State Local Oscillator"*  
(Dhrithi Maria, Universität Paderborn, 2026) and each component of this simulation.

---

## Core Mathematical Isomorphism

### Thesis (Homodyne Detection)

The difference photocurrent variance in balanced homodyne detection with an imperfect LO:

```
Var(δ̂(φ)) = |⟨b̂⟩|² · Var_signal(φ)  +  Var_LO(φ)
```

Where:
- `δ̂(φ)` — difference photocurrent at LO phase φ
- `⟨b̂⟩` — mean field of the LO (coherence amplitude)
- `Var_signal(φ)` — true signal quadrature variance (what we want)
- `Var_LO(φ)` — LO noise contribution (what we must remove)

The calibration protocol (vacuum substitution) measures `Var_LO` independently and recovers:

```
Var_signal(φ) = [Var(δ̂(φ)) − Var_LO(φ)] / |⟨b̂⟩|²
```

**Validity condition**: `⟨b̂⟩ ≠ 0` — the LO must carry a non-zero mean field.

---

### This Simulation (QAOA)

The measured QAOA energy landscape on NISQ hardware:

```
E_measured(γ, β) = E_true(γ, β)  +  λ · E_noise(γ, β)
```

Where:
- `E_measured` — expectation value observed on noisy hardware
- `E_true` — noiseless landscape (what the optimizer needs)
- `λ` — noise scale factor (decoherence strength)
- `E_noise` — landscape distortion due to gate errors

ZNE recovers `E_true` by:

```
E_true ≈ P(λ=0)   where   P fits {(λ₁, E(λ₁)), (λ₂, E(λ₂)), (λ₃, E(λ₃))}
```

**Validity condition**: Wigner peak amplitude `W_peak > 0` — the microwave pulse retains coherence.

---

## Chapter-by-Chapter Reference Map

### Chapter 1: Experimental Setup

| Thesis | Simulation |
|--------|------------|
| Beam splitter separates signal and LO modes | QAOA Hadamard initialises superposition across all computational basis states |
| Balanced detector measures photocurrent difference | PennyLane `qml.expval(H_C)` measures the cost Hamiltonian expectation |
| Local Oscillator drives interference | Phase parameters `(γ, β)` control interference between cost and mixer layers |

**Relevant file**: `qaoa_engine.py` → `_make_ideal_qnode()`, `_make_noisy_qnode()`

---

### Chapter 2: Photocurrent Operator and Wigner Functions

| Thesis | Simulation |
|--------|------------|
| Difference photocurrent `δ̂(φ) = â†b̂e^{iφ} + h.c.` | Cost Hamiltonian `H_C = Σ w_{ij}(I − Z_iZ_j)/2` |
| Wigner function `W(x,p)` encodes full quantum state | `wigner_calibrate.py` computes `W_ideal`, `W_noisy`, `W_zne` |
| Phase-space negativity signals non-classicality | Wigner negativity loss `ΔW` quantifies decoherence severity |

**Relevant file**: `wigner_calibrate.py` → `WignerNoiseProfiler.run()`

---

### Chapter 3: Validity of the LO

| Thesis | Simulation |
|--------|------------|
| Condition `⟨b̂⟩ ≠ 0` must be verified | Wigner peak `W_peak(x,p)` must remain positive |
| Coherent state LO has `⟨b̂⟩ = α ≠ 0` | Ideal squeezed state has `W_peak = 0.633` (maximum) |
| Degraded LO reduces `|⟨b̂⟩|`, increasing noise floor | NISQ decoherence reduces `W_peak` to `0.611` (3.5% loss) |
| If `⟨b̂⟩ = 0`, calibration fails entirely | If `W_peak → 0`, ZNE cannot recover the landscape |

**Relevant file**: `wigner_calibrate.py` → `noise_report['ideal_negativity']`, `noise_report['noisy_negativity']`

---

### Chapter 4: Law of Total Variance and Calibration

This is the deepest analogy in the project.

| Thesis | Simulation |
|--------|------------|
| Law of total variance separates Var_signal from Var_LO | ZNE separates `E_true` from `E_noise` |
| Vacuum substitution: replace signal with vacuum, measure Var_LO | Noise scaling: run circuit at `λ₁, λ₂, λ₃`, measure `E(λ_k)` |
| Subtract: `Var_signal = (Var_total − Var_LO) / |⟨b̂⟩|²` | Extrapolate: fit polynomial to `{(λ_k, E(λ_k))}`, evaluate at `λ=0` |
| Covariance matrix Γ reconstructed from 3 LO phases | Energy landscape reconstructed from 3 ZNE scale points |

**Relevant file**: `landscape.py` → `ZNECalibrator.extrapolate()`, `qaoa_engine.py` → ZNE branch in `cost()`

---

### Chapter 5: Non-Classicality Criteria and Stress Tests

| Thesis | Simulation |
|--------|------------|
| D-criterion: squeezing below vacuum noise level | Cut weight below classical brute-force optimum |
| Squeezed LO: signal recovery under non-Gaussian LO | Noisy NISQ vs ZNE-mitigated landscape comparison |
| Negativity threshold: minimum `W_peak` for valid calibration | Minimum Wigner coherence for ZNE validity |

**Relevant file**: `landscape.py` → `LandscapeScanner.brute_force_max_cut()`

---

### Chapter 6: Covariance Matrix Reconstruction

| Thesis | Simulation |
|--------|------------|
| Covariance matrix `Γ` reconstructed by sweeping `φ ∈ {0, π/4, π/2}` | Energy landscape scanned over 30×30 `(γ, β)` grid |
| Linear system built from 3 quadrature measurements | Polynomial system built from 3 ZNE scale points |
| Eigenvalue analysis certifies squeezing | Landscape minima certify QAOA approximation ratio |

**Relevant file**: `landscape.py` → `LandscapeScanner.scan()`

---

## Recovery Metric

The landscape recovery percentage directly parallels the thesis's signal-to-noise recovery:

```
Recovery(%) = [E_mitig − E_noisy] / [E_ideal − E_noisy] × 100

Thesis analog: SNR_recovery = [Var_recovered − Var_noisy] / [Var_ideal − Var_noisy] × 100
```

Both measure what fraction of the true signal was successfully isolated from the noise floor.

---

## Future Extensions (Section 7.1.1 Analog)

| Thesis Extension | QAOA Extension |
|---|---|
| Multi-mode LO with entangled modes | Multi-layer QAOA (p > 1) with entangled parameters |
| Hardware-level LO noise characterization | Pulse-level gate stretching for hardware ZNE |
| Frequency-dependent squeezing | Frequency-dependent noise model (non-Markovian) |
| Real-time adaptive calibration | Online ZNE with adaptive scale selection |
| Non-Gaussian state tomography | Shot-noise limited QAOA with measurement backaction |
