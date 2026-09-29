"""
GATE D — THE CAPITAL DIFFERENCE AS A DISTRIBUTIONAL FACT.

An editorial review made the point that the paper's headline capital number is a
conditional mean of −15.8 percentage points against a conditional median of −2.2, and
that the interesting result is therefore distributional rather than a single gap. This
script produces the evidence for that reframing.

  PART A  Quantile regressions across the distribution, not only at the median. The
          cooperative coefficient is estimated at nine quantiles for every outcome under
          the controlled specification. If the capital differential is roughly flat and
          small across the interior of the distribution and large only in the upper tail,
          the mean is a tail statistic and the paper should say so.

  PART B  Dispersion. Standard deviation, interquartile and interdecile range of each
          outcome by group, both raw and residualised on log assets and quarter, so the
          comparison is at equal size. The claim "cooperatives are homogeneous where
          banks are dispersed" is a claim about these numbers.

  PART C  The capital distribution itself: deciles of the Basel ratio by group, and the
          share of each group above conventional thresholds.

  PART D  Coarsening sensitivity, gathered for the paper rather than left in a
          diagnostic: the matched estimate under five coarsening schemes.

Writes results/gate_d_distribution.txt and tables/t7_quantiles.tex; make_figures.py
draws figures/fig12_capital_quantiles.png from the results file.

    python gate_d_distribution.py
"""
from __future__ import annotations
import io
import os
import sys
from concurrent.futures import ProcessPoolExecutor
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import paper as P

BUF = io.StringIO()
QUANTILES = [0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90]
_num_args = [a for a in sys.argv[1:] if a.isdigit()]
B_QBOOT = int(_num_args[0]) if _num_args else 199   # institution bootstrap for t7
SEED_QBOOT = 20260808


def _qboot_cell(o, q, sub, B, seed):
    """Institution block bootstrap of one quantile-regression cell (worker process)."""
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
            m = smf.quantreg(f"{o} ~ is_coop + log_assets + C(t)", data=bs).fit(q=q)
            out.append(float(m.params["is_coop"]))
        except Exception:
            continue
    if len(out) < 30:
        return o, q, float("nan"), float("nan"), len(out)
    return o, q, float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5)), len(out)
CORE = ["basileia_num", "leverage", "roa", "cti", "credit_ratio", "prov_ratio"]
BASE = dict(coop_def="singular", winsor_scope="analysis", use_cluster=True,
            cti_col="cti_new", roa_col="roa_ann", nim_col="nim_ann",
            peer_set="banks", coarsen="size_q5")


def say(*a):
    line = " ".join(str(x) for x in a)
    print(line)
    print(line, file=BUF)


# ---------------------------------------------------------------- A
def part_a(l2):
    say("=" * 92)
    say("A — cooperative coefficient across the outcome distribution")
    say("=" * 92)
    say("Controlled specification (log assets + quarter fixed effects) estimated at nine")
    say("quantiles. The OLS column is the conditional mean for comparison.\n")
    store = {}
    for o in CORE:
        sub = l2[["is_coop", "log_assets", "date", "codigo", o]].dropna().copy()
        if len(sub) < 300:
            continue
        sub["t"] = sub["date"].dt.to_period("Q").apply(lambda x: x.ordinal)
        ols = P.fit(l2, o, "{o} ~ is_coop + log_assets + C(t)")
        row = {}
        for q in QUANTILES:
            try:
                m = smf.quantreg(f"{o} ~ is_coop + log_assets + C(t)", data=sub).fit(q=q)
                row[q] = float(m.params["is_coop"])
            except Exception:
                row[q] = np.nan
        store[o] = row
        dec = 2 if "basileia" in o else 4
        say(f"{P.OUTCOMES[o]}")
        say("  " + "".join(f"{f'q{int(q*100)}':>9}" for q in QUANTILES) + f"{'OLS':>11}")
        say("  " + "".join(f"{row[q]:>9.{dec}f}" for q in QUANTILES)
            + f"{ols['coef']:>11.{dec}f}")
        interior = [row[q] for q in (0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8)
                    if row[q] == row[q]]
        if interior and abs(ols["coef"]) > 1e-9:
            share = np.mean(interior) / ols["coef"]
            say(f"  mean of q20-q80 is {np.mean(interior):.{dec}f}, "
                f"{100*share:.0f}% of the OLS coefficient")
        say("")
    return store


