"""
FIGURE GENERATOR — draws every figure in the paper and the online appendix.

Estimate-based figures parse the results files that paper.py, gate_d_distribution.py
and make_tables.py already read, so a figure cannot drift from the tables. Data-based
figures rebuild the analysis sample through paper.py's own functions (build_panel,
select_sample, winsorize) without re-running any regression.

    python make_figures.py

Main text
    fig5_regulatory.png          methodology split over time, cooperatives and non-cooperatives
    fig8_overlap.png             common support in log total assets
    fig14_broad_group.png        who is in the broad comparison group (credit vs funding)
    fig12_capital_quantiles.png  capital differential across the distribution, with intervals
    fig11_stable.png             medians and interquartile ranges over time
    fig13_ladder.png             every outcome across the comparison-group ladder
Online appendix
    fig10_stability.png          standardised coefficients across the four specifications
    fig15_quantile_profiles.png  quantile coefficients relative to the conditional mean
    fig16_dispersion.png         cooperative-to-bank dispersion ratios at equal size
    fig17_decumulation.png       raw against de-cumulated return on assets
"""
from __future__ import annotations
import re
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker
import matplotlib.dates

import paper as P
import make_tables as MT

FIG = P.FIGURES
RES = P.RESULTS

# ------------------------------------------------------------------ palette and chrome
# Categorical slots 1-3 of the reference palette (validated all-pairs in light mode).
COOP, BANK, OTHER = "#2a78d6", "#eb6834", "#1baf7a"
INK, INK2, MUTED = "#0b0b0b", "#52514e", "#898781"
GRID, AXIS, BAND = "#e1e0d9", "#c3c2b7", "#f0efec"
TEXTWIDTH = 6.3   # inches, a4 with 1in margins

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.size": 8,
    "axes.titlesize": 8.5,
    "axes.titleweight": "bold",
    "axes.titlelocation": "left",
    "axes.labelsize": 8,
    "axes.labelcolor": INK2,
    "axes.edgecolor": AXIS,
    "axes.linewidth": 0.6,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": False,
    "grid.color": GRID,
    "grid.linewidth": 0.5,
    "grid.linestyle": "-",
    "xtick.color": INK2,
    "ytick.color": INK2,
    "xtick.labelsize": 7,
    "ytick.labelsize": 7,
    "xtick.major.width": 0.6,
    "ytick.major.width": 0.6,
    "xtick.major.size": 2.5,
    "ytick.major.size": 2.5,
    "text.color": INK,
    "legend.frameon": False,
    "legend.fontsize": 7.5,
    "lines.linewidth": 1.5,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
    "figure.facecolor": "white",
    "axes.facecolor": "white",
})

LABEL = {  # results-file label -> short plot label
    "Basel Capital Ratio (%)": "Basel capital ratio (pp)",
    "Leverage (liabilities/assets)": "Leverage",
    "Return on Assets": "Return on assets",
    "Cost-to-Income Ratio": "Cost-to-income",
    "Credit Portfolio / Assets": "Credit / assets",
    "Provisioning (provisions/gross credit)": "Provisioning ratio",
    "Net Interest Margin": "Intermediation margin",
    "Funding Ratio (captacoes/assets)": "Funding ratio",
    "Return on assets volatility": "Return volatility",
    "Z-score": "Z-score",
}
SHORT = {  # panel titles in the ladder figure
    "Basel Capital Ratio (%)": "Capital (pp)",
    "Leverage (liabilities/assets)": "Leverage",
    "Return on Assets": "ROA",
    "Cost-to-Income Ratio": "Cost-to-income",
    "Credit Portfolio / Assets": "Credit / assets",
    "Provisioning (provisions/gross credit)": "Provisioning",
    "Net Interest Margin": "Margin",
    "Funding Ratio (captacoes/assets)": "Funding",
    "Return on assets volatility": "ROA volatility",
    "Z-score": "Z-score",
}
KEY = {v: k for k, v in P.OUTCOMES.items()}   # results-file label -> panel column


def save(fig, name):
    fig.savefig(FIG / name)
    plt.close(fig)
    print(f"  figures/{name}")


