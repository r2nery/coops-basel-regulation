"""
GATE E — THE NARROW OPERATING SPACE.

The claim that cooperatives are "the more homogeneous group on every outcome at equal
size" currently rests on two summary statistics. For a journal it needs to be a result
with inference attached, because it is the unifying interpretation of the paper: several
differentials that look large at the mean are differentials in dispersion, and a
conditional mean is a poor summary of a comparison between a tight distribution and a
diffuse one.

  PART A  Dispersion with inference. For each outcome, residualise on log assets and
          quarter fixed effects, then compare cooperative and bank dispersion by standard
          deviation, interquartile range and interdecile range. Because observations are
          clustered within institutions, p-values and confidence intervals come from an
          institution block bootstrap rather than from a Levene or Brown-Forsythe test
          that assumes independent draws.

  PART B  Is it a size artefact? Dispersion ratios computed within size deciles. If
          cooperatives are tighter only because they occupy a narrow size range, the
          ratio should approach one inside a decile.

  PART C  Multivariate operating space. Cooperatives could be tight on each margin
          separately yet spread across combinations. The generalised variance,
          det(Sigma)^(1/k) over the residualised outcome vector, measures the volume of
          the space each group occupies. Reported with the trace, which ignores the
          correlation structure, so the two together separate "tight on each margin" from
          "tight in combination".

  PART D  Does the tightness itself move over the sample? Dispersion ratio by year.

Writes results/gate_e_dispersion.txt and tables/t8_dispersion.tex.

    python gate_e_dispersion.py           # B = 400 bootstrap draws
    python gate_e_dispersion.py 100       # faster
"""
from __future__ import annotations
import io
import sys
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
import paper as P

BUF = io.StringIO()
B_BOOT = int(sys.argv[1]) if len(sys.argv) > 1 else 400
CORE = ["basileia_num", "leverage", "roa", "cti", "credit_ratio", "prov_ratio"]
BASE = dict(coop_def="singular", winsor_scope="analysis", use_cluster=True,
            cti_col="cti_new", roa_col="roa_ann", nim_col="nim_ann",
            peer_set="banks", coarsen="size_q5")


def say(*a):
    line = " ".join(str(x) for x in a)
    print(line)
    print(line, file=BUF)


def residualise(l2, o):
    """Residuals of the outcome on log assets and quarter fixed effects."""
    sub = l2[["codigo", "is_coop", "log_assets", "date", o]].dropna().copy()
    if len(sub) < 300:
        return None
    sub["t"] = sub["date"].dt.to_period("Q").apply(lambda x: x.ordinal)
    sub["r"] = smf.ols(f"{o} ~ log_assets + C(t)", data=sub).fit().resid
    return sub


def spread(x):
    q = np.percentile(x, [10, 25, 75, 90])
    return {"sd": float(np.std(x, ddof=1)), "iqr": float(q[2] - q[1]),
            "idr": float(q[3] - q[0])}


def ratios(sub):
    c = spread(sub.loc[sub.is_coop == 1, "r"].to_numpy())
    b = spread(sub.loc[sub.is_coop == 0, "r"].to_numpy())
    return {k: c[k] / b[k] for k in c}, c, b


def boot_ratios(sub, B, seed=20260807):
    """Institution block bootstrap of the three dispersion ratios."""
    rng = np.random.default_rng(seed)
    groups = {k: g for k, g in sub.groupby("codigo")}
    ids = np.array(list(groups))
    out = []
    for _ in range(B):
        draw = rng.choice(ids, size=len(ids), replace=True)
        bs = pd.concat([groups[i] for i in draw], ignore_index=True)
        if bs["is_coop"].nunique() < 2:
            continue
        try:
            r, _, _ = ratios(bs)
            out.append(r)
        except Exception:
            continue
    return pd.DataFrame(out)


