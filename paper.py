"""
One-Size-Fits-All? Credit cooperatives under full Basel regulation in Brazil.
Analysis pipeline. Rewrite of paper1_v5.ipynb.

Outputs (written to ROOT/results/):
    results_primary.txt   every reported number under the recommended specification
    results_legacy.txt    same pipeline under the original notebook's choices (paper reproduction)
    diagnostics.txt       data-quality and classification diagnostics
    changes_log.txt       every deviation from the original notebook, with reasons, plus a
                          primary-vs-legacy coefficient diff
    robustness.txt        winsorisation variants, selection into the sample, reverters,
                          provisioning coverage, small-cluster simulation, system bootstrap
Figures regenerate to ROOT/figures/ under the exact filenames the .tex expects.

Run:  python paper1.py
Override data root with the ICA_ROOT environment variable.
"""

from __future__ import annotations
import os
import io
import json
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import statsmodels.formula.api as smf

pd.options.mode.chained_assignment = None

# ----------------------------------------------------------------------------- paths
ROOT = Path(os.environ.get("ICA_ROOT", Path(__file__).resolve().parent))
DATA = ROOT / "data"
PRUD = DATA / "raw" / "if.data" / "prudential_conglomerates"
SRC = {
    "summary": PRUD / "summary",
    "seg": PRUD / "segmentation",
    "assets": PRUD / "assets",
    "income": PRUD / "income_statement",
    "liab": PRUD / "liabilities",
}
CAD_PATH = DATA / "raw" / "cadastro" / "cooperativas_cadastro.csv"
FIGURES = ROOT / "figures"
RESULTS = ROOT / "results"
for d in (FIGURES, RESULTS):
    d.mkdir(parents=True, exist_ok=True)

COOP_C, NONCOOP_C, ACCENT, GREY = "#2563eb", "#dc2626", "#f59e0b", "#6b7280"

# ----------------------------------------------------------------------------- outcomes
OUTCOMES = {
    "basileia_num": "Basel Capital Ratio (%)",
    "leverage": "Leverage (liabilities/assets)",
    "roa": "Return on Assets",
    "nim": "Net Interest Margin",
    "cti": "Cost-to-Income Ratio",
    "credit_ratio": "Credit Portfolio / Assets",
    "prov_ratio": "Provisioning (provisions/gross credit)",
    "deposit_ratio": "Funding Ratio (captacoes/assets)",
}
HET_OUTCOMES = ["basileia_num", "leverage", "roa", "prov_ratio"]

# Institution-level stability outcomes, computed once per institution over its
# full-methodology quarters in the analysis sample (see stability_estimates). They
# are NOT panel outcomes and are never put through the institution-quarter machinery
# in run_pipeline; they are estimated on an institution-level cross-section.
STAB_LABELS = {"roa_vol": "Return on assets volatility", "zscore": "Z-score"}

# ----------------------------------------------------------------------------- column maps
SUMM_MAP = {
    "Instituição": "instituicao", "Código": "codigo", "Data": "data_str",
    "UF": "uf",
    "Ativo Total": "ativo_total",
    "Carteira de Crédito Classificada": "carteira_credito",
    "Passivo Circulante e Exigível a Longo Prazo e Resultados de Exercícios Futuros": "passivo",
    "Captações": "captacoes",
    "Patrimônio Líquido": "patrimonio_liquido",
    "Lucro Líquido": "lucro_liquido",
    "Patrimônio de Referência para Comparação com o RWA": "pat_referencia",
    "Índice de Basileia": "basileia",
    "SR": "segmento",
}
SUMM_NUM = ["ativo_total", "carteira_credito", "passivo", "captacoes",
            "patrimonio_liquido", "lucro_liquido", "pat_referencia", "basileia"]

SEG_MAP = {
    "Código": "codigo", "Data": "data_str",
    "Instituição Utiliza Metodologia Simplificada": "simplified",
}

ASSET_MAP = {
    "Código": "codigo", "Data": "data_str",
    "Operações de Crédito": "credito_bruto",
    "Operações de Crédito - Provisão sobre Operações de Crédito (d2)": "provisao_credito",
}
ASSET_NUM = ["credito_bruto", "provisao_credito"]

# liabilities module: total deposits (line (a) of Captacoes), used only to define the
# structural peer rung (banks with strictly positive deposits in every sample quarter)
LIAB_MAP = {
    "Código": "codigo", "Data": "data_str",
    "Captações - Depósito Total (a)": "depositos",
}
LIAB_NUM = ["depositos"]

INCOME_MAP = {
    "Código": "codigo", "Data": "data_str",
    "Resultado de Intermediação Financeira - Receitas de Intermediação Financeira (a) = (a1) + (a2) + (a3) + (a4) + (a5) + (a6)": "receitas_intermediacao",
    "Resultado de Intermediação Financeira - Resultado de Intermediação Financeira (c) = (a) + (b)": "resultado_intermediacao",
    "Resultado de Intermediação Financeira - Resultado de Provisão para Créditos de Difícil Liquidação (b5)": "resultado_pcld",
    "Outras Receitas/Despesas Operacionais - Rendas de Tarifas Bancárias (d2)": "tarifas",
    "Outras Receitas/Despesas Operacionais - Despesas de Pessoal (d3)": "despesas_pessoal",
    "Outras Receitas/Despesas Operacionais - Despesas Administrativas (d4)": "despesas_admin",
}
INCOME_NUM = ["receitas_intermediacao", "resultado_intermediacao", "resultado_pcld",
              "tarifas", "despesas_pessoal", "despesas_admin"]

# Income-statement fields accumulate WITHIN THE SEMESTER in IF.data (Brazilian
# balanco semestral convention): Q1 is a one-quarter flow, Q2 is Jan-Jun, Q3 resets
# to a one-quarter flow, Q4 is Jul-Dec. Verified empirically in the Gate A
# diagnostic: median Q2/Q1 = 2.11 and Q4/Q3 = 2.07 while Q3/Q1 = 1.14, against
# 1.09-1.11 for balance-sheet stocks over the same institution-years.
FLOW_COLS = ["lucro_liquido", "receitas_intermediacao", "resultado_intermediacao",
             "resultado_pcld", "tarifas", "despesas_pessoal", "despesas_admin"]

# Comparison-group ladder. The cooperative side is always b3S; this selects which
# non-cooperative institutions it is compared against, on the regulator's own
# consolidation type (exogenous to the outcomes; never select peers on an outcome).
#   all        every non-b3 institution under full methodology (the v5 comparison)
#   bank_like  b1, b2, b4 - banks incl. development banks (b4 = banco de
#              desenvolvimento, per BCB's IF.data/SCR.data methodology)
#   banks      b1, b2     - commercial/multiple/investment banks
#   commercial b1         - banks with a commercial portfolio, the closest analogue
#                           to a deposit-funded retail cooperative
# Reporting-level rungs. IF.data's prudential report carries a document-type field
# (TD): "C" is a prudential-conglomerate consolidation, "I" an institution reporting
# individually. Every singular cooperative is "I"; most banks are "C", so a bank row
# consolidates the whole conglomerate (leasing, DTVM, consorcio...). A dict entry
# restricts on modal tcb AND modal td (td_stable, set in build_panel).
#   banks_individual     b1, b2 reporting individually (td == I)
#   banks_conglomerate   b1, b2 reporting as prudential conglomerates (td == C)
# Business-model rung. "structural" keeps b1 banks with strictly positive total
# deposits (liabilities line (a)) in every full-methodology quarter of their presence
# in the sample: an ex-ante definition of a deposit-funded commercial bank.
#   structural             b1 with positive deposits in every sample quarter
#   commercial_individual  b1 reporting individually
#   structural_individual  structural, reporting individually
PEER_SETS = {
    "all": None,
    "bank_like": {"b1", "b2", "b4"},
    "banks": {"b1", "b2"},
    "commercial": {"b1"},
    "banks_individual": {"tcb": {"b1", "b2"}, "td": {"I"}},
    "banks_conglomerate": {"tcb": {"b1", "b2"}, "td": {"C"}},
    "structural": {"tcb": {"b1"}, "structural": True},
    "commercial_individual": {"tcb": {"b1"}, "td": {"I"}},
    "structural_individual": {"tcb": {"b1"}, "td": {"I"}, "structural": True},
}

UF_REGION = {
    "AC": "N", "AL": "NE", "AM": "N", "AP": "N", "BA": "NE", "CE": "NE", "DF": "CO",
    "ES": "SE", "GO": "CO", "MA": "NE", "MG": "SE", "MS": "CO", "MT": "CO", "PA": "N",
    "PB": "NE", "PE": "NE", "PI": "NE", "PR": "S", "RJ": "SE", "RN": "NE", "RO": "N",
    "RR": "N", "RS": "S", "SC": "S", "SE": "NE", "SP": "SE", "TO": "N",
}


# ============================================================================= IO
def parse_br(s: pd.Series) -> pd.Series:
    """Parse Brazilian-formatted numerics: 1.234.567,89 -> 1234567.89; strip %."""
    return pd.to_numeric(
        s.astype(str).str.replace(".", "", regex=False)
        .str.replace(",", ".", regex=False).str.replace("%", "", regex=False),
        errors="coerce")


def read_csv(path: Path) -> pd.DataFrame:
    for enc in ("utf-8-sig", "latin-1", "utf-8", "cp1252"):
        try:
            df = pd.read_csv(path, sep=";", encoding=enc, skipinitialspace=True)
            df.columns = df.columns.str.strip()
            return df
        except (UnicodeDecodeError, ValueError):
            continue
    raise ValueError(f"unreadable: {path}")


def dedupe(df: pd.DataFrame, keys=("codigo", "date")):
    """Drop exact dups, then collapse remaining key-dups keeping the most-populated row.
    Returns (df, n_total_dropped, n_conflicting) where conflicting = key-dups that were
    not exact duplicates (i.e. genuinely different values for the same key)."""
    keys = list(keys)
    if not set(keys).issubset(df.columns):
        return df, 0, 0
    n0 = len(df)
    df = df.drop_duplicates()
    n_after_exact = len(df)
    conflicting = int(df.duplicated(subset=keys).sum())
    df = df.assign(_nn=df.notna().sum(axis=1))
    df = (df.sort_values(keys + ["_nn"])
            .drop_duplicates(subset=keys, keep="last")
            .drop(columns="_nn"))
    return df, n0 - len(df), conflicting


def load_folder(folder: Path, rename_map: dict, num_cols: list):
    chunks, dedupe_info = [], {}
    for f in sorted(folder.glob("*.csv")):
        df = read_csv(f)
        # capture tcb before it is renamed away (column may arrive as TCB)
        for raw in ("TCB", "TD", "TC"):
            if raw in df.columns:
                df = df.rename(columns={raw: raw.lower()})
        df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})
        chunks.append(df)
    out = pd.concat(chunks, ignore_index=True)
    if "data_str" in out.columns:
        out["date"] = pd.to_datetime(out["data_str"], format="%m/%Y", errors="coerce")
        out = out.dropna(subset=["date"])
    for c in num_cols:
        if c in out.columns:
            out[c] = parse_br(out[c])
    out, dropped, conflicting = dedupe(out)
    dedupe_info = {"rows": len(out), "dropped": dropped, "conflicting": conflicting}
    return out, dedupe_info


# ============================================================================= de-cumulation
def decumulate_semiannual(df: pd.DataFrame, cols) -> tuple[pd.DataFrame, dict]:
    """Convert semester-cumulative income-statement flows into ANNUALIZED quarterly
    flows, written to `<col>_q`.

    Within each (institution, year, semester): the opening quarter (Q1, Q3) is
    already a one-quarter flow; the closing quarter (Q2, Q4) is a two-quarter
    cumulative, so the quarterly flow is closing minus opening. Every quarterly
    flow is then multiplied by 4 so that ratios built on it (ROA, NIM) are stated
    at an annual rate and are comparable across quarters.

    A closing quarter whose opening quarter is absent cannot be de-cumulated and is
    set to NaN rather than silently treated as a one-quarter flow. Counts of such
    rows are returned so the loss is visible in diagnostics.
    """
    d = df.copy()
    d["_y"] = d["date"].dt.year
    d["_q"] = d["date"].dt.quarter
    d["_sem"] = np.where(d["_q"] <= 2, 1, 2)
    d["_pos"] = np.where(d["_q"].isin([1, 3]), 1, 2)

    keys = ["codigo", "_y", "_sem"]
    opening = d[d["_pos"] == 1].set_index(keys)
    idx = pd.MultiIndex.from_frame(d[keys])
    pos = d["_pos"].to_numpy()
    info = {}
    for c in cols:
        if c not in d.columns:
            d[c + "_q"] = np.nan
            info[c] = {"status": "column absent", "unmatched": None}
            continue
        prev = opening[c].reindex(idx).to_numpy()
        val = d[c].to_numpy()
        q = np.where(pos == 1, val, val - prev)
        # closing quarter with no opening quarter on file -> not recoverable
        orphan = (pos == 2) & np.isnan(prev) & ~np.isnan(val)
        q = np.where(orphan, np.nan, q)
        d[c + "_q"] = q * 4.0
        info[c] = {"status": "ok", "unmatched": int(orphan.sum()),
                   "nonnull_before": int(np.sum(~np.isnan(val))),
                   "nonnull_after": int(np.sum(~np.isnan(q)))}
    return d.drop(columns=["_y", "_q", "_sem", "_pos"]), info


def seasonal_profile(df: pd.DataFrame, cols) -> dict:
    """Median of each column by calendar quarter. Acceptance test for de-cumulation:
    a correctly de-cumulated flow ratio is FLAT across Q1-Q4; a semester-cumulative
    one shows the 1,2,1,2 staircase."""
    q = df["date"].dt.quarter
    out = {}
    for c in cols:
        if c in df.columns:
            out[c] = {int(k): float(v) for k, v in df.groupby(q)[c].median().items()}
    return out