def ygrid(ax):
    ax.yaxis.grid(True)
    ax.set_axisbelow(True)


def xgrid(ax):
    ax.xaxis.grid(True)
    ax.set_axisbelow(True)


# ------------------------------------------------------------------ data
def analysis_sample(panel, peer_set="banks"):
    """The primary analysis sample exactly as run_pipeline builds it: singular
    cooperatives against the peer set, full-methodology quarters, winsorised 1/99."""
    sub, _, _ = P.select_sample(panel, "singular", "cti_new", "roa_ann", "nim_ann", peer_set)
    l2 = sub[sub["full_method"] == 1].copy()
    l2, _ = P.winsorize(l2, list(P.OUTCOMES))
    return sub, l2


def gate_d_text():
    return (RES / "gate_d_distribution.txt").read_text(encoding="utf-8")


def quantile_rows(txt):
    """Section A of gate_d: nine quantile coefficients and the OLS coefficient per outcome."""
    out, lines = {}, txt.splitlines()
    for i, line in enumerate(lines):
        name = line.strip()
        if name in KEY and i + 2 < len(lines) and lines[i + 1].strip().startswith("q10"):
            vals = [float(x) for x in lines[i + 2].split()]
            m = re.search(r"mean of q20-q80 is (-?[\d.]+), (-?\d+)%", lines[i + 3])
            out[name] = {"q": vals[:9], "ols": vals[9],
                         "mid": float(m.group(1)) if m else np.nan,
                         "share": int(m.group(2)) / 100 if m else np.nan}
    return out


def quantile_ci(txt):
    out = {}
    block = txt.split("[QUANTILE_CI]")[1] if "[QUANTILE_CI]" in txt else ""
    for line in block.splitlines()[1:]:
        r = line.split("\t")
        if len(r) >= 5:
            try:
                out[(r[0], float(r[1]))] = (float(r[2]), float(r[3]), float(r[4]))
            except ValueError:
                continue
    return out


def dispersion_rows(txt):
    """Section B of gate_d: residual sd and IQR by group at equal size."""
    out = {}
    num = r"(-?[\d.]+)"
    for line in txt.splitlines():
        m = re.match(r"^(\S.*?)\s+" + r"\s+".join([num] * 6) + r"\s*$", line)
        if m and m.group(1) in KEY:
            v = [float(m.group(k)) for k in range(2, 8)]
            out[m.group(1)] = {"sd_ratio": v[2], "iqr_ratio": v[5]}
    return out


def share_above(txt, level=50):
    m = re.search(rf"share above\s+{level}%: cooperatives\s+([\d.]+)%, banks\s+([\d.]+)%", txt)
    return (float(m.group(1)), float(m.group(2))) if m else (np.nan, np.nan)


# ------------------------------------------------------------------ R3: figure 1
def fig_regulatory(panel):
    pf = panel.copy()
    pf["grp"] = np.where(pf["is_coop_any"] == 1, "coop", "noncoop")
    fig, ax = plt.subplots(1, 3, figsize=(TEXTWIDTH, 2.1))
    shares = {}
    for a, grp, c, title in [(ax[0], "coop", COOP, "(a) Cooperatives"),
                             (ax[1], "noncoop", BANK, "(b) Non-cooperatives")]:
        m = (pf[pf.grp == grp].groupby(["year_q", "full_method"])["codigo"].nunique()
             .unstack(fill_value=0))
        x = m.index.to_timestamp()
        simp, full = m.get(0, 0 * m.sum(axis=1)), m.get(1, 0 * m.sum(axis=1))
        a.fill_between(x, 0, simp, color=AXIS, lw=0, label="Simplified")
        a.fill_between(x, simp, simp + full, color=c, alpha=0.85, lw=0, label="Full")
        a.set_title(title)
        a.set_ylim(0, None)
        ygrid(a)
        mid = len(x) // 2
        a.text(x[mid], float(simp.iloc[mid]) / 2, "Simplified", ha="center", va="center",
               fontsize=7, color=INK)
        a.text(x[mid], float(simp.iloc[mid]) + float(full.iloc[mid]) / 2, "Full",
               ha="center", va="center", fontsize=7, color="white")
        shares[grp] = full / (simp + full) * 100
        a.set_xlim(x.min(), x.max())
    ax[0].set_ylabel("Number of institutions")
    for grp, c, lab in [("coop", COOP, "Cooperatives"), ("noncoop", BANK, "Non-cooperatives")]:
        s = shares[grp]
        ax[2].plot(s.index.to_timestamp(), s.values, color=c)
        ax[2].text(s.index[2].to_timestamp(), 66 if grp == "noncoop" else s.values[2] + 6,
                   lab, ha="left", va="bottom", fontsize=7, color=INK2)
    ax[2].set_title("(c) Share under full method.")
    ax[2].set_ylabel("Percent")
    ax[2].set_ylim(0, 105)
    ygrid(ax[2])
    for a in ax:
        a.tick_params(axis="x", rotation=0)
        a.xaxis.set_major_locator(matplotlib.dates.YearLocator(2))
        a.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%Y"))
    fig.tight_layout(w_pad=1.2)
    save(fig, "fig5_regulatory.png")


