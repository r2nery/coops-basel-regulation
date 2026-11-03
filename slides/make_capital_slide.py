"""Slide figure: Basel capital ratio distributions of cooperatives and banks
(slides/figures/s_capital_dist.png).

Analysis sample (singular cooperatives against banks, full-methodology quarters,
winsorised 1/99, as in tables/t1); kernel densities estimated on the log of the ratio, so
the smoothing is even on the log axis; solid lines at the group means, dashed at the
medians.

    uv run --no-project --with pandas,numpy,matplotlib,scipy,statsmodels,linearmodels,seaborn \
        python slides/make_capital_slide.py
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker
from scipy.stats import gaussian_kde

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import make_figures as F   # noqa: E402
import paper as P          # noqa: E402

OUT = ROOT / "slides" / "figures" / "s_capital_dist.png"
COOP, BANK, DARK, GREY = "#2A78D6", "#EB6834", "#333333", "#666666"


def brace(ax, x0, x1, y, h, label, color=DARK):
    """Horizontal curly brace from x0 to x1 (data units, log axis) at axes height y,
    tip pointing up, with the label centred above the tip."""
    t = np.linspace(0, 1, 401)
    k = 60.0
    half = 1 / (1 + np.exp(-k * (t[:201] - 0.0))) + 1 / (1 + np.exp(-k * (t[:201] - 0.5)))
    yy = np.concatenate([half, half[-2::-1]]) - 1           # 0 at the ends, 1 at the tip
    lx0, lx1 = np.log10(x0), np.log10(x1)
    xs = 10 ** (lx0 + t * (lx1 - lx0))
    ax.plot(xs, y + h * yy, color=color, lw=1.3, transform=ax.get_xaxis_transform(),
            clip_on=False)
    ax.text(10 ** ((lx0 + lx1) / 2), y + h * 1.25, label, ha="center", va="bottom",
            fontsize=10.5, color=color, linespacing=1.1, transform=ax.get_xaxis_transform())


def main():
    panel, _, _ = P.build_panel()
    _, l2 = F.analysis_sample(panel, "banks")
    d = l2[["basileia_num", "is_coop"]].dropna()
    lo, hi = d.basileia_num.min(), d.basileia_num.max()
    grid = np.logspace(np.log10(lo), np.log10(hi), 500)
    stats = {}
    with plt.rc_context({"font.family": "DejaVu Sans", "font.size": 11}):
        fig, ax = plt.subplots(figsize=(10, 3.2))
        for v, c in [(0, BANK), (1, COOP)]:
            x = d.loc[d.is_coop == v, "basileia_num"]
            dens = gaussian_kde(np.log10(x))(np.log10(grid))   # density of log10 capital
            ax.fill_between(grid, dens, color=c, alpha=0.25, lw=0)
            ax.plot(grid, dens, color=c, lw=2)
            stats[v] = (x.median(), x.mean(), dens.max())
            ax.axvline(x.mean(), ymax=1.0, color=c, lw=1.8)
            ax.axvline(x.median(), ymax=1.0, color=c, lw=1.8, ls=(0, (4, 2.5)))
            print(f"  {'cooperatives' if v else 'banks'}: median {x.median():.2f}, mean {x.mean():.2f}")
        ymax = max(stats[0][2], stats[1][2])
        ax.set_ylim(0, ymax * 1.05)
        # direct labels on the curves
        ax.text(15.2, stats[1][2] * 0.98, "cooperatives", color=COOP, ha="right", fontsize=11)
        ax.text(60, stats[0][2] * 0.22, "banks", color=BANK, ha="left", fontsize=11)
        # braces above the plot: medians (dashed lines) and means (solid lines)
        mb, mc = stats[0][0], stats[1][0]
        ab, ac = stats[0][1], stats[1][1]
        ax.set_xscale("log")
        ax.set_xlim(lo, hi)
        brace(ax, mb, mc, 1.04, 0.08, f"medians\ncoops +{mc - mb:.1f}")
        brace(ax, ac, ab, 1.04, 0.08, f"means\nbanks +{ab - ac:.1f}")
        ax.set_xscale("log")
        ax.set_xticks([10, 15, 20, 30, 50, 100, 150])
        ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:g}"))
        ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
        ax.set_xlim(lo, hi)
        ax.set_yticks([])
        ax.text(0, 1.5, "Basel capital ratio, % of risk-weighted assets (log scale)",
                transform=ax.transAxes, ha="left", va="bottom", color=GREY, fontsize=16)   # 9 pt
        ax.tick_params(length=0, colors=GREY, labelsize=10)
        for s_ in ("top", "right", "left"):
            ax.spines[s_].set_visible(False)
        ax.spines["bottom"].set_color("#CCCCCC")
        fig.tight_layout()
        fig.subplots_adjust(top=0.64)
        fig.savefig(OUT, dpi=250, facecolor="white")
        plt.close(fig)
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