# ============================================================================= build base panel
def build_panel():
    """Load all sources, merge, classify on tcb, construct raw outcomes.
    Returns (panel, dedupe_info, tcb_varied)."""
    info = {}
    summary, info["summary"] = load_folder(SRC["summary"], SUMM_MAP, SUMM_NUM)
    seg, info["seg"] = load_folder(SRC["seg"], SEG_MAP, [])
    assets, info["assets"] = load_folder(SRC["assets"], ASSET_MAP, ASSET_NUM)
    income, info["income"] = load_folder(SRC["income"], INCOME_MAP, INCOME_NUM)
    liab, info["liab"] = load_folder(SRC["liab"], LIAB_MAP, LIAB_NUM)

    seg["simplified"] = seg["simplified"].astype(str).str.strip().str.upper()
    seg["full_method"] = (seg["simplified"] == "NÃO").astype(int)

    panel = summary.merge(
        seg[["codigo", "date", "simplified", "full_method"]],
        on=["codigo", "date"], how="left")
    panel = panel.merge(assets[["codigo", "date"] + ASSET_NUM],
                        on=["codigo", "date"], how="left")
    panel = panel.merge(income[["codigo", "date"] + INCOME_NUM],
                        on=["codigo", "date"], how="left")
    panel = panel.merge(liab[["codigo", "date"] + LIAB_NUM],
                        on=["codigo", "date"], how="left")

    # ---- institution-stable cooperative classification from tcb ----------------
    # modal tcb per institution guarantees a time-invariant group label by construction
    modal = (panel.dropna(subset=["tcb"])
             .groupby("codigo")["tcb"]
             .agg(lambda s: s.mode().iloc[0] if len(s.mode()) else np.nan))
    tcb_varied = (panel.dropna(subset=["tcb"]).groupby("codigo")["tcb"].nunique()
                  .pipe(lambda s: s[s > 1]).index.tolist())
    panel["tcb_stable"] = panel["codigo"].map(modal)

    # reporting level (TD: C = prudential-conglomerate consolidation, I = individual),
    # made time-invariant the same way so a peer rung can be defined on it
    if "td" not in panel.columns:
        panel["td"] = np.nan
    panel["td"] = panel["td"].astype("string").str.strip().str.upper()
    modal_td = (panel.dropna(subset=["td"]).groupby("codigo")["td"]
                .agg(lambda s: s.mode().iloc[0] if len(s.mode()) else np.nan))
    panel["td_stable"] = panel["codigo"].map(modal_td)

    def klass(t):
        t = "" if pd.isna(t) else str(t)
        if t == "b3S":
            return "singular"
        if t == "b3C":
            return "central"
        if t.startswith("b3"):
            return "coop_other"
        return "noncoop"

    panel["coop_class"] = panel["tcb_stable"].map(klass)
    panel["is_coop_any"] = panel["coop_class"].isin(
        ["singular", "central", "coop_other"]).astype(int)
    # legacy flag: tcb-b3 OR name contains COOPERAT (reproduces the original notebook)
    panel["is_coop_legacy"] = (
        panel["tcb"].astype(str).str.startswith("b3")
        | panel["instituicao"].astype(str).str.contains("COOPERAT", case=False, na=False)
    ).astype(int)

    # ---- de-cumulate semester-cumulative income flows into annualized quarterly ----
    seasonal_before = seasonal_profile(
        panel.assign(_roa=panel["lucro_liquido"] / panel["ativo_total"].clip(lower=1),
                     _nim=panel["resultado_intermediacao"] / panel["ativo_total"].clip(lower=1)),
        ["_roa", "_nim"])
    panel, flow_info = decumulate_semiannual(panel, FLOW_COLS)

    # ---- outcomes (raw; winsorization happens per analysis population later) ----
    A = panel["ativo_total"].clip(lower=1)
    panel["log_assets"] = np.log(A)
    panel["basileia_num"] = panel["basileia"]
    panel["leverage"] = panel["passivo"] / A
    panel["credit_ratio"] = panel["carteira_credito"] / A
    # stock over stock: unaffected by flow cumulation
    panel["prov_ratio"] = panel["provisao_credito"].abs() / panel["credito_bruto"].abs().replace(0, np.nan)
    panel["deposit_ratio"] = panel["captacoes"] / A

    # profitability: annualized de-cumulated flow over assets
    panel["roa_ann"] = panel["lucro_liquido_q"] / A
    panel["roa_legacy"] = panel["lucro_liquido"] / A          # semester-cumulative (original)

    # intermediation margin. (c) = (a) + (b) and (b) INCLUDES the loan-loss line (b5),
    # so (c) is net of credit provisions and is not a net interest margin. The primary
    # measure adds (b5) back; the version including it is retained for comparison and
    # overlaps mechanically with the provisioning outcome.
    inter_ex_pcld = panel["resultado_intermediacao_q"] - panel["resultado_pcld_q"]
    panel["nim_ann"] = inter_ex_pcld / A                      # gross of provisions (primary)
    panel["nim_ann_incl_prov"] = panel["resultado_intermediacao_q"] / A
    panel["nim_legacy"] = panel["resultado_intermediacao"] / A  # original

    # cost-to-income. Numerator and denominator are both flows over the same window,
    # so the ratio is invariant to annualization, but not to de-cumulation.
    opex_q = panel["despesas_pessoal_q"].abs() + panel["despesas_admin_q"].abs()
    op_income_q = inter_ex_pcld + panel["tarifas_q"].abs()
    panel["cti_new"] = opex_q / op_income_q.where(op_income_q > 0, np.nan)
    panel["op_income_ratio"] = op_income_q / A   # cost-to-income denominator over assets
    opex = panel["despesas_pessoal"].abs() + panel["despesas_admin"].abs()
    op_income = panel["resultado_intermediacao"] + panel["tarifas"].abs()
    panel["cti_semcum"] = opex / op_income.where(op_income > 0, np.nan)   # v5 "proper" cti
    panel["cti_gross"] = opex / panel["receitas_intermediacao"].abs().replace(0, np.nan)  # v5 legacy

    seasonal_after = seasonal_profile(panel.assign(_roa=panel["roa_ann"], _nim=panel["nim_ann"]),
                                      ["_roa", "_nim"])
    flow_diag = {"info": flow_info, "before": seasonal_before, "after": seasonal_after,
                 "pcld_available": bool(panel["resultado_pcld"].notna().any())}

    panel["year_q"] = panel["date"].dt.to_period("Q")
    panel["region"] = panel["uf"].map(UF_REGION)
    info["_flows"] = flow_diag
    return panel, info, tcb_varied


# ============================================================================= winsorize
def winsorize(df: pd.DataFrame, cols, lo=0.01, hi=0.99, bounds=None):
    df = df.copy()
    out_bounds = {}
    for c in cols:
        if c not in df.columns:
            continue
        if bounds and c in bounds:
            lobnd, hibnd = bounds[c]
        else:
            lobnd, hibnd = df[c].quantile(lo), df[c].quantile(hi)
        df[c] = df[c].clip(lobnd, hibnd)
        out_bounds[c] = (lobnd, hibnd)
    return df, out_bounds


# ============================================================================= regression
def fit(df: pd.DataFrame, out: str, formula: str, weight_col: str | None = None):
    """Fit one OLS (or WLS when weight_col is given); return cluster-by-institution
    and HC3 inference. Weights are used for the CEM stratum weighting."""
    need = ["is_coop", "log_assets", "date", "codigo", out]
    if weight_col:
        need = need + [weight_col]
    sub = df[[c for c in dict.fromkeys(need)]].dropna().copy()
    if len(sub) < 50 or sub["is_coop"].nunique() < 2:
        return None
    sub["t"] = sub["date"].dt.to_period("Q").apply(lambda x: x.ordinal)
    if weight_col:
        model = smf.wls(formula.format(o=out), data=sub, weights=sub[weight_col])
    else:
        model = smf.ols(formula.format(o=out), data=sub)
    cl = model.fit(cov_type="cluster", cov_kwds={"groups": sub["codigo"]})
    hc = model.fit(cov_type="HC3")
    ci_cl, ci_hc = cl.conf_int().loc["is_coop"], hc.conf_int().loc["is_coop"]
    return {
        "coef": float(cl.params["is_coop"]),
        "cl_lo": float(ci_cl.iloc[0]), "cl_hi": float(ci_cl.iloc[1]),
        "cl_p": float(cl.pvalues["is_coop"]),
        "cl_se": float(cl.bse["is_coop"]),
        "hc_lo": float(ci_hc.iloc[0]), "hc_hi": float(ci_hc.iloc[1]),
        "hc_p": float(hc.pvalues["is_coop"]),
        "hc_se": float(hc.bse["is_coop"]),
        "N": int(len(sub)), "n_clusters": int(sub["codigo"].nunique()),
        "n_treated": int(sub.loc[sub.is_coop == 1, "codigo"].nunique()),
    }


def cem_weights(snap: pd.DataFrame, mvars: list) -> pd.Series:
    """Coarsened-exact-matching weights (Iacus, King & Porro 2012, sec. 5).

    Treated units get weight 1. A control unit in stratum s gets
        w = (m_T^s / m_C^s) * (m_C / m_T),
    which equalises the treated:control ratio within every stratum and normalises
    the control weights to sum to m_C. Without these weights, OLS on the matched
    sample is not the CEM estimand: strata are implicitly weighted by their control
    count, so a stratum holding 2 cooperatives and 93 banks would dominate one
    holding 38 cooperatives and 7 banks.

    `snap` is one row per institution with is_coop and the coarsened covariates.
    Returns a Series indexed by codigo.
    """
    g = snap.groupby(mvars)["is_coop"].agg(mT="sum", n="count")
    g["mC"] = g["n"] - g["mT"]
    g = g[(g["mT"] > 0) & (g["mC"] > 0)]
    MT, MC = g["mT"].sum(), g["mC"].sum()
    if MT == 0 or MC == 0:
        return pd.Series(1.0, index=snap["codigo"])
    key = snap[mvars[0]] if len(mvars) == 1 else pd.MultiIndex.from_frame(snap[mvars])
    ratio = g["mT"] / g["mC"] * (MC / MT)
    wc = pd.Series(ratio.reindex(key).to_numpy(), index=snap["codigo"].to_numpy())
    w = pd.Series(np.where(snap["is_coop"].to_numpy() == 1, 1.0, wc.to_numpy()),
                  index=snap["codigo"].to_numpy())
    return w.groupby(level=0).first()


# Coarsening schemes for the matching specification. Exact-matching on macro-region
# is the binding constraint: cooperatives concentrate in the South and banks in the
# Southeast, so region-exact strata have very thin support on one side or the other.
# Each entry is (n size quantiles, match on region).
COARSENINGS = {
    "size_q5_region": (5, True),     # v5 default
    "size_q5": (5, False),
    "size_q10": (10, False),
    "size_q3_region": (3, True),
    "size_q10_region": (10, True),
}

RHO_ROBUST = 0.40   # retain >=40% of the raw gap  (== attenuation below 60%)

def wild_cluster_bootstrap(df: pd.DataFrame, out: str, formula: str,
                           cluster_col: str = "codigo", B: int = 999,
                           seed: int = 20260806, weight_col: str | None = None):
    """Wild cluster bootstrap-t for the coefficient on is_coop, imposing the null.

    Cluster-robust standard errors are unreliable when the number of TREATED
    clusters is small (Cameron, Gelbach & Miller 2008; MacKinnon & Webb 2017), which
    is the situation in the system-by-system estimates where one system contributes
    six cooperatives. The restricted wild bootstrap re-samples cluster-level
    Rademacher weights under H0: b_coop = 0 and compares the observed t to the
    bootstrap distribution.

    Returns the observed t, the bootstrap p-value, the number of clusters, and the
    number of TREATED clusters, which is the quantity that governs reliability. With
    G_treated small the Rademacher distribution itself has few distinct treated sign
    patterns (2^G_treated), so the bootstrap p-value is discrete and still
    conservative rather than exact; it is reported with G_treated alongside so the
    reader can judge.
    """
    from patsy import dmatrices
    need = ["is_coop", "log_assets", "date", cluster_col, out] + ([weight_col] if weight_col else [])
    sub = df[list(dict.fromkeys(need))].dropna().copy()
    if len(sub) < 50 or sub["is_coop"].nunique() < 2:
        return None
    sub["t"] = sub["date"].dt.to_period("Q").apply(lambda x: x.ordinal)
    y, X = dmatrices(formula.format(o=out), data=sub, return_type="dataframe")
    names = list(X.columns)
    if "is_coop" not in names:
        return None
    k = names.index("is_coop")
    y = np.asarray(y).ravel()
    X = np.asarray(X, dtype=float)
    if weight_col:
        # WLS as OLS on sqrt(w)-scaled rows, so the CEM estimand is bootstrapped with
        # the same weights fit() uses; the treated-cluster test below still works
        # because sqrt(w) * is_coop is positive exactly where is_coop is.
        sw = np.sqrt(np.asarray(sub[weight_col], dtype=float))
        X = X * sw[:, None]
        y = y * sw
    n, K = X.shape

    # sort by cluster once so cluster sums can use reduceat
    cl = pd.factorize(sub[cluster_col].to_numpy())[0]
    order = np.argsort(cl, kind="stable")
    X, y, cl = X[order], y[order], cl[order]
    starts = np.flatnonzero(np.r_[True, np.diff(cl) != 0])
    G = len(starts)
    treated_by_cluster = np.add.reduceat(X[:, k], starts) > 0
    G_treated = int(treated_by_cluster.sum())

    XtX_inv = np.linalg.pinv(X.T @ X)
    A = XtX_inv @ X.T           # beta = A y

    def cluster_t(yv):
        b = A @ yv
        e = yv - X @ b
        S = np.add.reduceat(X * e[:, None], starts, axis=0)
        meat = S.T @ S
        V = XtX_inv @ meat @ XtX_inv
        c = (G / (G - 1)) * ((n - 1) / (n - K))
        se = np.sqrt(max(c * V[k, k], 1e-30))
        return b[k] / se, b[k]

    t_obs, b_obs = cluster_t(y)

    # restricted fit: drop is_coop, impose the null
    keep = [j for j in range(K) if j != k]
    X0 = X[:, keep]
    b0 = np.linalg.pinv(X0.T @ X0) @ X0.T @ y
    fitted0 = X0 @ b0
    resid0 = y - fitted0

    rng = np.random.default_rng(seed)
    count = 0
    for _ in range(B):
        w = rng.choice(np.array([-1.0, 1.0]), size=G)
        yb = fitted0 + resid0 * np.repeat(w, np.diff(np.r_[starts, n]))
        tb, _ = cluster_t(yb)
        if abs(tb) >= abs(t_obs) - 1e-12:
            count += 1
    return {"coef": float(b_obs), "t": float(t_obs),
            "p_boot": (count + 1) / (B + 1), "G": int(G),
            "G_treated": G_treated, "B": B}


