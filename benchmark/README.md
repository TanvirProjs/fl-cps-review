# Reference benchmark: continual, uncertainty-aware and structure-consistent FL on the IEEE 33-bus feeder

Online Resource 6 of the review "Continual, Uncertainty-Aware and Structure-Consistent Federated Learning for Distributed Cyber-Physical Systems and Edge Digital Twins: A Critical Review, Unified Formulation and Reproducible Benchmark". The code reproduces every number in Tables 13–15
and Figs. 6–8 of Section 10.

## Requirements

Python 3.10 or later with numpy, pandas, matplotlib and pandapower (2.13 or later). No GPU is needed.

## Reproduce everything

```bash
./run_all.sh              # JOBS=4 ./run_all.sh to use four cores
```

Runtime on two CPU cores: about 3 minutes for the power-flow data (5 seeds) and about 5 minutes for the
120 federated runs.

## Files

| File | Role |
|---|---|
| `gen_data.py SEED OUT` | AC power flow on pandapower `case33bw` every 15 min for 300 rounds × 4 steps. Mixed daily load profile with day factor and AR(1) bus noise; unmetered rooftop PV on buses 25–32 from round 150; reconfiguration at round 225 (tie 17–32 closed, line 31–32 opened). Stores features, labels (V < 0.95 p.u.), voltages, line endpoints and nominal and current path R/X |
| `bench_fl.py DATA TOPO W FEAT SEED OUT` | One prequential run. `TOPO` ∈ {star, aligned, misaligned, local}; `W` = training buffer in rounds; `FEAT` ∈ {current, stale} topology features. MLP 9–32–1, 5 local SGD steps per round, Metropolis–Hastings mixing; 75/25 split of each round into training and held-out calibration buffers; temperature scaling (static, sliding) and split conformal sets (pooled/per-client × static/sliding) |
| `analyse.py` | Aggregates the 120 runs into `results/long_metrics.csv`, `per_client_metrics.csv`, `recovery.csv`, `series.npz` and `tables.md` |
| `plot_benchmark.py` | Figs. 6–8 of the review into `figures/` |
| `run_all.sh` | Runs the whole pipeline |
| `results/tables.md`, `results/recovery.csv` | Reference outputs for comparison |

## Definitions used in the paper

- Zone groups: drifted = Z1, Z2, Z3, Z6, Z7; never-alarm = Z0, Z4, Z5; PV zones = Z6, Z7.
- Phases: before drift = rounds 125–149; transient = 150–161; steady state = 200–224; reconfiguration transient = 225–236.
- ECE: ten equal-width bins of top-label confidence on [0.5, 1].
- Recovery time: rounds after drift until a 4-round rolling mean of the metric on drifted zones has shed 75 % of its
  excess over the pre-drift level and stays there for 3 rounds.
- Ordering-violation rate: share of (line, time) pairs with |V_u − V_v| > 1e-3 p.u. where the order of alarm logits
  disagrees with the true voltage order; reported for all lines and for the seven lines whose endpoints belong to
  different clients.
- The misaligned communication graph is the zone tree relabelled (exhaustive search over 8! relabellings) to
  maximise the communication distance between physically adjacent zones; it has the same spectral gap as the
  aligned tree.

- Notation: the training-buffer length is called `W` in the code and in `results/tables.md`, and $H$ in the paper (where $\mathbf{W}$ denotes the mixing matrix).
- `plot_benchmark.py` checks every figure automatically for text that leaves its box, overlapping labels and lines that cross labels, and stops if a check fails.

All randomness is seeded; reruns reproduce the reference outputs exactly.
