"""
landscape.py
------------
Scans the QAOA energy landscape over a (γ, β) grid and provides
brute-force classical Max-Cut for comparison.

zne_calibration.py contents are also here to keep the file count clean.

THESIS CONNECTION
-----------------
In Chapter 6 of the thesis, the signal covariance matrix is reconstructed
by sweeping the LO phase φ ∈ {0, π/4, π/2} and building a linear system.

Here we sweep (γ, β) on a 2D grid — the analogous operation in QAOA space.
The landscape scan reveals:
  - Ideal:    clear valleys at optimal (γ*, β*)
  - Noisy:    landscape flattened — valleys filled, gradient ≈ 0
  - Mitigated: valleys restored — optimizer can navigate again

The recovery is quantified exactly as in the thesis:
  Recovery(%) = [E_mitig − E_noisy] / [E_ideal − E_noisy] × 100
  Analogous to: Var_signal recovered after subtracting Var_LO
"""

import numpy as np
import networkx as nx
from itertools import product


class LandscapeScanner:
    """
    Scan the QAOA cost function over a (γ, β) grid.

    Parameters
    ----------
    G : weighted NetworkX graph
    """

    def __init__(self, G: nx.Graph):
        self.G = G

    def scan(self, engine, gamma_vals: np.ndarray, beta_vals: np.ndarray) -> np.ndarray:
        """
        Evaluate engine.cost(γ, β) on a full 2D grid.

        Returns
        -------
        landscape : ndarray of shape (len(gamma_vals), len(beta_vals))
        """
        landscape = np.zeros((len(gamma_vals), len(beta_vals)))
        for i, g in enumerate(gamma_vals):
            for j, b in enumerate(beta_vals):
                landscape[i, j] = engine.cost(g, b)
        return landscape

    def brute_force_max_cut(self, G: nx.Graph) -> dict:
        """
        Find the optimal Max-Cut by exhaustive search over all 2^n bitstrings.

        For n ≤ 20 this is tractable. Returns the best partition and its weight.
        """
        n = G.number_of_nodes()
        edges = list(G.edges(data=True))
        best_cut   = -np.inf
        best_bits  = '0' * n

        for bits in product('01', repeat=n):
            assignment = [int(b) for b in bits]
            cut = sum(d['weight'] for u, v, d in edges
                      if assignment[u] != assignment[v])
            if cut > best_cut:
                best_cut  = cut
                best_bits = ''.join(bits)

        return {'cut': best_cut, 'bitstring': best_bits}


# ─────────────────────────────────────────────────────────────────────────
# ZNE Calibrator (standalone utility, used by QAOAEngine internally)
# ─────────────────────────────────────────────────────────────────────────

class ZNECalibrator:
    """
    Zero-Noise Extrapolation calibrator.

    Given a set of (noise_scale, expectation_value) pairs, fits a polynomial
    and extrapolates to noise_scale = 0 to recover the noiseless estimate.

    THESIS PARALLEL
    ---------------
    ZNE is algebraically identical to the law-of-total-variance subtraction:

      Var_signal = [Var_total − Var_LO] / |⟨b̂⟩|²

    ZNE version:
      E_true ≈ Polynomial(λ=0)  where  E(λ) = E_true + λ · E_noise

    Both procedures isolate the true quantum signal by measuring and
    subtracting the noise contribution at multiple operating points.

    Parameters
    ----------
    degree : polynomial degree for extrapolation (1=linear, 2=quadratic)
    """

    def __init__(self, degree: int = 2):
        self.degree = degree

    def extrapolate(self, scales: list, values: list) -> float:
        """
        Extrapolate to zero noise.

        Parameters
        ----------
        scales : list of noise scale factors [λ₁, λ₂, ...]
        values : corresponding expectation values [E(λ₁), E(λ₂), ...]

        Returns
        -------
        E_zero : float, estimated noiseless expectation value
        """
        scales = np.asarray(scales, dtype=float)
        values = np.asarray(values, dtype=float)
        deg    = min(self.degree, len(scales) - 1)
        try:
            coeffs = np.polyfit(scales, values, deg=deg)
            return float(np.polyval(coeffs, 0.0))
        except (np.linalg.LinAlgError, ValueError):
            return float(values[0])   # fallback to lowest-noise point

    def extrapolate_landscape(
        self,
        scales: list,
        landscapes: list,
    ) -> np.ndarray:
        """
        Apply ZNE pixel-by-pixel across a set of landscapes.

        Parameters
        ----------
        scales     : list of noise scale factors
        landscapes : list of 2D arrays, one per scale

        Returns
        -------
        recovered : 2D array with ZNE-corrected values
        """
        shape     = landscapes[0].shape
        recovered = np.zeros(shape)
        for i in range(shape[0]):
            for j in range(shape[1]):
                vals = [ls[i, j] for ls in landscapes]
                recovered[i, j] = self.extrapolate(scales, vals)
        return recovered
