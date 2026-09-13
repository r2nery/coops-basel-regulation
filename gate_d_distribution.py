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

Writes results/gate_d_distribution.txt and figures/fig12_capital_quantiles.png.

    python gate_d_distribution.py
"""
from __future__ import annotations
import io
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import paper as P

BUF = io.StringIO()
QUANTILES = [0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90]
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
        f"{'eff. n controls':>17}")
    for cs in P.COARSENINGS:
        cfg = dict(BASE); cfg["coarsen"] = cs
        try:
            r = P.run_pipeline(panel, **cfg)
        except Exception as e:                                    # noqa: BLE001
            say(f"{cs:<20}  failed: {e}")
            continue
        a = r["reg"]["cem"].get("basileia_num")
        u = r["reg_extra"]["cem_unweighted"].get("basileia_num")
        say(f"{cs:<20}{a['coef']:>15.2f}{u['coef']:>13.2f}"
            f"{r['cem_w']['eff_n_controls']:>17.1f}")
    say("\nReported so the reader can see that the choice of coarsening, not only its")
    say("existence, is an analyst decision with consequences.")


# ---------------------------------------------------------------- figure
def figure(store, l2):
    fig, ax = plt.subplots(1, 2, figsize=(11, 4))
    row = store.get("basileia_num")
    if row:
        ax[0].axhline(0, color="0.7", lw=.8)
        ax[0].plot([q * 100 for q in QUANTILES], [row[q] for q in QUANTILES],
                   "o-", color="tab:blue", label="quantile estimate")
        ols = P.fit(l2, "basileia_num", "{o} ~ is_coop + log_assets + C(t)")
        ax[0].axhline(ols["coef"], color="tab:red", ls="--",
                      label=f"conditional mean ({ols['coef']:.1f})")
        ax[0].set_xlabel("quantile of the Basel ratio distribution")
        ax[0].set_ylabel("cooperative coefficient (pp)")
        ax[0].set_title("(a) Capital differential across the distribution")
        ax[0].legend(fontsize=8)
    c = l2.loc[l2.is_coop == 1, "basileia_num"].dropna()
    b = l2.loc[l2.is_coop == 0, "basileia_num"].dropna()
    TOP = 80.0
    bins = np.linspace(0, TOP, 60)
    cc, bb = c[c <= TOP], b[b <= TOP]
    ax[1].hist(cc, bins=bins, density=True, alpha=.55,
               color="tab:blue", label=f"cooperatives ({100*(c>TOP).mean():.1f}% above)")
    ax[1].hist(bb, bins=bins, density=True, alpha=.55,
               color="tab:red", label=f"banks ({100*(b>TOP).mean():.1f}% above)")
    ax[1].set_xlabel("Basel capital ratio (%)")
    ax[1].set_ylabel("density")
    ax[1].set_title("(b) Capital ratio distributions")
    ax[1].legend(fontsize=8)
    fig.tight_layout()
    out = P.FIGURES / "fig12_capital_quantiles.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    say(f"\nwrote {out}")


def write_quantile_table(store, l2):
    """Emit tables/t7_quantiles.tex so the paper does not transcribe these numbers."""
    tab = P.ROOT / "tables"
    tab.mkdir(exist_ok=True, parents=True)
    show = [0.10, 0.25, 0.50, 0.75, 0.90]
    rows = []
    for o in CORE:
        sub = l2[["is_coop", "log_assets", "date", "codigo", o]].dropna().copy()
        if len(sub) < 300:
            continue
        sub["t"] = sub["date"].dt.to_period("Q").apply(lambda x: x.ordinal)
        vals = {}
        for q in show:
            if o in store and q in store[o]:
                vals[q] = store[o][q]
            else:
                try:
                    m = smf.quantreg(f"{o} ~ is_coop + log_assets + C(t)",
                                     data=sub).fit(q=q)
                    vals[q] = float(m.params["is_coop"])
                except Exception:
                    vals[q] = float("nan")
        ols = P.fit(l2, o, "{o} ~ is_coop + log_assets + C(t)")
        d = 2 if "basileia" in o else 4
        lab = P.OUTCOMES[o].replace("%", r"\%")
        rows.append(f"{lab} & "
                    + " & ".join(f"{vals[q]:.{d}f}" for q in show)
                    + f" & {ols['coef']:.{d}f} " + r"\\")
    body = (r"\small" + "\n" + r"\setlength{\tabcolsep}{5pt}" + "\n"
            + r"\begin{tabular}{lrrrrrr}" + "\n" + r"\toprule" + "\n"
            + r"Outcome & $q_{10}$ & $q_{25}$ & $q_{50}$ & $q_{75}$ & $q_{90}$ & Mean \\"
            + "\n" + r"\midrule" + "\n" + "\n".join(rows) + "\n"
            + r"\bottomrule" + "\n" + r"\end{tabular}" + "\n"
            + r"\begin{tablenotes}[flushleft]\footnotesize" + "\n"
            + r"\item Cooperative coefficient from quantile regressions of each outcome "
              r"on the cooperative indicator, log assets and quarter fixed effects, at "
              r"five quantiles of the conditional distribution, with the OLS conditional "
              r"mean for comparison. Where the coefficient changes sign across quantiles, "
              r"the mean describes neither tail." + "\n"
            + r"\end{tablenotes}" + "\n")
    (tab / "t7_quantiles.tex").write_text(body, encoding="utf-8")
    say(f"wrote {tab / 't7_quantiles.tex'}")


def main():
    panel, info, _ = P.build_panel()
    res = P.run_pipeline(panel, **BASE)
    l2 = res["_l2"]
    say("GATE D — DISTRIBUTIONAL EVIDENCE ON THE CAPITAL RESULT\n")
    store = part_a(l2)
    part_b(l2)
    part_c(l2)
    part_d(panel)
    write_quantile_table(store, l2)
    figure(store, l2)
    (P.RESULTS / "gate_d_distribution.txt").write_text(BUF.getvalue(), encoding="utf-8")
    print(f"\nwrote {P.RESULTS / 'gate_d_distribution.txt'}")


if __name__ == "__main__":
    main()