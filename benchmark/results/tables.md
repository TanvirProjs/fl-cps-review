## Table B2: topology comparison (W = 24 rounds, current topology features), mean ± sd over 5 seeds
| Metric | star | aligned | misaligned | local |
|---|---|---|---|---|
| Error, drifted zones, pre-drift | 0.044 ± 0.007 | 0.030 ± 0.001 | 0.036 ± 0.004 | 0.019 ± 0.003 |
| ECE, drifted zones, pre-drift | 0.024 ± 0.004 | 0.032 ± 0.004 | 0.032 ± 0.005 | 0.019 ± 0.003 |
| Error, drifted zones, rounds 0–11 after drift | 0.156 ± 0.026 | 0.103 ± 0.021 | 0.156 ± 0.032 | 0.145 ± 0.040 |
| ECE, drifted zones, rounds 0–11 after drift | 0.072 ± 0.024 | 0.031 ± 0.011 | 0.070 ± 0.025 | 0.091 ± 0.036 |
| ECE after sliding temperature scaling, rounds 0–11 | 0.100 ± 0.019 | 0.068 ± 0.019 | 0.105 ± 0.025 | 0.104 ± 0.036 |
| ECE after sliding temperature scaling, pre-drift | 0.011 ± 0.003 | 0.010 ± 0.003 | 0.010 ± 0.004 | 0.009 ± 0.001 |
| Error, drifted zones, steady state after drift | 0.031 ± 0.024 | 0.026 ± 0.022 | 0.028 ± 0.021 | 0.023 ± 0.028 |
| False-alarm rate, never-alarm zones, pre-drift | 0.021 ± 0.005 | 0.001 ± 0.002 | 0.015 ± 0.001 | 0.000 ± 0.000 |
| Brier score, never-alarm zones, pre-drift | 0.017 ± 0.003 | 0.002 ± 0.001 | 0.011 ± 0.002 | 0.000 ± 0.000 |
| Ordering-violation rate, all lines, pre-drift | 0.097 ± 0.022 | 0.072 ± 0.014 | 0.106 ± 0.028 | 0.161 ± 0.024 |
| Ordering-violation rate, all lines, rounds 0–11 after drift | 0.087 ± 0.013 | 0.094 ± 0.042 | 0.104 ± 0.018 | 0.249 ± 0.029 |
| Ordering-violation rate, cross-zone lines, pre-drift | 0.056 ± 0.042 | 0.135 ± 0.067 | 0.075 ± 0.047 | 0.299 ± 0.022 |
| Ordering-violation rate, cross-zone lines, rounds 0–11 | 0.048 ± 0.063 | 0.181 ± 0.152 | 0.073 ± 0.063 | 0.518 ± 0.060 |
| Recovery time, error (rounds) | 13.2 ± 0.8 | 12.6 ± 2.5 | 13.0 ± 1.0 | 12.4 ± 0.5 |
| Recovery time, ECE (rounds) | 11.4 ± 0.5 | 11.6 ± 1.8 | 11.4 ± 0.5 | 11.6 ± 0.9 |
| Recovery time, coverage gap, local sliding conformal (rounds) | 13.6 ± 2.8 | 15.0 ± 3.1 | 15.2 ± 2.7 | 13.0 ± 2.0 |

