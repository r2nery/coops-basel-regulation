# Institutional Profiles Under a Common Prudential Framework

**Evidence from Brazilian Credit Cooperatives and Banks**

Replication materials for the paper of the same name (`paper.tex`), prepared for ICA CCR 2026.

## What the paper does

Credit cooperatives in Brazil that cross a complexity threshold compute capital, leverage
and risk under the same full Basel-style methodology as commercial banks. The paper uses
that setting to ask whether organisational form still leaves an imprint on the balance
sheet once the regulatory rules are held fixed. Because the comparison is restricted to
institutions under the full methodology, the rulebook is constant by construction, and
because cooperative status is time-invariant, the estimates are conditional correlations
rather than causal effects of form.

The analysis sample is the population of full-methodology institutions from 2017Q1 to
2024Q4: **130 singular credit cooperatives** and **144 banks** (commercial and multiple
banks `b1` plus investment banks `b2`), **7,234 institution-quarters**. The panel is built
from the Central Bank of Brazil's public IF.data bulk files.

## Headline results

All coefficients are on a cooperative indicator, controlled for log assets and
quarter fixed effects, against the bank comparison group. Standard errors are clustered by
institution and every reported coefficient is checked with a restricted wild cluster
bootstrap.

- **Credit intensity.** Cooperatives allocate about **19 percentage points** more of assets
  to credit than banks of comparable size. The most stable result in the study.
- **Return on assets.** Cooperatives earn about **2.1 percentage points** more on assets, on
  an intermediation margin indistinguishable from that of banks, so the return comes from
  volume and cost rather than spread.
- **Cost efficiency.** Cooperatives run markedly leaner cost-to-income ratios.
- **Capital.** The size-adjusted mean gap is large and negative (about −15.8 pp), but this
  is a statement about the bank upper tail, not a shift of the cooperative distribution. The
  cooperative coefficient is **positive at the bottom** of the conditional capital
  distribution and **negative at the top**, crossing zero near the fortieth percentile.
  Cooperatives are the more homogeneous group on every outcome at equal size.
- **Leverage** moves with capital (correlation −0.84 among cooperatives) and is treated as
  one result with it.
- **Two nulls against banks.** Cooperatives provision no differently from banks and their
  intermediation margin is indistinguishable from banks'. Both differences appear only
  against a broad comparison group that contains institutions holding no credit and taking
  no deposits.
- **Heterogeneity.** The capital gap is concentrated in the integrated systems (Sicredi,
  Sicoob); the six independent cooperatives point the other way but are too few to measure.

## Repository layout

```
paper/paper.tex           the manuscript; \input's tables/ and \includegraphics from figures/
paper/supplement.tex      the online appendix, compiled separately
paper.py                  the analysis pipeline: builds the panel and writes results/*.txt
gate_d_distribution.py    quantile / distributional evidence -> results/gate_d_distribution.txt, capital_quantile_ci.txt, coarsening_sensitivity.txt, tables/t7
gate_e_dispersion.py      dispersion at equal size            -> tables/t8
gate_f_reporting_level.py reporting level (conglomerate vs individual banks) -> results/reporting_level.txt, tables/t11
gate_g_peers.py           peer rungs, cooperative-owned banks, provisioning by capital tercile, cost-to-income trim -> results/peer_rungs.txt, tables/t12
make_tables.py            parses results/*.txt into tables/t1..t6 and t9 (no recomputation)
make_figures.py           draws every figure from results/*.txt and the panel (no regressions), plus figures/slides/
gate_h_pretax.py          return on assets before taxes (line g) through the four specifications; results/pretax_roa.txt, feeds t13
make_docx.py              fills the ICA CCR Word template (paper/FINAL ABSTRACT-*.docx) with the proceedings
                          abstract (from expanded_abstract.md) and the full paper (from paper/paper.tex), APA 7 references;
                          also fills the Sistema OCB briefing template with the Portuguese whitepaper (from whitepaper_ocb.md)
make_whitepaper_figures.py  Portuguese versions of four figures for the whitepaper (figures/wp*.png), same loaders as make_figures.py
expanded_abstract.md      source text of the proceedings abstract (800 to 1,500 words including references)
whitepaper_ocb.md         source text of the Sistema OCB whitepaper (Portuguese)
cleanup_outputs.py        empties figures/, results/, tables/ before a fresh run

results/                  machine-written result files (see below)
tables/                   LaTeX table fragments (tabular + tablenotes only)
figures/                  PNG figures referenced by the manuscript
data/                     raw and processed BACEN inputs (git-ignored; see Data)
```

### Result files

