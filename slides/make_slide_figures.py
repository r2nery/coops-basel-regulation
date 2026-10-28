"""Slide-format figures for the ICA CCR 2026 deck (slides/deck.tex).

Reads the generated tables in tables/*.txt (no recomputation) and writes PNGs to
slides/figures/. Palette and chrome follow make_figures.py.

    uv run --no-project --with matplotlib,numpy python slides/make_slide_figures.py
"""
from __future__ import annotations
import re
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker

ROOT = Path(__file__).resolve().parents[1]
TAB = ROOT / "tables"
OUT = ROOT / "slides" / "figures"
OUT.mkdir(parents=True, exist_ok=True)

COOP, BANK, OTHER = "#2a78d6", "#eb6834", "#1baf7a"
INK, INK2, MUTED = "#0b0b0b", "#52514e", "#898781"
GRID, AXIS, BAND = "#e1e0d9", "#c3c2b7", "#f0efec"

plt.rcParams.update({
    "font.family": "sans-serif", "font.size": 11, "axes.titlesize": 12,
    "axes.titleweight": "bold", "axes.titlelocation": "left", "axes.labelsize": 11,
    "axes.labelcolor": INK2, "axes.edgecolor": AXIS, "axes.linewidth": 0.8,
    "axes.spines.top": False, "axes.spines.right": False, "xtick.color": INK2,
    "ytick.color": INK2, "xtick.labelsize": 10, "ytick.labelsize": 11,
    "savefig.dpi": 220, "savefig.bbox": "tight", "savefig.facecolor": "white",
})

NUM = r"(-?\d+\.\d+)"


def parse_t3():
    """t3_peer_ladder.txt: outcome row with five starred coefficients, then a row of SEs."""
    lines = (TAB / "t3_peer_ladder.txt").read_text(encoding="utf-8").splitlines()
    out, i = {}, 0
    while i < len(lines):
        m = re.match(r"^([A-Z][^&]*?)\s*&\s*(.*)\\\\\s*$", lines[i])
        if m and i + 1 < len(lines) and lines[i + 1].strip().startswith("&"):
            name = m.group(1).strip()
            coefs = [float(x) for x in re.findall(NUM, m.group(2))]
            ses = [float(x) for x in re.findall(NUM, lines[i + 1])]
            if len(coefs) == 5 and len(ses) == 5:
                out[name] = (np.array(coefs), np.array(ses))
            i += 2
        else:
            i += 1
    return out


RUNGS = ["All non-cooperatives (483)", "Banks (144)", "Banks, within region (144)",
         "Commercial banks (105)", "Deposit-funded banks (94)"]


def ladder(ax, title, coefs, ses, unit=""):
    y = np.arange(5)[::-1]
    ax.axvline(0, color=AXIS, lw=1)
    ax.axhspan(y[1] - 0.45, y[1] + 0.45, color=BAND, lw=0, zorder=0)
    for yy, c, s in zip(y, coefs, ses):
        lo, hi = c - 1.96 * s, c + 1.96 * s
        sig = abs(c / s) > 1.96
        ax.plot([lo, hi], [yy, yy], color=COOP, lw=2.2, solid_capstyle="round")
        ax.plot(c, yy, "o", ms=9, mew=2, mec=COOP, mfc=COOP if sig else "white", zorder=3)
    reach = max(abs(coefs - 1.96 * ses).max(), abs(coefs + 1.96 * ses).max())
    ax.set_xlim(-1.1 * reach, 1.1 * reach)
    ax.set_ylim(-0.6, 4.6)
    ax.set_yticks(y)
    ax.set_yticklabels(RUNGS)
    ax.set_title(title)
    ax.xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(nbins=5, symmetric=True))
    ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:g}"))
    if unit:
        ax.set_xlabel(unit)
    ax.grid(axis="x", color=GRID, lw=0.7)
    ax.set_axisbelow(True)


def fig_vanish(t3):
    fig, axes = plt.subplots(1, 2, figsize=(11, 3.9), sharey=True)
    ladder(axes[0], "Provisioning ratio", *t3["Provisioning ratio"],
           unit="Cooperative coefficient (share of gross credit)")
    ladder(axes[1], "Intermediation margin", *t3["Intermediation margin"],
           unit="Cooperative coefficient (share of assets)")
    fig.tight_layout(w_pad=2)
    fig.savefig(OUT / "ladder_vanish.png")
    plt.close(fig)


def fig_survive(t3):
    fig, axes = plt.subplots(2, 2, figsize=(11, 6.2), sharey=True)
    spec = [("Return on assets, after tax", "Return on assets, after tax", "share of assets, annualised"),
            ("Cost-to-income ratio", "Cost-to-income ratio", "ratio"),
            ("Credit portfolio / assets", "Credit portfolio / assets", "share of assets"),
            ("Return on assets volatility", "Return volatility", "s.d. of annualised return")]
    for ax, (key, title, unit) in zip(axes.flatten(), spec):
        ladder(ax, title, *t3[key], unit=unit)
    fig.tight_layout(w_pad=2, h_pad=1.5)
    fig.savefig(OUT / "ladder_survive.png")
    plt.close(fig)