SPECS = [
    ("raw", "{o} ~ is_coop"),
    ("ctrl", "{o} ~ is_coop + log_assets + C(t)"),
    ("cem", "{o} ~ is_coop + log_assets + C(t)"),
    ("trim", "{o} ~ is_coop + log_assets + C(t)"),
]


# ============================================================================= sample selection
def select_sample(panel: pd.DataFrame, coop_def: str, cti_col: str, roa_col: str,
                  nim_col: str, peer_set: str, exclude_segments: tuple = (),
                  exclude_codigos: tuple = ()):
    """Apply the cooperative definition, the segment exclusion and the peer-set
    restriction. Returns the un-winsorised frame (all methodologies) plus the two
    drop diagnostics. Shared by run_pipeline and the robustness checks so that every
    variant starts from the same population."""
    p = panel.copy()
    p["cti"] = p[cti_col]
    p["roa"] = p[roa_col]
    p["nim"] = p[nim_col]

    if coop_def == "singular":
        sub = p[p["coop_class"].isin(["singular", "noncoop"])].copy()
        sub["is_coop"] = (sub["coop_class"] == "singular").astype(int)
    elif coop_def == "all_coop":
        sub = p.copy()
        sub["is_coop"] = sub["is_coop_any"]
    elif coop_def == "legacy_name":
        sub = p.copy()
        sub["is_coop"] = sub["is_coop_legacy"]
    else:
        raise ValueError(coop_def)

    seg_drop = {}
    if exclude_segments:
        if "segmento" not in sub.columns:
            raise KeyError("segmento not on the panel; cannot apply exclude_segments")
        modal_seg = (sub.dropna(subset=["segmento"])
                        .groupby("codigo")["segmento"].agg(
                            lambda x: x.astype(str).mode().iat[0] if len(x.mode()) else None))
        drop_ids = set(modal_seg[modal_seg.isin(exclude_segments)].index)
        seg_drop = {"excluded_segments": list(exclude_segments),
                    "institutions_dropped": int(len(drop_ids & set(sub["codigo"]))),
                    "coop_dropped": int(sub[sub.codigo.isin(drop_ids) & (sub.is_coop == 1)]
                                        ["codigo"].nunique()),
                    "obs_dropped": int(sub["codigo"].isin(drop_ids).sum())}
        sub = sub[~sub["codigo"].isin(drop_ids)].copy()

    allowed = PEER_SETS[peer_set]
    peer_drop = {}
    if allowed is not None:
        # a set restricts on modal tcb only; a dict restricts on modal tcb and on the
        # modal reporting level td (see the PEER_SETS comment)
        tcb_allowed = allowed["tcb"] if isinstance(allowed, dict) else allowed
        td_allowed = allowed.get("td") if isinstance(allowed, dict) else None
        tcb = sub["tcb_stable"].astype(str)
        before = sub.loc[sub.is_coop == 0, "codigo"].nunique()
        peer_ok = tcb.isin(tcb_allowed)
        if td_allowed is not None:
            if "td_stable" not in sub.columns:
                raise KeyError("td_stable not on the panel; cannot apply a reporting-level rung")
            peer_ok = peer_ok & sub["td_stable"].astype(str).isin(td_allowed)
        if isinstance(allowed, dict) and allowed.get("structural"):
            # strictly positive total deposits in every full-methodology quarter of the
            # institution's presence; a missing deposits field in any quarter disqualifies
            if "depositos" not in sub.columns:
                raise KeyError("depositos not on the panel; cannot apply the structural rung")
            fm = sub[(sub["is_coop"] == 0) & (sub["full_method"] == 1)]
            ok = fm.groupby("codigo")["depositos"].agg(
                lambda s: bool(s.notna().all() and (s > 0).all() and len(s) > 0))
            peer_ok = peer_ok & sub["codigo"].map(ok).fillna(False).astype(bool)
            peer_drop["structural_rule"] = "depositos > 0 in every full-methodology quarter"
        keep = (sub["is_coop"] == 1) | peer_ok
        peer_drop.update({"peers_before": int(before),
                          "peers_after": int(sub.loc[keep & (sub.is_coop == 0), "codigo"].nunique())})
        sub = sub[keep].copy()
    if exclude_codigos:
        drop = sub["codigo"].isin(set(exclude_codigos))
        peer_drop["excluded_codigos"] = {"codigos": list(exclude_codigos),
                                         "institutions_dropped": int(sub.loc[drop, "codigo"].nunique()),
                                         "obs_dropped": int(drop.sum())}
        sub = sub[~drop].copy()
    return sub, seg_drop, peer_drop


# ============================================================================= pipeline
def run_pipeline(panel: pd.DataFrame, coop_def: str, winsor_scope: str,
                 use_cluster: bool, cti_col: str,
                 roa_col: str = "roa_ann", nim_col: str = "nim_ann",
                 peer_set: str = "all", coarsen: str = "size_q5_region",
                 cem_weight_mode: str = "per_obs",
                 exclude_segments: tuple = (),
                 winsor_bounds: dict | None = None,
                 exclude_codigos: tuple = ()):
    """Returns a results dict for one configuration.
    coop_def: 'singular' | 'all_coop' | 'legacy_name'
    winsor_scope: 'analysis' | 'panel'
    winsor_bounds: optional {outcome: (lo, hi)} that overrides the winsorisation
      bounds, so a sub-rung can be clipped exactly as the primary sample was (pass
      primary["winsor_bounds"]) and its coefficients compared with the main table.
    cti_col / roa_col / nim_col: which constructed column carries each flow outcome.
      primary: cti_new / roa_ann / nim_ann   (de-cumulated, annualized, gross of PCLD)
      v5     : cti_semcum / roa_legacy / nim_legacy
      original notebook: cti_gross / roa_legacy / nim_legacy
    peer_set: which non-cooperative institutions form the comparison group (PEER_SETS)
    exclude_segments: drop institutions whose modal Res. 4.553/2017 segment is listed.
      Proportionality is applied by segment, not by institution type: the systemic
      capital buffer, the liquidity ratios and internal-model eligibility bind the
      largest segments, which contain banks only. Passing ("S1", "S2") removes them so
      that the comparison runs entirely within segments facing one set of requirements.
      Exclusion is by modal segment, at institution level, to keep panels balanced.
    """
    if peer_set not in PEER_SETS:
        raise ValueError(f"peer_set must be one of {list(PEER_SETS)}")
    if coarsen not in COARSENINGS:
        raise ValueError(f"coarsen must be one of {list(COARSENINGS)}")
    if cem_weight_mode not in ("per_obs", "per_institution"):
        raise ValueError("cem_weight_mode must be per_obs or per_institution")
    sub, seg_drop, peer_drop = select_sample(panel, coop_def, cti_col, roa_col, nim_col,
                                             peer_set, exclude_segments, exclude_codigos)

    cols = list(OUTCOMES)
    panel_bounds = winsorize(sub, cols)[1] if winsor_scope == "panel" else None

    l2 = sub[sub["full_method"] == 1].copy()
    if winsor_bounds is not None:
        l2, wbounds = winsorize(l2, cols, bounds=winsor_bounds)
    elif winsor_scope == "panel":
        l2, wbounds = winsorize(l2, cols, bounds=panel_bounds)
    else:
        l2, wbounds = winsorize(l2, cols)

    # per-institution typical size for coarsening (median over the period, not entry quarter)
    nq, use_region = COARSENINGS[coarsen]
    med_la = l2.groupby("codigo")["log_assets"].median()
    l2["size_bin"] = pd.qcut(l2["codigo"].map(med_la), q=nq, labels=False, duplicates="drop")
    n_bins_realised = int(pd.Series(l2["size_bin"]).nunique())

    # common support on log assets (5/95 of each group)
    cq = l2.loc[l2.is_coop == 1, "log_assets"].quantile([0.05, 0.95])
    nq = l2.loc[l2.is_coop == 0, "log_assets"].quantile([0.05, 0.95])
    ov_lo, ov_hi = max(cq.iloc[0], nq.iloc[0]), min(cq.iloc[1], nq.iloc[1])

    # CEM strata
    snap = l2.drop_duplicates("codigo")[["codigo", "is_coop", "size_bin", "region"]].dropna()
    mvars = (["size_bin", "region"]
             if (use_region and snap["region"].nunique() > 1) else ["size_bin"])
    st = snap.groupby(mvars)["is_coop"].agg(["sum", "count"])
    st["nc"] = st["count"] - st["sum"]
    valid = st[(st["sum"] > 0) & (st["nc"] > 0)].index
    if len(mvars) == 1:
        keep_ids = snap[snap[mvars[0]].isin(valid)]["codigo"]
    else:
        snap = snap.copy()
        snap["_s"] = list(zip(*[snap[v] for v in mvars]))
        keep_ids = snap[snap["_s"].isin(valid)]["codigo"]
    l2_cem = l2[l2["codigo"].isin(keep_ids)].copy()
    _snapc = l2_cem.drop_duplicates("codigo")[["codigo", "is_coop"] + mvars].dropna()
    _w = cem_weights(_snapc, mvars)
    l2_cem["cem_w"] = l2_cem["codigo"].map(_w)
    if cem_weight_mode == "per_institution":
        # each institution contributes its stratum weight in total rather than per
        # quarter, so institutions observed for longer do not count proportionally more
        _T = l2_cem.groupby("codigo")["codigo"].transform("size")
        l2_cem["cem_w"] = l2_cem["cem_w"] / _T
    _wo = l2_cem.loc[l2_cem.is_coop == 0, "cem_w"].dropna().to_numpy()
    cem_w_diag = {"n_weighted": int(l2_cem["cem_w"].notna().sum()),
                  "coarsen": coarsen, "weight_mode": cem_weight_mode,
                  "size_bins_realised": n_bins_realised,
                  "match_vars": list(mvars), "n_strata": int(len(valid)),
                  "eff_n_control_obs": float((_wo.sum() ** 2) / max((_wo ** 2).sum(), 1e-12))
                  if len(_wo) else np.nan,
                  "w_min": float(np.nanmin(_w.to_numpy())) if len(_w) else np.nan,
                  "w_max": float(np.nanmax(_w.to_numpy())) if len(_w) else np.nan,
                  "eff_n_controls": float(
                      (_w[_snapc.set_index("codigo")["is_coop"].reindex(_w.index) == 0].sum() ** 2)
                      / max((_w[_snapc.set_index("codigo")["is_coop"].reindex(_w.index) == 0] ** 2).sum(), 1e-12))
                  if (_snapc["is_coop"] == 0).any() else np.nan}
    l2_trim = l2[l2["log_assets"].between(ov_lo, ov_hi)].copy()
    frames = {"raw": l2, "ctrl": l2, "cem": l2_cem, "trim": l2_trim}

    # regressions
    skipped = []
    reg = {sl: {} for sl, _ in SPECS}
    reg_extra = {"cem_unweighted": {}}
    for sl, ftmpl in SPECS:
        for o in OUTCOMES:
            wcol = "cem_w" if sl == "cem" else None
            r = fit(frames[sl], o, ftmpl, weight_col=wcol)
            if r:
                reg[sl][o] = r
            else:
                skipped.append((sl, o))
    # conditional-median counterpart of every cell. Several outcomes are heavily
    # skewed (Basel skew ~4, cost-to-income ~4.5), and where the conditional mean and
    # conditional median disagree in magnitude the mean result is a tail phenomenon
    # rather than a statement about the typical institution. Reported alongside the
    # OLS coefficient rather than relegated to robustness.
    med = {sl: {} for sl, _ in SPECS}
    for sl, ftmpl in SPECS:
        for o in OUTCOMES:
            need = ["is_coop", "log_assets", "date", "codigo", o]
            sq = frames[sl][need].dropna().copy()
            if len(sq) < 100 or sq["is_coop"].nunique() < 2:
                continue
            sq["t"] = sq["date"].dt.to_period("Q").apply(lambda x: x.ordinal)
            try:
                q = smf.quantreg(ftmpl.format(o=o), data=sq).fit(q=0.5)
                med[sl][o] = {"coef": float(q.params["is_coop"]),
                              "p": float(q.pvalues["is_coop"]),
                              "skew": float(sq[o].skew()), "N": int(len(sq))}
            except Exception:
                pass

    # unweighted matched-sample OLS retained for comparison with the CEM estimand
    for o in OUTCOMES:
        r = fit(frames["cem"], o, SPECS[2][1])
        if r:
            reg_extra["cem_unweighted"][o] = r

    # ---- classification --------------------------------------------------------
    # Significance is evaluated FIRST. The retention ratio rho = |b_trim|/|b_raw| is
    # only meaningful when the raw coefficient is itself distinguishable from zero;
    # computing it around a null produces arbitrary values (a near-zero denominator),
    # which is why it is reported as NaN for outcomes that fail the significance gate.
    # rho is reported instead of 1-rho so that amplification (rho > 1, the coefficient
    # growing as the design tightens) reads naturally rather than as negative
    # attenuation. rho >= RHO_ROBUST keeps the substantive threshold used previously
    # (retaining at least 40% of the raw gap, i.e. attenuation below 60%).
    summ = {}
    pkey = "cl_p" if use_cluster else "hc_p"
    for o in OUTCOMES:
        present = [s for s, _ in SPECS if o in reg[s]]
        if not present:
            continue
        coefs = [reg[s][o]["coef"] for s in present]
        pvals = {s: reg[s][o][pkey] for s in present}
        nsig = sum(1 for s in present if pvals[s] < 0.05)
        allsig = (nsig == len(present)) and len(present) == len(SPECS)
        same_sign = len({np.sign(c) for c in coefs if c != 0}) == 1

        raw = reg["raw"].get(o, {}).get("coef", np.nan)
        trim = reg["trim"].get(o, {}).get("coef", np.nan)
        rho = (abs(trim) / abs(raw)) if (allsig and abs(raw) > 1e-12
                                         and not np.isnan(trim)) else np.nan

        if not allsig:
            tier = "null"
        elif not same_sign:
            tier = "sign_unstable"
        elif rho >= RHO_ROBUST:
            tier = "robust"
        else:
            tier = "attenuated"
        summ[o] = {"rho": rho, "atten": (1 - rho) if rho == rho else np.nan,
                   "tier": tier, "n_sig": nsig, "n_specs": len(present),
                   "amplifies": bool(rho == rho and rho > 1.10),
                   "min": min(coefs), "max": max(coefs)}

    # descriptive means (winsorized analysis sample)
    desc = {}
    for c in cols:
        if c in l2.columns:
            desc[c] = {
                "coop_mean": float(l2.loc[l2.is_coop == 1, c].mean()),
                "coop_sd": float(l2.loc[l2.is_coop == 1, c].std()),
                "coop_med": float(l2.loc[l2.is_coop == 1, c].median()),
                "coop_n": int(l2.loc[l2.is_coop == 1, c].notna().sum()),
                "nc_mean": float(l2.loc[l2.is_coop == 0, c].mean()),
                "nc_sd": float(l2.loc[l2.is_coop == 0, c].std()),
                "nc_med": float(l2.loc[l2.is_coop == 0, c].median()),
                "nc_n": int(l2.loc[l2.is_coop == 0, c].notna().sum()),
            }

    # overlap shares, correlations, sign-flip decomposition
    def pct_inside(v):
        d = l2[l2.is_coop == v]
        return 100 * len(d[d.log_assets.between(ov_lo, ov_hi)]) / max(len(d), 1)

    def corr(df):
        d = df[["basileia_num", "leverage"]].dropna()
        return float(d.corr().iloc[0, 1]) if len(d) > 2 else None

    flips = {}
    for o in OUTCOMES:
        if summ.get(o, {}).get("tier") == "sign_flip":
            ins_c = l2[(l2.is_coop == 1) & (l2.log_assets.between(ov_lo, ov_hi))][o].mean()
            ins_n = l2[(l2.is_coop == 0) & (l2.log_assets.between(ov_lo, ov_hi))][o].mean()
            out_c = l2[(l2.is_coop == 1) & (~l2.log_assets.between(ov_lo, ov_hi))][o].mean()
            out_n = l2[(l2.is_coop == 0) & (~l2.log_assets.between(ov_lo, ov_hi))][o].mean()
            flips[o] = {"inside_gap": float(ins_c - ins_n), "outside_gap": float(out_c - out_n),
                        "inside_coop": float(ins_c), "inside_nc": float(ins_n),
                        "outside_coop": float(out_c), "outside_nc": float(out_n)}

    # standardized mean differences (matching-literature denominator)
    def smd_table(df):
        rows = {}
        for c in cols + ["log_assets"]:
            if c not in df.columns:
                continue
            a = df.loc[df.is_coop == 1, c].dropna()
            b = df.loc[df.is_coop == 0, c].dropna()
            if len(a) < 5 or len(b) < 5:
                continue
            denom = np.sqrt((a.var() + b.var()) / 2.0)
            rows[c] = float((a.mean() - b.mean()) / denom) if denom > 0 else np.nan
        return rows
    balance = {"full": smd_table(l2), "cem": smd_table(l2_cem), "trim": smd_table(l2_trim)}

    res = {
        "config": {"coop_def": coop_def, "winsor_scope": winsor_scope,
                   "cluster": use_cluster, "cti_col": cti_col,
                   "roa_col": roa_col, "nim_col": nim_col, "peer_set": peer_set,
                   "coarsen": coarsen, "cem_weight_mode": cem_weight_mode,
                   "exclude_segments": list(exclude_segments),
                   "winsor_bounds": "given" if winsor_bounds is not None else None,
                   "exclude_codigos": list(exclude_codigos)},
        "seg_drop": seg_drop,
        "peer_drop": peer_drop,
        "n_inst": int(l2["codigo"].nunique()),
        "n_coop": int(l2.loc[l2.is_coop == 1, "codigo"].nunique()),
        "n_nc": int(l2.loc[l2.is_coop == 0, "codigo"].nunique()),
        "n_obs": int(len(l2)),
        "date_min": str(l2["date"].min().date()), "date_max": str(l2["date"].max().date()),
        "winsor_bounds": {k: [float(v[0]), float(v[1])] for k, v in wbounds.items()},
        "desc": desc, "reg": reg, "reg_extra": reg_extra, "median": med, "summary": summ,
        "skipped": skipped, "cem_w": cem_w_diag,
        "overlap": {"lo": float(ov_lo), "hi": float(ov_hi),
                    "coop_pct": pct_inside(1), "nc_pct": pct_inside(0)},
        "cem": {"n_inst": int(l2_cem["codigo"].nunique()),
                "dropped": int(l2["codigo"].nunique() - l2_cem["codigo"].nunique())},
        "trim": {"n_inst": int(l2_trim["codigo"].nunique()), "n_obs": int(len(l2_trim))},
        "corr": {"analysis_all": corr(l2),
                 "analysis_coop": corr(l2[l2.is_coop == 1]),
                 "analysis_nc": corr(l2[l2.is_coop == 0])},
        "flips": flips, "balance": balance,
        "_l2": l2, "_l2_cem": l2_cem, "_l2_trim": l2_trim,
        "_ov": (ov_lo, ov_hi),
    }
    return res


