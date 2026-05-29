# One-Size-Fits-All? Credit Cooperatives Under Full Basel Regulation in Brazil

**Author:** Arthur Gomes Nery
**Affiliation:** Sistema OCB (Organization of Brazilian Cooperatives)
**Date:** 2025–2026

## Overview

This repository contains the replication materials for *"One-Size-Fits-All? Credit Cooperatives Under Full Basel Regulation in Brazil."* The study uses institution-level quarterly data from Brazil's Central Bank (BACEN) IF.data system to compare the financial behavior of singular credit cooperatives and non-cooperative financial institutions operating under the same full Basel-style prudential methodology. By restricting attention to the full-methodology population, the regulatory environment is held fixed by construction, isolating the association between organizational form and financial outcomes.

### Key Findings

- All **eight outcomes keep their sign and 1% significance across all four specifications**, and **none reverses** under common-support trimming. The "unstable" category is empty; the classification reduces to *robust* versus *partially robust* on the magnitude of attenuation.
- Cooperatives hold **8–12 percentage points less regulatory capital** (Basel ratio), with only ~21% attenuation from raw to trimmed — among the most stable results.
- Cooperatives report a **~3.3 percentage point lower provisioning ratio**, with essentially **zero attenuation** (the most stable finding). This is an *accounting* quantity (provisions / gross credit), **not** a measure of delinquency; we do **not** interpret it as lower credit risk.
- Cooperatives run **leaner** (cost-to-income ~3.1pp lower raw → ~1.2pp trimmed) and devote a **larger share of assets to credit** (~25pp raw → ~13pp trimmed).
- Cooperatives are **more leveraged** (~22pp raw → ~9pp trimmed). Leverage and the Basel ratio are two views of one equity cushion (r ≈ −0.84 among cooperatives) and should not be read as independent findings.
- **Return on assets** is positive but modest (~0.86pp raw → ~0.34pp trimmed, ~61% attenuation); **net interest margin** is lower (~6.5pp raw → ~1.1pp trimmed, ~84% attenuation); **deposit ratio** is higher (~28pp raw → ~8pp trimmed, ~71% attenuation).
- Splitting by integrated system, the **capital gap is concentrated in Sicredi**, insignificant for Sicoob, and positive-but-insignificant for the six independent cooperatives — consistent with, but not establishing, a network-backstop story. **Lower provisioning holds and is significant in every system.**

## Repository Structure

```
paper1_v4.ipynb              # Main analysis notebook (current, consolidated)
paper1_comprehensive.ipynb   # Comprehensive version integrating all IF.data sources
expanded_abstract.md         # Extended abstract with full results narrative
requirements.txt             # Python dependencies
figures/                     # All output figures (PNG)
tables/                      # All output tables (CSV)
  table1_balance.csv         # Balance test: matched vs. unmatched
  table2_four_specs.csv      # All outcomes × four specifications
  table3_main.csv            # Main results
  tableA1_descriptive.csv    # Descriptive statistics
data/
  raw/
    if.data/                 # BACEN IF.data bulk CSVs (semicolon-delimited)
      prudential_conglomerates/
        summary/             # Balance sheet overview (primary source)
        segmentation/        # S1–S5 tier + simplified methodology flag
        assets/              # Asset decomposition
        liabilities/         # Funding structure
        income_statement/    # P&L
        capital_information/ # RWA decomposition, CET1/Tier1/Basel ratios
      financial_conglomerates/
        portfolio_risk_level/          # AA–H loan quality buckets
        portfolio_legal_person_*       # SME vs. large lending
        portfolio_geographic_region/   # Regional breakdown
        portfolio_number_clients_operations/
    bcb/
      cadastro/              # Cooperative registry (CNPJ, filiação) for system assignment
      agencias/              # Monthly branch office locations (2007–2024)
      postos/                # Monthly ATM/service points (2007–2024)
  processed/
    if.data/                 # Processed panels and results
```

## Data Sources

All data are publicly available from BACEN's IF.data bulk download system:

- **Full panel**: 61,377 institution-quarter observations, 1,959 institutions (2014–2024), of which 1,197 are cooperatives (1,157 singular, 40 central) and 762 are non-cooperatives.
- **Analysis sample**: 13,912 observations, 613 institutions under full Basel methodology (130 singular cooperatives, 483 non-cooperatives), 2017Q1–2024Q4.
- **Monetary values**: All figures in R$ thousands (R$ mil).
- **Frequency**: Quarterly (March, June, September, December).

Data portal: `https://www.bcb.gov.br/estatisticas/ifdata`

## Methodology

### Classification

Institutions are classified on the Central Bank's consolidation type (*tipo de consolidado bancário*, `tcb`), not on trade names: `b3S` = singular credit cooperative, `b3C` = central cooperative, all other categories = non-cooperative. Each institution is assigned its **modal** `tcb` over the period, so cooperative status is **time-invariant by construction**. Central cooperatives (`b3C`) are **excluded** from the comparison as wholesale infrastructure entities; the cooperative group is restricted to **singular retail cooperatives** (`b3S`).

System membership (Sicredi, Sicoob, independent, etc.) is assigned by joining the analysis sample to the BACEN cooperative cadastro on the tax identifier (CNPJ) and reading the *filiação* field, rolling each central up to its confederation. Of the 130 singular cooperatives, 118 match directly on CNPJ and 12 are filled from a manual mapping; none is left unclassified.

### Identification Strategy