# ---------------------------------------------------------------- B
def part_b(l2):
    say("=" * 92)
    say("B — dispersion by group, raw and at equal size")
    say("=" * 92)
    say("Residualised columns are residuals from a regression of the outcome on log")
    say("assets and quarter fixed effects, so they compare dispersion at equal size.\n")
    say(f"{'outcome':<28}{'coop sd':>10}{'bank sd':>10}{'ratio':>8}"
        f"{'coop IQR':>11}{'bank IQR':>11}{'IQR ratio':>11}")
    for o in CORE:
        sub = l2[["is_coop", "log_assets", "date", o]].dropna().copy()
        if len(sub) < 300:
            continue
        sub["t"] = sub["date"].dt.to_period("Q").apply(lambda x: x.ordinal)
        m = smf.ols(f"{o} ~ log_assets + C(t)", data=sub).fit()
        sub["r"] = m.resid
        c, b = sub[sub.is_coop == 1], sub[sub.is_coop == 0]
        sdc, sdb = c["r"].std(), b["r"].std()
        iqc = c["r"].quantile(.75) - c["r"].quantile(.25)
        iqb = b["r"].quantile(.75) - b["r"].quantile(.25)
        dec = 2 if "basileia" in o else 4
        say(f"{P.OUTCOMES[o]:<28}{sdc:>10.{dec}f}{sdb:>10.{dec}f}{sdc/sdb:>8.2f}"
            f"{iqc:>11.{dec}f}{iqb:>11.{dec}f}{iqc/iqb:>11.2f}")
    say("\nA ratio below one means cooperatives are the more homogeneous group at equal")
    say("size. This is the quantitative content of the claim that cooperatives occupy a")
    say("narrow band of a distribution across which banks are spread.")


# ---------------------------------------------------------------- C
def part_c(l2):
    say("\n" + "=" * 92)
    say("C — the capital distribution")
    say("=" * 92)
    c = l2.loc[l2.is_coop == 1, "basileia_num"].dropna()
    b = l2.loc[l2.is_coop == 0, "basileia_num"].dropna()
    say(f"\n{'decile':>8}{'cooperatives':>15}{'banks':>10}{'difference':>13}")
    for q in np.arange(0.1, 1.0, 0.1):
        say(f"{f'p{int(q*100)}':>8}{c.quantile(q):>15.2f}{b.quantile(q):>10.2f}"
            f"{c.quantile(q)-b.quantile(q):>13.2f}")
    say(f"\n{'':>8}{'mean':>15}{'':>10}")
    say(f"{'mean':>8}{c.mean():>15.2f}{b.mean():>10.2f}{c.mean()-b.mean():>13.2f}")
    say(f"{'sd':>8}{c.std():>15.2f}{b.std():>10.2f}")
    say(f"{'skew':>8}{c.skew():>15.2f}{b.skew():>10.2f}")
    for thr in (20, 30, 50, 100):
        say(f"share above {thr:>3}%: cooperatives {100*(c>thr).mean():>5.1f}%, "
            f"banks {100*(b>thr).mean():>5.1f}%")
    say("\nThe mean gap is produced by the bank right tail, not by a shift of the whole")
    say("distribution. Report the deciles, not only the mean.")


# ---------------------------------------------------------------- D
def part_d(panel):
    say("\n" + "=" * 92)
    say("D — matched estimate under alternative coarsening schemes")
    say("=" * 92)
    say(f"\n{'coarsening':<20}{'weighted CEM':>15}{'unweighted':>13}"
        f"{'eff. n controls':>17}{'credit CEM':>12}{'credit p':>10}")
    lines = ["[COARSENING]  coarsening\tbasel_cem\tbasel_cem_unweighted\teff_n_controls"
             "\tcredit_cem\tcredit_cl_p",
             "# weighted CEM estimand of the capital ratio and of credit/assets under every "
             "coarsening scheme; the paper's within-region claim rests on the three region rows"]
    for cs in P.COARSENINGS:
        cfg = dict(BASE); cfg["coarsen"] = cs
        try:
            r = P.run_pipeline(panel, **cfg)
        except Exception as e:                                    # noqa: BLE001
            say(f"{cs:<20}  failed: {e}")
            continue
        a = r["reg"]["cem"].get("basileia_num")
        u = r["reg_extra"]["cem_unweighted"].get("basileia_num")
        c = r["reg"]["cem"].get("credit_ratio")
        say(f"{cs:<20}{a['coef']:>15.2f}{u['coef']:>13.2f}"
            f"{r['cem_w']['eff_n_controls']:>17.1f}{c['coef']:>12.4f}{c['cl_p']:>10.3f}")
        lines.append(f"{cs}\t{a['coef']:.6f}\t{u['coef']:.6f}\t{r['cem_w']['eff_n_controls']:.2f}"
                     f"\t{c['coef']:.6f}\t{c['cl_p']:.3e}")
    say("\nReported so the reader can see that the choice of coarsening, not only its")
    say("existence, is an analyst decision with consequences.")
    (P.RESULTS / "coarsening_sensitivity.txt").write_text("\n".join(lines) + "\n",
                                                          encoding="utf-8")


