# Continual, Uncertainty-Aware and Structure-Consistent Federated Learning for Distributed Cyber-Physical Systems and Edge Digital Twins

Supplementary code and data for the review article

> T. H. Sardar, *Continual, Uncertainty-Aware and Structure-Consistent Federated Learning for Distributed Cyber-Physical Systems and Edge Digital Twins: A Critical Review, Unified Formulation and Reproducible Benchmark* (submitted).

The repository contains the reproducible reference benchmark of Section 10 (IEEE 33-bus feeder with unmetered photovoltaic drift and network reconfiguration) and the Online Resources that document the literature search, screening, full-text extraction and claim verification.

## Contents

| Folder / file | Online Resource | What it holds |
|---|---|---|
| `online_resources/OR1_*` | 1 | Screening decisions for the 73 added records and `OR1_kappa_tools.py`, which draws a stratified reliability sample and computes Cohen's κ |
| `online_resources/OR2_*` | 2 | Claim-to-source tables, including `OR2_claim_verification_fulltext.csv`: each statement about a cited record with its full-text verdict and evidence |
| `online_resources/OR3_*` | 3 | Abstract-level extraction of benchmark characteristics for the added primary records |
| `online_resources/OR4_*` | 4 | Full-text extraction for the cited records read in full |
| `online_resources/OR5_*` | 5 | Database queries, the merging and field-equivalence script, the 671 merged records and the reference verification log |
| `benchmark/` | 6 | Code, data generators, seeds and reference outputs that reproduce Tables 13–15 and Figs. 6–8 |

## Reproducing the benchmark

```bash
pip install -r requirements.txt
cd benchmark
./run_all.sh            # JOBS=4 ./run_all.sh to use four cores
```

About 3 minutes of power-flow simulation (5 seeds) and 5 minutes for the 120 federated runs on two CPU cores; no GPU is needed. All randomness is seeded, and reruns reproduce `benchmark/results/` exactly. See `benchmark/README.md` for the definitions used in the paper.

## Reproducing the screening reliability check

```bash
cd online_resources
python3 OR1_kappa_tools.py sample decisions.csv > kappa_sample.csv            # draw a stratified sample from a decisions table
python3 OR1_kappa_tools.py kappa screener1.csv screener2.csv                    # Cohen's kappa on include/exclude
```

## Citation

If you use this material, please cite the article (see `CITATION.cff`).

## Licence

Code is released under the MIT Licence (`LICENSE`). Tables and data files in `online_resources/` and `benchmark/results/` are released under CC BY 4.0. Bibliographic records are derived from Scopus, IEEE Xplore and Web of Science exports; the full exports are not redistributed, in line with the providers' terms, and can be regenerated with the queries in `online_resources/OR5_search_queries_all_databases.txt`.

## Contact

Tanvir Habib Sardar, Department of Computer Science and Engineering, Dayananda Sagar University, Bengaluru, India · tanvir-cse@dsu.edu.in · ORCID [0000-0001-7880-0225](https://orcid.org/0000-0001-7880-0225)
