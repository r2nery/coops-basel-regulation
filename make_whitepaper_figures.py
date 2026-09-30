"""Portuguese figures for the Sistema OCB whitepaper.

Drawn from the same results files and the same analysis sample as make_figures.py, through
its own loaders, so nothing here can drift from the paper's tables. No regression is run.

    python make_whitepaper_figures.py

    figures/wp1_metodologia.png   instituições por metodologia prudencial ao longo do tempo
    figures/wp2_capital.png       índice de Basileia: coeficiente por quantil e as duas distribuições
    figures/wp3_perfil.png        todos os indicadores contra bancos, em desvios-padrão, com a classificação
    figures/wp4_grupos.png        quatro indicadores ao longo dos cinco grupos de comparação
"""
from __future__ import annotations
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker
import matplotlib.dates

import paper as P
import make_tables as MT
import make_figures as MF
from make_figures import COOP, BANK, INK, INK2, MUTED, AXIS, BAND, ygrid, xgrid, save

W = 6.5   # inches: A4 with the template's 2 cm side margins is 17 cm

PT = {  # results-file label -> Portuguese label
    "Basel Capital Ratio (%)": "Índice de Basileia (p.p.)",
    "Leverage (liabilities/assets)": "Alavancagem",
    "Return on Assets": "Retorno sobre ativos",
    "Cost-to-Income Ratio": "Custo / receita",
    "Credit Portfolio / Assets": "Crédito / ativos",
    "Provisioning (provisions/gross credit)": "Provisão / crédito",
    "Net Interest Margin": "Margem de intermediação",
    "Funding Ratio (captacoes/assets)": "Captações / ativos",
    "Return on assets volatility": "Volatilidade do retorno",
    "Z-score": "Z-score",
}
RUNGS = [("Todas as não cooperativas", "broad", "ctrl"), ("Bancos", "primary", "ctrl"),
         ("Bancos, mesma região", "within", "cem"), ("Bancos comerciais", "commercial", "ctrl"),
         ("Bancos com depósitos", "structural", "ctrl")]


# ------------------------------------------------------------------ figura 1
def fig_metodologia(panel):
    pf = panel.copy()
    pf["grp"] = np.where(pf["is_coop_any"] == 1, "coop", "noncoop")
    fig, ax = plt.subplots(1, 3, figsize=(W, 2.2))
    shares = {}
    for a, grp, c, title in [(ax[0], "coop", COOP, "(a) Cooperativas"),
                             (ax[1], "noncoop", BANK, "(b) Não cooperativas")]:
        m = (pf[pf.grp == grp].groupby(["year_q", "full_method"])["codigo"].nunique()
             .unstack(fill_value=0))
        x = m.index.to_timestamp()
        simp, full = m.get(0, 0 * m.sum(axis=1)), m.get(1, 0 * m.sum(axis=1))
        a.fill_between(x, 0, simp, color=AXIS, lw=0)
        a.fill_between(x, simp, simp + full, color=c, alpha=0.85, lw=0)
        a.set_title(title)
        a.set_ylim(0, None)
        ygrid(a)
        mid = len(x) // 2
        a.text(x[mid], float(simp.iloc[mid]) / 2, "Simplificada", ha="center", va="center",
               fontsize=7, color=INK)
        a.text(x[mid], float(simp.iloc[mid]) + float(full.iloc[mid]) / 2, "Completa",
               ha="center", va="center", fontsize=7, color="white")
        shares[grp] = full / (simp + full) * 100
        a.set_xlim(x.min(), x.max())
    ax[0].set_ylabel("Número de instituições")
    for grp, c, lab in [("coop", COOP, "Cooperativas"), ("noncoop", BANK, "Não cooperativas")]:
        s = shares[grp]
        ax[2].plot(s.index.to_timestamp(), s.values, color=c)
        ax[2].text(s.index[1].to_timestamp(), 48 if grp == "noncoop" else 24, lab,
                   ha="left", va="bottom", fontsize=7, color=INK2)
    ax[2].set_title("(c) Parcela na metod. completa")
    ax[2].set_ylabel("Percentual")
    ax[2].set_ylim(0, 105)
    ygrid(ax[2])
    for a in ax:
        a.xaxis.set_major_locator(matplotlib.dates.YearLocator(2))
        a.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%Y"))
    fig.tight_layout(w_pad=1.2)
    save(fig, "wp1_metodologia.png")


