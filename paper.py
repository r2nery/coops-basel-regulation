"""
One-Size-Fits-All? Credit cooperatives under full Basel regulation in Brazil.
Analysis pipeline. Rewrite of paper1_v5.ipynb.

Outputs (written to ROOT/results/):
    results_primary.txt   every reported number under the recommended specification
    results_legacy.txt    same pipeline under the original notebook's choices (paper reproduction)
    diagnostics.txt       data-quality and classification diagnostics
    changes_log.txt       every deviation from the original notebook, with reasons, plus a
                          primary-vs-legacy coefficient diff
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
ROOT = Path(os.environ.get("ICA_ROOT", r"C:\Users\arthur.nery\Downloads\credit-paper-ica"))
DATA = ROOT / "data"
PRUD = DATA / "raw" / "if.data" / "prudential_conglomerates"
SRC = {
    "summary": PRUD / "summary",
    "seg": PRUD / "segmentation",
    "assets": PRUD / "assets",
    "income": PRUD / "income_statement",
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
    "npl_ratio": "Provisioning (provisions/gross credit)",
    "deposit_ratio": "Deposit Ratio (funding/assets)",
}
HET_OUTCOMES = ["basileia_num", "leverage", "roa", "npl_ratio"]

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

INCOME_MAP = {
    "Código": "codigo", "Data": "data_str",
    "Resultado de Intermediação Financeira - Receitas de Intermediação Financeira (a) = (a1) + (a2) + (a3) + (a4) + (a5) + (a6)": "receitas_intermediacao",
    "Resultado de Intermediação Financeira - Resultado de Intermediação Financeira (c) = (a) + (b)": "resultado_intermediacao",
    "Outras Receitas/Despesas Operacionais - Rendas de Tarifas Bancárias (d2)": "tarifas",
    "Outras Receitas/Despesas Operacionais - Despesas de Pessoal (d3)": "despesas_pessoal",
    "Outras Receitas/Despesas Operacionais - Despesas Administrativas (d4)": "despesas_admin",
}
INCOME_NUM = ["receitas_intermediacao", "resultado_intermediacao", "tarifas",
              "despesas_pessoal", "despesas_admin"]

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


# ============================================================================= build base panel
def build_panel():
    """Load all sources, merge, classify on tcb, construct raw outcomes.
    Returns (panel, dedupe_info, tcb_varied)."""
    info = {}
    summary, info["summary"] = load_folder(SRC["summary"], SUMM_MAP, SUMM_NUM)
    seg, info["seg"] = load_folder(SRC["seg"], SEG_MAP, [])
    assets, info["assets"] = load_folder(SRC["assets"], ASSET_MAP, ASSET_NUM)
    income, info["income"] = load_folder(SRC["income"], INCOME_MAP, INCOME_NUM)

    seg["simplified"] = seg["simplified"].astype(str).str.strip().str.upper()
    seg["full_method"] = (seg["simplified"] == "NÃO").astype(int)

    panel = summary.merge(
        seg[["codigo", "date", "simplified", "full_method"]],
        on=["codigo", "date"], how="left")
    panel = panel.merge(assets[["codigo", "date"] + ASSET_NUM],
                        on=["codigo", "date"], how="left")
    panel = panel.merge(income[["codigo", "date"] + INCOME_NUM],
                        on=["codigo", "date"], how="left")

    # ---- institution-stable cooperative classification from tcb ----------------
    # modal tcb per institution guarantees a time-invariant group label by construction
    modal = (panel.dropna(subset=["tcb"])
             .groupby("codigo")["tcb"]
             .agg(lambda s: s.mode().iloc[0] if len(s.mode()) else np.nan))
    tcb_varied = (panel.dropna(subset=["tcb"]).groupby("codigo")["tcb"].nunique()
                  .pipe(lambda s: s[s > 1]).index.tolist())
    panel["tcb_stable"] = panel["codigo"].map(modal)

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

    # ---- outcomes (raw; winsorization happens per analysis population later) ----
    A = panel["ativo_total"].clip(lower=1)
    panel["log_assets"] = np.log(A)
    panel["basileia_num"] = panel["basileia"]
    panel["leverage"] = panel["passivo"] / A
    panel["credit_ratio"] = panel["carteira_credito"] / A
    panel["npl_ratio"] = panel["provisao_credito"].abs() / panel["credito_bruto"].abs().replace(0, np.nan)
    panel["roa"] = panel["lucro_liquido"] / A
    panel["nim"] = panel["resultado_intermediacao"] / A
    panel["deposit_ratio"] = panel["captacoes"] / A
    opex = panel["despesas_pessoal"].abs() + panel["despesas_admin"].abs()
    # proper cost-to-income: opex over operating income (net interest income + fee income)
    op_income = panel["resultado_intermediacao"] + panel["tarifas"].abs()
    panel["cti"] = opex / op_income.where(op_income > 0, np.nan)
    # legacy cost-to-income: opex over gross intermediation revenue (original denominator)
    panel["cti_gross"] = opex / panel["receitas_intermediacao"].abs().replace(0, np.nan)

    panel["year_q"] = panel["date"].dt.to_period("Q")
    panel["region"] = panel["uf"].map(UF_REGION)
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
def fit(df: pd.DataFrame, out: str, formula: str):
    """Fit one OLS; return both cluster-by-institution and HC3 inference."""
    need = ["is_coop", "log_assets", "date", "codigo", out]
    sub = df[need].dropna().copy()
    if len(sub) < 50 or sub["is_coop"].nunique() < 2:
        return None
    sub["t"] = sub["date"].dt.to_period("Q").apply(lambda x: x.ordinal)
    model = smf.ols(formula.format(o=out), data=sub)
    cl = model.fit(cov_type="cluster", cov_kwds={"groups": sub["codigo"]})
    hc = model.fit(cov_type="HC3")
    ci_cl, ci_hc = cl.conf_int().loc["is_coop"], hc.conf_int().loc["is_coop"]
    return {
        "coef": float(cl.params["is_coop"]),
        "cl_lo": float(ci_cl.iloc[0]), "cl_hi": float(ci_cl.iloc[1]),
        "cl_p": float(cl.pvalues["is_coop"]),
        "hc_lo": float(ci_hc.iloc[0]), "hc_hi": float(ci_hc.iloc[1]),
        "hc_p": float(hc.pvalues["is_coop"]),
        "N": int(len(sub)), "n_clusters": int(sub["codigo"].nunique()),
    }


SPECS = [
    ("raw", "{o} ~ is_coop"),
    ("ctrl", "{o} ~ is_coop + log_assets + C(t)"),
    ("cem", "{o} ~ is_coop + log_assets + C(t)"),
    ("trim", "{o} ~ is_coop + log_assets + C(t)"),
]


# ============================================================================= pipeline
def run_pipeline(panel: pd.DataFrame, coop_def: str, winsor_scope: str,
                 use_cluster: bool, cti_col: str):
    """Returns a results dict for one configuration.
    coop_def: 'singular' | 'all_coop' | 'legacy_name'
    winsor_scope: 'analysis' | 'panel'
    cti_col: which constructed column is labelled 'cti' in OUTCOMES
    """
    p = panel.copy()
    p["cti"] = p[cti_col]

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

    cols = list(OUTCOMES)
    panel_bounds = winsorize(sub, cols)[1] if winsor_scope == "panel" else None

    l2 = sub[sub["full_method"] == 1].copy()
    if winsor_scope == "panel":
        l2, wbounds = winsorize(l2, cols, bounds=panel_bounds)
    else:
        l2, wbounds = winsorize(l2, cols)

    # per-institution typical size for coarsening (median over the period, not entry quarter)
    med_la = l2.groupby("codigo")["log_assets"].median()
    l2["size_bin"] = pd.qcut(l2["codigo"].map(med_la), q=5, labels=False, duplicates="drop")

    # common support on log assets (5/95 of each group)
    cq = l2.loc[l2.is_coop == 1, "log_assets"].quantile([0.05, 0.95])
    nq = l2.loc[l2.is_coop == 0, "log_assets"].quantile([0.05, 0.95])
    ov_lo, ov_hi = max(cq.iloc[0], nq.iloc[0]), min(cq.iloc[1], nq.iloc[1])

    # CEM strata
    snap = l2.drop_duplicates("codigo")[["codigo", "is_coop", "size_bin", "region"]].dropna()
    mvars = ["size_bin", "region"] if snap["region"].nunique() > 1 else ["size_bin"]
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
    l2_trim = l2[l2["log_assets"].between(ov_lo, ov_hi)].copy()
    frames = {"raw": l2, "ctrl": l2, "cem": l2_cem, "trim": l2_trim}

    # regressions
    reg = {sl: {} for sl, _ in SPECS}
    for sl, ftmpl in SPECS:
        for o in OUTCOMES:
            r = fit(frames[sl], o, ftmpl)
            if r:
                reg[sl][o] = r

    # attenuation + stability
    summ = {}
    for o in OUTCOMES:
        coefs = [reg[s][o]["coef"] for s, _ in SPECS if o in reg[s]]
        if not coefs:
            continue
        raw = reg["raw"].get(o, {}).get("coef", np.nan)
        trim = reg["trim"].get(o, {}).get("coef", np.nan)
        atten = (1 - abs(trim) / abs(raw)) if (abs(raw) > 1e-12 and not np.isnan(trim)) else np.nan
        same_sign = len({np.sign(c) for c in coefs}) == 1
        pkey = "cl_p" if use_cluster else "hc_p"
        allsig = all(reg[s][o][pkey] < 0.05 for s, _ in SPECS if o in reg[s])
        if same_sign and allsig and (atten == atten) and atten < 0.60:
            tier = "robust"
        elif same_sign and allsig:
            tier = "partial"
        elif same_sign:
            tier = "stable_dir"
        else:
            tier = "sign_flip"
        summ[o] = {"atten": atten, "tier": tier, "min": min(coefs), "max": max(coefs)}

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
                   "cluster": use_cluster, "cti_col": cti_col},
        "n_inst": int(l2["codigo"].nunique()),
        "n_coop": int(l2.loc[l2.is_coop == 1, "codigo"].nunique()),
        "n_nc": int(l2.loc[l2.is_coop == 0, "codigo"].nunique()),
        "n_obs": int(len(l2)),
        "date_min": str(l2["date"].min().date()), "date_max": str(l2["date"].max().date()),
        "winsor_bounds": {k: [float(v[0]), float(v[1])] for k, v in wbounds.items()},
        "desc": desc, "reg": reg, "summary": summ,
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


def system_heterogeneity(primary, panel, use_cluster=True):
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
                row[o] = {"coef": r["coef"], "p": r["cl_p" if use_cluster else "hc_p"]}
        out["reg"][s] = row
    return out


# ============================================================================= figures
def make_figures(primary, panel):
    l2, l2_cem, l2_trim = primary["_l2"], primary["_l2_cem"], primary["_l2_trim"]
    ov_lo, ov_hi = primary["_ov"]
    cols = list(OUTCOMES)

    # fig2: size distribution (analysis sample, singular vs non-coop), latest quarter
    snap = l2[l2.year_q == l2.year_q.max()]
    fig, ax = plt.subplots(1, 2, figsize=(12, 4.5))
    for v, lab, c in [(1, "Coop", COOP_C), (0, "Non-coop", NONCOOP_C)]:
        s = snap.loc[snap.is_coop == v, "log_assets"].dropna()
        if len(s) > 2:
            s.plot.kde(ax=ax[0], color=c, lw=1.5, label=f"{lab} (N={len(s)})")
    ax[0].set_title("(a) Log Assets Density"); ax[0].legend(frameon=False)
    box = [snap.loc[snap.is_coop == 1, "log_assets"].dropna(),
           snap.loc[snap.is_coop == 0, "log_assets"].dropna()]
    bp = ax[1].boxplot(box, patch_artist=True, medianprops=dict(color="white"))
    bp["boxes"][0].set_facecolor(COOP_C); bp["boxes"][1].set_facecolor(NONCOOP_C)
    ax[1].set_xticks([1, 2]); ax[1].set_xticklabels(["Coop", "Non-coop"])
    ax[1].set_title("(b) Box Plot")
    fig.tight_layout(); fig.savefig(FIGURES / "fig2_size.png", bbox_inches="tight"); plt.close(fig)

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

    # fig9: balance (standardized differences, three samples)
    bal = primary["balance"]
    labels = [OUTCOMES.get(c, c) for c in cols] + ["Log Assets"]
    keys = cols + ["log_assets"]
    full = [bal["full"].get(k, np.nan) for k in keys]
    cem = [bal["cem"].get(k, np.nan) for k in keys]
    trim = [bal["trim"].get(k, np.nan) for k in keys]
    fig, ax = plt.subplots(figsize=(8, 4.5))
    y = np.arange(len(keys)); w = 0.25
    ax.barh(y - w, full, height=w, color=GREY, alpha=0.7, label="Full")
    ax.barh(y, cem, height=w, color=COOP_C, alpha=0.7, label="CEM")
    ax.barh(y + w, trim, height=w, color=ACCENT, alpha=0.7, label="Trimmed")
    for x in (-0.25, 0, 0.25):
        ax.axvline(x, color="grey", ls=":" if x else "-", lw=0.7)
    ax.set_yticks(y); ax.set_yticklabels(labels, fontsize=8)
    ax.set_xlabel("Std. Diff"); ax.legend(fontsize=8, frameon=False)
    fig.tight_layout(); fig.savefig(FIGURES / "fig9_balance.png", bbox_inches="tight"); plt.close(fig)

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
      f"se={'cluster' if cfg['cluster'] else 'HC3'} cti={cfg['cti_col']}")
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

    P("\n[MAIN_COEFFICIENTS]  outcome\tspec\tcoef\tcl_lo\tcl_hi\tcl_p\thc_lo\thc_hi\thc_p\tN\tn_clusters")
    for c, lab in OUTCOMES.items():
        for sl, _ in SPECS:
            r = res["reg"][sl].get(c)
            if r:
                P(f"{lab}\t{sl}\t{r['coef']:.6f}\t{r['cl_lo']:.6f}\t{r['cl_hi']:.6f}\t{r['cl_p']:.3e}"
                  f"\t{r['hc_lo']:.6f}\t{r['hc_hi']:.6f}\t{r['hc_p']:.3e}\t{r['N']}\t{r['n_clusters']}")

    P("\n[ATTENUATION_STABILITY]  outcome\traw\ttrim\tattenuation\ttier\tcoef_min\tcoef_max")
    for c, lab in OUTCOMES.items():
        s = res["summary"].get(c)
        if s:
            raw = res["reg"]["raw"].get(c, {}).get("coef", float("nan"))
            trim = res["reg"]["trim"].get(c, {}).get("coef", float("nan"))
            at = s["atten"]
            P(f"{lab}\t{raw:.6f}\t{trim:.6f}\t{at if at != at else round(at, 4)}\t{s['tier']}"
              f"\t{s['min']:.6f}\t{s['max']:.6f}")

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
        P("\n[SYSTEM_COEFFICIENTS]  system\tn\toutcome\tcoef\tp")
        for s, row in het.get("reg", {}).items():
            if row.get("skip"):
                P(f"{s}\t{row['n']}\t--too_few--")
                continue
            for o in HET_OUTCOMES:
                if o in row:
                    P(f"{s}\t{row['n']}\t{OUTCOMES[o]}\t{row[o]['coef']:.6f}\t{row[o]['p']:.3e}")

    path.write_text(b.getvalue(), encoding="utf-8")


def w_diagnostics(panel, info, tcb_varied, primary, legacy, het, path: Path):
    b = io.StringIO()
    P = lambda *a: print(*a, file=b)
    P("# DIAGNOSTICS")

    P("\n[DEDUPE]  source\trows_kept\tdropped\tconflicting_keydups")
    for k, v in info.items():
        P(f"{k}\t{v['rows']}\t{v['dropped']}\t{v['conflicting']}")

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

    primary = run_pipeline(panel, coop_def="singular", winsor_scope="analysis",
                           use_cluster=True, cti_col="cti")
    legacy = run_pipeline(panel, coop_def="legacy_name", winsor_scope="panel",
                          use_cluster=False, cti_col="cti_gross")
    het = system_heterogeneity(primary, panel, use_cluster=True)

    make_figures(primary, panel)

    w_results(primary, het, RESULTS / "results_primary.txt", "RESULTS (PRIMARY / recommended)")
    w_results(legacy, None, RESULTS / "results_legacy.txt", "RESULTS (LEGACY / paper reproduction)")
    w_diagnostics(panel, info, tcb_varied, primary, legacy, het, RESULTS / "diagnostics.txt")
    w_changes(primary, legacy, RESULTS / "changes_log.txt")

    print("done. wrote:")
    for f in ("results_primary.txt", "results_legacy.txt", "diagnostics.txt", "changes_log.txt"):
        print("  ", RESULTS / f)
    print("figures in:", FIGURES)


if __name__ == "__main__":
    main()