# ------------------------------------------------------------------ R3: figure 2
def fig_overlap(l2):
    cq = l2.loc[l2.is_coop == 1, "log_assets"].quantile([0.05, 0.95])
    nq = l2.loc[l2.is_coop == 0, "log_assets"].quantile([0.05, 0.95])
    lo, hi = max(cq.iloc[0], nq.iloc[0]), min(cq.iloc[1], nq.iloc[1])
    fig, ax = plt.subplots(figsize=(TEXTWIDTH * 0.78, 2.4))
    ax.axvspan(lo, hi, color=BAND, lw=0)
    grid = np.linspace(l2["log_assets"].min() - 1, l2["log_assets"].max() + 1, 400)
    for v, lab, c in [(1, "Cooperatives", COOP), (0, "Banks", BANK)]:
        s = l2.loc[l2.is_coop == v, "log_assets"].dropna()
        from scipy.stats import gaussian_kde
        d = gaussian_kde(s)(grid)
        ax.plot(grid, d, color=c, label=f"{lab} ({l2.loc[l2.is_coop == v, 'codigo'].nunique()})")
    ax.text(lo + 0.1, ax.get_ylim()[1] * 0.97, "common\nsupport", ha="left", va="top",
            fontsize=7, color=INK2)
    ax.set_xlabel("Log total assets (thousands of reais)")
    ax.set_ylabel("Density")
    ax.set_ylim(0, None)
    ax.legend(loc="upper right")
    ygrid(ax)
    fig.tight_layout()
    save(fig, "fig8_overlap.png")
    return lo, hi


# ------------------------------------------------------------------ N2: broad group
def fig_broad_group(panel):
    sub, l2 = analysis_sample(panel, peer_set="all")
    fm = sub[sub["full_method"] == 1]
    med = fm.groupby("codigo").agg(credit=("credit_ratio", "median"),
                                   funding=("deposit_ratio", "median"),
                                   is_coop=("is_coop", "first"),
                                   tcb=("tcb_stable", "first"))
    med["grp"] = np.where(med.is_coop == 1, "coop",
                          np.where(med.tcb.astype(str).isin(P.PEER_SETS["banks"]), "bank", "other"))
    zero = med[(med.is_coop == 0) & (med.credit == 0) & (med.funding == 0)]
    n_zero, n_non = len(zero), int((med.is_coop == 0).sum())
    fig, ax = plt.subplots(figsize=(TEXTWIDTH * 0.7, 3.0))
    cap = 1.2
    for grp, c, lab in [("other", OTHER, "Other non-cooperatives"), ("bank", BANK, "Banks"),
                        ("coop", COOP, "Cooperatives")]:
        m = med[(med.grp == grp) & ~med.index.isin(zero.index)]
        ax.scatter(m.credit.clip(upper=cap), m.funding.clip(upper=cap), s=14, color=c,
                   alpha=0.75, lw=0.5, edgecolor="white",
                   label=f"{lab} ({int((med.grp == grp).sum())})")
    ax.scatter([0], [0], s=90, facecolor=OTHER, edgecolor="white", lw=1.2, zorder=3)
    ax.annotate(f"{n_zero} institutions with a median of zero\ncredit and zero funding",
                (0, 0), xytext=(0.14, 0.08), textcoords="data", fontsize=7, color=INK,
                bbox=dict(boxstyle="round,pad=0.25", fc="white", ec=AXIS, lw=0.5),
                arrowprops=dict(arrowstyle="-", color=INK2, lw=0.6), zorder=5)
    ax.set_xlim(-0.04, cap + 0.02)
    ax.set_ylim(-0.04, cap + 0.02)
    ax.set_xlabel("Credit portfolio / total assets (institution median)")
    ax.set_ylabel("Funds raised / total assets (institution median)")
    ax.legend(loc="upper left", handletextpad=0.2)
    xgrid(ax); ygrid(ax)
    fig.tight_layout()
    save(fig, "fig14_broad_group.png")
    return n_zero, n_non


