"""
GATE F — REPORTING LEVEL.

Every row of the panel comes from IF.data's prudential report, which carries a
document-type field, TD: "C" marks a prudential-conglomerate consolidation and "I" an
institution that reports individually. Every singular cooperative reports individually.
Most banks in the analysis sample report as conglomerates, so a bank row consolidates
the whole prudential conglomerate (bank plus leasing, DTVM, consorcio and other
subsidiaries) rather than the bank alone. This script measures how much of the capital
and leverage results depends on that.

  PART A  Reporting level of every institution in the analysis sample: institutions
          and institution-quarters by TD, switchers, and a validation of the TD field
          against IF.data's individual-institution report (how many individual
          institutions each prudential row consolidates).
  PART B  The cooperative differential for the Basel ratio and leverage against the
          banks that report individually (peer rung `banks_individual`, all singular
          cooperatives on the other side), under the raw, controlled, matched and
          trimmed specifications, with clustered and HC3 standard errors and the
          restricted wild cluster bootstrap. Two winsorisation variants: `fixed` clips
          at the primary sample's bounds, so the coefficients are comparable with the
          main table; `own` recomputes the bounds on the rung, as the peer ladder does.
          The conglomerate rung is run alongside for contrast.
  PART C  Quantile coefficients q10 to q90 for the Basel ratio on each rung.
  PART D  Residual dispersion at equal size, as in t8, on the individual rung.
  PART E  The unconditional Basel distribution by reporting level: mean, median, p90
          and the share above 50 percent, on the winsorised analysis sample the paper
          uses and on the raw values.

Writes results/reporting_level.txt and tables/t11_reporting_level.tex.

    python gate_f_reporting_level.py          # B = paper.BOOT_B bootstrap replications
    python gate_f_reporting_level.py 199      # faster
"""
from __future__ import annotations
import io
import sys
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
import paper as P
import gate_e_dispersion as E

B = int(sys.argv[1]) if len(sys.argv) > 1 else P.BOOT_B
E.B_BOOT = 400 if B >= 999 else 40  # dispersion bootstrap, as in gate_e's default
BUF = io.StringIO()
BASE = dict(coop_def="singular", winsor_scope="analysis", use_cluster=True,
            cti_col="cti_new", roa_col="roa_ann", nim_col="nim_ann",
            peer_set="banks", coarsen="size_q5")
CTRL = "{o} ~ is_coop + log_assets + C(t)"
OUT2 = ["basileia_num", "leverage"]
QUANTILES = [0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90]
RUNGS = [("banks_individual", "Banks reporting individually"),
         ("banks_conglomerate", "Banks reporting as prudential conglomerates")]
VARIANTS = ["fixed", "own"]
SPEC_LABEL = {"raw": "(1) Raw", "ctrl": "(2) Controls", "cem": "(3) CEM", "trim": "(4) Trim"}
LABEL = {"basileia_num": "Basel capital ratio (pp)", "leverage": "Leverage"}
IND = P.DATA / "raw" / "if.data" / "individual_institutions" / "summary"


def say(*a):
    line = " ".join(str(x) for x in a)
    print(line)
    print(line, file=BUF)


def stars(p):
    if p != p:
        return ""
    return "***" if p < 0.01 else "**" if p < 0.05 else "*" if p < 0.10 else ""


def dec(o):
    return 2 if o == "basileia_num" else 3


def prud_code(codigo):
    """Prudential-report codes carry a 1000 prefix in front of the conglomerate code."""
    s = str(int(codigo))
    return int(s[4:]) if s.startswith("1000") and len(s) >= 10 else int(s)