# ============================================================================= system heterogeneity
def filiacao_to_system(fil):
    f = "" if pd.isna(fil) else str(fil).upper()
    if f == "":
        return "Independent"
    for key, name in [("SICOOB", "Sicoob"), ("SICREDI", "Sicredi"), ("UNICRED", "Unicred"),
                      ("UNIPRIME", "Uniprime")]:
        if key in f:
            return name
    if any(k in f for k in ("CRESOL", "ASCOOB", "CONFESOL")):
        return "Cresol"
    if any(k in f for k in ("AILOS", "CECRED")):
        return "Ailos"
    if "CREDISIS" in f:
        return "Credisis"
    return "OtherCentral"


MANUAL_SYSTEM = {  # singulars absent from the cadastro CNPJ table (no fuzzy matching)
    53923116: "Sicoob", 26408187: "Sicredi", 10772401: "Sicredi", 57647653: "Sicredi",
    87789178: "Sicredi", 25626490: "Sicredi", 83315408: "Sicredi", 8143326: "Sicredi",
    8418804: "Cresol", 54603022: "Independent", 42240382: "Independent", 67607564: "Independent",
}


def system_heterogeneity(primary, panel, use_cluster=True, boot=False, B=999):
    """Assign each singular cooperative to its system via the cadastro CNPJ join, then
    re-estimate the controlled specification per system against all non-cooperatives.
    Singular set comes from tcb (coop_class == 'singular'); no EXCLUDE list."""
    l2 = primary["_l2"]
    coop = l2[l2.is_coop == 1].copy()  # singular cooperatives only, by construction
    out = {"composition": {}, "reg": {}, "join": {}, "n_singular": int(coop["codigo"].nunique())}

    if not CAD_PATH.exists():
        out["error"] = f"cadastro not found at {CAD_PATH}"
        return out
    cad = pd.read_csv(CAD_PATH, sep=",", encoding="utf-8")
    cad.columns = cad.columns.str.strip()
    cad = cad[cad["CLASSE"] == "Singular"].copy()
    cad["coop_system"] = cad["FILIACAO"].map(filiacao_to_system)
    cad["cnpj_key"] = cad["CNPJ"].astype(str).str.zfill(8)

    snap = coop.drop_duplicates("codigo").copy()
    snap["cnpj_key"] = snap["codigo"].astype(str).str.zfill(8)
    j = snap.merge(cad[["cnpj_key", "coop_system"]], on="cnpj_key", how="left")
    out["join"] = {"attempted": int(len(j)),
                   "matched_cnpj": int(j["coop_system"].notna().sum()),
                   "unmatched": int(j["coop_system"].isna().sum())}
    j["coop_system"] = j.apply(
        lambda r: MANUAL_SYSTEM.get(r["codigo"], r["coop_system"]), axis=1)
    out["join"]["still_null"] = int(j["coop_system"].isna().sum())
    sys_of = dict(zip(j["codigo"], j["coop_system"]))
    coop["coop_system"] = coop["codigo"].map(sys_of)

    comp = coop.drop_duplicates("codigo").groupby("coop_system")["codigo"].nunique()
    out["composition"] = {k: int(v) for k, v in comp.sort_values(ascending=False).items()}
    out["assign"] = dict(sys_of)

    nc = l2[l2.is_coop == 0].copy()
    for s in comp.sort_values(ascending=False).index:
        sd = coop[coop["coop_system"] == s]
        n = sd["codigo"].nunique()
        if n < 5:
            out["reg"][s] = {"n": int(n), "skip": True}
            continue
        comb = pd.concat([sd, nc], ignore_index=True)
        row = {"n": int(n)}
        for o in HET_OUTCOMES:
            r = fit(comb, o, "{o} ~ is_coop + log_assets + C(t)")
            if r:
                cell = {"coef": r["coef"], "p": r["cl_p" if use_cluster else "hc_p"],
                        "N": r["N"], "n_clusters": r["n_clusters"]}
                if boot:
                    wb = wild_cluster_bootstrap(comb, o, "{o} ~ is_coop + log_assets + C(t)",
                                                B=B)
                    if wb:
                        cell.update({"p_boot": wb["p_boot"], "G": wb["G"],
                                     "G_treated": wb["G_treated"]})
                row[o] = cell
        out["reg"][s] = row
    return out


# ============================================================================= robustness
BOOT_B = 1999       # wild cluster bootstrap replications for the reported tables
SIM_DRAWS = 200     # small-cluster simulation: random draws per design
SIM_B = 499         # bootstrap replications inside each simulation draw

WINSOR_VARIANTS = {
    "pooled_1_99": dict(lo=0.01, hi=0.99, by_group=False),   # primary
    "pooled_5_95": dict(lo=0.05, hi=0.95, by_group=False),
    "by_group_1_99": dict(lo=0.01, hi=0.99, by_group=True),
    "none": None,
}


def bootstrap_main(res, B=BOOT_B, seed=20260806):
    """Restricted wild cluster bootstrap p-value for every cell of the main table,
    attached in place as reg[spec][outcome]['p_boot'] with the treated cluster count.
    The CEM column is bootstrapped under the same stratum weights fit() uses."""
    frames = {"raw": res["_l2"], "ctrl": res["_l2"],
              "cem": res["_l2_cem"], "trim": res["_l2_trim"]}
    for sl, ftmpl in SPECS:
        for o in OUTCOMES:
            cell = res["reg"][sl].get(o)
            if not cell:
                continue
            wb = wild_cluster_bootstrap(frames[sl], o, ftmpl, B=B, seed=seed,
                                        weight_col="cem_w" if sl == "cem" else None)
            if wb:
                cell.update({"p_boot": wb["p_boot"], "G_treated": wb["G_treated"], "B": B})
    return res


def winsor_variants(panel, coop_def="singular", cti_col="cti_new", roa_col="roa_ann",
                    nim_col="nim_ann", peer_set="banks", exclude_segments=()):
    """Controlled specification under alternative winsorisation rules: pooled 1/99
    (the primary rule), pooled 5/95, 1/99 within each group, and none."""
    sub, _, _ = select_sample(panel, coop_def, cti_col, roa_col, nim_col,
                              peer_set, exclude_segments)
    l2_raw = sub[sub["full_method"] == 1].copy()
    cols = list(OUTCOMES)
    out = {}
    for name, spec in WINSOR_VARIANTS.items():
        if spec is None:
            l2 = l2_raw.copy()
        elif spec["by_group"]:
            parts = [winsorize(l2_raw[l2_raw.is_coop == g], cols, spec["lo"], spec["hi"])[0]
                     for g in (1, 0)]
            l2 = pd.concat(parts, ignore_index=True)
        else:
            l2 = winsorize(l2_raw, cols, spec["lo"], spec["hi"])[0]
        out[name] = {o: fit(l2, o, SPECS[1][1]) for o in OUTCOMES}
    return out


def adopter_selection(panel, cti_col="cti_new", roa_col="roa_ann", nim_col="nim_ann"):
    """Selection into the full-methodology sample. Singular cooperatives that move
    from the simplified to the full methodology inside the window are compared, on
    their pre-adoption simplified-method quarters, with singular cooperatives never
    observed under the full methodology, controlling for size and quarter. The
    is_coop slot carries the treatment (1 = future adopter) so fit() can be reused.
    Winsorised at the pooled 1/99 within this comparison sample."""
    p = panel[panel["coop_class"] == "singular"].dropna(subset=["full_method"]).copy()
    p["cti"], p["roa"], p["nim"] = p[cti_col], p[roa_col], p[nim_col]
    first_full = p[p.full_method == 1].groupby("codigo")["date"].min()
    p["first_full"] = p["codigo"].map(first_full)
    pre = (p.full_method == 0) & p["first_full"].notna() & (p["date"] < p["first_full"])
    post = (p.full_method == 0) & p["first_full"].notna() & (p["date"] > p["first_full"])
    adopters = set(p.loc[pre, "codigo"])
    reverters = set(p.loc[post, "codigo"])
    ever_full = set(first_full.index)
    never = set(p["codigo"]) - ever_full
    has_simp = p.groupby("codigo")["full_method"].apply(lambda s: bool((s == 0).any()))
    always_full = {c for c in ever_full if not has_simp.get(c, False)}
    keep = p[(pre & p["codigo"].isin(adopters))
             | ((p.full_method == 0) & p["codigo"].isin(never))].copy()
    keep["is_coop"] = keep["codigo"].isin(adopters).astype(int)
    keep, _ = winsorize(keep, list(OUTCOMES))
    reg = {o: fit(keep, o, SPECS[1][1]) for o in OUTCOMES}
    # Looser variant: every full-methodology cooperative observed under the simplified
    # methodology at any point, on all its simplified quarters. This includes the
    # cooperatives whose simplified quarters come after, not before, their first
    # full-methodology quarter, so it is not a pre-adoption comparison. Kept because
    # an earlier draft quoted it.
    any_simp = {c for c in ever_full if has_simp.get(c, False)}
    keep_b = p[(p.full_method == 0)
               & (p["codigo"].isin(any_simp) | p["codigo"].isin(never))].copy()
    keep_b["is_coop"] = keep_b["codigo"].isin(any_simp).astype(int)
    keep_b, _ = winsorize(keep_b, list(OUTCOMES))
    reg_b = {o: fit(keep_b, o, SPECS[1][1]) for o in OUTCOMES}
    return {"n_singular_in_window": int(p["codigo"].nunique()),
            "n_adopters": len(adopters), "n_never": len(never),
            "n_always_full": len(always_full), "n_reverters_any": len(reverters),
            "obs_adopter_pre": int(keep["is_coop"].sum()),
            "obs_never": int((keep["is_coop"] == 0).sum()),
            "reg": reg,
            "n_any_simplified": len(any_simp),
            "obs_any_simplified": int(keep_b["is_coop"].sum()),
            "reg_any_simplified": reg_b}