| File | Contents |
|------|----------|
| `results_primary.txt` | main specification, cooperatives vs banks, four columns, with bootstrap p |
| `results_broad_peers.txt` | cooperatives vs all non-cooperatives |
| `results_within_market.txt` | cooperatives vs banks, region-exact matching |
| `results_no_s12.txt` | cooperatives vs banks, excluding modal-S1/S2 banks |
| `results_legacy.txt` | the original notebook's choices, for comparison |
| `robustness.txt` | winsorisation variants, selection test, reverters, coverage, small-cluster simulation, system bootstrap |
| `diagnostics.txt` | dedup, de-cumulation and seasonal tests, classification, balance |
| `changes_log.txt` | every deviation from the original notebook, with reasons |

## Method in brief

- **Classification.** Institutions are classified on the Central Bank's consolidation type
  (`tcb`): `b3S` singular cooperative, `b3C` central cooperative (excluded), everything else
  non-cooperative. Each institution takes its modal `tcb`, so the group label is
  time-invariant.
- **Comparison groups.** A ladder defined on the regulator's categories: all
  non-cooperatives, bank-like (`b1`,`b2`,`b4`), banks (`b1`,`b2`, the primary group), and
  commercial (`b1`). The divergence between the broad group and banks is itself a result.
  Two further rungs split banks by reporting level in IF.data's prudential report
  (`banks_individual`: banks reporting individually, TD = I; `banks_conglomerate`:
  prudential-conglomerate consolidations, TD = C); see `gate_f_reporting_level.py`.
- **Two measurement corrections.** IF.data income fields accumulate within the semester and
  are de-cumulated and annualised; the intermediation margin is computed gross of the
  loan-loss line so it does not reproduce the provisioning result.
- **Specifications.** (1) raw difference, (2) log assets + quarter fixed effects, (3)
  coarsened exact matching on size quintile with the same controls, (4) common-support
  trimming. The CEM estimand is weighted; the unweighted matched-sample regression is
  reported alongside.
- **Inference.** Clustered by institution, HC3 reported alongside, and a restricted wild
  cluster bootstrap with Rademacher weights for every coefficient. System-level estimates
  print the treated-cluster count because bootstrap p-values are coarse when few clusters
  are treated.

## Data

All inputs are public BACEN IF.data bulk files, downloaded from
`https://www.bcb.gov.br/estatisticas/ifdata`, plus the cooperative registry (cadastro) used
to assign system membership. The `data/` tree is git-ignored because of its size. The
pipeline expects:

```
data/raw/if.data/prudential_conglomerates/{summary,segmentation,assets,liabilities,income_statement}/
data/raw/if.data/individual_institutions/summary/      (gate_f validation only)
data/raw/cadastro/cooperativas_cadastro.csv
```

Raw CSVs are semicolon-delimited with Portuguese headers and Brazilian number format; the
`parse_br` helper handles conversion. Monetary values are in thousands of reais.

## Reproducing the results

```bash
python -m venv .venv
.venv/Scripts/activate            # Windows; use source .venv/bin/activate on POSIX
pip install -r requirements.txt

python cleanup_outputs.py         # optional: clear stale outputs
python paper.py                   # writes results/
python gate_d_distribution.py     # writes results/gate_d_distribution.txt, capital_quantile_ci.txt, coarsening_sensitivity.txt and tables/t7
                                  #   (--capital-ci reruns only the nine-quantile capital band for Figure 4;
                                  #    --coarsening reruns only the coarsening block, capital and credit)
python gate_e_dispersion.py       # writes tables/t8
python gate_f_reporting_level.py  # writes results/reporting_level.txt and tables/t11
python gate_g_peers.py            # writes results/peer_rungs.txt and tables/t12
python make_tables.py             # writes tables/t1..t6 and t9 from results/
python make_figures.py            # writes figures/ from results/ and the panel
python make_whitepaper_figures.py # writes figures/wp1..wp4 (Portuguese) for the whitepaper
python make_docx.py               # writes paper/ICACCR2026_abstract_*.docx, paper/ICACCR2026_paper_*.docx and
                                  # paper/Whitepaper_SistemaOCB_*.docx (the OCB template comes from the sistemaocb-docx skill)
```

Then compile `paper/paper.tex` and `paper/supplement.tex` with the usual
`pdflatex -> bibtex -> pdflatex -> pdflatex` cycle, with `tables/` and `figures/` beside
them (the paper is rendered on Overleaf). The bibliography is `paper/references.bib`.

Every number in the manuscript comes from a results file or a generated table; none is
transcribed by hand. Re-running the pipeline is deterministic (fixed bootstrap seed).

## Citation

```bibtex
@unpublished{nery2026profiles,
  title  = {Institutional Profiles Under a Common Prudential Framework:
            Evidence from Brazilian Credit Cooperatives and Banks},
  author = {Nery, Arthur Gomes},
  year   = {2026},
  note   = {ICA CCR 2026}
}
```

**Keywords:** credit cooperatives; prudential regulation; Basel; proportionality; Brazil.
**JEL:** G21, G28, P13.
