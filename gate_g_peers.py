"""
GATE G — PEER RUNGS, THE COOPERATIVE-OWNED BANKS, PROVISIONING BY CAPITAL, COST-TO-INCOME.

  PART A  The Basel-ratio distribution and the controlled coefficients on six rungs of the
          bank side: banks (b1+b2), commercial (b1), structural (b1 with strictly positive
          total deposits in every full-methodology quarter of presence), and each of the
          three restricted to banks that report individually. The distribution is read off
          the primary winsorised sample restricted to the rung's banks; the coefficients
          come from run_pipeline with the primary sample's winsorisation bounds, so every
          rung is clipped exactly as the main table. All ten outcomes, clustered SE and
          the wild cluster bootstrap for the eight panel outcomes; HC3 and the institution
          bootstrap for the two stability outcomes.
  PART B  Dropping the cooperative sector's own banks (Banco Cooperativo Sicredi and
          Bancoob / Banco Sicoob) from the bank comparison group: controlled coefficients
          for all ten outcomes and their deltas against the primary results.
  PART C  Provisioning by capital tercile: the analysis sample split into terciles of the
          Basel ratio residualised on log assets and quarter fixed effects, and into
          terciles of the unconditional Basel ratio; the provisioning differential
          (controlled specification, clustered SE, bootstrap p) within each tercile.
  PART D  Cost-to-income with the denominator trimmed: observations whose operating
          income gross of provisions is below 0.5 percent of total assets removed;
          controlled coefficient, conditional median and its institution-bootstrap
          interval, and the number of quarters removed by group.
  PART E  Provisioning-ratio coverage by group and by year.

Writes results/peer_rungs.txt and tables/t12_provisioning_by_capital.tex.

    python gate_g_peers.py          # B = paper.BOOT_B bootstrap replications
    python gate_g_peers.py 199      # faster
"""
from __future__ import annotations
import io
import sys
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
import paper as P

_num_args = [a for a in sys.argv[1:] if a.isdigit()]
B = int(_num_args[0]) if _num_args else P.BOOT_B
B_STAB = 499 if B >= 999 else 49
B_MED = 499 if B >= 999 else 49
BUF = io.StringIO()
BASE = dict(coop_def="singular", winsor_scope="analysis", use_cluster=True,
            cti_col="cti_new", roa_col="roa_ann", nim_col="nim_ann",
            peer_set="banks", coarsen="size_q5")
CTRL = "{o} ~ is_coop + log_assets + C(t)"
RUNGS = [("banks", "Banks (b1+b2)"),
         ("banks_individual", "Banks, individual"),
         ("commercial", "Commercial (b1)"),
         ("commercial_individual", "Commercial, individual"),
         ("structural", "Structural"),
         ("structural_individual", "Structural, individual")]
COOP_BANK_PATTERN = "SICREDI|SICOOB|BANCOOB"
TERCILES = ["Bottom", "Middle", "Top"]


def say(*a):
    line = " ".join(str(x) for x in a)
    print(line)
    print(line, file=BUF)


def stars(p):
    if p != p:
        return ""
    return "***" if p < 0.01 else "**" if p < 0.05 else "*" if p < 0.10 else ""


def boot_p(df, o, B_):
    wb = P.wild_cluster_bootstrap(df, o, CTRL, B=B_)
    return (wb["p_boot"], wb["G_treated"]) if wb else (np.nan, np.nan)


