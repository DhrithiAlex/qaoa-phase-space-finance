"""
qaoa_engine.py
--------------
QAOA circuit engine with three operating modes:
  1. Ideal       — noiseless simulator (ground truth)
  2. Noisy       — depolarising channel per gate (NISQ hardware model)
  3. ZNE         — Zero-Noise Extrapolation using Wigner-derived scale factors

THESIS CONNECTION
-----------------
The core equation in the thesis (Eq. 2.32 / 4.2) is:

    Var(δ̂(φ)) = |⟨b̂⟩|² · Var_signal(φ)  +  Var_LO(φ)

Rearranged, the signal is recovered by:

    Var_signal(φ) = [Var(δ̂(φ)) − Var_LO(φ)] / |⟨b̂⟩|²

In QAOA terms:

    E_measured(γ, β) = E_true(γ, β)  +  E_noise(γ, β)

ZNE recovers E_true by:
  1. Running the circuit at noise scales λ₁ < λ₂ < λ₃
  2. Fitting a polynomial to [E(λ₁), E(λ₂), E(λ₃)] vs [λ₁, λ₂, λ₃]
  3. Extrapolating to λ = 0  →  E_true

This is precisely parallel to the law of total variance + vacuum
substitution calibration of Chapter 4 of the thesis.

QAOA COST FUNCTION
------------------
We implement the weighted Max-Cut cost Hamiltonian:

    H_C = Σ_{(i,j)∈E} w_{ij} · (I − Z_i Z_j) / 2

The QAOA ansatz alternates between:
  Cost layer:   exp(−i γ H_C)  →  IsingZZ rotations
  Mixer layer:  exp(−i β H_B)  →  RX rotations (B = Σ_i X_i)

We use p=1 (single layer) for clarity; p can be increased for better
approximation ratios.
"""

import numpy as np
import pennylane as qml
from typing import List, Optional
import networkx as nx