# ------------------------------------------------------------------ A
def load_individual_members():
    """From IF.data's individual-institution report: how many individual institutions
    each prudential conglomerate code groups in each quarter, and their assets."""
    rows, cover = [], {}
    for f in sorted(IND.glob("20*.csv")):
        yr = int(f.name[:4])
        if yr < 2017 or yr > 2024:
            continue
        df = None
        for enc in ("utf-8-sig", "latin-1", "utf-8", "cp1252"):
            try:
                df = pd.read_csv(f, sep=";", encoding=enc, dtype=str)
                break
            except (UnicodeDecodeError, ValueError):
                continue
        cols = [c.strip() for c in df.columns]
        df.columns = cols
        pc = [c for c in cols if c.startswith("Conglomerado Prudencial")]
        if not pc:
            cover[f.name] = "no prudential-conglomerate column"
            continue
        d = pd.DataFrame({"member": df[cols[1]].astype(str).str.strip(),
                          "prud": df[pc[-1]].astype(str).str.strip(),
                          "data_str": df["Data"].astype(str).str.strip(),
                          "ativo": P.parse_br(df["Ativo Total"])})
        d = d[d["prud"].str.fullmatch(r"\d+")]
        cover[f.name] = int(len(d))
        rows.append(d)
    m = pd.concat(rows, ignore_index=True)
    m["date"] = pd.to_datetime(m["data_str"], format="%m/%Y", errors="coerce")
    m["prud"] = m["prud"].astype(int)
    g = (m.groupby(["prud", "date"])
          .agg(n_members=("member", "nunique"), sum_assets=("ativo", "sum"),
               max_assets=("ativo", "max")).reset_index())
    return g, cover


def part_a(panel, l2):
    say("=" * 92)
    say("A — reporting level in the analysis sample (IF.data prudential report, field TD)")
    say("=" * 92)
    say("TD = C: prudential-conglomerate consolidation; TD = I: institution reporting")
    say("individually. Modal TD over the institution's analysis-sample quarters defines")
    say("its level; switchers are institutions whose TD takes both values.\n")
    out = {}
    say("[REPORTING_LEVEL]  group\tlevel\tinstitutions\tquarters_by_row_td\tquarters_by_modal_td\tmean_log_assets")
    for v, lab in [(0, "banks"), (1, "cooperatives")]:
        d = l2[l2.is_coop == v]
        inst = d.groupby("codigo").agg(td_modal=("td_stable", "first"),
                                       n_td=("td", "nunique"),
                                       nq=("td", "size"),
                                       name=("instituicao", "first"),
                                       la=("log_assets", "mean"))
        for lev in ["C", "I"]:
            sub_i = inst[inst.td_modal == lev]
            nq_row = int((d["td"] == lev).sum())
            nq_modal = int((d["td_stable"] == lev).sum())
            say(f"{lab}\t{lev}\t{len(sub_i)}\t{nq_row}\t{nq_modal}\t{sub_i['la'].mean():.3f}")
            out[(lab, lev)] = {"inst": int(len(sub_i)), "quarters": nq_modal, "quarters_row": nq_row,
                               "la": float(sub_i["la"].mean()) if len(sub_i) else np.nan}
        missing = inst["td_modal"].isna().sum()
        say(f"{lab}\tmissing\t{int(missing)}\t{int(d['td'].isna().sum())}\t{int(d['td_stable'].isna().sum())}\tnan")
        sw = inst[inst.n_td > 1]
        out[(lab, "switchers")] = int(len(sw))
        say(f"# {lab}: {len(inst)} institutions, {len(d)} institution-quarters, "
            f"{len(sw)} switch level inside the analysis sample")
        for cod, r in sw.iterrows():
            seq = d[d.codigo == cod].sort_values("date")
            path = " ".join(f"{yy}:{''.join(sorted(set(g['td'].astype(str))))}"
                            for yy, g in seq.groupby(seq["date"].dt.year))
            say(f"#   switcher {cod} {str(r['name'])[:40]} (modal {r['td_modal']}): {path}")
        w = panel[panel.codigo.isin(inst.index) & panel.date.between("2017-01-01", "2024-12-31")]
        sw_w = (w.dropna(subset=["td"]).groupby("codigo")["td"].nunique() > 1).sum()
        out[(lab, "switchers_window")] = int(sw_w)
        say(f"# {lab}: {int(sw_w)} switch level anywhere in 2017-2024 (all methodologies)")

    # code prefix: in the prudential report every code carries the 1000 prefix, so the
    # prefix does not separate the two levels; TD does
    b = l2[l2.is_coop == 0].copy()
    b["pref"] = b["codigo"].astype(str).str.startswith("1000") & (b["codigo"].astype(str).str.len() >= 10)
    ct = pd.crosstab(b["td"].astype(str), b["pref"])
    say("\n# bank-quarters by TD (rows) and 1000-prefixed code (columns): the prefix is universal")
    say(ct.to_string())

    # validation against the individual-institution report
    say("\n# validation: members per prudential row, from IF.data's individual-institution report")
    g, cover = load_individual_members()
    say("# coverage (rows with a prudential-conglomerate code) by file: "
        + ", ".join(f"{k[:7]}={v}" for k, v in cover.items()))
    bb = l2[l2.is_coop == 0][["codigo", "date", "td", "ativo_total"]].copy()
    bb["prud"] = bb["codigo"].map(prud_code)
    bb = bb.merge(g, on=["prud", "date"], how="left")
    bb["ratio"] = bb["ativo_total"] / bb["max_assets"]
    say("[MEMBERS_BY_TD]  td\tbank_quarters\tmatched\tshare_one_member\tmedian_members\tmax_members\tmedian_assets_ratio\tp90_assets_ratio")
    for lev in ["C", "I"]:
        x = bb[bb.td == lev]
        m = x.dropna(subset=["n_members"])
        say(f"{lev}\t{len(x)}\t{len(m)}\t{(m.n_members == 1).mean():.4f}\t{m.n_members.median():.0f}\t"
            f"{m.n_members.max():.0f}\t{m.ratio.median():.4f}\t{m.ratio.quantile(.9):.4f}")
        out[("members", lev)] = {"n": int(len(x)), "matched": int(len(m)),
                                 "one": float((m.n_members == 1).mean()),
                                 "med": float(m.n_members.median()), "ratio": float(m.ratio.median())}
    cc = l2[l2.is_coop == 1][["codigo", "date", "ativo_total"]].copy()
    cc["prud"] = cc["codigo"].map(prud_code)
    cc = cc.merge(g, on=["prud", "date"], how="left")
    m = cc.dropna(subset=["n_members"])
    say(f"cooperatives\t{len(cc)}\t{len(m)}\t{(m.n_members == 1).mean():.4f}\t{m.n_members.median():.0f}\t"
        f"{m.n_members.max():.0f}\t{(m.ativo_total / m.max_assets).median():.4f}\t"
        f"{(m.ativo_total / m.max_assets).quantile(.9):.4f}")
    say("# a prudential row marked I should group exactly one individual institution with")
    say("# the same assets (ratio 1); a row marked C groups several.\n")
    return out