# ------------------------------------------------------------------ A
def part_a(panel, primary):
    say("=" * 92)
    say("A — peer rungs: Basel distribution and controlled coefficients")
    say("=" * 92)
    say("Distribution: primary winsorised sample restricted to the rung's banks. Coefficients:")
    say("run_pipeline on the rung with the primary winsorisation bounds; controlled specification;")
    say(f"clustered SE, wild cluster bootstrap B={B}; stability rows HC3 with B={B_STAB}.\n")
    l2 = primary["_l2"]
    pb = {k: tuple(v) for k, v in primary["winsor_bounds"].items()}
    store = {}
    say("[RUNG_BASEL]  rung\tbanks\tbank_quarters\tmean\tmedian\tp90\tshare_gt_50\tshare_gt_20\tcoop_inside_pct\tbanks_inside_pct")
    rows_c = []
    for rung, lab in RUNGS:
        res = P.run_pipeline(panel, **{**BASE, "peer_set": rung, "winsor_bounds": pb})
        ids = set(res["_l2"].loc[res["_l2"].is_coop == 0, "codigo"])
        d = l2[(l2.is_coop == 0) & l2.codigo.isin(ids)]
        x = d["basileia_num"].dropna()
        say(f"{rung}\t{len(ids)}\t{len(d)}\t{x.mean():.3f}\t{x.median():.3f}\t{x.quantile(.9):.3f}\t"
            f"{(x > 50).mean():.4f}\t{(x > 20).mean():.4f}\t{res['overlap']['coop_pct']:.1f}\t{res['overlap']['nc_pct']:.1f}")
        cells = {}
        for o in P.OUTCOMES:
            r = res["reg"]["ctrl"].get(o)
            if not r:
                continue
            pbv, gt = boot_p(res["_l2"], o, B)
            cells[o] = dict(r, p_boot=pbv, G_treated=gt, label=P.OUTCOMES[o], se=r["cl_se"], p=r["cl_p"])
        st = P.stability_estimates(res, B=B_STAB)
        for o, lab_s in P.STAB_LABELS.items():
            r = st["reg"]["ctrl"].get(o)
            if r:
                cells[o] = dict(r, label=lab_s, se=r["hc_se"], p=r["hc_p"])
        store[rung] = {"n_banks": len(ids), "cells": cells, "basel": x,
                       "n_coop": res["n_coop"], "n_obs": res["n_obs"]}
        for o, c in cells.items():
            rows_c.append(f"{rung}\t{c['label']}\t{c['coef']:.6f}\t{c['se']:.6f}\t{c['p']:.3e}\t"
                          f"{c.get('p_boot', np.nan):.4f}\t{c.get('G_treated', 'na')}\t{c['N']}\t"
                          f"{c['n_clusters'] - c['n_treated']}")
    say("\n[RUNG_CTRL]  rung\toutcome\tcoef\tse\tp\tp_boot\tG_treated\tN\tn_banks")
    say("# se/p: clustered by institution for the eight panel outcomes, HC3 for the two stability rows")
    for r in rows_c:
        say(r)
    say("")
    return store


# ------------------------------------------------------------------ B
def part_b(panel, primary):
    say("=" * 92)
    say("B — dropping the cooperative sector's own banks from the bank comparison group")
    say("=" * 92)
    nc = panel[panel.coop_class == "noncoop"]
    m = nc[nc.instituicao.astype(str).str.upper().str.contains(COOP_BANK_PATTERN, regex=True)]
    ids = tuple(sorted(set(m["codigo"])))
    names = m.groupby("codigo")["instituicao"].agg(lambda s: " / ".join(sorted(set(map(str, s)))))
    l2 = primary["_l2"]
    for cod in ids:
        d = l2[l2.codigo == cod]
        say(f"# {cod}: {names[cod]}; tcb {m.loc[m.codigo == cod, 'tcb_stable'].iloc[0]}; "
            f"{len(d)} analysis-sample quarters; mean Basel {d['basileia_num'].mean():.2f}, "
            f"mean leverage {d['leverage'].mean():.3f}, mean credit/assets {d['credit_ratio'].mean():.3f}")
    pb = {k: tuple(v) for k, v in primary["winsor_bounds"].items()}
    res = P.run_pipeline(panel, **{**BASE, "exclude_codigos": ids, "winsor_bounds": pb})
    say(f"# without them: {res['n_coop']} cooperatives, {res['n_nc']} banks, {res['n_obs']} obs "
        f"(primary {primary['n_coop']}, {primary['n_nc']}, {primary['n_obs']}); primary winsorisation bounds kept")
    st_old = P.stability_estimates(primary, B=B_STAB)
    st_new = P.stability_estimates(res, B=B_STAB)
    say("[DROP_COOP_BANKS]  outcome\tcoef_primary\tcoef_excl\tdelta\tdelta_pct\tse_excl\tp_excl\tp_boot_excl\tN_excl")
    out = {}
    for o, lab in P.OUTCOMES.items():
        r0, r1 = primary["reg"]["ctrl"].get(o), res["reg"]["ctrl"].get(o)
        if not (r0 and r1):
            continue
        pbv, _ = boot_p(res["_l2"], o, B)
        delta = r1["coef"] - r0["coef"]
        pct = 100 * delta / r0["coef"] if abs(r0["coef"]) > 1e-12 else np.nan
        out[o] = (r0["coef"], r1["coef"], delta, pct)
        say(f"{lab}\t{r0['coef']:.6f}\t{r1['coef']:.6f}\t{delta:.6f}\t{pct:.2f}\t{r1['cl_se']:.6f}\t"
            f"{r1['cl_p']:.3e}\t{pbv:.4f}\t{r1['N']}")
    for o, lab in P.STAB_LABELS.items():
        r0, r1 = st_old["reg"]["ctrl"].get(o), st_new["reg"]["ctrl"].get(o)
        if not (r0 and r1):
            continue
        delta = r1["coef"] - r0["coef"]
        pct = 100 * delta / r0["coef"] if abs(r0["coef"]) > 1e-12 else np.nan
        out[o] = (r0["coef"], r1["coef"], delta, pct)
        say(f"{lab}\t{r0['coef']:.6f}\t{r1['coef']:.6f}\t{delta:.6f}\t{pct:.2f}\t{r1['hc_se']:.6f}\t"
            f"{r1['hc_p']:.3e}\t{r1.get('p_boot', np.nan):.4f}\t{r1['N']}")
    say("")
    return ids, out