# ------------------------------------------------------------------ figura 2
def fig_capital(l2, txt):
    q = MF.quantile_rows(txt)["Basel Capital Ratio (%)"]
    qs = [10, 20, 30, 40, 50, 60, 70, 80, 90]
    band = MF.capital_band()
    fig, ax = plt.subplots(1, 2, figsize=(W, 2.8))
    a = ax[0]
    floor = -38.0
    a.axhline(0, color=AXIS, lw=0.8)
    a.axhline(q["ols"], color=MUTED, lw=1)
    a.text(10, q["ols"] - 1.0, "média condicional", fontsize=7, color=INK2, ha="left", va="top")
    if band:
        bq = sorted(band)
        a.fill_between([100 * x for x in bq], [band[x][1] for x in bq],
                       [band[x][2] for x in bq], color=COOP, alpha=0.18, lw=0)
    a.plot(qs, q["q"], color=COOP, marker="o", ms=4, mec="white", mew=0.8, zorder=3)
    cross = next((qs[i] + (qs[i + 1] - qs[i]) * q["q"][i] / (q["q"][i] - q["q"][i + 1])
                  for i in range(len(qs) - 1) if q["q"][i] > 0 >= q["q"][i + 1]), None)
    if cross:
        a.annotate(f"positivo abaixo do\n~{round(cross / 10) * 10}º percentil",
                   (cross, 0), xytext=(cross + 4, 5.5), fontsize=7, color=INK, va="bottom",
                   arrowprops=dict(arrowstyle="-", color=INK2, lw=0.6))
    lo90 = band.get(0.9, (None, None))[1] if band else None
    if lo90 is not None and lo90 < floor:
        a.annotate(f"faixa até {lo90:.0f}".replace("-", "−"), (91.5, floor),
                   xytext=(70, floor + 3), ha="right", va="center", fontsize=6.5,
                   color=INK2, arrowprops=dict(arrowstyle="->", color=INK2, lw=0.6))
    a.set_ylim(floor, 12)
    a.set_xticks(qs)
    a.set_xlim(7, 93)
    a.set_xlabel("Quantil da distribuição do índice de Basileia")
    a.set_ylabel("Coeficiente da cooperativa (p.p.)")
    a.set_title("(a) Diferença ao longo da distribuição")
    ygrid(a)

    b = ax[1]
    col = "basileia_raw" if "basileia_raw" in l2.columns else "basileia_num"
    c = l2.loc[l2.is_coop == 1, col].dropna()
    k = l2.loc[l2.is_coop == 0, col].dropna()
    lo, hi = 5.0, 900.0
    c, k = c.clip(lower=lo, upper=hi), k.clip(lower=lo, upper=hi)
    bins = np.logspace(np.log10(lo), np.log10(hi), 40)
    for s, cc in [(k, BANK), (c, COOP)]:
        w = np.full(len(s), 100.0 / len(s))
        b.hist(s, bins=bins, weights=w, color=cc, alpha=0.25, lw=0)
        b.hist(s, bins=bins, weights=w, histtype="step", color=cc, lw=1.2)
    b.set_xscale("log")
    b.set_xticks([10, 20, 50, 100, 200, 500])
    b.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:g}"))
    b.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    sc50, sb50 = MF.share_above(txt, 50)
    sc100, sb100 = MF.share_above(txt, 100)
    top = b.get_ylim()[1]
    b.vlines(50, 0, top * 0.58, color=INK2, lw=0.8)
    b.vlines(100, 0, top * 0.26, color=INK2, lw=0.8)
    b.text(53, top * 0.58, f"acima de 50%\nbancos {sb50:.0f}%\ncooperativas {sc50:.0f}%",
           fontsize=6.5, color=INK, va="top")
    b.text(106, top * 0.30, f"acima de 100%\nbancos {sb100:.1f}%\ncooperativas {sc100:.1f}%",
           fontsize=6.5, color=INK, va="top")
    b.set_xlabel("Índice de Basileia (%), escala logarítmica")
    b.set_ylabel("Percentual dos trimestres")
    b.set_title("(b) As duas distribuições")
    b.text(33, top * 0.66, "Cooperativas", fontsize=7, color=COOP, fontweight="bold")
    b.text(3.9, top * 0.66, "Bancos", fontsize=7, color=BANK, fontweight="bold", ha="left")
    ygrid(b)
    fig.tight_layout(w_pad=1.5)
    save(fig, "wp2_capital.png")