# ------------------------------------------------------------------ B
def run_rung(panel, rung, bounds):
    kw = {**BASE, "peer_set": rung}
    if bounds is not None:
        kw["winsor_bounds"] = bounds
    return P.run_pipeline(panel, **kw)


def part_b(panel, primary):
    say("=" * 92)
    say("B — Basel ratio and leverage against each reporting-level rung")
    say("=" * 92)
    say("Cooperative side: all singular cooperatives under the full methodology. Two")
    say("winsorisation variants: fixed = clipped at the primary sample's 1/99 bounds, so")
    say("the numbers sit beside the main table; own = bounds recomputed on the rung, as")
    say(f"the peer ladder does. Common support and CEM strata are recomputed on each rung. B={B}.\n")
    pb = primary["winsor_bounds"]
    say("# primary winsorisation bounds: Basel [{:.2f}, {:.2f}], leverage [{:.4f}, {:.4f}]".format(
        pb["basileia_num"][0], pb["basileia_num"][1], pb["leverage"][0], pb["leverage"][1]))
    store = {}
    say("[RUNG_COEFFICIENTS]  rung\twinsor\toutcome\tspec\tcoef\tcl_se\tcl_p\thc_se\thc_p\tp_boot\tG_treated\tG\tN\tn_coop\tn_banks\tmedian_coef\tmedian_p")
    for rung, lab in RUNGS:
        store[rung] = {}
        for var in VARIANTS:
            res = run_rung(panel, rung, {k: tuple(v) for k, v in pb.items()} if var == "fixed" else None)
            frames = {"raw": res["_l2"], "ctrl": res["_l2"], "cem": res["_l2_cem"], "trim": res["_l2_trim"]}
            store[rung][var] = {"res": res, "cells": {}}
            wb_ = res["winsor_bounds"]
            say(f"# {rung}/{var}: {res['n_coop']} cooperatives, {res['n_nc']} banks, {res['n_obs']} obs; "
                f"Basel clipped at [{wb_['basileia_num'][0]:.2f}, {wb_['basileia_num'][1]:.2f}]; "
                f"common support [{res['overlap']['lo']:.2f}, {res['overlap']['hi']:.2f}], "
                f"coop inside {res['overlap']['coop_pct']:.1f}%, banks inside {res['overlap']['nc_pct']:.1f}%; "
                f"CEM strata {res['cem_w']['n_strata']}, eff. controls {res['cem_w']['eff_n_controls']:.1f}, "
                f"weights [{res['cem_w']['w_min']:.2f}, {res['cem_w']['w_max']:.2f}]")
            for o in OUT2:
                for sl, ftmpl in P.SPECS:
                    r = res["reg"][sl].get(o)
                    if not r:
                        continue
                    wb = P.wild_cluster_bootstrap(frames[sl], o, ftmpl, B=B,
                                                  weight_col="cem_w" if sl == "cem" else None)
                    m = res["median"][sl].get(o, {})
                    cell = dict(r)
                    cell.update({"p_boot": wb["p_boot"] if wb else np.nan,
                                 "G_treated": wb["G_treated"] if wb else np.nan,
                                 "G": wb["G"] if wb else np.nan,
                                 "n_banks": r["n_clusters"] - r["n_treated"],
                                 "median_coef": m.get("coef", np.nan), "median_p": m.get("p", np.nan)})
                    store[rung][var]["cells"][(o, sl)] = cell
                    say(f"{rung}\t{var}\t{P.OUTCOMES[o]}\t{sl}\t{cell['coef']:.6f}\t{cell['cl_se']:.6f}\t"
                        f"{cell['cl_p']:.3e}\t{cell['hc_se']:.6f}\t{cell['hc_p']:.3e}\t{cell['p_boot']:.4f}\t"
                        f"{cell['G_treated']}\t{cell['G']}\t{cell['N']}\t{cell['n_treated']}\t"
                        f"{cell['n_banks']}\t{cell['median_coef']:.6f}\t{cell['median_p']:.3e}")
            say("")
    return store


