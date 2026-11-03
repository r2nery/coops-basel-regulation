"""Slide figure: who is in the broad comparison group (slides/figures/s_broad_group.png).

Same data as the paper's fig14_broad_group.png (make_figures.fig_broad_group): institution
medians of credit and of funds raised over total assets, full-methodology quarters, for
cooperatives, banks and the other non-cooperatives. Redrawn with slide-sized type.

    uv run --no-project --with pandas,numpy,matplotlib,scipy,statsmodels,linearmodels,seaborn \
        python slides/make_broad_group_slide.py
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
import paper as P          # noqa: E402

OUT = ROOT / "slides" / "figures" / "s_broad_group.png"
CAP = 1.2   # a few non-cooperatives report ratios above one; drawn at the edge


def main():
    panel, _, _ = P.build_panel()
    sub, _ = F.analysis_sample(panel, peer_set="all")
    fm = sub[sub["full_method"] == 1]
    med = fm.groupby("codigo").agg(credit=("credit_ratio", "median"),
                                   funding=("deposit_ratio", "median"),
                                   is_coop=("is_coop", "first"),
                                   tcb=("tcb_stable", "first"))
    med["grp"] = np.where(med.is_coop == 1, "coop",
                          np.where(med.tcb.astype(str).isin(P.PEER_SETS["banks"]), "bank", "other"))
    zero = med[(med.is_coop == 0) & (med.credit == 0) & (med.funding == 0)]
    n = med.grp.value_counts()

    with plt.rc_context({"font.size": 12, "axes.labelsize": 12, "xtick.labelsize": 11,
                         "ytick.labelsize": 11, "legend.fontsize": 11.5}):
        fig, ax = plt.subplots(figsize=(6.2, 4.6))
        for grp, c, lab in [("other", F.OTHER, "Other non-cooperatives"), ("bank", F.BANK, "Banks"),
                            ("coop", F.COOP, "Cooperatives")]:
            m = med[(med.grp == grp) & ~med.index.isin(zero.index)]
            ax.scatter(m.credit.clip(upper=CAP), m.funding.clip(upper=CAP), s=30, color=c,
                       alpha=0.8, lw=0.6, edgecolor="white", label=lab)
        ax.scatter([0], [0], s=220, facecolor=F.OTHER, edgecolor="white", lw=1.5, zorder=3)
        ax.annotate(f"{len(zero)} with no loans\nand no deposits", (0, 0), xytext=(0.12, 0.13),
                    textcoords="data", fontsize=11, color=F.INK, va="center", ha="left",
                    bbox=dict(boxstyle="round,pad=0.3", fc="white", ec=F.AXIS, lw=0.6),
                    arrowprops=dict(arrowstyle="-", color=F.INK2, lw=0.8), zorder=5)
        ax.set_xlim(-0.04, CAP + 0.02)
        ax.set_ylim(-0.04, CAP + 0.02)
        ax.set_xlabel("Credit / total assets (institution median)")
        ax.text(0, 1.03, "Funds raised / total assets\n(institution median)", transform=ax.transAxes,
                ha="left", va="bottom", fontsize=17.5, color=F.INK2)   # 9 pt on the slide
        ax.legend(loc="upper left", handletextpad=0.2, frameon=False)
        F.xgrid(ax)
        F.ygrid(ax)
        fig.tight_layout()
        fig.savefig(OUT, dpi=220)
        plt.close(fig)
    print(f"wrote {OUT.relative_to(ROOT)}: cooperatives {n['coop']}, banks {n['bank']}, "
          f"other {n['other']} ({len(zero)} at zero credit and zero funding)")


if __name__ == "__main__":
    main()