def _delta_table(base_reg, alt_reg):
    out = {}
    for o in OUTCOMES:
        b, a = base_reg.get(o), alt_reg.get(o)
        if b and a:
            pct = (100 * (a["coef"] - b["coef"]) / abs(b["coef"])
                   if abs(b["coef"]) > 1e-12 else np.nan)
            out[o] = {"full": b["coef"], "alt": a["coef"], "pct_change": pct,
                      "alt_p": a["cl_p"], "N_full": b["N"], "N_alt": a["N"]}
    return out


def reverters(primary, panel):
    """Cooperatives in the analysis sample that report a simplified-method quarter
    after their first full-method quarter, and the controlled specification with
    them removed."""
    l2 = primary["_l2"]
    coops = l2[l2.is_coop == 1]
    p = panel[(panel["coop_class"] == "singular")
              & panel["codigo"].isin(coops["codigo"].unique())].dropna(subset=["full_method"])
    first_full = p[p.full_method == 1].groupby("codigo")["date"].min()
    ff = p["codigo"].map(first_full)
    rev_ids = set(p.loc[(p.full_method == 0) & (p["date"] > ff), "codigo"])
    rev_obs = int(coops["codigo"].isin(rev_ids).sum())
    sub = l2[~l2["codigo"].isin(rev_ids)]
    alt = {o: fit(sub, o, SPECS[1][1]) for o in OUTCOMES}
    return {"n_reverters": len(rev_ids), "reverter_obs": rev_obs,
            "coop_obs": int(len(coops)),
            "share_pct": 100 * rev_obs / max(len(coops), 1),
            "reg": _delta_table(primary["reg"]["ctrl"], alt)}


def provisioning_coverage(primary):
    """Controlled specification for every outcome on the rows where the provisioning
    ratio is observed, against the full-sample estimate."""
    l2 = primary["_l2"]
    sub = l2[l2["prov_ratio"].notna()]
    alt = {o: fit(sub, o, SPECS[1][1]) for o in OUTCOMES}
    return {"obs_full": int(len(l2)), "obs_covered": int(len(sub)),
            "coverage_pct": 100 * len(sub) / max(len(l2), 1),
            "reg": _delta_table(primary["reg"]["ctrl"], alt)}


def small_cluster_simulation(primary, outcome="basileia_num", n_treated=6,
                             draws=SIM_DRAWS, B=SIM_B, seed=20260806):
    """Size of the cluster-robust t-test against the restricted wild cluster
    bootstrap when only a handful of clusters are treated, on this design.
    Effect design: n_treated cooperatives drawn at random against every bank, so the
    true differential is the sample one. Null design: n_treated banks relabelled as
    treated inside the bank population, so the true differential is zero."""
    l2 = primary["_l2"]
    coop_ids = l2.loc[l2.is_coop == 1, "codigo"].unique()
    banks = l2[l2.is_coop == 0].copy()
    bank_ids = banks["codigo"].unique()
    rng = np.random.default_rng(seed)
    f = SPECS[1][1]
    eff, nul = [], []
    for _ in range(draws):
        ids = rng.choice(coop_ids, n_treated, replace=False)
        comb = pd.concat([l2[l2["codigo"].isin(ids)], banks], ignore_index=True)
        r = fit(comb, outcome, f)
        wb = wild_cluster_bootstrap(comb, outcome, f, B=B, seed=int(rng.integers(2**31)))
        if r and wb:
            eff.append((r["coef"], r["cl_p"], wb["p_boot"], wb["G_treated"]))
        pids = rng.choice(bank_ids, n_treated, replace=False)
        pl = banks.copy()
        pl["is_coop"] = pl["codigo"].isin(pids).astype(int)
        r0 = fit(pl, outcome, f)
        wb0 = wild_cluster_bootstrap(pl, outcome, f, B=B, seed=int(rng.integers(2**31)))
        if r0 and wb0:
            nul.append((r0["coef"], r0["cl_p"], wb0["p_boot"], wb0["G_treated"]))

    def summ(rows):
        a = np.array(rows, dtype=float)
        if not len(a):
            return {}
        return {"draws": int(len(a)),
                "median_coef": float(np.median(a[:, 0])),
                "median_asym_p": float(np.median(a[:, 1])),
                "median_boot_p": float(np.median(a[:, 2])),
                "reject5_asym": float((a[:, 1] < 0.05).mean()),
                "reject5_boot": float((a[:, 2] < 0.05).mean()),
                "reject1_asym": float((a[:, 1] < 0.01).mean()),
                "reject1_boot": float((a[:, 2] < 0.01).mean()),
                "median_G_treated": float(np.median(a[:, 3])),
                "min_boot_p": float(a[:, 2].min())}
    return {"outcome": outcome, "n_treated": n_treated, "draws": draws, "B": B,
            "effect": summ(eff), "null": summ(nul)}


def collapse_stability(l2: pd.DataFrame, min_q: int = 8, bounds=None):
    """Collapse an analysis-sample frame to one row per institution and build the two
    stability outcomes over that institution's full-methodology quarters:
      roa_vol = s.d. of the annualised de-cumulated quarterly ROA already used;
      zscore  = (mean ROA + mean equity/assets) / s.d.(ROA), equity/assets = 1 - leverage.
    Institutions with fewer than min_q quarters of ROA are dropped. roa_vol and zscore
    are winsorised at the pooled 1/99 within the institution-level sample (bounds are
    computed here unless passed, so subsamples inherit the full-sample clip).
    Returns (institution_frame, winsor_bounds, drop_counts)."""
    g = l2.groupby("codigo")
    d = pd.DataFrame({
        "is_coop": g["is_coop"].first(),
        "log_assets": g["log_assets"].mean(),
        "roa_mean": g["roa"].mean(),
        "roa_vol": g["roa"].std(ddof=1),
        "eq_mean": 1.0 - g["leverage"].mean(),
        "n_q": g["roa"].apply(lambda s: int(s.notna().sum())),
        "cem_w": g["cem_w"].first() if "cem_w" in l2.columns else np.nan,
    }).reset_index()
    before = {"coop": int((d.is_coop == 1).sum()), "bank": int((d.is_coop == 0).sum())}
    d = d[d["n_q"] >= min_q].copy()
    after = {"coop": int((d.is_coop == 1).sum()), "bank": int((d.is_coop == 0).sum())}
    d["zscore"] = (d["roa_mean"] + d["eq_mean"]) / d["roa_vol"].replace(0, np.nan)
    d, wb = winsorize(d, ["roa_vol", "zscore"], bounds=bounds)
    d["date"] = pd.Timestamp("2020-06-01")   # dummy: fit()/bootstrap expect a date column
    drops = {"before": before, "after": after,
             "dropped_coop": before["coop"] - after["coop"],
             "dropped_bank": before["bank"] - after["bank"], "min_q": min_q}
    return d, wb, drops


def stability_estimates(res, B=BOOT_B, min_q=8):
    """Institution-level cross-section of the two stability outcomes for one comparison
    group. Four designs, mirroring the panel specifications but at the institution level
    (the unit is the institution, so there are no quarter fixed effects):
      raw   y ~ coop
      ctrl  y ~ coop + mean log assets
      cem   the same on the size-matched institutions, with CEM weights
      trim  the same on institutions whose mean log assets lie in the common-support band
    Inference is HC3 (the reported p), with a wild bootstrap over institutions. The
    matched set and common-support band are taken from the panel result so they coincide
    with the eight panel outcomes."""
    l2 = res["_l2"]
    D_all, wbounds, drops = collapse_stability(l2, min_q=min_q)
    ov_lo, ov_hi = res["_ov"]
    matched_w = res["_l2_cem"].groupby("codigo")["cem_w"].first()
    D_cem = D_all[D_all["codigo"].isin(set(matched_w.index))].copy()
    D_cem["cem_w"] = D_cem["codigo"].map(matched_w)   # per-institution CEM weight
    D_trim = D_all[D_all["log_assets"].between(ov_lo, ov_hi)].copy()
    frames = {"raw": D_all, "ctrl": D_all, "cem": D_cem, "trim": D_trim}
    fml = {"raw": "{o} ~ is_coop", "ctrl": "{o} ~ is_coop + log_assets",
           "cem": "{o} ~ is_coop + log_assets", "trim": "{o} ~ is_coop + log_assets"}

    reg = {sl: {} for sl, _ in SPECS}
    med = {sl: {} for sl, _ in SPECS}
    for sl, _ in SPECS:
        for o in STAB_LABELS:
            wcol = "cem_w" if sl == "cem" else None
            r = fit(frames[sl], o, fml[sl], weight_col=wcol)
            if not r:
                continue
            wb = wild_cluster_bootstrap(frames[sl], o, fml[sl], B=B, weight_col=wcol)
            if wb:
                r["p_boot"] = wb["p_boot"]
                r["G_treated"] = wb["G_treated"]
            reg[sl][o] = r
            sq = frames[sl][["is_coop", "log_assets", o]].dropna()
            if len(sq) > 50 and sq["is_coop"].nunique() == 2:
                try:
                    q = smf.quantreg(fml[sl].format(o=o), data=sq).fit(q=0.5)
                    med[sl][o] = {"coef": float(q.params["is_coop"]),
                                  "p": float(q.pvalues["is_coop"]),
                                  "skew": float(sq[o].skew()), "N": int(len(sq))}
                except Exception:
                    pass

    # tier classification on HC3 significance, mirroring run_pipeline's summary
    summ = {}
    for o in STAB_LABELS:
        present = [s for s, _ in SPECS if o in reg[s]]
        if not present:
            continue
        coefs = [reg[s][o]["coef"] for s in present]
        nsig = sum(1 for s in present if reg[s][o]["hc_p"] < 0.05)
        allsig = (nsig == len(present)) and len(present) == len(SPECS)
        same_sign = len({np.sign(c) for c in coefs if c != 0}) == 1
        raw = reg["raw"].get(o, {}).get("coef", np.nan)
        trim = reg["trim"].get(o, {}).get("coef", np.nan)
        rho = (abs(trim) / abs(raw)) if (allsig and abs(raw) > 1e-12
                                         and not np.isnan(trim)) else np.nan
        tier = ("null" if not allsig else "sign_unstable" if not same_sign
                else "robust" if rho >= RHO_ROBUST else "attenuated")
        summ[o] = {"rho": rho, "atten": (1 - rho) if rho == rho else np.nan,
                   "tier": tier, "n_sig": nsig, "n_specs": len(present),
                   "amplifies": bool(rho == rho and rho > 1.10),
                   "min": min(coefs), "max": max(coefs)}

    desc = {}
    for o in STAB_LABELS:
        a, b = D_all.loc[D_all.is_coop == 1, o].dropna(), D_all.loc[D_all.is_coop == 0, o].dropna()
        desc[o] = {"coop_mean": float(a.mean()), "coop_med": float(a.median()),
                   "coop_n": int(len(a)), "nc_mean": float(b.mean()),
                   "nc_med": float(b.median()), "nc_n": int(len(b))}

    design = (f"institution-level cross-section, one row per institution over its "
              f">= {min_q} full-methodology quarters; raw = coop, ctrl/cem/trim add "
              f"mean log assets; no quarter fixed effects (unit is the institution); "
              f"HC3 errors and a wild bootstrap over institutions; roa_vol and zscore "
              f"winsorised at the pooled 1/99 within the institution-level sample.")
    return {"reg": reg, "median": med, "summary": summ, "desc": desc,
            "drops": drops, "wbounds": wbounds, "design": design,
            "n_inst": int(len(D_all)), "n_cem": int(len(D_cem)), "n_trim": int(len(D_trim))}


def subperiod_split(res, B=BOOT_B, cut="2022-01-01"):
    """Controlled specification against banks for the eight panel outcomes on the two
    subperiods either side of the entry into force of Res. 4.955/4.958 (3 Jan 2022),
    beside the full-sample estimate. Clustered SE, wild bootstrap, N and institution
    counts. Runs on the winsorised primary analysis frame so it inherits the primary
    sample exactly."""
    l2 = res["_l2"]
    cutd = pd.Timestamp(cut)
    windows = {"full": l2,
               "p1": l2[l2["date"] < cutd],
               "p2": l2[l2["date"] >= cutd]}
    out = {"cut": cut, "reg": {w: {} for w in windows},
           "counts": {}}
    for w, fr in windows.items():
        out["counts"][w] = {
            "obs": int(len(fr)),
            "n_coop": int(fr.loc[fr.is_coop == 1, "codigo"].nunique()),
            "n_bank": int(fr.loc[fr.is_coop == 0, "codigo"].nunique()),
            "date_min": str(fr["date"].min().date()), "date_max": str(fr["date"].max().date())}
        for o in OUTCOMES:
            r = fit(fr, o, "{o} ~ is_coop + log_assets + C(t)")
            if not r:
                continue
            wb = wild_cluster_bootstrap(fr, o, "{o} ~ is_coop + log_assets + C(t)", B=B)
            if wb:
                r["p_boot"] = wb["p_boot"]
                r["G_treated"] = wb["G_treated"]
            out["reg"][w][o] = r
    return out


def w_stability_rows(P, res):
    """Append the stability outcomes to the sections make_tables already parses, so the
    two rows flow into t2/t3/t5 with no special-casing in the writer."""
    st = res.get("stab")
    if not st:
        return
    for o, lab in STAB_LABELS.items():
        for sl, _ in SPECS:
            r = st["reg"][sl].get(o)
            if r:
                pb = f"{r['p_boot']:.4f}" if "p_boot" in r else "na"
                gt = r.get("G_treated", "na")
                P(f"{lab}\t{sl}\t{r['coef']:.6f}\t{r['cl_lo']:.6f}\t{r['cl_hi']:.6f}\t{r['cl_p']:.3e}"
                  f"\t{r['hc_lo']:.6f}\t{r['hc_hi']:.6f}\t{r['hc_p']:.3e}\t{r['N']}\t{r['n_clusters']}"
                  f"\t{pb}\t{gt}\t{r.get('cl_se', float('nan')):.6f}\t{r.get('hc_se', float('nan')):.6f}")


