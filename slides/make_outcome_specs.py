"""Specifications figure for each stable outcome, in the style of slides/figures/s_specs.png.

The top row (size distributions under each specification) is the same for every outcome.
The bottom row plots the outcome against size with the fitted lines of each
specification; the arrow is the cooperative coefficient, reproduced from the data and
matching tables/t2_main:

    credit   credit portfolio / assets, institution-quarters, as the after-tax return
    vol      return volatility, one row per institution (paper.collapse_stability)
    z        z-score, one row per institution

The two stability outcomes follow paper.stability_estimates: no quarter effects (the unit
is the institution), mean log assets as the size control, the CEM weights of the panel
match per institution, and the common-support band on mean log assets.

    uv run --no-project --with pandas,numpy,matplotlib,scipy,statsmodels,linearmodels,seaborn \
        python slides/make_outcome_specs.py
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "slides"))
sys.path.insert(0, str(ROOT))
import make_spec_variants as S   # noqa: E402  (panel style, sample, CEM and support)
import paper as P                # noqa: E402

OUT = ROOT / "slides" / "figures"
PANEL_TITLES = {"quarter": S.TITLES,
                "institution": ["Naive\ncomparison", "Size\ncontrols", "Match\non size",
                                "Common\nsupport"]}

# key, column, scale, level, y label, y limits, y ticks, unit after the coefficient
OUTCOMES = [
    ("credit", "credit_ratio", 100, "quarter", "credit portfolio,\n% of assets",
     (0, 100), [0, 50, 100], " pp"),
    ("vol", "roa_vol", 100, "institution", "return volatility,\npp a year",
     (0, 6), [0, 2, 4, 6], " pp"),
    ("z", "zscore", 1, "institution", "z-score", (0, 50), [0, 25, 50], ""),
]


def frames(col, scale, level, d, cem, support, l2):
    """The four estimation frames for one outcome, with columns y, log_assets, is_coop,
    w and (quarter level) year_q."""
    lo, hi = support
    if level == "quarter":
        base = l2[["codigo", col, "log_assets", "is_coop", "year_q"]].dropna(subset=[col, "log_assets"])
        base = base.rename(columns={col: "y"}).assign(y=lambda f: f.y * scale, w=1.0)
        cw = cem.drop_duplicates("codigo").set_index("codigo")["w"]
        fc = base[base.codigo.isin(cw.index)].assign(w=lambda f: f.codigo.map(cw))
        ft = base[base.log_assets.between(lo, hi)]
        return [base, base, fc, ft]
    inst, _, _ = P.collapse_stability(l2)
    base = inst[["codigo", col, "log_assets", "is_coop"]].dropna().rename(columns={col: "y"})
    base = base.assign(y=lambda f: f.y * scale, w=1.0)
    cw = cem.drop_duplicates("codigo").set_index("codigo")["w"]   # per-institution weight
    fc = base[base.codigo.isin(cw.index)].assign(w=lambda f: f.codigo.map(cw))
    ft = base[base.log_assets.between(lo, hi)]
    return [base, base, fc, ft]


def fit(frame, controls, quarter):
    y, w = frame["y"].to_numpy(), frame["w"].to_numpy()
    cols = [np.ones(len(frame)), frame["is_coop"].to_numpy()]
    if controls:
        cols.append(frame["log_assets"].to_numpy())
        if quarter:
            cols.extend(pd.get_dummies(frame["year_q"].astype(str), drop_first=True)
                        .to_numpy(float).T)
    X = np.column_stack(cols)
    sw = np.sqrt(w)
    b = np.linalg.lstsq(X * sw[:, None], y * sw, rcond=None)[0]
    coef, slope = b[1], (b[2] if controls else 0.0)
    c0 = (np.average(y, weights=w) - coef * np.average(frame["is_coop"], weights=w)
          - slope * np.average(frame["log_assets"], weights=w))
    return {"coef": coef, "slope": slope, "c0": c0}


def arrow_x(i, spec, ylim):
    """Near the right end of the lines, moved left until both ends sit inside the axes."""
    lo, hi = ylim
    m = 0.06 * (hi - lo)
    start = [17.6, 17.6, 18.2, 16.2][i]   # room for labels like "+16.5 pp" before the next panel
    for x in np.linspace(start, S.XLIM[0] + 2, 300):
        a = spec["c0"] + spec["slope"] * x
        if lo + m <= min(a, a + spec["coef"]) and max(a, a + spec["coef"]) <= hi - m:
            return x
    return start


def regression_panel(ax, i, fr, base, support, spec, cfg, level, ylab):
    _, _, _, _, ylabel, ylim, yticks, unit = cfg
    lo, hi = support
    big = level == "institution"
    if i == 3:
        ax.axvspan(lo, hi, color="#EFEFEF", zorder=0)
        o = base[~base.log_assets.between(lo, hi)]
        ax.scatter(o.log_assets, o.y, s=14 if big else 2.5, color="#BBBBBB",
                   alpha=0.6 if big else 0.4, lw=0, zorder=1)
    x0 = arrow_x(i, spec, ylim)
    for v, c in [(0, S.BANK), (1, S.COOP)]:
        g = fr[fr.is_coop == v]
        size = np.clip((14 if big else 2) * g.w, 4 if big else 1, 60 if big else 16)
        ax.scatter(g.log_assets, g.y, s=size, color=c, alpha=0.55 if big else 0.18, lw=0, zorder=3)
        # lines end at the arrow, so the label sits in open space past their ends
        xs = np.array([lo, hi]) if i == 3 else np.array([S.XLIM[0] + 1.5, x0])
        ax.plot(xs, spec["c0"] + spec["coef"] * v + spec["slope"] * xs, color=c, lw=2, zorder=2)
    y0 = spec["c0"] + spec["slope"] * x0
    ax.annotate("", xy=(x0, y0 + spec["coef"]), xytext=(x0, y0),
                arrowprops=dict(arrowstyle="<->", color=S.DARK, lw=1.5, mutation_scale=9,
                                shrinkA=0, shrinkB=0), zorder=5)
    label = f"{spec['coef']:+.1f}{unit}".replace("-", "\u2212")
    ax.text(x0 + 0.4, y0 + spec["coef"] / 2, label, va="center", ha="left",
            fontsize=10, color=S.DARK, fontweight="bold", zorder=6,
            bbox=dict(fc="white", ec="none", alpha=0.85, pad=1.5))
    ax.set_xlim(*S.XLIM)
    ax.set_ylim(*ylim)
    ax.set_yticks(yticks)
    ax.tick_params(length=0, colors=S.GREY, labelsize=8)
    if ylab:
        ax.set_ylabel(ylabel, color=S.GREY, fontsize=9)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.spines["left"].set_color("#CCCCCC")
    S.size_axis(ax)


def main():
    panel, _, _ = P.build_panel()
    import make_figures as F
    _, l2 = F.analysis_sample(panel, "banks")
    d, cem, trim, support, _ = S.specifications()
    for cfg in OUTCOMES:
        key, col, scale, level = cfg[:4]
        frs = frames(col, scale, level, d, cem, support, l2)
        specs = [fit(f, c, level == "quarter") for f, c in zip(frs, [False, True, True, True])]
        S.TITLES[:] = PANEL_TITLES[level]
        fig, axes = plt.subplots(2, 4, figsize=(10, 4.5), sharex=True,
                                 gridspec_kw={"height_ratios": [1, 1.5]})
        for i in range(4):
            S.density_panel(axes[0, i], i, d, cem, support)
            S.panel_title(axes[0, i], i)
            axes[0, i].set_xlabel("")
            regression_panel(axes[1, i], i, frs[i], frs[0], support, specs[i], cfg, level, i == 0)
        axes[0, 0].set_ylabel("sample\n(size)", color=S.GREY, fontsize=9)
        fig.tight_layout()
        fig.subplots_adjust(hspace=0.22, wspace=0.28)
        fig.savefig(OUT / f"s_specs_{key}.png")
        plt.close(fig)
        out = 100 * (~frs[0].y.between(*cfg[5])).mean()
        print(f"s_specs_{key}.png ({len(frs[0])} {'quarters' if level == 'quarter' else 'institutions'}, "
              f"{out:.0f}% outside the y axis): "
              + ", ".join(f"{s['coef']:+.2f}" for s in specs))


if __name__ == "__main__":
    main()