# ------------------------------------------------------------------ R1: figure 3
def fig_capital(l2, txt):
    q = quantile_rows(txt)["Basel Capital Ratio (%)"]
    ci = quantile_ci(txt)
    qs = [10, 20, 30, 40, 50, 60, 70, 80, 90]
    band = capital_band()
    fig, ax = plt.subplots(1, 2, figsize=(TEXTWIDTH, 2.7))
    a = ax[0]
    floor = -38.0                              # the q90 interval runs past this; marked below
    a.axhline(0, color=AXIS, lw=0.8)
    a.axhline(q["ols"], color=MUTED, lw=1)
    a.text(10, q["ols"] - 1.0, "conditional mean", fontsize=7, color=INK2, ha="left",
           va="top")
    if band:
        bq = sorted(band)
        a.fill_between([100 * x for x in bq], [band[x][1] for x in bq],
                       [band[x][2] for x in bq], color=COOP, alpha=0.18, lw=0)
    else:                                      # fall back to the five t7 intervals
        for qq in (10, 25, 50, 75, 90):
            c = ci.get(("Basel Capital Ratio (%)", qq / 100))
            if c:
                a.plot([qq, qq], [c[1], c[2]], color=COOP, lw=1.2, alpha=0.55)
    a.plot(qs, q["q"], color=COOP, marker="o", ms=4, mec="white", mew=0.8, zorder=3)
    # where the coefficient changes sign, by linear interpolation between quantiles
    cross = next((qs[i] + (qs[i + 1] - qs[i]) * q["q"][i] / (q["q"][i] - q["q"][i + 1])
                  for i in range(len(qs) - 1) if q["q"][i] > 0 >= q["q"][i + 1]), None)
    if cross:
        a.annotate(f"positive below about\nthe {round(cross / 10) * 10}th percentile",
                   (cross, 0), xytext=(cross + 4, 5.5), fontsize=7, color=INK, va="bottom",
                   arrowprops=dict(arrowstyle="-", color=INK2, lw=0.6))
    lo90 = band.get(0.9, (None, None))[1] if band else None
    if lo90 is not None and lo90 < floor:
        a.annotate(f"band to {lo90:.0f}".replace("-", "−"), (91.5, floor),
                   xytext=(70, floor + 3), ha="right", va="center", fontsize=6.5,
                   color=INK2, arrowprops=dict(arrowstyle="->", color=INK2, lw=0.6))
    a.set_ylim(floor, 12)
    a.set_xticks(qs)
    a.set_xlim(7, 93)
    a.set_xlabel("Quantile of the Basel ratio distribution")
    a.set_ylabel("Cooperative coefficient (pp)")
    a.set_title("(a) Differential across the distribution")
    ygrid(a)

    b = ax[1]
    c = l2.loc[l2.is_coop == 1, "basileia_num"].dropna()
    k = l2.loc[l2.is_coop == 0, "basileia_num"].dropna()
    lo, hi = max(1.0, min(c.min(), k.min()) * 0.9), max(c.max(), k.max()) * 1.1
    bins = np.logspace(np.log10(lo), np.log10(hi), 46)
    for s, col, lab in [(k, BANK, "Banks"), (c, COOP, "Cooperatives")]:
        w = np.full(len(s), 100.0 / len(s))     # bar height: percent of the group's quarters
        b.hist(s, bins=bins, weights=w, color=col, alpha=0.25, lw=0)
        b.hist(s, bins=bins, weights=w, histtype="step", color=col, lw=1.2, label=lab)
    b.set_xscale("log")
    ticks = [t for t in (10, 20, 50, 100, 200, 500, 1000) if lo <= t <= hi]
    b.set_xticks(ticks)
    b.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:g}"))
    b.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    sc50, sb50 = share_above(txt, 50)
    sc100, sb100 = share_above(txt, 100)
    b.axvline(50, color=INK2, lw=0.8)
    b.axvline(100, color=INK2, lw=0.8)
    top = b.get_ylim()[1]
    b.text(53, top * 0.62, f"above 50%\nbanks {sb50:.0f}%\ncoops {sc50:.0f}%",
           fontsize=6.5, color=INK, va="top")
    b.text(106, top * 0.30, f"above 100%\nbanks {sb100:.1f}%\ncoops {sc100:.1f}%",
           fontsize=6.5, color=INK, va="top")
    b.set_xlabel("Basel capital ratio (%), log scale")
    b.set_ylabel("Percent of quarters")
    b.set_title("(b) The two distributions")
    b.text(27.5, top * 0.78, "Cooperatives", fontsize=7, color=COOP, fontweight="bold")
    b.text(9.3, top * 0.82, "Banks", fontsize=7, color=BANK, fontweight="bold")
    ygrid(b)
    fig.tight_layout(w_pad=1.5)
    save(fig, "fig12_capital_quantiles.png")
    # consistency check against the text
    chk = (100 * (k > 50).mean(), 100 * (c > 50).mean())
    print(f"    share above 50% recomputed: banks {chk[0]:.1f}, cooperatives {chk[1]:.1f}")
    if cross:
        print(f"    capital coefficient crosses zero at about q{cross:.1f}")