# ------------------------------------------------------------------ C
def part_c(store):
    say("=" * 92)
    say("C — quantile coefficients for the Basel ratio, controlled specification")
    say("=" * 92)
    qs = {}
    say("[QUANTILES]  rung\twinsor\t" + "\t".join(f"q{int(q*100)}" for q in QUANTILES)
        + "\tOLS\tmean_q20_q80\tshare_of_OLS")
    for rung, lab in RUNGS:
        for var in VARIANTS:
            l2 = store[rung][var]["res"]["_l2"]
            sub = l2[["is_coop", "log_assets", "date", "codigo", "basileia_num"]].dropna().copy()
            sub["t"] = sub["date"].dt.to_period("Q").apply(lambda x: x.ordinal)
            row = {}
            for q in QUANTILES:
                try:
                    row[q] = float(smf.quantreg(CTRL.format(o="basileia_num"), data=sub)
                                   .fit(q=q).params["is_coop"])
                except Exception:
                    row[q] = np.nan
            ols = store[rung][var]["cells"][("basileia_num", "ctrl")]["coef"]
            interior = [row[q] for q in (0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8) if row[q] == row[q]]
            share = np.mean(interior) / ols if interior and abs(ols) > 1e-9 else np.nan
            qs[(rung, var)] = {"row": row, "ols": ols, "interior": float(np.mean(interior)),
                               "share": float(share)}
            say(f"{rung}\t{var}\t" + "\t".join(f"{row[q]:.4f}" for q in QUANTILES)
                + f"\t{ols:.4f}\t{np.mean(interior):.4f}\t{share:.3f}")
    say("")
    return qs


