# One-Size-Fits-All? Cooperative vs. Non-Cooperative Financial Institutions Under Full Basel-Style Regulation in Brazil

**Author:** Arthur Gomes Nery
**Affiliation:** Sistema OCB
**Date:** 2025–2026

## Overview

This repository contains the replication materials for *"One-Size-Fits-All? Cooperative vs. Non-Cooperative Financial Institutions Under Full Basel-Style Regulation in Brazil."* The study uses institution-level quarterly data from Brazil's Central Bank (BACEN) IF.data system to compare the financial behavior of credit cooperatives and conventional financial institutions operating under the same full Basel-style prudential methodology.

### Key Findings

- Cooperatives hold **7–8 percentage points less regulatory capital** than non-cooperatives of comparable size and geography (CEM specification: −7.16pp, 95% CI [−7.89, −6.42], p < 0.001)
- Cooperatives are **11–15 percentage points more leveraged**, reflecting structural dependence on deposit funding rather than equity markets
- Cooperatives operate with **lower net interest margins** (−3.48pp) but **higher operational efficiency** (−1.51 cost-to-income) and **marginally higher ROA** (+0.28pp)
- Cooperatives exhibit **4 percentage points lower NPL ratios** — lower credit risk despite lower capital buffers
- Credit portfolio allocation and deposit reliance results **do not survive** common-support restriction, suggesting they reflect size composition effects rather than genuine behavioral differences
- Six of eight outcomes are **stable across all four specifications**, including unconditional differences, size-controlled OLS, coarsened exact matching, and common-support restriction

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
  table3_main.csv            # Main CEM results
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
      agencias/              # Monthly branch office locations (2007–2024)
      postos/                # Monthly ATM/service points (2007–2024)
  processed/
    if.data/                 # Processed panels and results
```

## Data Sources

All data are publicly available from BACEN's IF.data bulk download system:

- **Prudential conglomerates panel**: 61,380 institution-quarter observations, 1,959 institutions (2014–2024)
- **Analysis sample**: 15,004 observations, 650 institutions under full Basel methodology (168 cooperatives, 483 non-cooperatives)
- **Monetary values**: All figures in R$ thousands (R$ mil)
- **Frequency**: Quarterly (March, June, September, December)

Data portal: `https://www.bcb.gov.br/estatisticas/ifdata`

## Methodology

### Identification Strategy

Comparison is restricted to institutions already operating under **full Basel-style prudential methodology** (i.e., `Instituição Utiliza Metodologia Simplificada == Não`). This holds constant the regulatory rules — capital requirements, risk-weighting methodology, reporting standards — and isolates the association between institutional form and financial outcomes.

### Four Specifications

| Spec | Description | N institutions |
|------|-------------|----------------|
| 1 | Unconditional mean difference | 650 |
| 2 | OLS: log(assets) + calendar-quarter FE | 650 |
| 3 | Coarsened Exact Matching on size quintile × macro-region + OLS | 599 |
| 4 | Common support restriction (log assets ∈ [11.47, 15.96]) + OLS | varies |

Heteroskedasticity-robust (HC3) standard errors throughout.

### Outcomes (8)

| Dimension | Outcome |
|-----------|---------|
| Capital structure | Basel capital adequacy ratio (%), leverage ratio |
| Profitability | Return on assets, net interest margin, cost-to-income ratio |
| Credit quality | Credit portfolio / assets, NPL ratio (provisions / gross credit) |
| Funding | Deposit ratio (captações / assets) |

## Main Results (CEM Specification)

| Outcome | Coop differential | 95% CI | p-value |
|---------|:-----------------:|--------|---------|
| Basel Capital Ratio (%) | −7.16pp | [−7.89, −6.42] | <0.001 |
| Leverage (Passivo / Assets) | +14.89pp | [+14.37, +15.42] | <0.001 |
| Return on Assets | +0.28pp | [+0.21, +0.35] | <0.001 |
| Net Interest Margin | −3.48pp | [−3.67, −3.29] | <0.001 |
| Cost-to-Income Ratio | −1.51 | [−1.63, −1.39] | <0.001 |
| Credit Portfolio / Assets | +4.90pp | [+3.76, +6.04] | <0.001 |
| NPL Ratio | −4.08pp | [−4.37, −3.79] | <0.001 |
| Deposit Ratio | +6.48pp | [+5.33, +7.63] | <0.001 |

*Credit portfolio and deposit ratio results do not survive common-support restriction — see Section 3.2.*

## Robustness

All six stable results are robust to:

- Unconditional comparison, size-controlled OLS, coarsened exact matching, and common-support restriction (Specifications 1–4)
- Sign and significance maintained across all four specifications (p < 0.001 in each)
- Coefficient stability plots across the four specifications confirm monotonic attenuation or strengthening patterns

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
  title={One-Size-Fits-All? Cooperative vs. Non-Cooperative Financial Institutions
         Under Full Basel-Style Regulation in Brazil},
  author={Nery, Arthur Gomes},
  institution={Sistema OCB},
  year={2026}
}
```

---

**Keywords:** credit cooperatives, prudential regulation, Basel, coarsened exact matching, institutional form, Brazil, BACEN
**JEL codes:** G21, G28, P13