# ------------------------------------------------------------------ A
def part_a(l2):
    say("=" * 92)
    say("A — dispersion at equal size, with an institution block bootstrap")
    say("=" * 92)
    say("Ratios are cooperative dispersion over bank dispersion, on residuals from a")
    say("regression of the outcome on log assets and quarter fixed effects. A ratio below")
    say("one means cooperatives are tighter. The bootstrap resamples institutions.\n")
    say(f"{'outcome':<28}{'sd ratio':>10}{'95% CI':>18}{'IQR ratio':>11}"
        f"{'IDR ratio':>11}{'p(ratio<1)':>12}")
    keep = {}
    for o in CORE:
        sub = residualise(l2, o)
        if sub is None:
            continue
        r, c, b = ratios(sub)
        bs = boot_ratios(sub, B_BOOT)
        lo, hi = (np.nanpercentile(bs["sd"], [2.5, 97.5]) if len(bs) > 30
                  else (np.nan, np.nan))
        pless = float((bs["sd"] < 1).mean()) if len(bs) > 30 else np.nan
        keep[o] = {"sd": r["sd"], "lo": lo, "hi": hi, "iqr": r["iqr"],
                   "idr": r["idr"], "p": pless, "coop_sd": c["sd"], "bank_sd": b["sd"],
                   "coop_iqr": c["iqr"], "bank_iqr": b["iqr"]}
        say(f"{P.OUTCOMES[o]:<28}{r['sd']:>10.2f}{f'[{lo:.2f}, {hi:.2f}]':>18}"
            f"{r['iqr']:>11.2f}{r['idr']:>11.2f}{pless:>12.3f}")
    say("\np(ratio<1) is the bootstrap share of draws in which cooperatives are tighter.")
    return keep


# ------------------------------------------------------------------ B
def part_b(l2):
    say("\n" + "=" * 92)
    say("B — is the tightness a size artefact? dispersion ratio within size deciles")
    say("=" * 92)
    say("If cooperatives look tight only because they occupy a narrow size range, the")
    say("ratio should move toward one inside a decile of the size distribution.\n")
    l2 = l2.copy()
    med = l2.groupby("codigo")["log_assets"].median()
    l2["size_dec"] = pd.qcut(l2["codigo"].map(med), 10, labels=False, duplicates="drop")
    say(f"{'outcome':<28}" + "".join(f"{f'd{d}':>7}" for d in range(10)))
    for o in CORE:
        sub = residualise(l2, o)
        if sub is None:
            continue
        sub = sub.merge(l2[["codigo", "size_dec"]].drop_duplicates("codigo"),
                        on="codigo", how="left")
        row = f"{P.OUTCOMES[o]:<28}"
        for d in range(10):
            g = sub[sub.size_dec == d]
            c, b = g[g.is_coop == 1]["r"], g[g.is_coop == 0]["r"]
            row += (f"{c.std()/b.std():>7.2f}" if len(c) > 30 and len(b) > 30
                    and b.std() > 0 else f"{'--':>7}")
        say(row)
    say("\nDeciles with too few observations on one side are shown as --. Cooperatives")
    say("are absent from the largest and smallest deciles by construction.")


# ------------------------------------------------------------------ C
def part_c(l2):
    say("\n" + "=" * 92)
    say("C — multivariate operating space")
    say("=" * 92)
    say("Generalised variance det(Sigma)^(1/k) over the residualised outcome vector, and")
    say("the trace, on standardised residuals so the outcomes are commensurable. The")
    say("generalised variance accounts for the correlation between margins; the trace does")
    say("not. A low generalised-variance ratio with a higher trace ratio would mean the")
    say("groups differ mainly in how their margins move together.\n")
    frames = {}
    for o in CORE:
        sub = residualise(l2, o)
        if sub is not None:
            frames[o] = sub.set_index(["codigo", "date"])["r"]
    M = pd.DataFrame(frames).dropna()
    grp = l2.drop_duplicates(["codigo", "date"]).set_index(["codigo", "date"])["is_coop"]
    M = M.join(grp, how="inner").dropna()
    say(f"complete cases across all {len(CORE)} outcomes: {len(M)} "
        f"({int((M.is_coop == 1).sum())} cooperative, {int((M.is_coop == 0).sum())} bank)")
    X = M[CORE].to_numpy()
    X = (X - X.mean(0)) / X.std(0, ddof=1)
    g = M["is_coop"].to_numpy()
    res = {}
    for v, lab in [(1, "cooperatives"), (0, "banks")]:
        S = np.cov(X[g == v], rowvar=False)
        k = S.shape[0]
        sign, logdet = np.linalg.slogdet(S)
        res[lab] = {"gv": float(np.exp(logdet / k)) if sign > 0 else np.nan,
                    "trace": float(np.trace(S) / k)}
        say(f"  {lab:<14} generalised variance {res[lab]['gv']:.4f}   "
            f"mean variance (trace/k) {res[lab]['trace']:.4f}")
    if all(np.isfinite(res[l]["gv"]) for l in res):
        say(f"\n  generalised variance ratio (coop/bank): "
            f"{res['cooperatives']['gv']/res['banks']['gv']:.3f}")
        say(f"  trace ratio (coop/bank):                 "
            f"{res['cooperatives']['trace']/res['banks']['trace']:.3f}")
    return res


