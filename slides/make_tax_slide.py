"""Tax slide figures.

s_tax_simple.png  main slide: median return on assets before and after tax for cooperatives
                  and for banks of the same size, from the median regression of
                  specification (2) (log assets and quarter effects, as in paper.py),
                  predicted at the cooperatives' own sizes and quarters; the gap in
                  each pair is the specification (2) median coefficient
s_tax_split.png   supplementary: the after-tax return gap split into its before-tax part
                  and the rest, for each of the four specifications

Before tax is line (g) of the income statement, after tax line (j), net of income tax,
social contribution and profit sharing; the wedge is the difference of the two
cooperative coefficients in each specification. Coefficients from
results/results_primary.txt (as tables/t13_pretax); a before-tax part not significant at
five percent is drawn hatched.

    uv run --no-project --with pandas,numpy,matplotlib,scipy,statsmodels,linearmodels,seaborn \
        python slides/make_tax_slide.py
"""
from __future__ import annotations
import sys
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "slides"))
from make_outcome_slides import coefficients, COOP, BANK, DARK, GREY   # noqa: E402

OUT = ROOT / "slides" / "figures" / "s_tax_split.png"
SPECS = [("raw", "(1) Naive\ncomparison"), ("ctrl", "(2) Size and\nquarter controls"),
         ("cem", "(3) Matched\non size"), ("trim", "(4) Common\nsupport")]
LIGHT = "#A9C9F0"


def medians():
    """outcome label -> (cooperative median, bank median) from [DESCRIPTIVE_MEANS]."""
    out, on = {}, False
    for line in (ROOT / "results" / "results_primary.txt").read_text(encoding="utf-8").splitlines():
        if line.startswith("[DESCRIPTIVE_MEANS]"):
            on = True
            continue
        if on and (not line or line.startswith("[")):
            break
        f = line.split("\t")
        if len(f) >= 5 and not line.startswith("#"):
            out[f[0]] = (float(f[3]), float(f[4]))
    return out


def predicted_medians():
    """Median regression of specification (2) for each return, predicted for every
    cooperative quarter as a cooperative and as a bank, then averaged."""
    import statsmodels.formula.api as smf
    import make_figures as F
    import paper as P
    panel, _, _ = P.build_panel()
    _, l2 = F.analysis_sample(panel, "banks")
    out = {}
    for o in ("roa_pretax", "roa"):
        d = l2[[o, "is_coop", "log_assets", "date"]].dropna().copy()
        d["t"] = d["date"].dt.to_period("Q").apply(lambda x: x.ordinal)
        q = smf.quantreg(f"{o} ~ is_coop + log_assets + C(t)", data=d).fit(q=0.5)
        c = d[d.is_coop == 1]
        out[o] = (100 * q.predict(c.assign(is_coop=1)).mean(),
                  100 * q.predict(c.assign(is_coop=0)).mean(), 100 * q.params["is_coop"])
    return out


def simple():
    m = predicted_medians()
    with plt.rc_context({"font.family": "DejaVu Sans", "font.size": 11}):
        fig, ax = plt.subplots(figsize=(5.4, 3.7))
        w = 0.36
        for j, (lab, o) in enumerate([("Before tax", "roa_pretax"), ("After tax", "roa")]):
            coop, bank, gap = m[o]
            print(f"  {lab}: cooperatives {coop:.2f}, banks of the same size {bank:.2f}, gap {gap:.2f}")
            for k, (v, col) in enumerate([(coop, COOP), (bank, BANK)]):
                x = j + (k - 0.5) * (w + 0.04)
                ax.bar(x, v, width=w, color=col, zorder=2)
                ax.text(x, v + 0.06, f"{v:.1f}", ha="center", va="bottom", fontsize=12,
                        fontweight="bold", color=DARK)
        ax.set_xticks([0, 1])
        ax.set_xticklabels(["Before tax", "After tax"], fontsize=12, color=DARK)
        ax.set_ylim(0, 3.8)
        ax.set_yticks([])
        ax.text(0, 1.04, "Median return on assets, % a year", transform=ax.transAxes,
                ha="left", va="bottom", color=GREY, fontsize=16)   # 9 pt on the slide
        for s_ in ("top", "right", "left"):
            ax.spines[s_].set_visible(False)
        ax.spines["bottom"].set_color("#CCCCCC")
        ax.tick_params(length=0)
        handles = [plt.Rectangle((0, 0), 1, 1, color=COOP), plt.Rectangle((0, 0), 1, 1, color=BANK)]
        ax.legend(handles, ["Cooperatives", "Banks of the same size"], loc="upper right",
                  frameon=False, fontsize=10)
        fig.tight_layout()
        fig.savefig(ROOT / "slides" / "figures" / "s_tax_simple.png", dpi=250, facecolor="white")
        plt.close(fig)


def main():
    simple()
    co = coefficients()
    after, before = co["Return on Assets"], co["Return on Assets, pre-tax"]
    with plt.rc_context({"font.family": "DejaVu Sans", "font.size": 10}):
        fig, ax = plt.subplots(figsize=(5.6, 3.7))
        for i, (sp, lab) in enumerate(SPECS):
            a, b = 100 * after[sp]["coef"], 100 * before[sp]["coef"]
            sig = before[sp]["cl_p"] < 0.05
            ax.bar(i, b, width=0.6, color=COOP if sig else "white", edgecolor=COOP, lw=1.4,
                   hatch=None if sig else "////", zorder=2)
            ax.bar(i, a - b, bottom=b, width=0.6, color=LIGHT, edgecolor=LIGHT, lw=1.4, zorder=2)
            ax.text(i, a + 0.06, f"{a:.1f}", ha="center", va="bottom", fontsize=11,
                    fontweight="bold", color=DARK)
            ax.text(i, b / 2, f"{b:.1f}" + ("" if sig else "\nn.s."), ha="center", va="center",
                    fontsize=9.5, color="white" if sig else COOP, fontweight="bold",
                    bbox=None if sig else dict(fc="white", ec="none", pad=1))
            ax.text(i, b + (a - b) / 2, f"{a - b:.1f}", ha="center", va="center", fontsize=9.5,
                    color=DARK)
            print(f"  {sp}: after {a:.2f}, before {b:.2f} (p={before[sp]['cl_p']:.3f}), wedge {a - b:.2f}")
        ax.set_xticks(range(len(SPECS)))
        ax.set_xticklabels([l for _, l in SPECS], fontsize=9, color=DARK)
        ax.set_ylim(0, 2.6)
        ax.set_yticks([0, 1, 2])
        ax.text(0, 1.04, "Cooperative minus bank, pp of assets a year (bar total: kept after tax)",
                transform=ax.transAxes, ha="left", va="bottom", color=GREY, fontsize=9)
        ax.tick_params(length=0, colors=GREY, labelsize=9)
        ax.yaxis.grid(True, color="#E6E6E6", lw=0.6)
        ax.set_axisbelow(True)
        for s in ("top", "right", "left"):
            ax.spines[s].set_visible(False)
        ax.spines["bottom"].set_color("#CCCCCC")
        handles = [plt.Rectangle((0, 0), 1, 1, color=COOP),
                   plt.Rectangle((0, 0), 1, 1, fc="white", ec=COOP, hatch="////"),
                   plt.Rectangle((0, 0), 1, 1, color=LIGHT)]
        ax.legend(handles, ["earned before tax", "earned before tax, not significant", "less paid in tax and profit sharing"],
                  loc="upper right", frameon=False, fontsize=8.5, ncol=1)
        fig.tight_layout()
        fig.savefig(OUT, dpi=250, facecolor="white")
        plt.close(fig)
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
