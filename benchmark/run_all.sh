#!/usr/bin/env bash
# Reproduces the benchmark of Section 10: 5 data seeds x 4 topologies x 3 buffers x 2 feature variants = 120 runs.
# Requirements: Python 3.10+, numpy, pandas, pandapower (>= 2.13), matplotlib.  Runtime: about 3 min (data)
# plus about 5 min (runs) on two CPU cores.
set -euo pipefail
mkdir -p data runs results figures
for s in 0 1 2 3 4; do echo "$s data/seed$s.npz"; done | xargs -P "${JOBS:-2}" -n 2 python3 gen_data.py
: > runs/jobs.txt
for s in 0 1 2 3 4; do for t in star aligned misaligned local; do for w in 6 24 96; do for f in current stale; do
  echo "data/seed$s.npz $t $w $f $s runs/${t}_W${w}_${f}_s${s}.npz" >> runs/jobs.txt
done; done; done; done
xargs -P "${JOBS:-2}" -n 6 python3 bench_fl.py < runs/jobs.txt
python3 analyse.py          # writes results/long_metrics.csv, per_client_metrics.csv, recovery.csv, tables.md
python3 plot_benchmark.py   # writes figures/fig6..fig8
