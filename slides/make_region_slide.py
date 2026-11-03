"""Slide figure: credit share differential, nationally and within macro-region
(slides/figures/s_region.png).

Both bars are specification (3), coarsened exact matching on size quintile, from
results/coarsening_sensitivity.txt: "size_q5" matches on size only (the main table's
coarsening), "size_q5_region" also matches exactly on macro-region. The p-value column
there is clustered by institution.

    uv run --no-project --with matplotlib,numpy python slides/make_region_slide.py
"""
from __future__ import annotations
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "slides" / "figures" / "s_region.png"
COOP, DARK, GREY, MUTED = "#2A78D6", "#333333", "#666666", "#B0B0B0"


def read():
    out = {}
    for line in (ROOT / "results" / "coarsening_sensitivity.txt").read_text(encoding="utf-8").splitlines():
        f = line.split("\t")
        if len(f) == 6 and not line.startswith(("[", "#")):
            out[f[0]] = {"credit": 100 * float(f[4]), "p": float(f[5]), "eff_n": float(f[3])}
    return out


def main():
    r = read()
    nat, reg = r["size_q5"], r["size_q5_region"]
    print(f"  national {nat['credit']:+.2f} (p={nat['p']:.1e}); within region {reg['credit']:+.2f} "
          f"(p={reg['p']:.2f}, about {reg['eff_n']:.0f} effective control banks)")
    with plt.rc_context({"font.family": "DejaVu Sans", "font.size": 12}):
        fig, ax = plt.subplots(figsize=(6.0, 4.0))
        ax.bar([0, 1], [nat["credit"], reg["credit"]], width=0.55, color=[COOP, MUTED], zorder=2)
        ax.text(0, nat["credit"] + 0.8, f"+{nat['credit']:.0f} pp", ha="center", va="bottom",
                fontsize=15, fontweight="bold", color=DARK)
        ax.text(1, reg["credit"] - 1.0, f"−{abs(reg['credit']):.0f} pp, not significant",
                ha="center", va="top", fontsize=11.5, color=DARK)
        ax.axhline(0, color=DARK, lw=1)
        ax.set_ylim(-9, 22)
        ax.set_yticks([-5, 0, 5, 10, 15, 20])
        ax.set_xticks([0, 1])
        ax.set_xticklabels(["Banks of the same size,\nanywhere in Brazil",
                            "Banks of the same size,\nin the same region"], fontsize=11, color=DARK)
        ax.text(0, 1.03, "Credit share gap, pp of assets",
                transform=ax.transAxes, ha="left", va="bottom", color=GREY, fontsize=19.5)   # 9 pt
        ax.tick_params(length=0, colors=GREY, labelsize=10)
        ax.yaxis.grid(True, color="#E6E6E6", lw=0.6)
        ax.set_axisbelow(True)
        for s in ("top", "right", "left", "bottom"):
            ax.spines[s].set_visible(False)
        fig.tight_layout()
        fig.savefig(OUT, dpi=250, facecolor="white")
        plt.close(fig)
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
