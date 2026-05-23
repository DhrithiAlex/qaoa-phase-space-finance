## Installation

### Requirements

- Python 3.9+
- PennyLane (quantum circuit simulation)
- NumPy, SciPy, Matplotlib, NetworkX

### Setup

```bash
# Clone the repository
git clone https://github.com/DhrithiAlex/qaoa-phase-space-finance.git
cd qaoa-phase-space-finance

# Create and activate a virtual environment (recommended)
python -m venv venv

# On Windows (VS Code terminal):
venv\Scripts\activate

# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

---

## Usage

```bash
python simulation.py
```

**Expected runtime**: 2–5 minutes on a modern laptop.  
The landscape scan runs 30×30 = 900 circuit evaluations × 3 regimes (2,700 total).

**Outputs** (saved to `results/`):
- `results/full_analysis.png` — 4-row composite figure (main result)
- `results/wigner_analysis.png` — Detailed Wigner profiling (6 panels)

### Advanced Usage

```python
from market_graph import build_silver_futures_graph
from qaoa_engine import QAOAEngine

# Build the financial graph
G = build_silver_futures_graph()

# Run ideal QAOA at a specific (γ, β) point
engine = QAOAEngine(G, noise_level=0.0, label="Ideal")
cost = engine.cost(gamma=0.5, beta=0.3)
print(f"Cost at (0.5, 0.3): {cost:.4f}")

# Decode the optimal partition bitstring
bitstring = engine.get_best_bitstring(0.5, 0.3)
cut_weight = engine.evaluate_cut(bitstring)
print(f"Partition: {bitstring} → Max-Cut = {cut_weight:.4f}")
from landscape import ZNECalibrator



```