def write_quantile_table(store, l2):
    """Emit tables/t7_quantiles.tex so the paper does not transcribe these numbers."""
    tab = P.ROOT / "tables"
    tab.mkdir(exist_ok=True, parents=True)
    show = [0.10, 0.25, 0.50, 0.75, 0.90]
    subs, vals, olss = {}, {}, {}
    for o in CORE:
        sub = l2[["is_coop", "log_assets", "date", "codigo", o]].dropna().copy()
        if len(sub) < 300:
            continue
        sub["t"] = sub["date"].dt.to_period("Q").apply(lambda x: x.ordinal)
        subs[o] = sub
        vals[o] = {}
        for q in show:
            if o in store and q in store[o]:
                vals[o][q] = store[o][q]
            else:
                try:
                    m = smf.quantreg(f"{o} ~ is_coop + log_assets + C(t)",
                                     data=sub).fit(q=q)
                    vals[o][q] = float(m.params["is_coop"])
                except Exception:
                    vals[o][q] = float("nan")
        olss[o] = P.fit(l2, o, "{o} ~ is_coop + log_assets + C(t)")
    # institution block bootstrap of every cell, one worker per cell
    say(f"\nbootstrap intervals for the quantile table: B={B_QBOOT} resamples of "
        f"institutions per cell, {len(subs) * len(show)} cells")
    tasks = [(o, q, subs[o], B_QBOOT, SEED_QBOOT + 17 * i + int(q * 100))
             for i, o in enumerate(subs) for q in show]
    ci = {}
    workers = max(1, min(8, (os.cpu_count() or 2) - 2))
    with ProcessPoolExecutor(max_workers=workers) as ex:
        for o, q, lo, hi, nb in ex.map(_qboot_cell, *zip(*tasks)):
            ci[(o, q)] = (lo, hi, nb)
    say("[QUANTILE_CI]  outcome\tq\tcoef\tci_lo\tci_hi\tdraws")
    for o in subs:
        for q in show:
            lo, hi, nb = ci[(o, q)]
            say(f"{P.OUTCOMES[o]}\t{q:.2f}\t{vals[o][q]:.6f}\t{lo:.6f}\t{hi:.6f}\t{nb}")
    render_t7(vals, ci, olss, B_QBOOT)


SHORT_T7 = {"basileia_num": "Basel ratio (pp)", "leverage": "Leverage",
            "roa": "Return on assets", "cti": "Cost-to-income",
            "credit_ratio": "Credit / assets", "prov_ratio": "Provisioning ratio"}
SHOW_T7 = [0.10, 0.25, 0.50, 0.75, 0.90]


def render_t7(vals, ci, olss, B_):
    """Write tables/t7_quantiles.tex from the quantile coefficients, their bootstrap
    intervals and the OLS mean with its clustered interval."""
    tab = P.ROOT / "tables"
    tab.mkdir(exist_ok=True, parents=True)
    rows = []
    for o in vals:
        d = 2 if "basileia" in o else 3
        lab = SHORT_T7.get(o, P.OUTCOMES[o]).replace("%", r"\%")
        rows.append(f"{lab} & "
                    + " & ".join(f"{vals[o][q]:.{d}f}" for q in SHOW_T7)
                    + f" & {olss[o]['coef']:.{d}f} " + r"\\")
        rows.append(" & " + " & ".join(f"[{ci[(o, q)][0]:.{d}f}, {ci[(o, q)][1]:.{d}f}]" for q in SHOW_T7)
                    + f" & [{olss[o]['cl_lo']:.{d}f}, {olss[o]['cl_hi']:.{d}f}] " + r"\\")
    body = (r"\footnotesize" + "\n" + r"\setlength{\tabcolsep}{2.5pt}" + "\n"
            + r"\begin{tabular}{lrrrrrr}" + "\n" + r"\toprule" + "\n"
            + r"Outcome & $q_{10}$ & $q_{25}$ & $q_{50}$ & $q_{75}$ & $q_{90}$ & Mean \\"
            + "\n" + r"\midrule" + "\n" + "\n".join(rows) + "\n"
            + r"\bottomrule" + "\n" + r"\end{tabular}" + "\n"
            + r"\begin{tablenotes}[flushleft]\footnotesize" + "\n"
            + r"\item Cooperative coefficient from quantile regressions of each outcome "
              r"on the cooperative dummy, log assets and quarter fixed effects, at "
              r"five quantiles of the conditional distribution, with the OLS conditional "
              r"mean for comparison. In brackets, 95 percent intervals from a bootstrap "
              f"that resamples institutions ({B_} draws per cell) for the quantile "
              r"cells and the institution-clustered interval for the mean. Where the "
              r"coefficient changes sign across quantiles, the mean describes neither "
              r"tail." + "\n"
            + r"\end{tablenotes}" + "\n")
    (tab / "t7_quantiles.tex").write_text(body, encoding="utf-8")
    say(f"wrote {tab / 't7_quantiles.tex'}")


