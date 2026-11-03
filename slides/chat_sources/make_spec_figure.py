"""Four specifications on the real size distributions. Curves are traced from figures/fig8_overlap.png
(kernel densities of log total assets, cooperatives and banks); size_curves.json holds the trace.
Numbers below each panel: after-tax return differential, tables/t2_main columns (1) to (4).
Common support bounds from tables/MANIFEST.txt."""
import sys, json, numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
out, curves = sys.argv[1], json.load(open(sys.argv[2]))
COOP, BANK, DARK = "#2A78D6", "#EB6834", "#333333"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 12})
x = np.linspace(7.5, 22.5, 600)
def interp(k):
    c = curves[k]; return np.interp(x, c["x"], c["y"], left=0, right=0)
coop, bank = interp("coop"), interp("bank")
# light smoothing of the pixel trace
kern = np.ones(9)/9; coop = np.convolve(coop, kern, "same"); bank = np.convolve(bank, kern, "same")
lo, hi = 11.3945, 15.6835
fig, axes = plt.subplots(1, 4, figsize=(13, 4.2), dpi=200)
titles = ["(1) Naive comparison", "(2) Adjust for size and quarter", "(3) Match on size", "(4) Common support"]
texts = ["Raw difference in means.", "Regression with log assets\nand quarter effects.", "Banks reweighted so each size\nquintile has the same mix.\nAbout 76 effective control banks.", "Only sizes where both groups exist:\n90% of cooperative quarters,\n48% of bank quarters."]
gaps = ["+1.8 pp", "+2.1 pp", "+1.8 pp", "+1.6 pp"]
for i, ax in enumerate(axes):
    if i < 3:
        ax.fill_between(x, coop, color=COOP, alpha=0.35); ax.plot(x, coop, color=COOP, lw=2)
    if i in (0, 1):
        ax.fill_between(x, bank, color=BANK, alpha=0.35); ax.plot(x, bank, color=BANK, lw=2)
    if i == 2:
        ax.plot(x, bank, color=BANK, lw=1, ls="--", alpha=0.6)
        w = np.where((x > 9.5) & (x < 17.5), coop*0.9, 0)
        ax.fill_between(x, w, color=BANK, alpha=0.35); ax.plot(x, w, color=BANK, lw=2)
    if i == 3:
        m = (x >= lo) & (x <= hi)
        ax.axvspan(lo, hi, color="#EFEFEF", zorder=0)
        ax.plot(x, coop, color=COOP, lw=1, ls="--", alpha=0.5); ax.plot(x, bank, color=BANK, lw=1, ls="--", alpha=0.5)
        ax.fill_between(x[m], coop[m], color=COOP, alpha=0.35); ax.fill_between(x[m], bank[m], color=BANK, alpha=0.35)
    if i == 1:
        ax.annotate("", xy=(14.3, 0.26), xytext=(16.2, 0.26), arrowprops=dict(arrowstyle="<->", color=DARK, lw=1.5))
        ax.text(15.3, 0.275, "size gap\nabsorbed by\ncontrols", ha="center", va="bottom", fontsize=10, color=DARK)
    ax.set_xlim(7.5, 22.5); ax.set_ylim(0, 0.42); ax.set_yticks([]); ax.set_xticks([10, 15, 20])
    ax.tick_params(length=0, colors="#666666", labelsize=9)
    ax.set_xlabel("log total assets", color="#666666")
    for s in ("top", "right", "left"): ax.spines[s].set_visible(False)
    ax.set_title(titles[i], fontsize=13, color=DARK)
    ax.text(0.5, -0.26, texts[i], transform=ax.transAxes, ha="center", va="top", fontsize=10, color=DARK)
    ax.text(0.5, -0.66, gaps[i], transform=ax.transAxes, ha="center", va="top", fontsize=20, color=COOP, fontweight="bold")
axes[0].text(14.3, 0.395, "cooperatives", color=COOP, ha="center", fontsize=11)
axes[0].text(18.8, 0.17, "banks", color=BANK, ha="center", fontsize=11)
fig.text(0.5, 0.02, "Size distributions as in Figure 8 of the paper. Below each panel: cooperative return on assets after tax, above banks, pp of assets; all four significant at one percent.", ha="center", fontsize=10, color="#666666")
fig.tight_layout(rect=(0, 0.12, 1, 1)); fig.subplots_adjust(bottom=0.44)
fig.savefig(out); print("ok")
