"""Slide figure: cooperatives and banks on six outcomes, as densities.

Rebuilds the primary analysis sample through make_figures.analysis_sample (singular
cooperatives against banks, full-methodology quarters, winsorised 1/99) and draws one
kernel density per group and outcome, in the style of fig8_overlap.png. Pools all
institution-quarters; the dashed lines are the group medians. The share of observations
outside each panel's window is printed for the slide footnote.

Variants (one figure each, in slides/figures/):

    centred     s_outcome_densities.png             window centred on the cooperative
                                                    median, WIDTH_SD cooperative SDs each side
    full        s_outcome_densities_full.png        the pooled range of the data
    tukey       s_outcome_densities_tukey.png       the pooled range without Tukey outliers
                                                    (beyond 1.5 IQR of the pooled quartiles)
    reflect     s_outcome_densities_reflect.png     tukey, with the density reflected at zero
                                                    for credit and provisioning
    zero        s_outcome_densities_zero.png        tukey, with exact zeros shown as a share
                                                    at 0 and the density drawn on the rest,
                                                    where they exceed 5% (bank credit, 12%)
    structural  s_outcome_densities_structural.png  reflect, against deposit-funded commercial
                                                    banks only (the paper's "structural" rung)

    uv run --no-project --with pandas,numpy,matplotlib,scipy,statsmodels,linearmodels,seaborn \
        python slides/make_outcome_densities.py [variant ...]
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import gaussian_kde

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import make_figures as F   # noqa: E402  (sets the paper rcParams; overridden below)
import paper as P          # noqa: E402

OUT = ROOT / "slides" / "figures"
COOP, BANK = F.COOP, F.BANK
INK2, AXIS = F.INK2, F.AXIS

plt.rcParams.update({
    "font.size": 11, "axes.titlesize": 12.5, "axes.titleweight": "bold",   # panel titles 7 pt on the slide
    "axes.titlelocation": "left", "axes.labelsize": 10, "xtick.labelsize": 10,
    "ytick.labelsize": 10, "legend.fontsize": 10.5, "axes.linewidth": 0.8,
    "lines.linewidth": 1.8, "savefig.dpi": 220,
})

WIDTH_SD = 4   # half-width of every panel in the centred variant, in cooperative SDs

# column, title, scale to display units, axis label
# Six outcomes, one per later slide: capital (Result 2); credit, cost-to-income and the
# after-tax return (Result 1); the pre-tax return (tax slide); provisioning (Result 3).
# Top row balance sheet, bottom row income. Leverage is left out as the near mirror
# image of capital.
OUTCOMES = [
    ("basileia_num", "Basel capital ratio", 1, "% of risk-weighted assets"),
    ("credit_ratio", "Credit portfolio", 100, "% of assets"),
    ("prov_ratio", "Provisioning", 100, "% of gross credit"),
    ("roa", "Return on assets,\nafter tax", 100, "% a year"),
    ("roa_pretax", "Return on assets,\nbefore tax", 100, "% a year"),
    ("cti", "Cost-to-income", 100, "% of income"),
]
BOUNDED_AT_ZERO = {"credit_ratio", "prov_ratio"}   # many bank quarters sit at or near 0

NAMES = {"centred": "s_outcome_densities.png", "full": "s_outcome_densities_full.png",
         "tukey": "s_outcome_densities_tukey.png", "reflect": "s_outcome_densities_reflect.png",
         "zero": "s_outcome_densities_zero.png",
         "structural": "s_outcome_densities_structural.png"}


def window(x, is_coop, variant):
    if variant == "centred":
        c = x[is_coop == 1]
        return c.median() - WIDTH_SD * c.std(), c.median() + WIDTH_SD * c.std()
    if variant == "full":
        return x.min(), x.max()
    q1, q3 = x.quantile([0.25, 0.75])
    fence = 1.5 * (q3 - q1)
    return max(x.min(), q1 - fence), min(x.max(), q3 + fence)


def density(s, grid, col, variant):
    """Kernel density on the grid. Reflected at zero for the bounded outcomes in the
    reflect and structural variants, so mass at zero does not spill below the axis."""
    k = gaussian_kde(s)
    if variant in ("reflect", "structural") and col in BOUNDED_AT_ZERO:
        return k(grid) + k(-grid)
    return k(grid)


def sample(variant):
    panel, _, _ = P.build_panel()
    _, l2 = F.analysis_sample(panel, "banks")
    label = "Banks"
    if variant == "structural":
        sub, _, _ = P.select_sample(panel, "singular", "cti_new", "roa_ann", "nim_ann", "structural")
        keep = set(sub.loc[sub.is_coop == 0, "codigo"])
        l2 = l2[(l2.is_coop == 1) | l2.codigo.isin(keep)]   # primary winsorisation kept
        label = "Deposit-funded banks"
    return l2, label


def draw(variant):
    l2, bank_label = sample(variant)
    n = {v: l2.loc[l2.is_coop == v, "codigo"].nunique() for v in (0, 1)}
    fig, axes = plt.subplots(2, 3, figsize=(10, 4.4))
    for a, (col, title, k, xlab) in zip(axes.flatten(), OUTCOMES):
        d = l2[[col, "is_coop"]].dropna()
        x = d[col] * k
        lo, hi = window(x, d.is_coop, variant)
        grid = np.linspace(lo, hi, 400)
        for v, c, lab in [(1, COOP, "Cooperatives"), (0, BANK, bank_label)]:
            s = x[d.is_coop == v]
            zero = (s == 0).mean()
            if variant == "zero" and col in BOUNDED_AT_ZERO and zero > 0.05:
                y = (1 - zero) * gaussian_kde(s[s > 0])(grid)
                a.plot(grid, y, color=c, label=f"{lab} ({n[v]})")
                a.plot([0], [0], "o", ms=8, color=c, clip_on=False, zorder=4)
                a.annotate(f"{100 * zero:.0f}% of bank\nquarters at 0", (0, 0),
                           xytext=(0.06, 0.55), textcoords="axes fraction", fontsize=9,
                           color=c, ha="left", va="center",
                           arrowprops=dict(arrowstyle="-", color=c, lw=0.8))
            else:
                a.plot(grid, density(s, grid, col, variant), color=c, label=f"{lab} ({n[v]})")
            a.axvline(s.median(), color=c, lw=1.1, ls=(0, (3, 2)))
        a.set_title(title)
        a.set_xlabel(xlab)
        a.set_xlim(lo, hi)
        a.set_ylim(0, None)
        a.set_yticks([])
        a.spines["left"].set_visible(False)
    h, lab = axes[0, 0].get_legend_handles_labels()
    fig.legend(h, lab, loc="upper center", ncol=2, bbox_to_anchor=(0.5, 1.04))
    fig.tight_layout(h_pad=1.6, w_pad=2.0)
    fig.savefig(OUT / NAMES[variant])
    plt.close(fig)
    print(f"slides/figures/{NAMES[variant]}  ({len(l2)} institution-quarters, "
          f"{n[1]} cooperatives, {n[0]} {bank_label.lower()})")
    for col, title, k, _ in OUTCOMES:
        x = l2[col].dropna() * k
        g = l2.loc[x.index, "is_coop"]
        lo, hi = window(x, g, variant)
        m = x.groupby(g).median()
        out = (~x.between(lo, hi)).groupby(g).mean() * 100
        print(f"  {title}: window [{lo:.1f}, {hi:.1f}]; median coop {m[1]:.1f}, "
              f"bank {m[0]:.1f}; outside window coop {out[1]:.1f}%, bank {out[0]:.1f}%")


def main():
    variants = [a for a in sys.argv[1:] if a in NAMES] or ["centred"]
    for v in variants:
        draw(v)


if __name__ == "__main__":
    main()