def capital_band():
    """Nine-quantile bootstrap band for the capital coefficient (gate_d --capital-ci)."""
    path = RES / "capital_quantile_ci.txt"
    if not path.exists():
        return {}
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        r = line.split("\t")
        if len(r) == 5 and not line.startswith(("[", "#")):
            out[float(r[0])] = (float(r[1]), float(r[2]), float(r[3]))
    return out


# ------------------------------------------------------------------ slide: profile
def slide_profile(l2):
    """Presentation asset, not in the paper: every outcome against banks, controlled
    specification, in standard deviations of the outcome, with its tier."""
    c = MT.coefs(MT.parse(MT.FILES["primary"]))
    tiers = MT.tiers(MT.parse(MT.FILES["primary"]))
    inst, _, _ = P.collapse_stability(l2)
    sd = {k: l2[KEY[k]].std() for k, _ in MT.ORDER}
    sd["Return on assets volatility"] = inst["roa_vol"].std()
    sd["Z-score"] = inst["zscore"].std()
    order = ["Credit Portfolio / Assets", "Return on Assets", "Return on assets volatility",
             "Z-score", "Cost-to-Income Ratio", "Basel Capital Ratio (%)",
             "Leverage (liabilities/assets)", "Provisioning (provisions/gross credit)",
             "Net Interest Margin", "Funding Ratio (captacoes/assets)"]
    style = {"stable": dict(mfc=COOP, mec=COOP), "stable in sign": dict(mfc="white", mec=COOP),
             "null": dict(mfc="white", mec=MUTED)}
    with plt.rc_context({"font.size": 12, "xtick.labelsize": 11, "ytick.labelsize": 12,
                         "axes.labelsize": 12, "legend.fontsize": 11}):
        fig, ax = plt.subplots(figsize=(10, 5.6))
        ax.axvline(0, color=INK2, lw=1)
        y = np.arange(len(order))[::-1]
        for yy, k in zip(y, order):
            v = c[k]["ctrl"]
            stab = k in MT.STAB_LABELS
            lo, hi = (v["hc_lo"], v["hc_hi"]) if stab else (v["cl_lo"], v["cl_hi"])
            t = tiers.get(k, "null")
            col = MUTED if t == "null" else COOP
            ax.plot([lo / sd[k], hi / sd[k]], [yy, yy], color=col, lw=2.2,
                    solid_capstyle="round", alpha=0.8)
            ax.plot(v["coef"] / sd[k], yy, "o", ms=11, mew=2.2, zorder=3, **style[t])
        ax.set_yticks(y)
        ax.set_yticklabels([LABEL[k] for k in order])
        ax.set_xlabel("Cooperatives minus banks, in standard deviations of the outcome")
        for t, lab in [("stable", "stable"), ("stable in sign", "stable in sign"),
                       ("null", "null: not significant in all four designs")]:
            ax.plot([], [], "o", ms=10, mew=2, label=lab, **style[t])
        ax.legend(loc="upper left", frameon=False)
        xgrid(ax)
        fig.tight_layout()
        FIG.joinpath("slides").mkdir(exist_ok=True)
        fig.savefig(FIG / "slides" / "profile.png", dpi=200)
        plt.close(fig)
        print("  figures/slides/profile.png")