def w_subperiod(sp, path: Path):
    b = io.StringIO()
    P = lambda *a: print(*a, file=b)
    P("# SUBPERIOD SPLIT (primary sample: singular cooperatives vs banks b1+b2)")
    P(f"# controlled specification; boundary {sp['cut']} = entry into force of Res. 4.955/4.958")
    P("\n[SUBPERIOD_COUNTS]  window\tobs\tn_coop\tn_bank\tdate_min\tdate_max")
    for w in ("full", "p1", "p2"):
        c = sp["counts"][w]
        P(f"{w}\t{c['obs']}\t{c['n_coop']}\t{c['n_bank']}\t{c['date_min']}\t{c['date_max']}")
    P("\n[SUBPERIOD_COEFFICIENTS]  outcome\twindow\tcoef\tcl_lo\tcl_hi\tcl_p\tp_boot\tN\tn_clusters")
    for o, lab in OUTCOMES.items():
        for w in ("full", "p1", "p2"):
            r = sp["reg"][w].get(o)
            if r:
                pb = f"{r['p_boot']:.4f}" if "p_boot" in r else "na"
                P(f"{lab}\t{w}\t{r['coef']:.6f}\t{r['cl_lo']:.6f}\t{r['cl_hi']:.6f}\t{r['cl_p']:.3e}"
                  f"\t{pb}\t{r['N']}\t{r['n_clusters']}")
    path.write_text(b.getvalue(), encoding="utf-8")


def w_robustness(rob, primary, path: Path):
    b = io.StringIO()
    P = lambda *a: print(*a, file=b)
    P("# ROBUSTNESS (primary sample: singular cooperatives vs banks b1+b2)")
    P("# every block is the controlled specification: log assets + quarter FE, SE clustered by institution")

    P("\n[WINSOR_VARIANTS]  variant\toutcome\tcoef\tcl_lo\tcl_hi\tcl_p\tN")
    P("# pooled_1_99 is the rule used in every reported table; by_group clips each group at its own 1/99")
    for v, d in rob["winsor"].items():
        for o, lab in OUTCOMES.items():
            r = d.get(o)
            if r:
                P(f"{v}\t{lab}\t{r['coef']:.6f}\t{r['cl_lo']:.6f}\t{r['cl_hi']:.6f}\t{r['cl_p']:.3e}\t{r['N']}")

    a = rob["adopt"]
    P("\n[ADOPTER_SELECTION]")
    P("# REPORTED TEST (definition B): future adopters (simplified -> full inside the window),")
    P("# on their PRE-ADOPTION quarters only (date < first full-methodology quarter),")
    P("# against singular cooperatives never observed under the full methodology; both under simplified rules.")
    P("# treatment = 1 for future adopter. A negative coefficient means adopters were lower before adopting.")
    P("# The looser definition A (below) is a sensitivity line, not the reported test.")
    for k in ("n_singular_in_window", "n_adopters", "n_never", "n_always_full",
              "n_reverters_any", "obs_adopter_pre", "obs_never"):
        P(f"{k}\t{a[k]}")
    P("outcome\tcoef\tcl_lo\tcl_hi\tcl_p\tN\tn_clusters")
    for o, lab in OUTCOMES.items():
        r = a["reg"].get(o)
        if r:
            P(f"{lab}\t{r['coef']:.6f}\t{r['cl_lo']:.6f}\t{r['cl_hi']:.6f}\t{r['cl_p']:.3e}\t{r['N']}\t{r['n_clusters']}")

    P("\n[ADOPTER_SELECTION_ANY_SIMPLIFIED]")
    P("# SENSITIVITY (definition A), not the reported test: every full-methodology cooperative with any")
    P("# simplified quarter, on ALL its simplified quarters (includes post-reversion quarters, so not")
    P("# strictly pre-adoption). Retained because an earlier draft quoted these numbers.")
    P(f"n_any_simplified\t{a['n_any_simplified']}")
    P(f"obs_any_simplified\t{a['obs_any_simplified']}")
    P("outcome\tcoef\tcl_lo\tcl_hi\tcl_p\tN\tn_clusters")
    for o, lab in OUTCOMES.items():
        r = a["reg_any_simplified"].get(o)
        if r:
            P(f"{lab}\t{r['coef']:.6f}\t{r['cl_lo']:.6f}\t{r['cl_hi']:.6f}\t{r['cl_p']:.3e}\t{r['N']}\t{r['n_clusters']}")

    rv = rob["revert"]
    P("\n[REVERTERS]")
    P("# analysis-sample cooperatives with a simplified-method quarter after their first full-method quarter")
    for k in ("n_reverters", "reverter_obs", "coop_obs"):
        P(f"{k}\t{rv[k]}")
    P(f"share_of_coop_obs_pct\t{rv['share_pct']:.2f}")
    P("outcome\tfull_coef\tdropped_coef\tpct_change\tdropped_p")
    for o, lab in OUTCOMES.items():
        r = rv["reg"].get(o)
        if r:
            P(f"{lab}\t{r['full']:.6f}\t{r['alt']:.6f}\t{r['pct_change']:+.2f}\t{r['alt_p']:.3e}")

    cv = rob["coverage"]
    P("\n[PROVISIONING_COVERAGE]")
    P("# every outcome re-estimated on the rows where the provisioning ratio is observed")
    P(f"obs_full\t{cv['obs_full']}")
    P(f"obs_covered\t{cv['obs_covered']}")
    P(f"coverage_pct\t{cv['coverage_pct']:.2f}")
    P("outcome\tfull_coef\tcovered_coef\tpct_change\tcovered_p\tN_full\tN_covered")
    for o, lab in OUTCOMES.items():
        r = cv["reg"].get(o)
        if r:
            P(f"{lab}\t{r['full']:.6f}\t{r['alt']:.6f}\t{r['pct_change']:+.2f}\t{r['alt_p']:.3e}\t{r['N_full']}\t{r['N_alt']}")

    s = rob["sim"]
    P("\n[SMALL_CLUSTER_SIMULATION]")
    P("# effect: n_treated cooperatives drawn at random against all banks (true differential = sample one)")
    P("# null: n_treated banks relabelled as treated within the bank population (true differential = 0)")
    P("# reject5 = share of draws with p < 0.05; a correctly sized test rejects 5% under the null")
    P(f"outcome\t{OUTCOMES.get(s['outcome'], s['outcome'])}")
    P(f"n_treated\t{s['n_treated']}")
    P(f"draws\t{s['draws']}")
    P(f"B\t{s['B']}")
    for design in ("effect", "null"):
        for k, v in s[design].items():
            P(f"{design}_{k}\t{v:.4f}" if isinstance(v, float) else f"{design}_{k}\t{v}")

    P("\n[SYSTEM_BOOTSTRAP]  system\tn\toutcome\tcoef\tcl_p\tp_boot\tG\tG_treated")
    P("# G_treated is the number of cooperative clusters with the outcome observed; it bounds the attainable p")
    for sysname, row in rob.get("het", {}).get("reg", {}).items():
        if row.get("skip"):
            continue
        for o in HET_OUTCOMES:
            c = row.get(o)
            if c and "p_boot" in c:
                P(f"{sysname}\t{row['n']}\t{OUTCOMES[o]}\t{c['coef']:.6f}\t{c['p']:.3e}"
                  f"\t{c['p_boot']:.4f}\t{c['G']}\t{c['G_treated']}")
    path.write_text(b.getvalue(), encoding="utf-8")


# ============================================================================= figures
def make_figures(primary, panel):
    l2, l2_cem, l2_trim = primary["_l2"], primary["_l2_cem"], primary["_l2_trim"]
    ov_lo, ov_hi = primary["_ov"]
    cols = list(OUTCOMES)

    # fig5: regulatory environment (full panel, all cooperatives vs non-coops)
    pf = panel.copy()
    pf["grp"] = np.where(pf.is_coop_any == 1, "Coop", "Non-coop")
    fig, ax = plt.subplots(1, 3, figsize=(15, 4))
    for a, grp, c in [(ax[0], "Coop", COOP_C), (ax[1], "Non-coop", NONCOOP_C)]:
        m = (pf[pf.grp == grp].groupby(["year_q", "full_method"])["codigo"].nunique()
             .unstack(fill_value=0))
        m.columns = [{0: "Simplified", 1: "Full"}.get(x, str(x)) for x in m.columns]
        m.plot.area(ax=a, color=[GREY, c], alpha=0.7)
        a.set_title(grp); a.set_ylabel("N"); a.legend(frameon=False, fontsize=8)
    for grp, c, lab in [("Coop", COOP_C, "Coop"), ("Non-coop", NONCOOP_C, "Non-coop")]:
        m = (pf[pf.grp == grp].groupby(["year_q", "full_method"])["codigo"].nunique()
             .unstack(fill_value=0))
        share = m.get(1, pd.Series(0, index=m.index)) / m.sum(axis=1) * 100
        ax[2].plot(share.index.to_timestamp(), share.values, color=c, lw=1.5, label=lab)
    ax[2].set_title("% Under Full Methodology"); ax[2].legend(frameon=False)
    fig.tight_layout(); fig.savefig(FIGURES / "fig5_regulatory.png", bbox_inches="tight"); plt.close(fig)

    # fig8: common support
    fig, ax = plt.subplots(figsize=(8, 4))
    for v, lab, c in [(1, "Coop", COOP_C), (0, "Non-coop", NONCOOP_C)]:
        s = l2.loc[l2.is_coop == v, "log_assets"].dropna()
        if len(s) > 2:
            s.plot.kde(ax=ax, color=c, lw=1.5,
                       label=f"{lab} (N={l2.loc[l2.is_coop==v,'codigo'].nunique()})")
    ax.axvspan(ov_lo, ov_hi, alpha=0.1, color="green", label=f"Overlap [{ov_lo:.1f},{ov_hi:.1f}]")
    ax.set_xlabel("log(Assets)"); ax.legend(frameon=False, fontsize=8)
    fig.tight_layout(); fig.savefig(FIGURES / "fig8_overlap.png", bbox_inches="tight"); plt.close(fig)

    # fig10: coefficient stability across specs (cluster CIs)
    reg = primary["reg"]
    plot_outs = [o for o in OUTCOMES if all(o in reg[s] for s, _ in SPECS)]
    ncol = 4; nrow = (len(plot_outs) + ncol - 1) // ncol
    fig, axes = plt.subplots(nrow, ncol, figsize=(4 * ncol, 4.5 * nrow), squeeze=False)
    axf = axes.flatten()
    spec_c = [GREY, COOP_C, "#16a34a", ACCENT]
    for j, o in enumerate(plot_outs):
        a = axf[j]
        for i, (sl, _) in enumerate(SPECS):
            v = reg[sl][o]
            a.errorbar(i, v["coef"], yerr=[[abs(v["coef"] - v["cl_lo"])], [abs(v["cl_hi"] - v["coef"])]],
                       fmt="o", color=spec_c[i], capsize=4)
        a.axhline(0, color="grey", ls="--", lw=0.7)
        a.set_xticks(range(4)); a.set_xticklabels(["Raw", "Ctrl", "CEM", "Trim"], fontsize=7, rotation=30)
        a.set_title(OUTCOMES[o], fontsize=8)
    for k in range(len(plot_outs), len(axf)):
        axf[k].set_visible(False)
    fig.tight_layout(); fig.savefig(FIGURES / "fig10_stability.png", bbox_inches="tight"); plt.close(fig)

    # fig11: stable outcomes over time (median, analysis sample)
    stable = [o for o in OUTCOMES if primary["summary"].get(o, {}).get("tier") in ("robust", "partial")]
    k = max(min(len(stable), 4), 1)
    fig, axes = plt.subplots(1, k, figsize=(5 * k, 5), squeeze=False)
    for idx, o in enumerate(stable[:4]):
        a = axes[0][idx]
        for v, lab, c in [(1, "Coop", COOP_C), (0, "Non-coop", NONCOOP_C)]:
            ts = l2[l2.is_coop == v].groupby("year_q")[o].median()
            a.plot(ts.index.to_timestamp(), ts.values, color=c, lw=1.5, label=lab)
        a.set_title(OUTCOMES[o], fontsize=9); a.legend(fontsize=7, frameon=False)
        a.tick_params(axis="x", rotation=30, labelsize=7)
    fig.tight_layout(); fig.savefig(FIGURES / "fig11_stable.png", bbox_inches="tight"); plt.close(fig)

    # fig12: sign-flip scatter
    flips = [o for o in OUTCOMES if primary["summary"].get(o, {}).get("tier") == "sign_flip"]
    if flips:
        fig, axes = plt.subplots(1, len(flips), figsize=(6 * len(flips), 5), squeeze=False)
        for idx, o in enumerate(flips):
            a = axes[0][idx]
            for v, lab, c in [(1, "Coop", COOP_C), (0, "Non-coop", NONCOOP_C)]:
                s = l2[l2.is_coop == v].drop_duplicates("codigo")
                a.scatter(s["log_assets"], s[o], alpha=0.15, s=8, color=c, label=lab)
            a.axvspan(ov_lo, ov_hi, alpha=0.05, color="green")
            a.set_xlabel("log(Assets)"); a.set_ylabel(OUTCOMES[o]); a.set_title(OUTCOMES[o])
            a.legend(fontsize=8, frameon=False)
        fig.tight_layout(); fig.savefig(FIGURES / "fig12_signflips.png", bbox_inches="tight"); plt.close(fig)