class QAOAEngine:
    """
    Weighted Max-Cut QAOA engine.

    Parameters
    ----------
    G           : weighted NetworkX graph
    noise_level : depolarising noise probability per gate (0 = ideal)
    label       : human-readable name for this engine
    zne_scales  : list of noise scale factors for ZNE (None = no ZNE)
    p_layers    : number of QAOA layers (default 1)
    n_shots     : number of measurement shots (None = exact statevector)
    """

    def __init__(
        self,
        G: nx.Graph,
        noise_level: float = 0.0,
        label: str = "QAOA",
        zne_scales: Optional[List[float]] = None,
        p_layers: int = 1,
        n_shots: Optional[int] = None,
    ):
        self.G           = G
        self.noise_level = noise_level
        self.label       = label
        self.zne_scales  = zne_scales          # None → pure noisy (no ZNE)
        self.p_layers    = p_layers
        self.n_shots     = n_shots
        self.n_qubits    = G.number_of_nodes()

        self.edges   = list(G.edges(data=True))
        self.weights = {(u, v): d['weight'] for u, v, d in self.edges}

        # Devices: one noiseless for ideal, one mixed for noisy
        self._dev_ideal = qml.device('default.qubit', wires=self.n_qubits,
                                     shots=n_shots)
        self._dev_noisy = qml.device('default.mixed', wires=self.n_qubits,
                                     shots=n_shots)

    # ── Circuit building blocks ──────────────────────────────────────────

    def _cost_layer(self, gamma: float, noise: float = 0.0) -> None:
        """Apply the cost Hamiltonian layer exp(−i γ H_C)."""
        for u, v, d in self.edges:
            w = d['weight']
            qml.IsingZZ(2 * gamma * w, wires=[u, v])
            if noise > 0:
                qml.DepolarizingChannel(noise, wires=u)
                qml.DepolarizingChannel(noise, wires=v)

    def _mixer_layer(self, beta: float, noise: float = 0.0) -> None:
        """Apply the mixer Hamiltonian layer exp(−i β H_B)."""
        for i in range(self.n_qubits):
            qml.RX(2 * beta, wires=i)
            if noise > 0:
                qml.DepolarizingChannel(noise, wires=i)

    # ── Cost operator ────────────────────────────────────────────────────

    def _cost_observable(self):
        """Build the Max-Cut cost observable Σ w_{ij}(I − Z_i Z_j)/2."""
        terms = []
        for u, v, d in self.edges:
            w = d['weight']
            # w/2 · I term contributes a constant — omit for optimisation
            # −w/2 · ZZ term drives the minimisation
            terms.append(-w / 2 * qml.PauliZ(u) @ qml.PauliZ(v))
        return qml.sum(*terms)

    # ── QNodes ───────────────────────────────────────────────────────────

    def _make_ideal_qnode(self):
        obs = self._cost_observable()

        @qml.qnode(self._dev_ideal)
        def circuit(gamma, beta):
            for i in range(self.n_qubits):
                qml.Hadamard(wires=i)
            for _ in range(self.p_layers):
                self._cost_layer(gamma, noise=0.0)
                self._mixer_layer(beta,  noise=0.0)
            return qml.expval(obs)

        return circuit

    def _make_noisy_qnode(self, effective_noise: float):
        obs = self._cost_observable()

        @qml.qnode(self._dev_noisy)
        def circuit(gamma, beta):
            for i in range(self.n_qubits):
                qml.Hadamard(wires=i)
                qml.DepolarizingChannel(effective_noise * 0.5, wires=i)
            for _ in range(self.p_layers):
                self._cost_layer(gamma, noise=effective_noise)
                self._mixer_layer(beta,  noise=effective_noise)
            return qml.expval(obs)

        return circuit

    # ── Public interface ─────────────────────────────────────────────────

    def cost(self, gamma: float, beta: float) -> float:
        """
        Evaluate the QAOA cost function at (γ, β).

        If ZNE scales are set, applies Zero-Noise Extrapolation:
          1. Evaluate cost at each noise scale λ_k · ε
          2. Fit Richardson extrapolation to λ = 0
          3. Return the extrapolated (noise-free estimate) value

        Otherwise, evaluate at the nominal noise level.

        Returns the cost value (float). The optimizer minimises this.
        """
        if self.noise_level == 0.0:
            # Ideal — use statevector
            circuit = self._make_ideal_qnode()
            return float(circuit(gamma, beta))

        if self.zne_scales is None:
            # Raw noisy — no mitigation
            circuit = self._make_noisy_qnode(self.noise_level)
            return float(circuit(gamma, beta))

        # ── ZNE mitigation ──────────────────────────────────────────────
        # Evaluate at each noise scale
        vals   = []
        scales = self.zne_scales
        for scale in scales:
            eff_noise = min(self.noise_level * scale, 0.5)
            circuit   = self._make_noisy_qnode(eff_noise)
            vals.append(float(circuit(gamma, beta)))

        # Richardson / polynomial extrapolation to λ = 0
        # Fit polynomial of degree len(scales)−1 in λ and evaluate at λ=0
        try:
            coeffs = np.polyfit(scales, vals, deg=min(len(scales) - 1, 2))
            extrapolated = float(np.polyval(coeffs, 0.0))
        except np.linalg.LinAlgError:
            extrapolated = vals[0]   # fallback to lowest noise

        return extrapolated

    def get_best_bitstring(self, gamma: float, beta: float) -> str:
        """
        Sample the QAOA state at (γ, β) and return the most probable bitstring.
        Uses noiseless sampling for a clean readout.
        """
        obs_terms = [qml.PauliZ(i) for i in range(self.n_qubits)]

        @qml.qnode(self._dev_ideal)
        def state_circuit(g, b):
            for i in range(self.n_qubits):
                qml.Hadamard(wires=i)
            for _ in range(self.p_layers):
                self._cost_layer(g, noise=0.0)
                self._mixer_layer(b, noise=0.0)
            return qml.state()

        state_vec = state_circuit(gamma, beta)
        probs = np.abs(state_vec) ** 2
        best_idx = int(np.argmax(probs))
        return format(best_idx, f'0{self.n_qubits}b')

    def evaluate_cut(self, bitstring: str) -> float:
        """
        Evaluate the Max-Cut value for a given bitstring assignment.

        Parameters
        ----------
        bitstring : binary string of length n_qubits
                    '1' = node in set S, '0' = node in set S̄

        Returns
        -------
        cut_weight : sum of weights of edges crossing the partition
        """
        assignment = [int(b) for b in bitstring]
        cut = 0.0
        for u, v, d in self.edges:
            if assignment[u] != assignment[v]:
                cut += d['weight']
        return cut