## Table B3: buffer length (adaptation speed) vs retention
| Topology | W | Error pre | Error 0–11 | ECE 0–11 | ECE 0–11 after sliding TS | ECE pre after sliding TS |
|---|---|---|---|---|---|---|
| star | 6 | 0.059 ± 0.010 | 0.102 ± 0.027 | 0.032 ± 0.017 | 0.053 ± 0.016 | 0.015 ± 0.004 |
| star | 24 | 0.044 ± 0.007 | 0.156 ± 0.026 | 0.072 ± 0.024 | 0.100 ± 0.019 | 0.011 ± 0.003 |
| star | 96 | 0.044 ± 0.007 | 0.190 ± 0.032 | 0.104 ± 0.030 | 0.122 ± 0.026 | 0.010 ± 0.002 |
| aligned | 6 | 0.043 ± 0.004 | 0.054 ± 0.013 | 0.024 ± 0.007 | 0.027 ± 0.013 | 0.012 ± 0.003 |
| aligned | 24 | 0.030 ± 0.001 | 0.103 ± 0.021 | 0.031 ± 0.011 | 0.068 ± 0.019 | 0.010 ± 0.003 |
| aligned | 96 | 0.031 ± 0.003 | 0.151 ± 0.033 | 0.071 ± 0.026 | 0.095 ± 0.029 | 0.008 ± 0.001 |
| misaligned | 6 | 0.055 ± 0.004 | 0.091 ± 0.022 | 0.029 ± 0.007 | 0.052 ± 0.020 | 0.013 ± 0.002 |
| misaligned | 24 | 0.036 ± 0.004 | 0.156 ± 0.032 | 0.070 ± 0.025 | 0.105 ± 0.025 | 0.010 ± 0.004 |
| misaligned | 96 | 0.036 ± 0.003 | 0.196 ± 0.037 | 0.108 ± 0.033 | 0.134 ± 0.032 | 0.010 ± 0.004 |
| local | 6 | 0.019 ± 0.002 | 0.090 ± 0.021 | 0.045 ± 0.013 | 0.054 ± 0.020 | 0.007 ± 0.001 |
| local | 24 | 0.019 ± 0.003 | 0.145 ± 0.040 | 0.091 ± 0.036 | 0.104 ± 0.036 | 0.009 ± 0.001 |
| local | 96 | 0.018 ± 0.004 | 0.175 ± 0.054 | 0.128 ± 0.060 | 0.127 ± 0.052 | 0.007 ± 0.001 |

## Table B4: conformal coverage (alpha = 0.10), drifted zones; max per-client gap pre-drift over all 8 clients
| Topology | Scheme | Coverage pre | Coverage 0–11 | Coverage steady | Mean set size pre | Max per-client |cov − 0.90| pre |
|---|---|---|---|---|---|---|
| star | pooled, static | 0.880 ± 0.025 | 0.754 ± 0.046 | 0.927 ± 0.028 | 0.892 ± 0.034 | 0.107 ± 0.016 |
| star | pooled, sliding | 0.882 ± 0.012 | 0.736 ± 0.031 | 0.859 ± 0.036 | 0.893 ± 0.017 | 0.104 ± 0.009 |
| star | per-client, static | 0.907 ± 0.016 | 0.753 ± 0.039 | 0.944 ± 0.030 | 0.926 ± 0.023 | 0.073 ± 0.038 |
| star | per-client, sliding | 0.917 ± 0.003 | 0.752 ± 0.018 | 0.899 ± 0.037 | 0.941 ± 0.008 | 0.047 ± 0.018 |
| aligned | pooled, static | 0.859 ± 0.021 | 0.765 ± 0.052 | 0.905 ± 0.033 | 0.861 ± 0.021 | 0.121 ± 0.026 |
| aligned | pooled, sliding | 0.858 ± 0.010 | 0.722 ± 0.030 | 0.849 ± 0.031 | 0.860 ± 0.009 | 0.124 ± 0.019 |
| aligned | per-client, static | 0.901 ± 0.017 | 0.789 ± 0.040 | 0.941 ± 0.020 | 0.906 ± 0.022 | 0.077 ± 0.035 |
| aligned | per-client, sliding | 0.911 ± 0.004 | 0.765 ± 0.028 | 0.902 ± 0.032 | 0.918 ± 0.005 | 0.054 ± 0.030 |
| local | pooled, static | 0.847 ± 0.012 | 0.705 ± 0.044 | 0.899 ± 0.032 | 0.847 ± 0.012 | 0.140 ± 0.015 |
| local | pooled, sliding | 0.846 ± 0.009 | 0.690 ± 0.022 | 0.838 ± 0.044 | 0.846 ± 0.009 | 0.141 ± 0.012 |
| local | per-client, static | 0.901 ± 0.018 | 0.734 ± 0.042 | 0.930 ± 0.017 | 0.902 ± 0.018 | 0.090 ± 0.028 |
| local | per-client, sliding | 0.905 ± 0.012 | 0.737 ± 0.034 | 0.896 ± 0.037 | 0.906 ± 0.012 | 0.064 ± 0.030 |

## Table B5: reconfiguration of G_p (round 225), PV zones, error in rounds 0–11 after switching
| Topology | current topology features | stale (nominal) features |
|---|---|---|
| star | 0.051 ± 0.020 | 0.038 ± 0.015 |
| aligned | 0.069 ± 0.021 | 0.034 ± 0.032 |
| misaligned | 0.053 ± 0.029 | 0.031 ± 0.027 |
| local | 0.042 ± 0.058 | 0.046 ± 0.065 |