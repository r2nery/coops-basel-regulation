"""One slide's assets per stable outcome: a figure and a table.

Figure (slides/figures/s_out_<key>.png): the outcome against log total assets for
cooperatives and banks, with each group's kernel density along the right edge on the
same outcome axis and dashed lines at the group medians. The axis spans the pooled data
without Tukey outliers (beyond 1.5 IQR of the pooled quartiles); densities are
reflected at zero for outcomes bounded there.

Table (slides/tables/spec_<key>.tex): the cooperative differential in the four
specifications with its 95 percent interval, read from results/results_primary.txt
(clustered by institution for the quarterly outcomes, HC3 for the two institution-level
ones, as in tables/t2_main).

    uv run --no-project --with pandas,numpy,matplotlib,scipy,statsmodels,linearmodels,seaborn \
        python slides/make_outcome_slides.py
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
import make_figures as F   # noqa: E402
import paper as P          # noqa: E402

FIG = ROOT / "slides" / "figures"
TAB = ROOT / "slides" / "tables"
RES = ROOT / "results" / "results_primary.txt"
COOP, BANK, DARK, GREY = "#2A78D6", "#EB6834", "#333333", "#666666"

# key, results label, panel column, scale, level, axis label, unit, reflect at zero
OUTCOMES = [
    ("roa", "Return on Assets", "roa", 100, "quarter", "return on assets after tax, % a year", "pp", False),
    ("roa_pre", "Return on Assets, pre-tax", "roa_pretax", 100, "quarter",
     "return on assets before tax, % a year", "pp", False),
    ("credit", "Credit Portfolio / Assets", "credit_ratio", 100, "quarter", "credit portfolio, % of assets", "pp", True),
    ("vol", "Return on assets volatility", "roa_vol", 100, "institution", "return volatility, pp a year", "pp", True),
    ("z", "Z-score", "zscore", 1, "institution", "z-score", "", False),
]
SPECS = [("raw", "(1) Naive comparison"), ("ctrl", "(2) Size controls"),
         ("cem", "(3) Matched on size"), ("trim", "(4) Common support")]


def coefficients():
    """outcome label -> spec -> dict of the [MAIN_COEFFICIENTS] row."""
    out, on = {}, False
    cols = None
    for line in RES.read_text(encoding="utf-8").splitlines():
        if line.startswith("[MAIN_COEFFICIENTS]"):
            cols = line.split("]")[1].split()
            on = True
            continue
        if on and line.startswith("["):
            break
        if on and line and not line.startswith("#"):
            f = line.split("\t")
            out.setdefault(f[0], {})[f[1]] = dict(zip(cols[2:], map(float, f[2:])))
    return out


def window(x):
    q1, q3 = x.quantile([0.25, 0.75])
    f = 1.5 * (q3 - q1)
    lo = 0.0 if x.min() >= 0 else max(x.min(), q1 - f)   # non-negative outcomes start at 0
    return lo, min(x.max(), q3 + f)


def figure(key, frame, ylab, reflect):
    lo, hi = window(frame.y)
    fig, (ax, am) = plt.subplots(1, 2, figsize=(5.4, 3.7), sharey=True,
                                 gridspec_kw={"width_ratios": [3.2, 1], "wspace": 0.04})
    big = len(frame) < 1000
    grid = np.linspace(lo, hi, 400)
    for v, c, lab in [(0, BANK, "Banks"), (1, COOP, "Cooperatives")]:
        g = frame[frame.is_coop == v]
        ax.scatter(g.log_assets, g.y, s=12 if big else 2, color=c, alpha=0.5 if big else 0.3,
                   lw=0, label=lab, zorder=2)
        k = gaussian_kde(g.y)
        dens = k(grid) + (k(-grid) if reflect else 0)
        am.fill_betweenx(grid, dens, color=c, alpha=0.3, lw=0)
        am.plot(dens, grid, color=c, lw=1.8)
        med = g.y.median()
        for a in (ax, am):
            a.axhline(med, color=c, lw=1.1, ls=(0, (3, 2)), zorder=3)
    ax.set_ylim(lo, hi)
    ax.set_xlim(7.5, 22.5)
    ax.set_xticks([10, 15, 20])
    ax.set_xlabel("log total assets", color=GREY, fontsize=10)
    ax.text(0, 1.03, ylab[0].upper() + ylab[1:], transform=ax.transAxes, ha="left",
            va="bottom", color=GREY, fontsize=14)   # 9 pt on the slide
    am.set_xlim(0, None)
    am.set_xticks([])
    am.set_xlabel("density", color=GREY, fontsize=10)
    for a in (ax, am):
        a.tick_params(length=0, colors=GREY, labelsize=9)
        for s in ("top", "right"):
            a.spines[s].set_visible(False)
        a.spines["left"].set_color("#CCCCCC")
        a.spines["bottom"].set_color("#CCCCCC")
    am.spines["left"].set_visible(False)
    leg = ax.legend(loc="upper left", frameon=False, fontsize=9, markerscale=2.5 if not big else 1.2,
                    handletextpad=0.2)
    for h in leg.legend_handles:
        h.set_alpha(1)
    fig.savefig(FIG / f"s_out_{key}.png", dpi=250, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return (~frame.y.between(lo, hi)).mean()


def table(key, rows, scale, unit, stab):
    lo_k, hi_k, p_k = ("hc_lo", "hc_hi", "hc_p") if stab else ("cl_lo", "cl_hi", "cl_p")
    u = f"~{unit}" if unit else ""
    lines = [r"\begin{tabular}{lrr}", r"\toprule",
             r"Specification & Differential & 95\% interval \\", r"\midrule"]
    for sp, lab in SPECS:
        if sp == "ctrl" and not stab:
            lab = "(2) Size and quarter controls"
        r = rows[sp]
        c, lo, hi = (r[k] * scale + 0.0 for k in ("coef", lo_k, hi_k))
        lo, hi = (0.0 if abs(v) < 0.05 else v for v in (lo, hi))   # no "-0.0"
        lines.append(f"{lab} & ${c:+.1f}${u} & ${lo:.1f}$ to ${hi:.1f}$ \\\\".replace("+-", "-"))
    lines += [r"\bottomrule", r"\end{tabular}"]
    (TAB / f"spec_{key}.tex").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return [(rows[sp]["coef"] * scale, rows[sp][p_k]) for sp, _ in SPECS]


def main():
    TAB.mkdir(exist_ok=True)
    co = coefficients()
    panel, _, _ = P.build_panel()
    _, l2 = F.analysis_sample(panel, "banks")
    inst, _, _ = P.collapse_stability(l2)
    for key, label, col, scale, level, ylab, unit, reflect in OUTCOMES:
        src = l2 if level == "quarter" else inst
        frame = src[[col, "log_assets", "is_coop"]].dropna().rename(columns={col: "y"})
        frame = frame.assign(y=frame.y * scale)
        out = figure(key, frame, ylab, reflect)
        res = table(key, co[label], scale, unit, level == "institution")
        print(f"{key}: {len(frame)} rows, {100 * out:.0f}% outside the axis; "
              + "; ".join(f"{c:+.2f} (p={p:.1e})" for c, p in res))


if __name__ == "__main__":
    main()