# ------------------------------------------------------------------ D
def part_d(store):
    say("=" * 92)
    say("D — residual dispersion at equal size on the individual rung (as t8; fixed winsorisation)")
    say("=" * 92)
    l2 = store["banks_individual"]["fixed"]["res"]["_l2"]
    keep = {}
    say("[DISPERSION_INDIVIDUAL]  outcome\tcoop_sd\tbank_sd\tsd_ratio\tci_lo\tci_hi\tcoop_iqr\tbank_iqr\tiqr_ratio\tp_ratio_lt_1")
    for o in E.CORE:
        sub = E.residualise(l2, o)
        if sub is None:
            continue
        r, c, b = E.ratios(sub)
        bs = E.boot_ratios(sub, E.B_BOOT)
        lo, hi = (np.nanpercentile(bs["sd"], [2.5, 97.5]) if len(bs) > 30 else (np.nan, np.nan))
        pless = float((bs["sd"] < 1).mean()) if len(bs) > 30 else np.nan
        keep[o] = {"coop_sd": c["sd"], "bank_sd": b["sd"], "sd": r["sd"], "lo": lo, "hi": hi,
                   "coop_iqr": c["iqr"], "bank_iqr": b["iqr"], "iqr": r["iqr"], "p": pless}
        say(f"{P.OUTCOMES[o]}\t{c['sd']:.6f}\t{b['sd']:.6f}\t{r['sd']:.4f}\t{lo:.4f}\t{hi:.4f}\t"
            f"{c['iqr']:.6f}\t{b['iqr']:.6f}\t{r['iqr']:.4f}\t{pless:.3f}")
    dz, _, _ = P.collapse_stability(l2)
    dz = dz.dropna(subset=["zscore", "log_assets"]).copy()
    dz["r"] = smf.ols("zscore ~ log_assets", data=dz).fit().resid
    cz = E.spread(dz.loc[dz.is_coop == 1, "r"].to_numpy())
    bz = E.spread(dz.loc[dz.is_coop == 0, "r"].to_numpy())
    keep["zscore"] = {"coop_sd": cz["sd"], "bank_sd": bz["sd"], "sd": cz["sd"] / bz["sd"],
                      "lo": np.nan, "hi": np.nan, "coop_iqr": cz["iqr"], "bank_iqr": bz["iqr"],
                      "iqr": cz["iqr"] / bz["iqr"], "p": np.nan}
    say(f"Z-score\t{cz['sd']:.6f}\t{bz['sd']:.6f}\t{cz['sd']/bz['sd']:.4f}\tnan\tnan\t"
        f"{cz['iqr']:.6f}\t{bz['iqr']:.6f}\t{cz['iqr']/bz['iqr']:.4f}\tnan")
    say(f"# z-score: {int((dz.is_coop==1).sum())} cooperatives and {int((dz.is_coop==0).sum())} "
        f"banks with at least eight quarters")
    say("")
    return keep


# ------------------------------------------------------------------ E
def part_e(panel, l2):
    say("=" * 92)
    say("E — unconditional Basel ratio by reporting level (modal TD)")
    say("=" * 92)
    say("Winsorised: the analysis sample the paper's tables use (1/99 within the")
    say("cooperatives-vs-banks sample). Raw: the same institution-quarters before winsorisation.\n")
    raw_sub, _, _ = P.select_sample(panel, "singular", "cti_new", "roa_ann", "nim_ann", "banks")
    raw = raw_sub[raw_sub["full_method"] == 1]
    out = {}
    say("[BASEL_BY_LEVEL]  sample\tgroup\tinstitutions\tobs\tmean\tsd\tmedian\tp75\tp90\tp99\tshare_gt_20\tshare_gt_50\tmax")
    for sname, df in [("winsorised", l2), ("raw", raw)]:
        groups = [("Banks, conglomerate", df[(df.is_coop == 0) & (df.td_stable == "C")]),
                  ("Banks, individual", df[(df.is_coop == 0) & (df.td_stable == "I")]),
                  ("Banks, all", df[df.is_coop == 0]),
                  ("Cooperatives", df[df.is_coop == 1])]
        for g, d in groups:
            x = d["basileia_num"].dropna()
            rec = {"inst": int(d.loc[x.index, "codigo"].nunique()), "obs": int(len(x)),
                   "mean": x.mean(), "sd": x.std(), "med": x.median(), "p75": x.quantile(.75),
                   "p90": x.quantile(.90), "p99": x.quantile(.99),
                   "gt20": (x > 20).mean(), "gt50": (x > 50).mean(), "max": x.max()}
            out[(sname, g)] = rec
            say(f"{sname}\t{g}\t{rec['inst']}\t{rec['obs']}\t{rec['mean']:.3f}\t{rec['sd']:.3f}\t"
                f"{rec['med']:.3f}\t{rec['p75']:.3f}\t{rec['p90']:.3f}\t{rec['p99']:.3f}\t"
                f"{rec['gt20']:.4f}\t{rec['gt50']:.4f}\t{rec['max']:.2f}")
    hi = l2[(l2.is_coop == 0) & (l2.basileia_num > 50)]
    say(f"\n# bank-quarters above 50% in the winsorised sample: {len(hi)}; by modal level: "
        + ", ".join(f"{k}={v}" for k, v in hi["td_stable"].value_counts().items())
        + f"; institutions: {hi['codigo'].nunique()} "
        f"({hi.drop_duplicates('codigo')['td_stable'].value_counts().to_dict()})")
    say("")
    return out