# ------------------------------------------------------------------ C
def part_c(primary):
    say("=" * 92)
    say("C — provisioning differential within terciles of the Basel ratio")
    say("=" * 92)
    say("Terciles cut on the pooled analysis sample (cooperatives and banks together), first on")
    say("the Basel ratio residualised on log assets and quarter fixed effects, then on the")
    say(f"unconditional ratio. Controlled specification within each tercile; clustered SE; B={B}.\n")
    l2 = primary["_l2"]
    sub = l2[["codigo", "date", "is_coop", "log_assets", "basileia_num", "prov_ratio"]].dropna(
        subset=["basileia_num"]).copy()
    sub["t"] = sub["date"].dt.to_period("Q").apply(lambda x: x.ordinal)
    sub["r"] = smf.ols("basileia_num ~ log_assets + C(t)", data=sub).fit().resid
    out = {}
    say("[PROV_BY_TERCILE]  mode\ttercile\tcut_lo\tcut_hi\tcoef\tcl_se\tcl_p\tp_boot\tG_treated\tcoop_obs\tbank_obs\tcoop_inst\tbank_inst\tcoop_prov_mean\tbank_prov_mean\tcoop_basel_med\tbank_basel_med")
    for mode, col in [("residualised", "r"), ("unconditional", "basileia_num")]:
        sub["terc"], bins = pd.qcut(sub[col], 3, labels=TERCILES, retbins=True)
        for i, terc in enumerate(TERCILES):
            d = sub[sub.terc == terc]
            dp = d.dropna(subset=["prov_ratio"])
            r = P.fit(d, "prov_ratio", CTRL)
            pbv, gt = boot_p(d, "prov_ratio", B)
            rec = {"coef": r["coef"] if r else np.nan, "se": r["cl_se"] if r else np.nan,
                   "p": r["cl_p"] if r else np.nan, "p_boot": pbv, "G_treated": gt,
                   "lo": bins[i], "hi": bins[i + 1],
                   "coop_obs": int((dp.is_coop == 1).sum()), "bank_obs": int((dp.is_coop == 0).sum()),
                   "coop_inst": int(dp.loc[dp.is_coop == 1, "codigo"].nunique()),
                   "bank_inst": int(dp.loc[dp.is_coop == 0, "codigo"].nunique()),
                   "coop_prov": dp.loc[dp.is_coop == 1, "prov_ratio"].mean(),
                   "bank_prov": dp.loc[dp.is_coop == 0, "prov_ratio"].mean(),
                   "coop_basel": d.loc[d.is_coop == 1, "basileia_num"].median(),
                   "bank_basel": d.loc[d.is_coop == 0, "basileia_num"].median()}
            out[(mode, terc)] = rec
            say(f"{mode}\t{terc}\t{rec['lo']:.4f}\t{rec['hi']:.4f}\t{rec['coef']:.6f}\t{rec['se']:.6f}\t"
                f"{rec['p']:.3e}\t{rec['p_boot']:.4f}\t{rec['G_treated']}\t{rec['coop_obs']}\t{rec['bank_obs']}\t"
                f"{rec['coop_inst']}\t{rec['bank_inst']}\t{rec['coop_prov']:.6f}\t{rec['bank_prov']:.6f}\t"
                f"{rec['coop_basel']:.3f}\t{rec['bank_basel']:.3f}")
    say("")
    return out


