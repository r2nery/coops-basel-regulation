"""Simple explanatory figures for the ICA CCR 2026 slides. Numbers from tables/t1, t2, t3, t13, t14
and the manuscript. Output to figures/slides/."""
import sys, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from PIL import Image
out = sys.argv[1] if len(sys.argv) > 1 else "figures/slides"
COOP, BANK, GREY, DARK = "#2A78D6", "#EB6834", "#B0B0B0", "#333333"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 14, "axes.edgecolor": "#BBBBBB"})
def clean(ax):
    for s in ("top", "right"): ax.spines[s].set_visible(False)
    ax.tick_params(length=0, colors="#444444")

# ---------------------------------------------------------------- 1. medians, four outcomes (t1)
# exact medians from results/results_primary.txt [DESCRIPTIVE_MEANS]
panels = [("Loans as a share\nof assets", 0.589942, 0.395628, "{:.0%}"),
          ("Operating cost per unit\nof income", 0.551620, 0.645493, "{:.2f}"),
          ("Return on assets,\nbefore tax", 0.031532, 0.017278, "{:.1%}"),
          ("Return on assets,\nafter tax", 0.028368, 0.011627, "{:.1%}")]
fig, axes = plt.subplots(1, 4, figsize=(12, 4.2), dpi=200)
for ax, (t, c, b, f) in zip(axes, panels):
    bars = ax.bar(["Cooperatives", "Banks"], [c, b], color=[COOP, BANK], width=0.6)
    for bar, v in zip(bars, (c, b)):
        ax.text(bar.get_x() + bar.get_width()/2, v, f.format(v), ha="center", va="bottom", fontsize=14, color=DARK)
    ax.set_title(t, fontsize=14, color=DARK)
    ax.set_ylim(0, max(c, b)*1.25); ax.set_yticks([]); clean(ax); ax.spines["left"].set_visible(False)
fig.text(0.5, 0.01, "Median institution, 2017 to 2024, all quarters. Differences hold after controlling for size (tables/t2).", ha="center", fontsize=11, color="#666666")
fig.tight_layout(rect=(0, 0.04, 1, 1)); fig.savefig(f"{out}/s_medians.png"); plt.close(fig)

# ---------------------------------------------------------------- 2. tax: operating gap plus tax exemption (t13, controls)
fig, ax = plt.subplots(figsize=(7.5, 4.2), dpi=200)
ax.barh([0], [1.32], color=COOP, height=0.5)
ax.barh([0], [2.15-1.32], left=[1.32], color=COOP, alpha=0.4, height=0.5)
ax.text(1.32/2, 0, "Earned before tax\n1.3 pp", ha="center", va="center", color="white", fontsize=14, fontweight="bold")
ax.text(1.32+(2.15-1.32)/2, 0, "Tax\nexemption\n0.8 pp", ha="center", va="center", color=DARK, fontsize=13)
ax.text(2.15, 0.38, "2.1 pp kept after tax", ha="right", va="bottom", color=DARK, fontsize=14)
ax.set_xlim(0, 2.4); ax.set_ylim(-0.6, 0.7); ax.set_yticks([])
ax.set_xlabel("Return on assets above a bank of the same size, pp")
clean(ax); ax.spines["left"].set_visible(False)
ax.text(0, -0.52, "Median effective tax rate on profit: banks 35%, cooperatives 1%.", fontsize=11, color="#666666")
fig.tight_layout(); fig.savefig(f"{out}/s_tax.png"); plt.close(fig)

# ---------------------------------------------------------------- 3. capital: median vs mean (t1), tail shares (manuscript)
fig, ax = plt.subplots(figsize=(9, 3.8), dpi=200)
rows = [("Cooperatives", 20.46, 22.77, COOP, 1), ("Banks", 18.41, 30.96, BANK, 0)]
for name, med, mean, col, y in rows:
    ax.plot([med, mean], [y, y], color=col, lw=4, alpha=0.5, zorder=1)
    ax.plot(med, y, "o", ms=16, color=col, zorder=2)
    ax.plot(mean, y, "s", ms=14, color=col, zorder=2)
    ax.text(med, y+0.22, f"median {med:.0f}%", ha="center", fontsize=12, color=DARK)
    ax.text(mean, y-0.3, f"mean {mean:.0f}%", ha="center", fontsize=12, color=DARK)
