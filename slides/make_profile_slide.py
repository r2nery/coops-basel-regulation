"""Slide figure: all eleven outcomes against banks at comparable size (slides/figures/profile.png).

Values come from the primary results file through make_tables, as in
make_figures.slide_profile: the controlled specification (2), divided by the standard
deviation of each outcome, with 95 percent intervals (clustered; HC3 for the two
institution-level outcomes). Outcomes are grouped by
the paper's tier, stable first.

    uv run --no-project --with pandas,numpy,matplotlib,scipy,statsmodels,linearmodels,seaborn \
        python slides/make_profile_slide.py
"""
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import make_figures as F   # noqa: E402
import make_tables as MT   # noqa: E402
import paper as P          # noqa: E402

OUT = ROOT / "slides" / "figures" / "profile.png"
COOP, MUTED, INK2 = F.COOP, F.MUTED, F.INK2

ORDER = [  # grouped by tier: stable, stable in sign, null
    "Credit Portfolio / Assets", "Z-score", "Return on Assets", "Return on assets volatility",
    "Leverage (liabilities/assets)", "Basel Capital Ratio (%)", "Cost-to-Income Ratio",
    "Return on Assets, pre-tax", "Funding Ratio (captacoes/assets)",
    "Provisioning (provisions/gross credit)", "Net Interest Margin",
]
STYLE = {"stable": dict(mfc=COOP, mec=COOP), "stable in sign": dict(mfc="white", mec=COOP),
         "null": dict(mfc="white", mec=MUTED)}
LEGEND = [("stable", "stable"), ("stable in sign", "stable in sign"),
          ("null", "null: not significant in\nall four specifications")]


def main():
    panel, _, _ = P.build_panel()
    _, l2 = F.analysis_sample(panel, "banks")
    res = MT.parse(MT.FILES["primary"])
    c, tiers = MT.coefs(res), MT.tiers(res)
    inst, _, _ = P.collapse_stability(l2)
    sd = {k: l2[F.KEY[k]].std() for k, _ in MT.ORDER}
    sd["Return on assets volatility"] = inst["roa_vol"].std()
    sd["Z-score"] = inst["zscore"].std()

    with plt.rc_context({"font.size": 12, "xtick.labelsize": 11, "ytick.labelsize": 12,
                         "axes.labelsize": 12, "legend.fontsize": 11}):
        fig, ax = plt.subplots(figsize=(10, 5.6))
        ax.axvline(0, color=INK2, lw=1)
        y = np.arange(len(ORDER))[::-1]
        for yy, k in zip(y, ORDER):
            v = c[k]["ctrl"]
            lo, hi = (v["hc_lo"], v["hc_hi"]) if k in MT.STAB_LABELS else (v["cl_lo"], v["cl_hi"])
            t = tiers.get(k, "null")
            col = MUTED if t == "null" else COOP
            ax.plot([lo / sd[k], hi / sd[k]], [yy, yy], color=col, lw=2.6,
                    solid_capstyle="round", alpha=0.85)
            ax.plot(v["coef"] / sd[k], yy, "o", ms=12, mew=2.4, zorder=3, **STYLE[t])
            print(f"  {F.LABEL[k]:32s} {v['coef'] / sd[k]:+.2f} sd  [{lo / sd[k]:+.2f}, {hi / sd[k]:+.2f}]  {t}")
        ax.set_yticks(y)
        ax.set_yticklabels([F.LABEL[k] for k in ORDER])
        ax.set_xlabel("Cooperatives minus banks, in standard deviations of the outcome")
        for t, lab in LEGEND:
            ax.plot([], [], "o", ms=10, mew=2, label=lab, **STYLE[t])
        ax.legend(loc="upper left", frameon=False)
        F.xgrid(ax)
        fig.tight_layout()
        fig.savefig(OUT, dpi=200)
        plt.close(fig)
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
