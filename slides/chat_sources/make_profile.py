"""Redraw figures/slides/profile.png with a fixed outcome order.
Values are the controlled specification (column 2 of t2_main) in standard deviations
of each outcome, read from the previous figure (CI half-widths agree with t2_main_ci)."""
import json, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

vals = json.load(open(sys.argv[1]))
BLUE, GREY = "#2A78D6", "#8C8C8C"
order = [  # (key, label, tier)
    ("credit",     "Credit / assets",              "stable"),
    ("z",          "Z-score",                      "stable"),
    ("roa_after",  "Return on assets, after tax",  "stable"),
    ("vol",        "Return volatility",            "stable"),
    ("lev",        "Leverage",                     "sign"),
    ("capital",    "Basel capital ratio (pp)",     "sign"),
    ("cti",        "Cost-to-income",               "sign"),
    ("roa_before", "Return on assets, before tax", "null"),
    ("funding",    "Funding ratio",                "null"),
    ("prov",       "Provisioning ratio",           "null"),
    ("margin",     "Intermediation margin",        "null"),
]
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 13})
fig, ax = plt.subplots(figsize=(9.85, 5.4), dpi=200)
n = len(order)
for i, (k, lab, tier) in enumerate(order):
    y = n - 1 - i
    v = vals[k]
    c = GREY if tier == "null" else BLUE
    ax.plot([v["lo"], v["hi"]], [y, y], color=c, lw=3, solid_capstyle="round", zorder=2)
    if tier == "stable":
        ax.plot(v["b"], y, "o", ms=14, color=c, zorder=3)
    else:
        ax.plot(v["b"], y, "o", ms=14, mfc="white", mec=c, mew=3, zorder=3)
ax.axvline(0, color="#333333", lw=1.2, zorder=1)
ax.set_yticks(range(n)); ax.set_yticklabels([o[1] for o in order][::-1])
ax.set_ylim(-0.6, n - 0.4)
ax.set_xlim(-1.4, 1.05)
ax.set_xlabel("Cooperatives minus banks, in standard deviations of the outcome", fontsize=13)
ax.grid(axis="x", color="#E6E6E6", lw=1, zorder=0)
for s in ("top", "right"): ax.spines[s].set_visible(False)
for s in ("left", "bottom"): ax.spines[s].set_color("#BBBBBB")
ax.tick_params(colors="#444444", length=0)
handles = [Line2D([], [], marker="o", ms=12, color=BLUE, ls="", label="stable"),
           Line2D([], [], marker="o", ms=12, mfc="white", mec=BLUE, mew=2.5, ls="", label="stable in sign"),
           Line2D([], [], marker="o", ms=12, mfc="white", mec=GREY, mew=2.5, ls="", label="null: not significant in all four designs")]
ax.legend(handles=handles, loc="upper left", frameon=False, fontsize=12, handletextpad=0.6, borderaxespad=0.2)
fig.tight_layout()
fig.savefig(sys.argv[2])