# ------------------------------------------------------------------ figura 3
def fig_perfil(l2):
    c = MT.coefs(MT.parse(MT.FILES["primary"]))
    tiers = MT.tiers(MT.parse(MT.FILES["primary"]))
    inst, _, _ = P.collapse_stability(l2)
    sd = {k: l2[MF.KEY[k]].std() for k, _ in MT.ORDER}
    sd["Return on assets volatility"] = inst["roa_vol"].std()
    sd["Z-score"] = inst["zscore"].std()
    order = ["Credit Portfolio / Assets", "Return on Assets", "Return on assets volatility",
             "Z-score", "Cost-to-Income Ratio", "Basel Capital Ratio (%)",
             "Leverage (liabilities/assets)", "Provisioning (provisions/gross credit)",
             "Net Interest Margin", "Funding Ratio (captacoes/assets)"]
    style = {"stable": dict(mfc=COOP, mec=COOP), "stable in sign": dict(mfc="white", mec=COOP),
             "null": dict(mfc="white", mec=MUTED)}
    fig, ax = plt.subplots(figsize=(W, 3.4))
    ax.axvline(0, color=INK2, lw=1)
    y = np.arange(len(order))[::-1]
    for yy, k in zip(y, order):
        v = c[k]["ctrl"]
        stab = k in MT.STAB_LABELS
        lo, hi = (v["hc_lo"], v["hc_hi"]) if stab else (v["cl_lo"], v["cl_hi"])
        t = tiers.get(k, "null")
        col = MUTED if t == "null" else COOP
        ax.plot([lo / sd[k], hi / sd[k]], [yy, yy], color=col, lw=1.8, solid_capstyle="round",
                alpha=0.8)
        ax.plot(v["coef"] / sd[k], yy, "o", ms=7, mew=1.6, zorder=3, **style[t])
    ax.set_yticks(y)
    ax.set_yticklabels([PT[k] for k in order])
    ax.set_xlabel("Cooperativas menos bancos, em desvios-padrão do indicador")
    for t, lab in [("stable", "estável"), ("stable in sign", "estável no sinal"),
                   ("null", "nulo: não significativo nas quatro especificações")]:
        ax.plot([], [], "o", ms=6, mew=1.5, label=lab, **style[t])
    ax.legend(loc="upper left", frameon=False)
    xgrid(ax)
    fig.tight_layout()
    save(fig, "wp3_perfil.png")


# ------------------------------------------------------------------ figura 4
def fig_grupos():
    srcs = [(n, MT.coefs(MT.parse(MT.FILES[k])), sp) for n, k, sp in RUNGS if MT.FILES[k].exists()]
    keys = ["Return on Assets", "Cost-to-Income Ratio",
            "Provisioning (provisions/gross credit)", "Net Interest Margin"]
    fig, axes = plt.subplots(2, 2, figsize=(W, 3.6), sharey=True)
    ypos = np.arange(len(srcs))[::-1]
    for a, key in zip(axes.flatten(), keys):
        a.axvline(0, color=AXIS, lw=0.8)
        reach = 0.0
        for yy, (name, c, sp) in zip(ypos, srcs):
            v = c.get(key, {}).get(sp)
            if not v:
                continue
            lo, hi = v["cl_lo"], v["cl_hi"]
            reach = max(reach, abs(lo), abs(hi))
            a.plot([lo, hi], [yy, yy], color=COOP, lw=1.2, solid_capstyle="round")
            a.plot(v["coef"], yy, "o", ms=4.2, mew=1.1, mec=COOP,
                   mfc=COOP if v["p"] < 0.05 else "white", zorder=3)
            if name == "Bancos":
                a.axhspan(yy - 0.42, yy + 0.42, color=BAND, lw=0, zorder=0)
        a.set_xlim(-1.08 * reach, 1.08 * reach)
        a.set_title(PT[key], fontsize=7.5, loc="center")
        a.tick_params(axis="x", labelsize=6.5)
        a.xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(nbins=4, symmetric=True))
        a.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:g}"))
        xgrid(a)
    axes[0, 0].set_yticks(ypos)
    for r in range(2):
        axes[r, 0].set_yticklabels([n for n, *_ in srcs])
    for a in axes.flatten():
        a.set_ylim(-0.6, len(srcs) - 0.4)
    fig.tight_layout(w_pad=1.5, h_pad=1.0)
    save(fig, "wp4_grupos.png")


def main():
    print("building the panel (no regressions)...")
    panel, _, _ = P.build_panel()
    _, l2 = MF.analysis_sample(panel, "banks")
    txt = MF.gate_d_text()
    print("writing figures:")
    fig_metodologia(panel)
    fig_capital(l2, txt)
    fig_perfil(l2)
    fig_grupos()


if __name__ == "__main__":
    main()