# ------------------------------------------------------------------ R2: figure 4
def fig_series(l2):
    outs = [("basileia_num", "Basel capital ratio (%)"), ("leverage", "Leverage"),
            ("roa", "Return on assets (annualised)"), ("cti", "Cost-to-income ratio")]
    fig, axes = plt.subplots(2, 2, figsize=(TEXTWIDTH, 4.2), sharex=True)
    for a, (o, title) in zip(axes.flatten(), outs):
        for v, col, lab in [(0, BANK, "Banks"), (1, COOP, "Cooperatives")]:
            g = l2[l2.is_coop == v].groupby("year_q")[o]
            x = g.median().index.to_timestamp()
            a.fill_between(x, g.quantile(0.25).values, g.quantile(0.75).values, color=col,
                           alpha=0.16, lw=0)
            a.plot(x, g.median().values, color=col, label=lab)
        a.set_title(title)
        ygrid(a)
        a.xaxis.set_major_locator(matplotlib.dates.YearLocator(2))
        a.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%Y"))
    axes[0, 0].legend(loc="upper right")
    fig.tight_layout(h_pad=1.2, w_pad=1.5)
    save(fig, "fig11_stable.png")


# ------------------------------------------------------------------ N1: the ladder
def fig_ladder():
    load = lambda k: MT.parse(MT.FILES[k]) if MT.FILES[k].exists() else None
    srcs = [("All non-cooperatives", load("broad"), "ctrl"),
            ("Banks", load("primary"), "ctrl"),
            ("Banks, within region", load("within"), "cem"),
            ("Commercial", load("commercial"), "ctrl"),
            ("Structural", load("structural"), "ctrl")]
    srcs = [(n, MT.coefs(s), sp) for n, s, sp in srcs if s is not None]
    keys = [k for k, _ in MT.ORDER + MT.STAB_ORDER]
    fig, axes = plt.subplots(2, 5, figsize=(TEXTWIDTH, 3.6), sharey=True)
    ypos = np.arange(len(srcs))[::-1]
    for a, key in zip(axes.flatten(), keys):
        stab = key in MT.STAB_LABELS
        a.axvline(0, color=AXIS, lw=0.8)
        for y, (name, c, sp) in zip(ypos, srcs):
            v = c.get(key, {}).get(sp)
            if not v:
                continue
            lo, hi = (v["hc_lo"], v["hc_hi"]) if stab else (v["cl_lo"], v["cl_hi"])
            p = v["hc_p"] if stab else v["p"]
            a.plot([lo, hi], [y, y], color=COOP, lw=1.2, solid_capstyle="round")
            a.plot(v["coef"], y, "o", ms=4.2, mew=1.1, mec=COOP,
                   mfc=COOP if p < 0.05 else "white", zorder=3)
            if name == "Banks":
                a.axhspan(y - 0.42, y + 0.42, color=BAND, lw=0, zorder=0)
        a.set_title(SHORT[key], fontsize=7.5, loc="center")
        a.tick_params(axis="x", labelsize=6.5)
        a.xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(nbins=2, min_n_ticks=2))
        a.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:g}"))
        xgrid(a)
    axes[0, 0].set_yticks(ypos)
    axes[0, 0].set_yticklabels([n for n, *_ in srcs])
    axes[1, 0].set_yticklabels([n for n, *_ in srcs])
    for a in axes.flatten():
        a.set_ylim(-0.6, len(srcs) - 0.4)
    fig.tight_layout(w_pad=0.6, h_pad=1.0)
    save(fig, "fig13_ladder.png")