# ============================================================================= writers
def w_results(res, het, path: Path, title: str):
    b = io.StringIO()
    P = lambda *a: print(*a, file=b)
    cfg = res["config"]
    P(f"# {title}")
    P(f"# config: coop_def={cfg['coop_def']} winsor={cfg['winsor_scope']} "
      f"se={'cluster' if cfg['cluster'] else 'HC3'} cti={cfg['cti_col']} "
      f"roa={cfg['roa_col']} nim={cfg['nim_col']} peers={cfg['peer_set']} "
      f"excl_segments={cfg.get('exclude_segments') or 'none'}")
    P("\n[SAMPLE]")
    P(f"analysis_institutions\t{res['n_inst']}")
    P(f"analysis_coops\t{res['n_coop']}")
    P(f"analysis_noncoops\t{res['n_nc']}")
    P(f"coop_plus_nc\t{res['n_coop'] + res['n_nc']}")
    P(f"analysis_obs\t{res['n_obs']}")
    P(f"date_range\t{res['date_min']}..{res['date_max']}")

    P("\n[DESCRIPTIVE_MEANS]  outcome\tcoop_mean\tnc_mean\tcoop_med\tnc_med\tcoop_n\tnc_n")
    for c, lab in OUTCOMES.items():
        d = res["desc"].get(c)
        if d:
            P(f"{lab}\t{d['coop_mean']:.6f}\t{d['nc_mean']:.6f}\t{d['coop_med']:.6f}\t"
              f"{d['nc_med']:.6f}\t{d['coop_n']}\t{d['nc_n']}")
    if res.get("stab"):
        for o, lab in STAB_LABELS.items():
            d = res["stab"]["desc"].get(o)
            if d:
                P(f"{lab}\t{d['coop_mean']:.6f}\t{d['nc_mean']:.6f}\t{d['coop_med']:.6f}\t"
                  f"{d['nc_med']:.6f}\t{d['coop_n']}\t{d['nc_n']}")

    P("\n[MAIN_COEFFICIENTS]  outcome\tspec\tcoef\tcl_lo\tcl_hi\tcl_p\thc_lo\thc_hi\thc_p\tN\tn_clusters\tp_boot\tG_treated\tcl_se\thc_se")
    P("# p_boot: restricted wild cluster bootstrap (Rademacher), na where not run; G_treated: treated clusters; cl_se/hc_se: standard errors")
    for c, lab in OUTCOMES.items():
        for sl, _ in SPECS:
            r = res["reg"][sl].get(c)
            if r:
                pb = f"{r['p_boot']:.4f}" if "p_boot" in r else "na"
                gt = r.get("G_treated", "na")
                P(f"{lab}\t{sl}\t{r['coef']:.6f}\t{r['cl_lo']:.6f}\t{r['cl_hi']:.6f}\t{r['cl_p']:.3e}"
                  f"\t{r['hc_lo']:.6f}\t{r['hc_hi']:.6f}\t{r['hc_p']:.3e}\t{r['N']}\t{r['n_clusters']}"
                  f"\t{pb}\t{gt}\t{r.get('cl_se', float('nan')):.6f}\t{r.get('hc_se', float('nan')):.6f}")
    w_stability_rows(P, res)

    P("\n[STABILITY]  outcome\traw\ttrim\trho_trim_over_raw\tattenuation\ttier"
      "\tspecs_sig\tamplifies\tcoef_min\tcoef_max")
    P("# rho = |b_trim|/|b_raw|, reported only when all four specs are significant;")
    P("# tier: robust rho>=0.40 | attenuated rho<0.40 | sign_unstable | null (a spec is n.s.)")
    for c, lab in OUTCOMES.items():
        s = res["summary"].get(c)
        if s:
            raw = res["reg"]["raw"].get(c, {}).get("coef", float("nan"))
            trim = res["reg"]["trim"].get(c, {}).get("coef", float("nan"))
            rho = s["rho"]
            rho_s = "na" if rho != rho else f"{rho:.4f}"
            at_s = "na" if s["atten"] != s["atten"] else f"{s['atten']:.4f}"
            P(f"{lab}\t{raw:.6f}\t{trim:.6f}\t{rho_s}\t{at_s}\t{s['tier']}"
              f"\t{s['n_sig']}/{s['n_specs']}\t{s['amplifies']}"
              f"\t{s['min']:.6f}\t{s['max']:.6f}")
    if res.get("stab"):
        for o, lab in STAB_LABELS.items():
            s = res["stab"]["summary"].get(o)
            if not s:
                continue
            raw = res["stab"]["reg"]["raw"].get(o, {}).get("coef", float("nan"))
            trim = res["stab"]["reg"]["trim"].get(o, {}).get("coef", float("nan"))
            rho_s = "na" if s["rho"] != s["rho"] else f"{s['rho']:.4f}"
            at_s = "na" if s["atten"] != s["atten"] else f"{s['atten']:.4f}"
            P(f"{lab}\t{raw:.6f}\t{trim:.6f}\t{rho_s}\t{at_s}\t{s['tier']}"
              f"\t{s['n_sig']}/{s['n_specs']}\t{s['amplifies']}"
              f"\t{s['min']:.6f}\t{s['max']:.6f}")

    P("\n[CONDITIONAL_MEDIAN]  outcome\tspec\tols_coef\tmedian_coef\tratio\tskew")
    P("# where |median| is far below |ols|, the mean gap is produced by the tail")
    for c, lab in OUTCOMES.items():
        for sl, _ in SPECS:
            a = res["reg"][sl].get(c)
            m = res.get("median", {}).get(sl, {}).get(c)
            if a and m:
                r = m["coef"] / a["coef"] if abs(a["coef"]) > 1e-12 else float("nan")
                P(f"{lab}\t{sl}\t{a['coef']:.6f}\t{m['coef']:.6f}\t{r:.3f}\t{m['skew']:.2f}")
    if res.get("stab"):
        for o, lab in STAB_LABELS.items():
            for sl, _ in SPECS:
                a = res["stab"]["reg"][sl].get(o)
                m = res["stab"]["median"][sl].get(o)
                if a and m:
                    r = m["coef"] / a["coef"] if abs(a["coef"]) > 1e-12 else float("nan")
                    P(f"{lab}\t{sl}\t{a['coef']:.6f}\t{m['coef']:.6f}\t{r:.3f}\t{m['skew']:.2f}")

    P("\n[CEM_WEIGHTING]  matched-sample OLS vs the weighted CEM estimand")
    cw = res.get("cem_w", {})
    P(f"control_weight_min\t{cw.get('w_min')}")
    P(f"control_weight_max\t{cw.get('w_max')}")
    P(f"effective_n_controls\t{cw.get('eff_n_controls')}")
    P("outcome\tcem_weighted\tcem_unweighted\tdifference")
    for c, lab in OUTCOMES.items():
        a = res["reg"]["cem"].get(c)
        cu = res.get("reg_extra", {}).get("cem_unweighted", {}).get(c)
        if a and cu:
            P(f"{lab}\t{a['coef']:.6f}\t{cu['coef']:.6f}\t{a['coef']-cu['coef']:+.6f}")

    if res.get("skipped"):
        P("\n[SKIPPED_REGRESSIONS]  spec\toutcome   (too few obs or single group)")
        for sl, o in res["skipped"]:
            P(f"{sl}\t{OUTCOMES.get(o, o)}")

    o = res["overlap"]
    P("\n[OVERLAP]")
    P(f"log_assets_lo\t{o['lo']:.4f}")
    P(f"log_assets_hi\t{o['hi']:.4f}")
    P(f"coop_inside_pct\t{o['coop_pct']:.2f}")
    P(f"nc_inside_pct\t{o['nc_pct']:.2f}")
    P(f"cem_inst\t{res['cem']['n_inst']}")
    P(f"cem_dropped\t{res['cem']['dropped']}")
    P(f"trim_inst\t{res['trim']['n_inst']}")
    P(f"trim_obs\t{res['trim']['n_obs']}")

    if res.get("seg_drop"):
        P("\n[SEGMENT_RESTRICTION]")
        for k, v in res["seg_drop"].items():
            P(f"{k}\t{v}")

    P("\n[PEER_COMPOSITION]  tcb\tinstitutions\tobs")
    _l2 = res.get("_l2")
    if _l2 is not None:
        _nc = _l2[_l2.is_coop == 0]
        for _t, _s in _nc.groupby(_nc["tcb_stable"].astype(str)):
            P(f"{_t}\t{_s['codigo'].nunique()}\t{len(_s)}")
    if res.get("peer_drop"):
        P(f"peers_before_restriction\t{res['peer_drop']['peers_before']}")
        P(f"peers_after_restriction\t{res['peer_drop']['peers_after']}")

    P("\n[SEGMENT_COMPOSITION]  segment\tcoop_inst\tcoop_obs\tbank_inst\tbank_obs")
    P("# Res. CMN 4.553/2017 segments. Requirements that vary by segment (systemic")
    P("# buffer, liquidity ratios, internal-model eligibility) bind S1 and S2.")
    if _l2 is not None and "segmento" in _l2.columns:
        for _sg, _g in _l2.groupby(_l2["segmento"].astype(str)):
            _c, _b = _g[_g.is_coop == 1], _g[_g.is_coop == 0]
            P(f"{_sg}\t{_c['codigo'].nunique()}\t{len(_c)}"
              f"\t{_b['codigo'].nunique()}\t{len(_b)}")
        _s5 = _l2[_l2["segmento"].astype(str) == "S5"]
        P(f"s5_labelled_obs\t{len(_s5)}\t({100*len(_s5)/max(len(_l2),1):.2f}% of sample)")

    P("\n[BASEL_LEVERAGE_CORR]")
    for k, v in res["corr"].items():
        P(f"{k}\t{'' if v is None else round(v, 4)}")

    if res["flips"]:
        P("\n[SIGN_FLIP_DECOMPOSITION]  outcome\tinside_gap\toutside_gap\tinside_coop\tinside_nc\toutside_coop\toutside_nc")
        for c, f in res["flips"].items():
            P(f"{OUTCOMES[c]}\t{f['inside_gap']:.4f}\t{f['outside_gap']:.4f}\t{f['inside_coop']:.4f}"
              f"\t{f['inside_nc']:.4f}\t{f['outside_coop']:.4f}\t{f['outside_nc']:.4f}")

    P("\n[WINSOR_BOUNDS]  outcome\tlo\thi")
    for c, (lo, hi) in res["winsor_bounds"].items():
        P(f"{OUTCOMES.get(c, c)}\t{lo:.6f}\t{hi:.6f}")

    if res.get("stab"):
        st = res["stab"]
        P("\n[STABILITY_DESIGN]")
        P(f"design\t{st['design']}")
        P(f"institutions\t{st['n_inst']}")
        P(f"cem_institutions\t{st['n_cem']}")
        P(f"trim_institutions\t{st['n_trim']}")
        d = st["drops"]
        P(f"min_quarters\t{d['min_q']}")
        P(f"coop_before\t{d['before']['coop']}\tcoop_after\t{d['after']['coop']}\tcoop_dropped\t{d['dropped_coop']}")
        P(f"bank_before\t{d['before']['bank']}\tbank_after\t{d['after']['bank']}\tbank_dropped\t{d['dropped_bank']}")
        for o, lab in STAB_LABELS.items():
            lo, hi = st["wbounds"].get(o, (float("nan"), float("nan")))
            P(f"winsor_bounds\t{lab}\t{lo:.6f}\t{hi:.6f}")

    if het is not None:
        P("\n[SYSTEM_COMPOSITION]")
        P(f"n_singular\t{het.get('n_singular')}")
        for k, v in het.get("composition", {}).items():
            P(f"{k}\t{v}")
        jd = het.get("join", {})
        P(f"join_attempted\t{jd.get('attempted')}")
        P(f"join_matched_cnpj\t{jd.get('matched_cnpj')}")
        P(f"join_manual_filled\t{jd.get('unmatched')}")
        P(f"join_still_null\t{jd.get('still_null')}")
        P("\n[SYSTEM_COEFFICIENTS]  system\tn\toutcome\tcoef\tp\tp_boot\tG\tG_treated")
        for s, row in het.get("reg", {}).items():
            if row.get("skip"):
                P(f"{s}\t{row['n']}\t--too_few--")
                continue
            for o in HET_OUTCOMES:
                if o in row:
                    c = row[o]
                    pb = f"{c['p_boot']:.4f}" if "p_boot" in c else "na"
                    P(f"{s}\t{row['n']}\t{OUTCOMES[o]}\t{c['coef']:.6f}\t{c['p']:.3e}"
                      f"\t{pb}\t{c.get('G', 'na')}\t{c.get('G_treated', 'na')}")

    path.write_text(b.getvalue(), encoding="utf-8")