def write_t12(out, B_=None):
    B_ = B if B_ is None else B_
    tab = P.ROOT / "tables"
    tab.mkdir(exist_ok=True, parents=True)
    L = [r"\footnotesize", r"\setlength{\tabcolsep}{4pt}",
         r"\begin{tabular}{llrrrrr}", r"\toprule",
         r"Tercile & Range & Coefficient & Bootstrap $p$ & Quarters "
         r"& \multicolumn{2}{c}{Mean provisioning} \\",
         r"\cmidrule(lr){6-7}",
         r" & & (clustered SE) & & coop.\ / banks & Coop. & Banks \\"]
    for mode, title in [("residualised", "Panel A. Terciles of the Basel ratio residualised on log assets and quarter fixed effects"),
                        ("unconditional", "Panel B. Terciles of the unconditional Basel ratio")]:
        L += [r"\midrule", r"\multicolumn{7}{l}{\textit{" + title + r"}} \\"]
        for terc in TERCILES:
            k = out[(mode, terc)]
            rng = f"[{k['lo']:.1f}, {k['hi']:.1f}]"
            L.append(f"{terc} & {rng} & {k['coef']:.4f}{stars(k['p_boot'])} ({k['se']:.4f}) & "
                     f"{k['p_boot']:.3f} & {k['coop_obs']:,} / {k['bank_obs']:,} & "
                     f"{k['coop_prov']:.3f} & {k['bank_prov']:.3f} " + r"\\")
    L += [r"\bottomrule", r"\end{tabular}"]
    note = (r"\begin{tablenotes}[flushleft]\footnotesize" "\n"
            r"\item Cooperative coefficient, controlled specification, within each tercile of the pooled "
            r"sample: Panel A cut on the Basel ratio residualised on log assets and quarter fixed effects, "
            r"Panel B on the ratio itself. Clustered standard errors in parentheses; $p$-values and stars "
            f"from the restricted wild cluster bootstrap ({B_:,} replications; *** $p<0.01$, ** $p<0.05$, "
            r"* $p<0.10$). Quarters with a provisioning ratio." "\n" r"\end{tablenotes}" "\n")
    (tab / "t12_provisioning_by_capital.tex").write_text("\n".join(L) + "\n" + note, encoding="utf-8")
    say(f"wrote {tab / 't12_provisioning_by_capital.tex'}")


def t12_from_results(path=None):
    """Rebuild tables/t12 from results/peer_rungs.txt without recomputing anything."""
    path = path or (P.RESULTS / "peer_rungs.txt")
    txt = path.read_text(encoding="utf-8")
    B_ = int(txt.split("(B=")[1].split(")")[0]) if "(B=" in txt else B
    sec = txt.split("[PROV_BY_TERCILE]")[1].split("\n\n")[0].strip().split("\n")[1:]
    out = {}
    for line in sec:
        p = line.split("\t")
        if len(p) < 17:
            continue
        out[(p[0], p[1])] = {"lo": float(p[2]), "hi": float(p[3]), "coef": float(p[4]),
                             "se": float(p[5]), "p": float(p[6]), "p_boot": float(p[7]),
                             "coop_obs": int(p[9]), "bank_obs": int(p[10]),
                             "coop_prov": float(p[13]), "bank_prov": float(p[14])}
    write_t12(out, B_)


# ------------------------------------------------------------------ D
def median_boot(df, o, B_, seed=20260809):
    """Conditional-median coefficient and an institution block bootstrap 95% interval."""
    d = df[["codigo", "is_coop", "log_assets", "date", o]].dropna().copy()
    d["t"] = d["date"].dt.to_period("Q").apply(lambda x: x.ordinal)
    point = float(smf.quantreg(CTRL.format(o=o), data=d).fit(q=0.5).params["is_coop"])
    rng = np.random.default_rng(seed)
    groups = {k: g for k, g in d.groupby("codigo")}
    ids = np.array(list(groups))
    out = []
    for _ in range(B_):
        draw = rng.choice(ids, size=len(ids), replace=True)
        bs = pd.concat([groups[i] for i in draw], ignore_index=True)
        if bs["is_coop"].nunique() < 2:
            continue
        try:
            out.append(float(smf.quantreg(CTRL.format(o=o), data=bs).fit(q=0.5).params["is_coop"]))
        except Exception:
            continue
    lo, hi = (np.percentile(out, [2.5, 97.5]) if len(out) > 30 else (np.nan, np.nan))
    return point, float(lo), float(hi), len(out)


