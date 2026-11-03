"""Specifications slide, three candidate figures drawn from the analysis sample.

Reproduces columns (1) to (4) of tables/t2_main for the after-tax return (raw, size and
quarter controls, CEM on size quintile, common support) with paper.py's own
sample, weights and trimming, then draws:

    s_specs_A.png  size densities in panels 1, 3, 4; panel 2 as the regression view
    s_specs_B.png  all four panels as the regression view (outcome against size)
    s_specs_C.png  two rows: size densities above, regression view below
    s_specs_scatter.png  as C, with every institution-quarter plotted (the deck's
                   s_specs.png is this version)

Regression view: size-bin means of the outcome per group (dot area by weight) and the
fitted lines of the specification; the vertical distance between the lines is the
coefficient printed under the panel.

    uv run --no-project --with pandas,numpy,matplotlib,scipy,statsmodels,linearmodels,seaborn \
        python slides/make_spec_variants.py
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import gaussian_kde

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import make_figures as F   # noqa: E402
import paper as P          # noqa: E402

OUT = ROOT / "slides" / "figures"
COOP, BANK, DARK, GREY = "#2A78D6", "#EB6834", "#333333", "#666666"
plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 10, "axes.titlesize": 12.5,   # panel titles 7 pt on the slide
    "axes.titlecolor": DARK, "savefig.dpi": 250, "savefig.facecolor": "white",
})
TITLES = ["Naive\ncomparison", "Size and\nquarter controls", "Matched\non size",
          "Common\nsupport"]


def panel_title(ax, i):
    """Title centred on the panel; the specification number sits apart at the left,
    level with the first line, so it does not shift the centring."""
    ax.set_title(TITLES[i], loc="center", fontweight="normal")
    ax.set_title(f"({i + 1})\n", loc="left", color=GREY, fontweight="normal")   # level with the first line
TEXTS = ["Raw difference in means.",
         "Regression with log assets\nand quarter effects.",
         "Banks reweighted so each size\nquintile has the same mix.",
         "Only sizes where both groups exist:\n90% of cooperative quarters,\n48% of bank quarters."]
XLIM = (7.5, 22.5)
YLIM = (-1.5, 4.5)   # return axis; the share of quarters outside it goes in the footnote
BINS = np.arange(8, 23, 1.0)


# ------------------------------------------------------------------ the four specifications
def specifications():
    panel, _, _ = P.build_panel()
    _, l2 = F.analysis_sample(panel, "banks")
    d = l2[["codigo", "roa", "log_assets", "is_coop", "year_q"]].dropna(
        subset=["roa", "log_assets"]).copy()
    d["roa"] *= 100
    d["w"] = 1.0

    # CEM strata: size quintile of the institution's median log assets (the main
    # table's coarsening, "size_q5"; the within-region run adds macro-region)
    med_la = d.groupby("codigo")["log_assets"].median()
    d["size_bin"] = pd.qcut(d["codigo"].map(med_la), q=5, labels=False, duplicates="drop")
    snap = d.drop_duplicates("codigo")[["codigo", "is_coop", "size_bin"]].dropna()
    st = snap.groupby("size_bin")["is_coop"].agg(["sum", "count"])
    valid = st[(st["sum"] > 0) & (st["count"] - st["sum"] > 0)].index
    cem = d[d["codigo"].isin(snap[snap["size_bin"].isin(valid)]["codigo"])].copy()
    cem["w"] = cem["codigo"].map(P.cem_weights(
        cem.drop_duplicates("codigo")[["codigo", "is_coop", "size_bin"]], ["size_bin"]))

    # common support: 5th to 95th percentile overlap in log assets
    cq = d.loc[d.is_coop == 1, "log_assets"].quantile([0.05, 0.95])
    bq = d.loc[d.is_coop == 0, "log_assets"].quantile([0.05, 0.95])
    lo, hi = max(cq.iloc[0], bq.iloc[0]), min(cq.iloc[1], bq.iloc[1])
    trim = d[d["log_assets"].between(lo, hi)].copy()

    specs = []
    for frame, controls in [(d, False), (d, True), (cem, True), (trim, True)]:
        specs.append(fit(frame, controls))
    return d, cem, trim, (lo, hi), specs


def fit(frame, controls):
    """Weighted least squares of the after-tax return on the cooperative dummy, log
    assets and quarter effects (or the dummy alone). Returns the coefficient and the
    two fitted lines evaluated at the average quarter."""
    y = frame["roa"].to_numpy()
    w = frame["w"].to_numpy()
    cols = [np.ones(len(frame)), frame["is_coop"].to_numpy()]
    if controls:
        cols.append(frame["log_assets"].to_numpy())
        q = pd.get_dummies(frame["year_q"].astype(str), drop_first=True).to_numpy(float)
        cols.extend(q.T)
    X = np.column_stack(cols)
    sw = np.sqrt(w)
    b = np.linalg.lstsq(X * sw[:, None], y * sw, rcond=None)[0]
    coef, slope = b[1], (b[2] if controls else 0.0)
    # line through the weighted centroid, at the weighted average quarter
    ybar = np.average(y, weights=w)
    cbar = np.average(frame["is_coop"], weights=w)
    xbar = np.average(frame["log_assets"], weights=w)
    c0 = ybar - coef * cbar - slope * xbar
    return {"coef": coef, "slope": slope, "c0": c0}


# ------------------------------------------------------------------ panel drawers
def density_panel(ax, i, d, cem, support):
    grid = np.linspace(*XLIM, 500)
    kd = {v: gaussian_kde(d.loc[d.is_coop == v, "log_assets"])(grid) for v in (0, 1)}
    lo, hi = support
    if i == 3:
        ax.axvspan(lo, hi, color="#EFEFEF", zorder=0)
        m = (grid >= lo) & (grid <= hi)
        for v, c in [(1, COOP), (0, BANK)]:
            ax.plot(grid, kd[v], color=c, lw=1, ls="--", alpha=0.5)
            ax.fill_between(grid[m], kd[v][m], color=c, alpha=0.35)
    else:
        ax.fill_between(grid, kd[1], color=COOP, alpha=0.35)
        ax.plot(grid, kd[1], color=COOP, lw=2)
        if i == 2:
            b = cem[cem.is_coop == 0]
            kw = gaussian_kde(b["log_assets"], weights=b["w"])(grid)
            ax.plot(grid, kd[0], color=BANK, lw=1, ls="--", alpha=0.6)
            ax.fill_between(grid, kw, color=BANK, alpha=0.35)
            ax.plot(grid, kw, color=BANK, lw=2)
        else:
            ax.fill_between(grid, kd[0], color=BANK, alpha=0.35)
            ax.plot(grid, kd[0], color=BANK, lw=2)
    if i == 0:
        ax.text(15.4, kd[1].max() * 0.78, "cooperatives", color=COOP, ha="left", fontsize=9)
        ax.text(18.7, kd[0].max() * 0.55, "banks", color=BANK, ha="left", fontsize=9)
    ax.set_xlim(*XLIM)
    ax.set_ylim(0, max(kd[1].max(), kd[0].max()) * 1.18)
    ax.set_yticks([])
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    size_axis(ax)


def regression_panel(ax, i, d, cem, trim, support, spec, ylab=True, points="bins"):
    """points: "bins" for size-bin means (area by weight), "all" for every
    institution-quarter (panel 3: area by CEM weight; panel 4: outside support in grey)."""
    frame = [d, d, cem, trim][i]
    lo, hi = support
    if i == 3:
        ax.axvspan(lo, hi, color="#EFEFEF", zorder=0)
        if points == "all":
            o = d[~d["log_assets"].between(lo, hi)]
            ax.scatter(o.log_assets, o.roa, s=2.5, color="#BBBBBB", alpha=0.4, lw=0, zorder=1)
    for v, c in [(0, BANK), (1, COOP)]:
        g = frame[frame.is_coop == v]
        if points == "all":
            ax.scatter(g.log_assets, g.roa, s=np.clip(2 * g.w, 1, 16), color=c, alpha=0.18,
                       lw=0, zorder=3)
        else:
            cut = pd.cut(g["log_assets"], BINS)
            m = g.groupby(cut, observed=True).apply(
                lambda s: pd.Series({"x": np.average(s.log_assets, weights=s.w),
                                     "y": np.average(s.roa, weights=s.w), "n": s.w.sum()}),
                include_groups=False)
            m = m[m.n >= 20]
            ax.scatter(m.x, m.y, s=14 + m.n / 12, color=c, alpha=0.8, lw=0, zorder=3)
        xs = np.array([lo, hi]) if i == 3 else np.array([XLIM[0] + 1.5, XLIM[1] - 1.5])
        ax.plot(xs, spec["c0"] + spec["coef"] * v + spec["slope"] * xs, color=c, lw=2, zorder=2)
    # arrow near the end of the lines, clear of the dots; label on the open side
    x0, side = [(19.5, 1), (19.3, 1), (20.0, 1), (16.4, 1)][i]
    if spec["slope"] > 0:   # keep the arrow's top inside the axes on steep lines
        x0 = min(x0, (YLIM[1] - 0.25 - spec["coef"] - spec["c0"]) / spec["slope"])
    y0 = spec["c0"] + spec["slope"] * x0
    ax.annotate("", xy=(x0, y0 + spec["coef"]), xytext=(x0, y0),
                arrowprops=dict(arrowstyle="<->", color=DARK, lw=1.5), zorder=5)
    ax.text(x0 + 0.5 * side, y0 + spec["coef"] / 2, f"+{spec['coef']:.1f} pp", va="center",
            ha="left" if side > 0 else "right", fontsize=10, color=DARK, fontweight="bold",
            zorder=6, bbox=dict(fc="white", ec="none", alpha=0.85, pad=1.5))
    ax.set_xlim(*XLIM)
    ax.set_ylim(*YLIM)
    ax.set_yticks([0, 2, 4])
    ax.tick_params(length=0, colors=GREY, labelsize=8)
    if ylab:
        ax.set_ylabel("Return\non assets\nafter tax,\n%", color=GREY, fontsize=9,
                      rotation=0, ha="right", va="center", labelpad=8)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.spines["left"].set_color("#CCCCCC")
    size_axis(ax)


def size_axis(ax):
    ax.set_xticks([10, 15, 20])
    ax.tick_params(axis="x", length=0, colors=GREY, labelsize=8)
    ax.set_xlabel("log total assets", color=GREY, fontsize=9)
    ax.spines["bottom"].set_color("#CCCCCC")


def caption(fig, specs, note):
    fig.text(0.5, 0.02, note, ha="center", fontsize=10, color=GREY)


def footer_numbers(ax, i, spec, y_text, y_num):
    ax.text(0.5, y_text, TEXTS[i], transform=ax.transAxes, ha="center", va="top",
            fontsize=10, color=DARK)
    ax.text(0.5, y_num, f"+{spec['coef']:.1f} pp", transform=ax.transAxes, ha="center",
            va="top", fontsize=20, color=COOP, fontweight="bold")


NOTE = ("Size distributions of the analysis sample. Below each panel: cooperative return on "
        "assets after tax, above banks, pp of assets; all four significant at one percent.")
NOTE_S = ("Dots: every institution-quarter, {out} outside the return axis not drawn (panel 3: "
          "area by matching weight; panel 4: outside the support in grey). Lines: the fitted "
          "specification; their vertical distance is the cooperative differential, "
          "significant at one percent in all four.")
NOTE_B = ("Dots: size-bin means of the after-tax return, area by weight. Lines: the fitted "
          "specification; their vertical distance is the cooperative differential, "
          "significant at one percent in all four.")


def version_a(d, cem, trim, support, specs):
    fig, axes = plt.subplots(1, 4, figsize=(13, 4.2))
    for i, ax in enumerate(axes):
        if i == 1:
            regression_panel(ax, i, d, cem, trim, support, specs[i])
        else:
            density_panel(ax, i, d, cem, support)
        panel_title(ax, i)
        footer_numbers(ax, i, specs[i], -0.3, -0.7)
    caption(fig, specs, NOTE)
    fig.tight_layout(rect=(0, 0.12, 1, 1))
    fig.subplots_adjust(bottom=0.44, wspace=0.3)
    fig.savefig(OUT / "s_specs_A.png")
    plt.close(fig)


def version_b(d, cem, trim, support, specs):
    fig, axes = plt.subplots(1, 4, figsize=(13, 4.2), sharey=True)
    for i, ax in enumerate(axes):
        regression_panel(ax, i, d, cem, trim, support, specs[i], ylab=(i == 0))
        panel_title(ax, i)
        ax.text(0.5, -0.3, TEXTS[i], transform=ax.transAxes, ha="center", va="top",
                fontsize=10, color=DARK)
    caption(fig, specs, NOTE_B)
    fig.tight_layout(rect=(0, 0.1, 1, 1))
    fig.subplots_adjust(bottom=0.36, wspace=0.15)
    fig.savefig(OUT / "s_specs_B.png")
    plt.close(fig)


def version_c(d, cem, trim, support, specs, points="bins", name="s_specs_C.png"):
    """Slide-proportioned (fills a 16:9 frame under the title); the panel descriptions
    and the footnote are typeset on the slide itself, see deck.tex."""
    fig, axes = plt.subplots(2, 4, figsize=(10, 4.5), sharex=True,
                             gridspec_kw={"height_ratios": [1, 1.5]})
    for i in range(4):
        density_panel(axes[0, i], i, d, cem, support)
        panel_title(axes[0, i], i)
        axes[0, i].set_xlabel("")
        regression_panel(axes[1, i], i, d, cem, trim, support, specs[i], ylab=(i == 0),
                         points=points)
    axes[0, 0].set_ylabel("Size\ndistribution", color=GREY, fontsize=9, rotation=0,
                          ha="right", va="center", labelpad=8)
    out = 100 * (~d["roa"].between(*YLIM)).mean()
    print(f"  share of quarters outside the return axis: {out:.0f} percent")
    fig.tight_layout()
    fig.subplots_adjust(hspace=0.22, wspace=0.28)
    fig.savefig(OUT / name)
    if name == "s_specs_scatter.png":   # the deck's figure
        fig.savefig(OUT / "s_specs.png")
    plt.close(fig)


def main():
    d, cem, trim, support, specs = specifications()
    print("common support [%.2f, %.2f]" % support)
    for k, (t, s) in enumerate(zip(TITLES, specs), 1):
        print(f"  ({k}) {t.replace(chr(10), ' ')}: +{s['coef']:.2f} pp (slope {s['slope']:.3f})")
    version_a(d, cem, trim, support, specs)
    version_b(d, cem, trim, support, specs)
    version_c(d, cem, trim, support, specs)
    version_c(d, cem, trim, support, specs, points="all", name="s_specs_scatter.png")
    print("wrote s_specs_A/B/C.png and s_specs_scatter.png")


if __name__ == "__main__":
    main()