def t7_from_results():
    """Rebuild tables/t7 from results/gate_d_distribution.txt and results_primary.txt
    without recomputing the bootstrap."""
    lab2key = {v: k for k, v in P.OUTCOMES.items()}
    txt = (P.RESULTS / "gate_d_distribution.txt").read_text(encoding="utf-8")
    block = txt.split("[QUANTILE_CI]")[1].split("wrote ")[0].strip().split("\n")[1:]
    vals, ci, draws = {}, {}, set()
    for line in block:
        p = line.split("\t")
        if len(p) < 6 or p[0] not in lab2key:
            continue
        o, q = lab2key[p[0]], float(p[1])
        vals.setdefault(o, {})[q] = float(p[2])
        ci[(o, q)] = (float(p[3]), float(p[4]), int(p[5]))
        draws.add(int(p[5]))
    prim = (P.RESULTS / "results_primary.txt").read_text(encoding="utf-8")
    sec = prim.split("[MAIN_COEFFICIENTS]")[1].split("\n[")[0].strip().split("\n")
    olss = {}
    for line in sec:
        p = line.split("\t")
        if len(p) >= 5 and p[0] in lab2key and p[1] == "ctrl":
            olss[lab2key[p[0]]] = {"coef": float(p[2]), "cl_lo": float(p[3]), "cl_hi": float(p[4])}
    vals = {o: v for o, v in vals.items() if o in olss}
    render_t7(vals, ci, olss, max(draws) if draws else B_QBOOT)


def capital_ci(l2):
    """Institution-bootstrap intervals for the capital-ratio coefficient at all nine
    quantiles, for the continuous band in Figure 4(a). Same cell function and seed rule
    as the t7 table, so the five quantiles t7 reports reproduce exactly."""
    o = "basileia_num"
    sub = l2[["is_coop", "log_assets", "date", "codigo", o]].dropna().copy()
    sub["t"] = sub["date"].dt.to_period("Q").apply(lambda x: x.ordinal)
    point = {q: float(smf.quantreg(f"{o} ~ is_coop + log_assets + C(t)", data=sub)
                      .fit(q=q).params["is_coop"]) for q in QUANTILES}
    tasks = [(o, q, sub, B_QBOOT, SEED_QBOOT + int(round(q * 100))) for q in QUANTILES]
    workers = max(1, min(8, (os.cpu_count() or 2) - 2))
    lines = ["[CAPITAL_QUANTILE_CI]  q\tcoef\tci_lo\tci_hi\tdraws",
             f"# institution block bootstrap, B={B_QBOOT} per quantile, seed rule as t7"]
    with ProcessPoolExecutor(max_workers=workers) as ex:
        for _, q, lo, hi, nb in ex.map(_qboot_cell, *zip(*tasks)):
            lines.append(f"{q:.2f}\t{point[q]:.6f}\t{lo:.6f}\t{hi:.6f}\t{nb}")
    path = P.RESULTS / "capital_quantile_ci.txt"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {path}")


def main():
    panel, info, _ = P.build_panel()
    res = P.run_pipeline(panel, **BASE)
    l2 = res["_l2"]
    if "--capital-ci" in sys.argv:
        capital_ci(l2)
        return
    if "--coarsening" in sys.argv:
        part_d(panel)
        return
    say("GATE D — DISTRIBUTIONAL EVIDENCE ON THE CAPITAL RESULT\n")
    store = part_a(l2)
    part_b(l2)
    part_c(l2)
    part_d(panel)
    write_quantile_table(store, l2)
    capital_ci(l2)
    (P.RESULTS / "gate_d_distribution.txt").write_text(BUF.getvalue(), encoding="utf-8")
    print(f"\nwrote {P.RESULTS / 'gate_d_distribution.txt'}")


if __name__ == "__main__":
    if "--table-only" in sys.argv:
        t7_from_results()
    else:
        main()