def part_d(primary):
    say("=" * 92)
    say("D — cost-to-income with the denominator trimmed")
    say("=" * 92)
    say("Rows whose operating income gross of provisions (the cost-to-income denominator) is")
    say("below 0.5 percent of total assets are removed. Controlled specification; clustered SE;")
    say(f"bootstrap B={B}; conditional median with an institution block bootstrap of {B_MED} draws.\n")
    l2 = primary["_l2"]
    base = l2[l2["cti"].notna()].copy()
    thr = 0.005
    low = base["op_income_ratio"] < thr
    keep, drop = base[~low], base[low]
    say("[CTI_TRIM]  item\tvalue")
    say(f"threshold_op_income_over_assets\t{thr}")
    say(f"quarters_with_cti\t{len(base)}\tcoop\t{int((base.is_coop == 1).sum())}\tbank\t{int((base.is_coop == 0).sum())}")
    say(f"quarters_removed\t{len(drop)}\tcoop\t{int((drop.is_coop == 1).sum())}\tbank\t{int((drop.is_coop == 0).sum())}")
    say(f"institutions_touched\t{drop['codigo'].nunique()}\tcoop\t{drop.loc[drop.is_coop == 1, 'codigo'].nunique()}\tbank\t{drop.loc[drop.is_coop == 0, 'codigo'].nunique()}")
    say(f"mean_cti_removed\tcoop\t{drop.loc[drop.is_coop == 1, 'cti'].mean():.4f}\tbank\t{drop.loc[drop.is_coop == 0, 'cti'].mean():.4f}")
    r0 = primary["reg"]["ctrl"]["cti"]
    r1 = P.fit(keep, "cti", CTRL)
    pbv, gt = boot_p(keep, "cti", B)
    say("[CTI_TRIM_COEF]  sample\tcoef\tcl_se\tcl_p\tp_boot\tG_treated\tN\tmedian_coef\tmed_ci_lo\tmed_ci_hi\tmed_draws")
    m0 = median_boot(base, "cti", B_MED)
    m1 = median_boot(keep, "cti", B_MED)
    say(f"full\t{r0['coef']:.6f}\t{r0['cl_se']:.6f}\t{r0['cl_p']:.3e}\t{r0.get('p_boot', np.nan):.4f}\t"
        f"{r0.get('G_treated', 'na')}\t{r0['N']}\t{m0[0]:.6f}\t{m0[1]:.6f}\t{m0[2]:.6f}\t{m0[3]}")
    say(f"trimmed\t{r1['coef']:.6f}\t{r1['cl_se']:.6f}\t{r1['cl_p']:.3e}\t{pbv:.4f}\t{gt}\t{r1['N']}\t"
        f"{m1[0]:.6f}\t{m1[1]:.6f}\t{m1[2]:.6f}\t{m1[3]}")
    say("")
    return {"n_drop_coop": int((drop.is_coop == 1).sum()), "n_drop_bank": int((drop.is_coop == 0).sum()),
            "full": (r0, m0), "trimmed": (r1, pbv, m1)}


# ------------------------------------------------------------------ E
def part_e(primary):
    say("=" * 92)
    say("E — provisioning-ratio coverage by group and by year (analysis sample)")
    say("=" * 92)
    l2 = primary["_l2"].copy()
    l2["year"] = l2["date"].dt.year
    say("[PROV_COVERAGE]  group\tyear\tobs\tobs_with_prov\tshare")
    for v, lab in [(1, "cooperatives"), (0, "banks")]:
        d = l2[l2.is_coop == v]
        say(f"{lab}\tall\t{len(d)}\t{int(d['prov_ratio'].notna().sum())}\t{d['prov_ratio'].notna().mean():.4f}")
        for y, g in d.groupby("year"):
            say(f"{lab}\t{y}\t{len(g)}\t{int(g['prov_ratio'].notna().sum())}\t{g['prov_ratio'].notna().mean():.4f}")
    say("")


def main():
    panel, info, _ = P.build_panel()
    primary = P.run_pipeline(panel, **BASE)
    say(f"GATE G — PEER RUNGS, COOPERATIVE-OWNED BANKS, PROVISIONING BY CAPITAL, COST-TO-INCOME (B={B})")
    say(f"# primary: {primary['n_coop']} cooperatives, {primary['n_nc']} banks, {primary['n_obs']} obs\n")
    part_a(panel, primary)
    part_b(panel, primary)
    out_c = part_c(primary)
    write_t12(out_c)
    part_d(primary)
    part_e(primary)
    (P.RESULTS / "peer_rungs.txt").write_text(BUF.getvalue(), encoding="utf-8")
    print(f"\nwrote {P.RESULTS / 'peer_rungs.txt'}")


if __name__ == "__main__":
    if "--table-only" in sys.argv:
        t12_from_results()
    else:
        main()