def w_diagnostics(panel, info, tcb_varied, primary, legacy, het, path: Path):
    b = io.StringIO()
    P = lambda *a: print(*a, file=b)
    P("# DIAGNOSTICS")

    P("\n[DEDUPE]  source\trows_kept\tdropped\tconflicting_keydups")
    for k, v in info.items():
        if k.startswith("_"):
            continue
        P(f"{k}\t{v['rows']}\t{v['dropped']}\t{v['conflicting']}")

    fd = info.get("_flows", {})
    if fd:
        P("\n[FLOW_DECUMULATION]  field\tstatus\tnonnull_before\tnonnull_after\torphan_closing_qtrs")
        for k, v in fd["info"].items():
            P(f"{k}\t{v['status']}\t{v.get('nonnull_before')}\t{v.get('nonnull_after')}"
              f"\t{v.get('unmatched')}")
        P(f"pcld_line_b5_available\t{fd['pcld_available']}")
        P("\n[SEASONAL_ACCEPTANCE_TEST]  median by calendar quarter")
        P("  a semester-cumulative series runs 1,2,1,2 across Q1..Q4;")
        P("  a correctly de-cumulated one is FLAT. Flatness here is the acceptance test.")
        for lab, blk in (("before", fd["before"]), ("after", fd["after"])):
            for c, qs in blk.items():
                vals = "\t".join(f"Q{q}={qs[q]:+.5f}" for q in sorted(qs))
                P(f"{lab}\t{c}\t{vals}")

    P("\n[TCB_VALUE_COUNTS]")
    for k, v in panel["tcb"].astype(str).value_counts().head(20).items():
        P(f"{k}\t{int(v)}")
    P("\n[COOP_CLASS_INSTITUTIONS]")
    cc = panel.drop_duplicates("codigo")["coop_class"].value_counts()
    for k, v in cc.items():
        P(f"{k}\t{int(v)}")
    P(f"\ntcb_varied_within_codigo\t{len(tcb_varied)}")
    if tcb_varied:
        P("varied_codigos\t" + ",".join(str(c) for c in tcb_varied[:50]))

    P("\n[FULL_PANEL_COUNTS]")
    P(f"obs\t{len(panel)}")
    P(f"institutions\t{panel['codigo'].nunique()}")
    P(f"coop_any_institutions\t{panel.loc[panel.is_coop_any==1,'codigo'].nunique()}")
    P(f"noncoop_institutions\t{panel.loc[panel.is_coop_any==0,'codigo'].nunique()}")
    P(f"date_range\t{panel['date'].min().date()}..{panel['date'].max().date()}")

    # segment x full_method consistency
    P("\n[SEGMENT_x_FULL_METHOD]  segment\tfull0\tfull1")
    if "segmento" in panel.columns:
        ct = pd.crosstab(panel["segmento"].astype(str), panel["full_method"].fillna(-1).astype(int))
        for seg_, row in ct.iterrows():
            P(f"{seg_}\t{int(row.get(0,0))}\t{int(row.get(1,0))}")

    # codigo length x coop_class (analysis sample)
    l2 = primary["_l2"]
    lc = l2.copy(); lc["L"] = lc["codigo"].astype(str).str.len()
    P("\n[CODIGO_LEN_x_ISCOOP analysis]  len\tcoop\tnoncoop")
    ct = pd.crosstab(lc["L"], lc["is_coop"])
    for L, row in ct.iterrows():
        P(f"{L}\t{int(row.get(1,0))}\t{int(row.get(0,0))}")

    # cti proper vs gross (analysis sample, primary coop split)
    P("\n[CTI_PROPER_vs_GROSS analysis means]  group\tcti_proper\tcti_gross")
    for v, lab in [(1, "coop"), (0, "noncoop")]:
        sub = l2[l2.is_coop == v]
        P(f"{lab}\t{sub['cti'].mean():.6f}\t{panel.loc[panel.index.isin(sub.index),'cti_gross'].mean():.6f}")

    # sector context (full panel, all cooperatives)
    P("\n[SECTOR_CONTEXT full panel, all cooperatives]")
    lastq = panel["year_q"].max()
    snap = panel[panel.year_q == lastq]
    tac = snap.loc[snap.is_coop_any == 1, "ativo_total"].sum()
    tan = snap.loc[snap.is_coop_any == 0, "ativo_total"].sum()
    P(f"final_quarter\t{lastq}")
    P(f"coop_asset_share_pct\t{100*tac/(tac+tan):.3f}")
    for v, lab in [(1, "coop_any"), (0, "noncoop")]:
        s = snap[snap.is_coop_any == v]
        nf = s[s.full_method == 1]["codigo"].nunique()
        ns = s[s.full_method == 0]["codigo"].nunique()
        P(f"{lab}_full_method_pct\t{(100*nf/(nf+ns)) if (nf+ns) else float('nan'):.2f}")
    ever_full = panel[(panel.is_coop_any == 1) & (panel.full_method == 1)]["codigo"].nunique()
    P(f"ever_full_method_coops\t{ever_full}")
    P(f"all_coops_ever\t{panel.loc[panel.is_coop_any==1,'codigo'].nunique()}")
    P(f"singular_full_method\t{primary['n_coop']}")

    # balance (primary)
    P("\n[BALANCE_SMD primary]  variable\tfull\tcem\ttrim")
    bal = primary["balance"]
    for c in list(OUTCOMES) + ["log_assets"]:
        if c in bal["full"]:
            P(f"{OUTCOMES.get(c,c)}\t{bal['full'].get(c,float('nan')):.4f}"
              f"\t{bal['cem'].get(c,float('nan')):.4f}\t{bal['trim'].get(c,float('nan')):.4f}")

    path.write_text(b.getvalue(), encoding="utf-8")


def w_changes(primary, legacy, path: Path):
    b = io.StringIO()
    P = lambda *a: print(*a, file=b)
    P("# CHANGES LOG  (deviations from paper1_v5.ipynb)")
    changes = [
        ("Cooperative classification", "tcb-based, institution-stable (modal tcb per codigo). "
         "Primary group = b3S singular cooperatives; non-coops = non-b3; b3C centrals excluded "
         "from the comparison.",
         "Original used (tcb startswith b3) OR (name contains 'COOPERAT'), per-row. The OR-name "
         "clause pulled Banco Cooperativo Sicredi (tcb=b1, a bank) into coops in later quarters "
         "only, double-counting one institution and breaking the time-invariance the design "
         "assumes (it appears as both coop and non-coop). tcb is the regulator's own consolidation "
         "type and is stable. This reconciles 1198+762->1959 and 168+483->650."),
        ("Singular vs central", "Centrals (b3C) dropped from the main comparison; only retail "
         "singular cooperatives (b3S) enter the coop group.",
         "The original main sample pooled singulars with ~37 wholesale centrals (high-capital "
         "infrastructure entities) and called them all cooperatives, while the heterogeneity "
         "section silently excluded the centrals via a 38-row hardcoded list. tcb makes the split "
         "principled and the hardcoded EXCLUDE list unnecessary. Expect the headline Basel gap to "
         "move toward the singular (Sicredi-dominated) value."),
        ("Standard errors", "Clustered by institution (codigo), reported alongside HC3.",
         "650 institutions observed up to ~32 quarters each are serially correlated within unit, "
         "and the treatment is assigned at the institution level; HC3 treats all ~15,000 rows as "
         "independent and understates SEs. Consensus is to cluster at the most aggregate feasible "
         "level (Cameron & Miller 2015; Abadie et al. 2017)."),
        ("Cost-to-income denominator", "Operating income (net interest income + fee income) "
         "instead of gross intermediation revenue; both reported (cti vs cti_gross).",
         "The original denominator (gross intermediation revenue, line a) produces a 2.97 ratio "
         "for non-coops, which is not a meaningful cost-to-income figure; some institutions have "
         "small or negative gross revenue. Net operating income is the standard banking "
         "denominator and is far more stable."),
        ("Winsorization scope", "Winsorize within the analysis sample, not the full panel.",
         "The original set 1/99 bounds on the full panel, which is dominated by simplified-method "
         "institutions that never enter the analysis; the bounds should come from the analysed "
         "population. Where you winsorize materially moves estimates."),
        ("Duplicate (codigo,date) rows", "Deduplicate every source: drop exact duplicates, then "
         "collapse remaining key-dups keeping the most-populated row.",
         "The assets module carried ~1,354 duplicate (codigo,date) rows (vs 3 elsewhere) that the "
         "original silently dropped via keep-first; an arbitrary pick can bias credit/provisioning "
         "outcomes. See [DEDUPE] in diagnostics for exact and conflicting counts."),
        ("CEM coarsening size", "Size quintile from each institution's median log-assets over the "
         "period, not the entry-quarter snapshot.",
         "drop_duplicates('codigo') kept the first (earliest) quarter's size bin; typical size is "
         "more representative for matching."),
        ("Standardized differences", "Denominator sqrt((var_t+var_c)/2) (Austin 2009; Stuart 2010).",
         "Original used an n-weighted pooled SD; the matching literature uses the simple average "
         "of group variances so the metric does not depend on group sizes."),
        ("Per-outcome N", "Reported for every coefficient.",
         "Provisioning runs on ~66% coverage (provisions/gross credit missing for a third of rows); "
         "this should be visible, not implied by 'roughly 15,004'."),
    ]
    for i, (t, what, why) in enumerate(changes, 1):
        P(f"\n{i}. {t}")
        P(f"   change: {what}")
        P(f"   reason: {why}")

    # primary vs legacy main coefficient diff
    P("\n\n[PRIMARY_vs_LEGACY main coefficients]")
    P("outcome\tspec\tlegacy_coef\tprimary_coef\tdelta")
    for c, lab in OUTCOMES.items():
        for sl, _ in SPECS:
            lp = legacy["reg"][sl].get(c, {}).get("coef")
            pp = primary["reg"][sl].get(c, {}).get("coef")
            if lp is not None and pp is not None:
                P(f"{lab}\t{sl}\t{lp:.6f}\t{pp:.6f}\t{pp-lp:+.6f}")
    P("\n[SAMPLE_SIZES]\tlegacy\tprimary")
    P(f"institutions\t{legacy['n_inst']}\t{primary['n_inst']}")
    P(f"coops\t{legacy['n_coop']}\t{primary['n_coop']}")
    P(f"noncoops\t{legacy['n_nc']}\t{primary['n_nc']}")
    P(f"obs\t{legacy['n_obs']}\t{primary['n_obs']}")

    path.write_text(b.getvalue(), encoding="utf-8")


# ============================================================================= main
def main():
    panel, info, tcb_varied = build_panel()

    # PRIMARY SPECIFICATION (see results/changes_log.txt and the README for the
    # evidence behind each choice):
    #   peers = banks (b1+b2). The full non-b3 population includes 196 institutions
    #     reporting zero credit and zero deposits; comparing a lender to a brokerage
    #     makes several outcomes mechanical.
    #   coarsen = size quintile only. Exact-matching on macro-region leaves ~18
    #     effective control institutions, and region is plausibly a mediator of
    #     cooperative form rather than a confounder of it. The region-matched
    #     estimates are reported as a within-market bound.
    primary = run_pipeline(panel, coop_def="singular", winsor_scope="analysis",
                           use_cluster=True, cti_col="cti_new",
                           roa_col="roa_ann", nim_col="nim_ann",
                           peer_set="banks", coarsen="size_q5")
    broad = run_pipeline(panel, coop_def="singular", winsor_scope="analysis",
                         use_cluster=True, cti_col="cti_new",
                         roa_col="roa_ann", nim_col="nim_ann",
                         peer_set="all", coarsen="size_q5")
    # Segment-restricted robustness. Res. CMN 4.553/2017 applies proportionality by
    # segment; S1 and S2 carry the systemic buffer, the liquidity ratios and internal
    # model eligibility, and contain no cooperatives. Excluding them leaves a comparison
    # in which every institution faces one set of prudential requirements.
    no_s12 = run_pipeline(panel, coop_def="singular", winsor_scope="analysis",
                          use_cluster=True, cti_col="cti_new", roa_col="roa_ann",
                          nim_col="nim_ann", peer_set="banks", coarsen="size_q5",
                          exclude_segments=("S1", "S2"))
    within_market = run_pipeline(panel, coop_def="singular", winsor_scope="analysis",
                                 use_cluster=True, cti_col="cti_new",
                                 roa_col="roa_ann", nim_col="nim_ann",
                                 peer_set="banks", coarsen="size_q5_region")
    # Two further rungs of the peer ladder, printed in t3 beside the three above:
    # commercial (b1 only) and structural (b1 with positive deposits in every quarter).
    commercial = run_pipeline(panel, coop_def="singular", winsor_scope="analysis",
                              use_cluster=True, cti_col="cti_new",
                              roa_col="roa_ann", nim_col="nim_ann",
                              peer_set="commercial", coarsen="size_q5")
    structural = run_pipeline(panel, coop_def="singular", winsor_scope="analysis",
                              use_cluster=True, cti_col="cti_new",
                              roa_col="roa_ann", nim_col="nim_ann",
                              peer_set="structural", coarsen="size_q5")
    legacy = run_pipeline(panel, coop_def="legacy_name", winsor_scope="panel",
                          use_cluster=False, cti_col="cti_gross",
                          roa_col="roa_legacy", nim_col="nim_legacy")
    # Bootstrap every cell of the main table and of the system split, and run the
    # robustness checks the text quotes: winsorisation variants, selection into the
    # sample, reverters, provisioning coverage, and the small-cluster simulation.
    bootstrap_main(primary, B=BOOT_B)
    het = system_heterogeneity(primary, panel, use_cluster=True, boot=True, B=BOOT_B)

    # institution-level stability outcomes (roa_vol, zscore) for the three comparison
    # groups that feed t2/t3/t5, plus the subperiod split (item: Res. 4.955/4.958).
    primary["stab"] = stability_estimates(primary, B=BOOT_B)
    broad["stab"] = stability_estimates(broad, B=BOOT_B)
    within_market["stab"] = stability_estimates(within_market, B=BOOT_B)
    commercial["stab"] = stability_estimates(commercial, B=BOOT_B)
    structural["stab"] = stability_estimates(structural, B=BOOT_B)
    subperiod = subperiod_split(primary, B=BOOT_B)

    robust = {
        "winsor": winsor_variants(panel),
        "adopt": adopter_selection(panel),
        "revert": reverters(primary, panel),
        "coverage": provisioning_coverage(primary),
        "sim": small_cluster_simulation(primary),
        "het": het,
    }

    make_figures(primary, panel)

    w_results(primary, het, RESULTS / "results_primary.txt",
              "RESULTS (PRIMARY / cooperatives vs banks b1+b2, size-quintile coarsening)")
    w_results(broad, None, RESULTS / "results_broad_peers.txt",
              "RESULTS (BROAD PEER SET / all non-cooperative full-methodology institutions)")
    w_results(within_market, None, RESULTS / "results_within_market.txt",
              "RESULTS (WITHIN-MARKET / banks, region-exact matching)")
    w_results(commercial, None, RESULTS / "results_commercial.txt",
              "RESULTS (COMMERCIAL / cooperatives vs b1 banks only)")
    w_results(structural, None, RESULTS / "results_structural.txt",
              "RESULTS (STRUCTURAL / cooperatives vs b1 banks with positive deposits in every quarter)")
    w_results(no_s12, None, RESULTS / "results_no_s12.txt",
              "RESULTS (SEGMENT-RESTRICTED / banks, excluding modal S1 and S2)")
    w_results(legacy, None, RESULTS / "results_legacy.txt", "RESULTS (LEGACY / paper reproduction)")
    w_diagnostics(panel, info, tcb_varied, primary, legacy, het, RESULTS / "diagnostics.txt")
    w_changes(primary, legacy, RESULTS / "changes_log.txt")
    w_robustness(robust, primary, RESULTS / "robustness.txt")
    w_subperiod(subperiod, RESULTS / "subperiod.txt")

    print("done. wrote:")
    for f in ("results_primary.txt", "results_legacy.txt", "diagnostics.txt", "changes_log.txt",
              "robustness.txt", "subperiod.txt"):
        print("  ", RESULTS / f)
    print("figures in:", FIGURES)


if __name__ == "__main__":
    main()