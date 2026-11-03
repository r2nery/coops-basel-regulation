"""Slide figure: provisioning and intermediation margin against four comparison groups
(slides/figures/s_group_ladder.png).

Cooperative differential in specification (2), log assets and quarter effects, with 95
percent intervals clustered by institution, read from the results file of each run:
all non-cooperatives (results_broad_peers), banks (results_primary), commercial banks
(results_commercial) and deposit-funded commercial banks (results_structural). Filled
markers: p < 0.05.

    uv run --no-project --with matplotlib,numpy python slides/make_group_slide.py
"""
from __future__ import annotations
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "slides" / "figures" / "s_group_ladder.png"
COOP, DARK, GREY, MUTED = "#2A78D6", "#333333", "#666666", "#898781"
GROUPS = [("results_broad_peers", "All non-\ncooperatives"), ("results_primary", "Banks"),
          ("results_commercial", "Commercial\nbanks"), ("results_structural", "Deposit-\nfunded banks")]
OUTCOMES = [("Provisioning (provisions/gross credit)", "Provisioning, pp of gross credit",
             "reserves set aside for expected loan losses"),
            ("Net Interest Margin", "Intermediation margin, pp of assets",
             "lending and investment income minus funding costs")]


def read(name):
    """outcome -> (coef, lo, hi, p) for the ctrl specification, and the bank count."""
    out, n, on = {}, None, False
    for line in (ROOT / "results" / f"{name}.txt").read_text(encoding="utf-8").splitlines():
        if line.startswith("analysis_noncoops"):
            n = int(line.split("\t")[1])
        if line.startswith("[MAIN_COEFFICIENTS]"):
            on = True
            continue
        if on and line.startswith("["):
            on = False
        f = line.split("\t")
        if on and len(f) > 6 and f[1] == "ctrl":
            out[f[0]] = tuple(100 * float(v) for v in f[2:5]) + (float(f[5]),)
    return out, n


def main():
    rows = [read(g) for g, _ in GROUPS]
    with plt.rc_context({"font.family": "DejaVu Sans", "font.size": 10.5}):
        fig, axes = plt.subplots(1, 2, figsize=(10, 3.5))
        for ax, (key, title, gloss) in zip(axes, OUTCOMES):
            for i, ((res, n), (_, lab)) in enumerate(zip(rows, GROUPS)):
                c, lo, hi, p = res[key]
                sig = p < 0.05
                ax.plot([i, i], [lo, hi], color=COOP if sig else MUTED, lw=2.4, zorder=2)
                ax.plot(i, c, "o", ms=10, mew=2.2, zorder=3, mec=COOP if sig else MUTED,
                        mfc=COOP if sig else "white")
                ax.text(i + 0.16, c, f"{c:+.1f}".replace("-", "\u2212"), va="center", ha="left", fontsize=10,
                        color=DARK if sig else GREY)
                print(f"  {title[:12]} | {lab.replace(chr(10), ' ')} ({n}): {c:+.2f} [{lo:+.2f}, {hi:+.2f}] p={p:.3f}")
            ax.axhline(0, color=DARK, lw=0.9, zorder=1)
            ax.set_xticks(range(len(GROUPS)))
            ax.set_xticklabels([lab for _, lab in GROUPS],
                               fontsize=9.5, color=DARK)
            ax.set_xlim(-0.5, len(GROUPS) - 0.3)
            ax.text(0, 1.13, title, transform=ax.transAxes, ha="left", va="bottom",
                    color=DARK, fontsize=13)   # panel titles 7 pt on the slide
            ax.text(0, 1.04, gloss, transform=ax.transAxes, ha="left", va="bottom",
                    color=GREY, fontsize=11)
            ax.tick_params(length=0, colors=GREY, labelsize=9.5)
            ax.yaxis.grid(True, color="#E6E6E6", lw=0.6)
            ax.set_axisbelow(True)
            for s in ("top", "right", "left"):
                ax.spines[s].set_visible(False)
            ax.spines["bottom"].set_visible(False)
        fig.tight_layout(w_pad=3)
        fig.savefig(OUT, dpi=250, facecolor="white")
        plt.close(fig)
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
