"""Reliability tools for Online Resource 1.

1) Draw the stratified 20 % reliability sample (64 of the 316 Scopus records, seed 2026):
     python3 OR1_kappa_tools.py sample scopus_decisions.csv > kappa_sample.csv
   scopus_decisions.csv needs columns: record_id, decision  (core/supporting/review/exclude/unclear)
2) Compute Cohen's kappa on the include/exclude decision of two screeners:
     python3 OR1_kappa_tools.py kappa screener1.csv screener2.csv
   each file needs columns: record_id, decision
Include = core, supporting or review; exclude = exclude; 'unclear' records are reported separately.
"""
import sys, pandas as pd

def sample(path, n_total=64, seed=2026):
    """Stratified sample of n_total records, allocated to decisions by largest remainder."""
    d = pd.read_csv(path)
    sizes = d.decision.value_counts().sort_index()
    quota = sizes * n_total / sizes.sum()
    alloc = quota.astype(int)
    for k in (quota - alloc).sort_values(ascending=False).index[: n_total - alloc.sum()]:
        alloc[k] += 1
    parts = [d[d.decision == k].sample(n=int(alloc[k]), random_state=seed) for k in alloc.index if alloc[k] > 0]
    return pd.concat(parts).sort_values('record_id')

def kappa(p1, p2):
    a = pd.read_csv(p1)[['record_id', 'decision']]; b = pd.read_csv(p2)[['record_id', 'decision']]
    m = a.merge(b, on='record_id', suffixes=('_1', '_2'))
    unclear = m[(m.decision_1 == 'unclear') | (m.decision_2 == 'unclear')]
    m = m.drop(unclear.index)
    inc = lambda x: 'include' if x in ('core', 'supporting', 'review') else 'exclude'
    x, y = m.decision_1.map(inc), m.decision_2.map(inc)
    po = (x == y).mean()
    pe = sum((x == c).mean() * (y == c).mean() for c in ('include', 'exclude'))
    k = (po - pe) / (1 - pe) if pe < 1 else float('nan')
    print(f'n = {len(m)} (unclear excluded: {len(unclear)}); observed agreement = {po:.3f}; '
          f'expected = {pe:.3f}; Cohen kappa = {k:.3f}')
    print(pd.crosstab(x, y, rownames=['screener 1'], colnames=['screener 2']))

if __name__ == '__main__':
    if sys.argv[1] == 'sample':
        sample(sys.argv[2]).to_csv(sys.stdout, index=False)
    elif sys.argv[1] == 'kappa':
        kappa(sys.argv[2], sys.argv[3])