# ------------------------------------------------------------------ N3: quantile profiles
def fig_profiles(txt):
    rows = quantile_rows(txt)
    tiers = MT.tiers(MT.parse(MT.FILES["primary"]))
    qs = [10, 20, 30, 40, 50, 60, 70, 80, 90]
    order = ["Credit Portfolio / Assets", "Return on Assets", "Leverage (liabilities/assets)",
             "Cost-to-Income Ratio", "Basel Capital Ratio (%)"]
    fig, ax = plt.subplots(figsize=(TEXTWIDTH * 0.8, 3.0))
    ax.axvspan(20, 80, color=BAND, lw=0)
    ax.axhline(1, color=INK2, lw=0.8)
    ax.axhline(0, color=AXIS, lw=0.8)
    ax.text(10.5, 0.95, "equal to the\nconditional mean", fontsize=6.5, color=INK2, va="top")
    ends = []
    for name in order:
        r = rows[name]
        rel = np.array(r["q"]) / r["ols"]
        stable = tiers.get(name) == "stable"
        col = INK if stable else MUTED
        ax.plot(qs, rel, color=col, lw=1.6 if stable else 1.2,
                marker="o", ms=3, mec="white", mew=0.5)
        ends.append([rel[-1], f"{LABEL[name]} ({r['share']:.0%})", col])
    ends.sort(key=lambda e: e[0])
    for i in range(1, len(ends)):          # keep end labels at least 0.16 apart
        ends[i][0] = max(ends[i][0], ends[i - 1][0] + 0.16)
    for y, lab, col in ends:
        ax.text(91.5, y, lab, va="center", fontsize=6.8, color=col)
    ax.set_xticks(qs)
    ax.set_xlim(8, 92)
    ax.set_xlabel("Quantile of the outcome distribution (shaded: 20th to 80th)")
    ax.set_ylabel("Quantile coefficient / conditional mean")
    ax.plot([], [], color=INK, label="stable")
    ax.plot([], [], color=MUTED, label="stable in sign")
    ax.legend(loc="lower left")
    ygrid(ax)
    fig.tight_layout()
    save(fig, "fig15_quantile_profiles.png")


# ------------------------------------------------------------------ N4: dispersion
def fig_dispersion(txt):
    rows = dispersion_rows(txt)
    names = [n for n in ["Basel Capital Ratio (%)", "Leverage (liabilities/assets)",
                         "Return on Assets", "Cost-to-Income Ratio",
                         "Credit Portfolio / Assets", "Provisioning (provisions/gross credit)"]
             if n in rows]
    y = np.arange(len(names))[::-1]
    fig, ax = plt.subplots(figsize=(TEXTWIDTH * 0.7, 2.4))
    ax.axvline(1, color=INK2, lw=0.8)
    ax.text(0.99, len(names) - 0.45, "equal dispersion", ha="right", fontsize=6.5, color=INK2)
    for yy, n in zip(y, names):
        r = rows[n]
        ax.plot([r["sd_ratio"], r["iqr_ratio"]], [yy, yy], color=AXIS, lw=1, zorder=1)
    ax.scatter([rows[n]["sd_ratio"] for n in names], y, s=26, color=INK, zorder=3,
               label="standard deviation")
    ax.scatter([rows[n]["iqr_ratio"] for n in names], y, s=26, facecolor="white",
               edgecolor=INK, lw=1.1, zorder=3, label="interquartile range")
    ax.set_yticks(y)
    ax.set_yticklabels([LABEL[n] for n in names])
    ax.set_xlim(0, 1.1)
    ax.set_xlabel("Cooperatives / banks, residualised on size and quarter")
    ax.legend(loc="lower right")
    xgrid(ax)
    fig.tight_layout()
    save(fig, "fig16_dispersion.png")