ax.set_yticks([0, 1]); ax.set_yticklabels(["Banks", "Cooperatives"], fontsize=14)
ax.set_ylim(-0.7, 1.6); ax.set_xlim(14, 36)
ax.set_xlabel("Basel capital ratio, percent")
clean(ax)
ax.text(35.8, 1.45, "Quarters with a capital ratio above 50%:\nbanks 14%, cooperatives 1%", ha="right", va="top", fontsize=12, color=DARK,
        bbox=dict(boxstyle="round,pad=0.4", fc="#F2F2F2", ec="none"))
fig.tight_layout(); fig.savefig(f"{out}/s_capital.png"); plt.close(fig)

# crop panel (b) of fig12 for the same slide
im = Image.open("figures/fig12_capital_quantiles.png"); w, h = im.size
im.crop((int(w*0.5), 0, w, h)).save(f"{out}/s_capital_hist.png")

# ---------------------------------------------------------------- 4. comparison group: composition and provisioning gap (t3, t14, manuscript)
fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 4.2), dpi=200, gridspec_kw=dict(width_ratios=[1, 1.3]))
parts = [("Banks", 144, BANK), ("Other lenders and\nnon-bank institutions", 181, "#C9C9C9"), ("Institutions with no loans\nand no deposits", 158, "#8A8A8A")]
left = 0
for name, n, col in parts:
    a1.barh([0], [n], left=[left], color=col, height=0.5)
    a1.text(left + n/2, 0, f"{n}", ha="center", va="center", color="white", fontsize=15, fontweight="bold")
    left += n
a1.text(72, -0.42, "Banks", ha="center", va="top", fontsize=11, color=DARK)
a1.text(234, -0.42, "Other lenders and\nnon-bank institutions", ha="center", va="top", fontsize=11, color=DARK)
a1.text(404, -0.78, "Institutions with\nno loans and no deposits", ha="center", va="top", fontsize=11, color=DARK)
a1.set_xlim(0, 483); a1.set_ylim(-1.5, 0.5); a1.set_yticks([]); a1.set_xticks([])
for s in a1.spines.values(): s.set_visible(False)
a1.set_title("Who is in \"all non-cooperatives\" (483)", fontsize=14, color=DARK)
groups = ["All non-\ncooperatives", "Banks", "Banks,\nsame region", "Commercial\nbanks", "Deposit-funded\nbanks"]
vals = [-3.30, -0.12, 0.10, 0.62, 0.80]; sig = [True, False, False, False, False]
cols = [DARK if s else GREY for s in sig]
bars = a2.bar(groups, vals, color=cols, width=0.6)
for bar, v, s in zip(bars, vals, sig):
    a2.text(bar.get_x()+bar.get_width()/2, v + (0.15 if v >= 0 else -0.15), f"{v:+.1f}" + ("" if s else "\nn.s."), ha="center", va="bottom" if v >= 0 else "top", fontsize=12, color=DARK)
a2.axhline(0, color=DARK, lw=1)
a2.set_ylim(-4.6, 2.2); a2.set_ylabel("Provisioning gap, pp of loans"); a2.tick_params(axis="x", labelsize=11)
clean(a2); a2.set_title("Cooperatives provision less only against the broad group", fontsize=13, color=DARK)
fig.tight_layout(); fig.savefig(f"{out}/s_group.png"); plt.close(fig)

# ---------------------------------------------------------------- 5. credit share: national vs within region (t3)
fig, ax = plt.subplots(figsize=(6.5, 4), dpi=200)
bars = ax.bar(["Banks of the same size,\nanywhere in Brazil", "Banks of the same size,\nin the same region"], [18.8, -2.5], color=[COOP, GREY], width=0.55)
ax.text(0, 19.5, "+19 pp", ha="center", va="bottom", fontsize=15, color=DARK)
ax.text(1, -3.3, "−3 pp, not significant\n(about 18 effective control banks)", ha="center", va="top", fontsize=12, color=DARK)
ax.axhline(0, color=DARK, lw=1); ax.set_ylim(-12, 26)
ax.set_ylabel("Loan share above the bank's,\npp of assets"); clean(ax)
fig.tight_layout(); fig.savefig(f"{out}/s_region.png"); plt.close(fig)
print("done")