Comparison is restricted to institutions operating under **full Basel-style prudential methodology** (i.e., not using the optional simplified capital computation). This holds constant the regulatory rules — capital requirements, risk-weighting methodology, reporting standards — and isolates the association between institutional form and financial outcomes. Because cooperative status is time-invariant, institution fixed effects cannot be estimated alongside the cooperative indicator; results are **conditional correlations**, not causal effects of organizational form.

### Four Specifications

| Spec | Description | N institutions |
|------|-------------|----------------|
| 1 | Unconditional mean difference | 613 |
| 2 | OLS: log(assets) + calendar-quarter FE | 613 |
| 3 | Coarsened Exact Matching on size quintile × macro-region + OLS | 525 (88 dropped) |
| 4 | Common-support restriction (log assets ∈ [11.4, 15.7]) + OLS | 346 (6,756 obs) |

Standard errors are **clustered by institution**; HC3 standard errors are reported alongside and are uniformly tighter, so the clustered errors are the conservative basis for inference. Every coefficient described as significant is significant under both.

### Outcomes (8)

| Dimension | Outcome |
|-----------|---------|
| Capital structure | Basel capital adequacy ratio (%), leverage ratio (liabilities / assets) |
| Profitability | Return on assets, net interest margin |
| Efficiency | Cost-to-income ratio (operating-income denominator) |
| Credit | Credit portfolio / assets, provisioning ratio (provisions / gross credit) |
| Funding | Deposit ratio (captações / assets) |

> **Note on terminology:** the credit-risk outcome is the **provisioning ratio** (provisions over gross credit), an accounting measure. It is **not** an NPL/delinquency ratio and is not interpreted as a measure of credit quality.

## Main Results (four specifications)

| Outcome | (1) Raw | (2) Controls | (3) CEM | (4) Trim | Attenuation | Tier |
|---------|:-------:|:------------:|:-------:|:--------:|:-----------:|------|
| Basel capital ratio (pp)   | −12.00  | −8.27  | −8.77  | −9.47  | 21%  | **Robust** |
| Leverage                   | +0.222  | +0.128 | +0.132 | +0.086 | 61%  | Partial |
| Return on assets           | +0.0086 | +0.0063| +0.0075| +0.0034| 61%  | Partial |
| Net interest margin        | −0.0654 | −0.0324| −0.0271| −0.0106| 84%  | Partial |
| Cost-to-income ratio       | −3.05   | −2.09  | −2.32  | −1.24  | 59%  | **Robust** |
| Credit portfolio / assets  | +0.253  | +0.203 | +0.202 | +0.127 | 50%  | **Robust** |
| Provisioning ratio         | −0.0334 | −0.0330| −0.0338| −0.0344| −3%  | **Robust** |
| Deposit ratio              | +0.280  | +0.177 | +0.195 | +0.081 | 71%  | Partial |

*Coefficient on the cooperative indicator. Spec (2) adds log assets and quarter FE; (3) CEM on size quintile × macro-region with the same controls; (4) trims to common support. All 32 cells significant at 1% under both clustered and HC3 standard errors. Attenuation is 1 − |β_trim| / |β_raw|; the negative value for provisioning means the trimmed coefficient is marginally larger in magnitude than the raw one. Robust = sign and significance hold across all four columns with attenuation below 60%; Partial = they hold but attenuation reaches 60% or more.*

### Heterogeneity by system (controlled specification)

| System | N | Basel (pp) | Leverage | ROA | Provisioning |
|--------|:-:|:----------:|:--------:|:---:|:------------:|
| Sicredi     | 106 | −9.70*** | +0.139*** | +0.0066*** | −0.0330*** |
| Sicoob      | 17  | −2.51    | +0.077**  | +0.0040    | −0.0308*** |
| Independent | 6   | +11.67   | −0.041    | +0.0075*** | −0.0403**  |

*\*\*\* p<0.001, \*\* p<0.01. Cresol (1 institution), Unicred, Uniprime, Ailos omitted (fewer than five each in the full-methodology sample). The pooled capital gap is concentrated in Sicredi; lower provisioning is significant in every system.*

## Robustness

- Sign and significance maintained across all four specifications (p < 0.001 in each), under both clustered and HC3 standard errors.
- No outcome reverses sign under common-support trimming.
- Coefficient stability plots across the four specifications show monotonic attenuation toward zero (without crossing it) or near-zero movement.

## Setup

```bash
# Python 3.12+
python -m venv .venv
source .venv/Scripts/activate   # Windows/bash

pip install pandas numpy matplotlib seaborn scipy statsmodels linearmodels
```

### Running the Analysis

Open `paper1_v4.ipynb` in Jupyter and run all cells sequentially. The notebook expects data at `data/raw/if.data/` as downloaded from BACEN IF.data.

Raw CSVs use semicolon delimiters (`;`), Portuguese column names, and Brazilian number format (`.` = thousands separator, `,` = decimal). The `parse_br()` helper handles conversion automatically.

## Citation

```bibtex
@unpublished{nery2026onesizefitsall,
  title={One-Size-Fits-All? Credit Cooperatives Under Full Basel Regulation in Brazil},
  author={Nery, Arthur Gomes},
  institution={Sistema OCB},
  year={2026}
}
```

---

**Keywords:** credit cooperatives, prudential regulation, Basel, coarsened exact matching, institutional form, Brazil, BACEN
**JEL codes:** G21, G28, P13