# ------------------------------------------------------------------ N5: de-cumulation
def fig_decumulation(l2_raw):
    d = l2_raw.copy()
    d["raw"] = 4 * d["roa_legacy"]          # the income field read as a quarterly flow
    g = d.groupby("year_q")
    x = g.size().index.to_timestamp()
    fig, ax = plt.subplots(figsize=(TEXTWIDTH * 0.75, 2.4))
    ax.plot(x, g["raw"].median().values, color=MUTED, lw=1.2, marker="o", ms=2.5)
    ax.plot(x, g["roa_ann"].median().values, color=INK, lw=1.6)
    ax.text(x[10], 0.054, "IF.data field read as a quarterly flow", fontsize=7, color=MUTED,
            va="bottom")
    ax.text(x[10], 0.011, "de-cumulated within the semester", fontsize=7, color=INK, va="top")
    ax.set_ylabel("Median return on assets, annualised")
    ax.set_ylim(0, 0.06)
    ygrid(ax)
    ax.xaxis.set_major_locator(matplotlib.dates.YearLocator(1))
    ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%Y"))
    fig.tight_layout()
    save(fig, "fig17_decumulation.png")


# ------------------------------------------------------------------ N6: specifications
def fig_specs(l2):
    c = MT.coefs(MT.parse(MT.FILES["primary"]))
    names = [k for k, _ in MT.ORDER]
    specs = [("raw", "Raw difference", "o", "white"), ("ctrl", "Controls", "o", INK),
             ("cem", "Matched (CEM)", "s", INK), ("trim", "Common support", "^", INK)]
    fig, ax = plt.subplots(figsize=(TEXTWIDTH * 0.8, 3.4))
    ax.axvline(0, color=INK2, lw=0.8)
    base = np.arange(len(names))[::-1]
    for j, (sp, lab, mk, fc) in enumerate(specs):
        off = 0.27 - j * 0.18
        for y, n in zip(base, names):
            v = c.get(n, {}).get(sp)
            sd = l2[KEY[n]].std()
            if not v or not sd:
                continue
            ax.plot([v["cl_lo"] / sd, v["cl_hi"] / sd], [y + off, y + off], color=AXIS, lw=1)
            ax.plot(v["coef"] / sd, y + off, mk, ms=4, mfc=fc, mec=INK, mew=0.9,
                    label=lab if y == base[0] else None, zorder=3)
    ax.set_yticks(base)
    ax.set_yticklabels([LABEL[n] for n in names])
    ax.set_xlabel("Cooperative coefficient in standard deviations of the outcome")
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=4, handletextpad=0.2,
              columnspacing=1.0)
    xgrid(ax)
    fig.tight_layout()
    save(fig, "fig10_stability.png")


# ------------------------------------------------------------------ main
def main():
    print("building the panel (no regressions)...")
    panel, _, _ = P.build_panel()
    sub, l2 = analysis_sample(panel, "banks")
    txt = gate_d_text()
    print("writing figures:")
    fig_regulatory(panel)
    lo, hi = fig_overlap(l2)
    print(f"    common support [{lo:.2f}, {hi:.2f}]")
    n_zero, n_non = fig_broad_group(panel)
    print(f"    broad group: {n_zero} of {n_non} non-cooperatives at zero credit and zero funding")
    fig_capital(l2, txt)
    fig_series(l2)
    fig_ladder()
    fig_profiles(txt)
    fig_dispersion(txt)
    fig_decumulation(sub[sub["full_method"] == 1])
    fig_specs(l2)
    slide_profile(l2)


if __name__ == "__main__":
    main()