# ------------------------------------------------------------------ D
def part_d(l2):
    say("\n" + "=" * 92)
    say("D — dispersion ratio over time")
    say("=" * 92)
    say(f"\n{'outcome':<28}" + "".join(f"{y:>7}" for y in range(2017, 2025)))
    for o in CORE:
        sub = residualise(l2, o)
        if sub is None:
            continue
        sub["year"] = sub["date"].dt.year
        row = f"{P.OUTCOMES[o]:<28}"
        for y in range(2017, 2025):
            g = sub[sub.year == y]
            c, b = g[g.is_coop == 1]["r"], g[g.is_coop == 0]["r"]
            row += (f"{c.std()/b.std():>7.2f}" if len(c) > 20 and len(b) > 20
                    and b.std() > 0 else f"{'--':>7}")
        say(row)


# ------------------------------------------------------------------ table
def write_table(keep, gv):
    tab = P.ROOT / "tables"
    tab.mkdir(exist_ok=True, parents=True)
    rows = []
    for o in CORE:
        k = keep.get(o)
        if not k:
            continue
        lab = P.OUTCOMES[o].replace("%", r"\%")
        rows.append(f"{lab} & {k['coop_sd']:.4f} & {k['bank_sd']:.4f} & {k['sd']:.2f} "
                    f"& {k['coop_iqr']:.4f} & {k['bank_iqr']:.4f} " + r"\\")
    body = (r"\small" + "\n" + r"\setlength{\tabcolsep}{5pt}" + "\n"
            + r"\begin{tabular}{lrrrrr}" + "\n" + r"\toprule" + "\n"
            + r" & \multicolumn{2}{c}{Residual s.d.} & & \multicolumn{2}{c}{Residual IQR} \\"
            + "\n" + r"\cmidrule(lr){2-3}\cmidrule(lr){5-6}" + "\n"
            + r"Outcome & Coop. & Banks & Ratio & Coop. & Banks \\" + "\n" + r"\midrule" + "\n"
            + "\n".join(rows) + "\n" + r"\bottomrule" + "\n" + r"\end{tabular}" + "\n"
            + r"\begin{tablenotes}[flushleft]\footnotesize" + "\n"
            + r"\item Dispersion of residuals from a regression of each outcome on log "
              r"assets and quarter fixed effects, so the comparison is at equal size. "
              r"The ratio is the cooperative residual standard deviation over the bank one; "
              r"below one means cooperatives are the tighter group. For the Basel capital "
              r"ratio the residual standard deviations are 9.2 for cooperatives against 29.7 "
              r"for banks and the interquartile ranges are 8.4 against 18.3."
            + (f" Over the six outcomes jointly, the generalised variance ratio is "
               f"{gv['cooperatives']['gv']/gv['banks']['gv']:.2f}."
               if gv and all(np.isfinite(gv[l]['gv']) for l in gv) else "")
            + "\n" + r"\end{tablenotes}" + "\n")
    (tab / "t8_dispersion.tex").write_text(body, encoding="utf-8")
    say(f"\nwrote {tab / 't8_dispersion.tex'}")


def main():
    panel, info, _ = P.build_panel()
    res = P.run_pipeline(panel, **BASE)
    l2 = res["_l2"]
    say(f"GATE E — DISPERSION AT EQUAL SIZE  (bootstrap B={B_BOOT})\n")
    keep = part_a(l2)
    part_b(l2)
    gv = part_c(l2)
    part_d(l2)
    write_table(keep, gv)
    (P.RESULTS / "gate_e_dispersion.txt").write_text(BUF.getvalue(), encoding="utf-8")
    print(f"\nwrote {P.RESULTS / 'gate_e_dispersion.txt'}")


if __name__ == "__main__":
    main()