# ------------------------------------------------------------------ table
def write_table(A, store, qs, disp, E_out):
    tab = P.ROOT / "tables"
    tab.mkdir(exist_ok=True, parents=True)
    L = []
    L += [r"\small", r"\setlength{\tabcolsep}{4pt}",
          r"\begin{tabular}{lrrrrrr}", r"\toprule",
          r"\multicolumn{7}{l}{\textit{Panel A. Reporting level and the unconditional Basel ratio, analysis sample}} \\",
          r"Group & Institutions & Quarters & Mean & Median & $p_{90}$ & Share $>50\%$ \\",
          r"\midrule"]
    emap = {("banks", "C"): "Banks, conglomerate", ("banks", "I"): "Banks, individual",
            ("cooperatives", "I"): "Cooperatives"}
    for g, key in [("Banks, conglomerate consolidations", ("banks", "C")),
                   ("Banks, individual", ("banks", "I")),
                   ("Cooperatives (all individual)", ("cooperatives", "I"))]:
        a, e = A[key], E_out[("winsorised", emap[key])]
        L.append(f"{g} & {a['inst']} & {a['quarters']:,} & {e['mean']:.1f} & {e['med']:.1f} "
                 f"& {e['p90']:.1f} & {100*e['gt50']:.1f} " + r"\\")
    L += [r"\bottomrule", r"\end{tabular}", r"\par\medskip"]
    L += [r"\begin{tabular}{lrrrr}", r"\toprule",
          r"\multicolumn{5}{l}{\textit{Panel B. Cooperative differential by reporting-level rung, primary winsorisation}} \\",
          r"Outcome & " + " & ".join(SPEC_LABEL[s] for s in ["raw", "ctrl", "cem", "trim"]) + r" \\"]
    for rung, lab in RUNGS:
        cells = store[rung]["fixed"]["cells"]
        L += [r"\midrule", r"\multicolumn{5}{l}{\textit{" + lab + r"}} \\"]
        for o in OUT2:
            d = dec(o)
            L.append(f"{LABEL[o]} & " + " & ".join(
                f"{cells[(o, s)]['coef']:.{d}f}{stars(cells[(o, s)]['p_boot'])}"
                for s in ["raw", "ctrl", "cem", "trim"]) + r" \\")
            L.append(" & " + " & ".join(f"({cells[(o, s)]['cl_se']:.{d}f})"
                                        for s in ["raw", "ctrl", "cem", "trim"]) + r" \\")
        L.append("Cooperative / bank clusters & " + " & ".join(
            f"{cells[('basileia_num', s)]['n_treated']} / {cells[('basileia_num', s)]['n_banks']}"
            for s in ["raw", "ctrl", "cem", "trim"]) + r" \\")
    L += [r"\bottomrule", r"\end{tabular}", r"\par\medskip"]
    L += [r"\begin{tabular}{l" + "r" * 10 + "}", r"\toprule",
          r"\multicolumn{11}{l}{\textit{Panel C. Basel ratio, cooperative coefficient across the conditional distribution}} \\",
          r"Bank rung & " + " & ".join(f"$q_{{{int(q*100)}}}$" for q in QUANTILES) + r" & OLS \\", r"\midrule"]
    for rung, lab in RUNGS:
        q = qs[(rung, "fixed")]
        short = "Individual" if rung == "banks_individual" else "Conglomerate"
        L.append(f"{short} & " + " & ".join(f"{q['row'][x]:.1f}" for x in QUANTILES) + f" & {q['ols']:.1f} " + r"\\")
    L += [r"\bottomrule", r"\end{tabular}", r"\par\medskip"]
    L += [r"\begin{tabular}{lrrrrr}", r"\toprule",
          r"\multicolumn{6}{l}{\textit{Panel D. Residual dispersion at equal size, banks reporting individually}} \\",
          r" & \multicolumn{2}{c}{Residual s.d.} & & \multicolumn{2}{c}{Residual IQR} \\",
          r"\cmidrule(lr){2-3}\cmidrule(lr){5-6}",
          r"Outcome & Coop. & Banks & Ratio & Coop. & Banks \\", r"\midrule"]
    for o in E.CORE + ["zscore"]:
        k = disp.get(o)
        if not k:
            continue
        lab = (P.OUTCOMES.get(o) or P.STAB_LABELS.get(o, o)).replace("%", r"\%")
        L.append(f"{lab} & {k['coop_sd']:.4f} & {k['bank_sd']:.4f} & {k['sd']:.2f} "
                 f"& {k['coop_iqr']:.4f} & {k['bank_iqr']:.4f} " + r"\\")
    L += [r"\bottomrule", r"\end{tabular}"]
    ind, con = store["banks_individual"]["fixed"]["res"], store["banks_conglomerate"]["fixed"]["res"]
    own = store["banks_individual"]["own"]["cells"][("basileia_num", "ctrl")]
    note = (r"\begin{tablenotes}[flushleft]\footnotesize" "\n"
            r"\item Reporting level is the document-type field of IF.data's prudential report "
            r"(C: prudential-conglomerate consolidation; I: institution reporting individually), "
            r"taken as the institution's modal value over its sample quarters; "
            f"{A[('banks', 'switchers')]} banks and {A[('cooperatives', 'switchers')]} cooperatives "
            r"switch level inside the sample. Panel A uses the winsorised analysis sample of the main tables. "
            r"Panel B re-runs the four specifications with the cooperative side unchanged "
            f"({ind['n_coop']} cooperatives) and the bank side restricted to one reporting level "
            f"({ind['n_nc']} individual, {con['n_nc']} conglomerate), clipping every outcome at the primary "
            r"sample's winsorisation bounds so the coefficients are comparable with the main table; common "
            r"support and CEM strata are recomputed on each sample. With the bounds recomputed on the "
            f"individual rung instead, the controlled Basel coefficient is {own['coef']:.1f} ({own['cl_se']:.1f}). "
            r"Clustered standard errors in parentheses; stars from the restricted wild cluster bootstrap with "
            f"{B:,} replications (*** $p<0.01$, ** $p<0.05$, * $p<0.10$). Panel C reports quantile regressions "
            r"of the Basel ratio on the cooperative dummy, log assets and quarter fixed effects. Panel D follows "
            r"the dispersion table: residuals from a regression on log assets and quarter fixed effects, the "
            r"z-score residualised on mean log assets at the institution level." "\n"
            r"\end{tablenotes}" "\n")
    (tab / "t11_reporting_level.tex").write_text("\n".join(L) + "\n" + note, encoding="utf-8")
    say(f"wrote {tab / 't11_reporting_level.tex'}")


def main():
    panel, info, _ = P.build_panel()
    primary = P.run_pipeline(panel, **BASE)
    l2 = primary["_l2"]
    say(f"GATE F — REPORTING LEVEL  (bootstrap B={B})")
    say(f"# banks rung: {primary['n_coop']} cooperatives, {primary['n_nc']} banks, {primary['n_obs']} obs\n")
    A = part_a(panel, l2)
    store = part_b(panel, primary)
    qs = part_c(store)
    disp = part_d(store)
    E_out = part_e(panel, l2)
    write_table(A, store, qs, disp, E_out)
    (P.RESULTS / "reporting_level.txt").write_text(BUF.getvalue(), encoding="utf-8")
    print(f"\nwrote {P.RESULTS / 'reporting_level.txt'}")


if __name__ == "__main__":
    main()