def fig_tax():
    # tables/t13_pretax.txt, rows (j) and (g), four specifications
    before = np.array([0.0118, 0.0132, 0.0088, 0.0062]) * 100
    after = np.array([0.0181, 0.0215, 0.0179, 0.0159]) * 100
    sig_before = [True, True, False, False]
    labels = ["(1) Raw", "(2) Size and\nquarter", "(3) Matched\non size", "(4) Common\nsupport"]
    x = np.arange(4)
    w = 0.36
    fig, ax = plt.subplots(figsize=(8.6, 4.3))
    ax.bar(x - w / 2, after, w, color=COOP, label="After tax (net income, line j)")
    bars = ax.bar(x + w / 2, before, w, color="white", edgecolor=COOP, lw=2,
                  label="Before tax (line g)")
    for b, s, v in zip(bars, sig_before, before):
        if not s:
            b.set_edgecolor(MUTED)
            ax.text(b.get_x() + w / 2, v + 0.08, "n.s.", ha="center", color=MUTED, fontsize=10)
    for xx, v in zip(x - w / 2, after):
        ax.text(xx, v + 0.08, f"{v:.1f}", ha="center", color=COOP, fontsize=10)
    for xx, v, s in zip(x + w / 2, before, sig_before):
        if s:
            ax.text(xx, v + 0.08, f"{v:.1f}", ha="center", color=COOP, fontsize=10)
    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylabel("Cooperative differential, pp of assets")
    ax.set_ylim(0, 2.9)
    ax.grid(axis="y", color=GRID, lw=0.7)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, loc="upper right")
    ax.annotate("Median effective tax rate on a positive result:\nbanks 35%, cooperatives 1%",
                xy=(0.02, 0.97), xycoords="axes fraction", va="top", color=INK2, fontsize=10)
    fig.tight_layout()
    fig.savefig(OUT / "tax_wedge.png")
    plt.close(fig)


def fig_survival():
    # tables/t14_survival.txt
    rows = [("Credit / assets", "+ + . + +"), ("Return on assets, after tax", "+ + + + +"),
            ("Return on assets, before tax", ". + . + +"), ("Return volatility", "- - - - -"),
            ("Z-score", "+ + . + +"), ("Cost-to-income", "- - - - -"),
            ("Basel capital ratio", "- - - - -"), ("Leverage", "+ + + + +"),
            ("Provisioning ratio", "- . . . ."), ("Intermediation margin", "- . . . +"),
            ("Funding ratio", "+ + . . .")]
    cols = ["All non-\ncooperatives\n(483)", "Banks\n(144)", "Banks,\nwithin region\n(144)",
            "Commercial\nbanks (105)", "Deposit-funded\nbanks (94)"]
    fig, ax = plt.subplots(figsize=(10.5, 5.8))
    n, m = len(rows), len(cols)
    ax.set_xlim(-0.6, m - 0.4)
    ax.set_ylim(-1.3, n - 0.5)
    ax.axvspan(0.5, 1.5, color=BAND, lw=0, zorder=0)
    for i, (name, signs) in enumerate(rows):
        yy = n - 1 - i
        for j, s in enumerate(signs.split()):
            if s == ".":
                ax.plot(j, yy, "o", ms=7, color=GRID, mec=AXIS, mew=1)
            else:
                col = COOP if s == "+" else BANK
                ax.plot(j, yy, "o", ms=24, color=col, zorder=2)
                ax.text(j, yy - 0.03, s, ha="center", va="center", color="white",
                        fontsize=15, fontweight="bold", zorder=3)
    ax.set_yticks(range(n))
    ax.set_yticklabels([r[0] for r in rows][::-1])
    ax.set_xticks(range(m))
    ax.set_xticklabels(cols, fontsize=10)
    ax.xaxis.tick_top()
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.text(m - 0.4, -0.85, "Filled: cooperative coefficient significant at 5 percent, with its sign. "
            "Dot: not significant.", ha="right", va="top", color=INK2, fontsize=9.5)
    fig.tight_layout()
    fig.savefig(OUT / "survival.png")
    plt.close(fig)


def fig_sample():
    """Analysis sample as two stacked bars: institutions and institution-quarters."""
    fig, ax = plt.subplots(figsize=(8.4, 2.4))
    items = [("Institutions", 130, 144), ("Institution-quarters", 3048, 4186)]
    for i, (lab, c, b) in enumerate(items):
        tot = c + b
        ax.barh(i, c / tot, color=COOP, height=0.55)
        ax.barh(i, b / tot, left=c / tot, color=BANK, height=0.55)
        ax.text(c / tot / 2, i, f"{c:,} cooperatives", ha="center", va="center", color="white",
                fontsize=11, fontweight="bold")
        ax.text(c / tot + b / tot / 2, i, f"{b:,} banks", ha="center", va="center",
                color="white", fontsize=11, fontweight="bold")
    ax.set_yticks([0, 1])
    ax.set_yticklabels([i[0] for i in items])
    ax.set_xticks([])
    for s in ax.spines.values():
        s.set_visible(False)
    ax.tick_params(length=0)
    fig.tight_layout()
    fig.savefig(OUT / "sample_bars.png")
    plt.close(fig)


if __name__ == "__main__":
    t3 = parse_t3()
    print("t3 outcomes:", list(t3))
    fig_vanish(t3)
    fig_survive(t3)
    fig_tax()
    fig_survival()
    fig_sample()
    print("written to", OUT)
