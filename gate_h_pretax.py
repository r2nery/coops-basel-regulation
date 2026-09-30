"""Gate H: profitability before taxes.

Line (j) of the IF.data income statement is net income after income tax and social
contribution (h) and profit sharing (i). Cooperative acts are exempt from IRPJ and CSLL
while banks carry both, so an after-tax return on assets could partly reflect taxes.
This gate re-estimates the return on assets on line (g), the result before taxes and
profit sharing, through the same four specifications as the main table, bootstraps the
controlled coefficient, and reports the effective tax burden and the interest on member
capital (line k) of each group. Everything else (sample, winsorisation, matching) is
paper.py's own machinery.

    python gate_h_pretax.py        -> results/pretax_roa.txt
"""
from __future__ import annotations
import numpy as np
import pandas as pd

import paper as P

EXTRA_MAP = {
    "Código": "codigo", "Data": "data_str",
    "Resultado antes da Tributação, Lucro e Participação (g) = (e) + (f)": "pretax",
    "Imposto de Renda e Contribuição Social (h)": "tax",
    "Participação nos Lucros (i)": "profit_sharing",
    "Lucro Líquido (j) = (g) + (h) + (i)": "lucro_j",
    "Juros Sobre Capital Social de Cooperativas (k)": "juros_capital",
}
EXTRA_NUM = ["pretax", "tax", "profit_sharing", "lucro_j", "juros_capital"]
OUT = P.RESULTS / "pretax_roa.txt"
CTRL = "{o} ~ is_coop + log_assets + C(t)"


def main():
    print("building the panel...")
    panel, _, _ = P.build_panel()
    extra, _ = P.load_folder(P.SRC["income"], EXTRA_MAP, EXTRA_NUM)
    panel = panel.merge(extra[["codigo", "date"] + EXTRA_NUM], on=["codigo", "date"], how="left")
    panel, _ = P.decumulate_semiannual(panel, EXTRA_NUM)          # annualised quarterly flows
    A = panel["ativo_total"].clip(lower=1)
    panel["roa_pretax"] = panel["pretax_q"] / A
    P.OUTCOMES["roa_pretax"] = "Return on assets, pre-tax"       # so run_pipeline carries it

    print("running the primary configuration with the pre-tax outcome...")
    res = P.run_pipeline(panel, coop_def="singular", winsor_scope="analysis", use_cluster=True,
                         cti_col="cti_new", roa_col="roa_ann", nim_col="nim_ann",
                         peer_set="banks", coarsen="size_q5")

    # the analysis sample as run_pipeline built it, for the bootstrap and the descriptives
    sub, _, _ = P.select_sample(panel, "singular", "cti_new", "roa_ann", "nim_ann", "banks")
    l2 = sub[sub["full_method"] == 1].copy()
    bounds = {k: tuple(v) for k, v in res["winsor_bounds"].items()}
    l2w, _ = P.winsorize(l2, list(P.OUTCOMES), bounds=bounds)
    print("bootstrapping the controlled coefficient...")
    boot = P.wild_cluster_bootstrap(l2w, "roa_pretax", CTRL, B=P.BOOT_B)

    lines = []
    w = lines.append
    w("GATE H: return on assets before taxes (line g) against the after-tax measure (line j)")
    w("Primary configuration: singular cooperatives vs banks, full-methodology quarters, "
      "winsorised 1/99 on the analysis sample, size-quintile coarsening.")
    w("")
    w("[PRETAX_VS_AFTERTAX]  spec\toutcome\tcoef\tcl_lo\tcl_hi\tcl_p\tN\tn_treated")
    for sl in ("raw", "ctrl", "cem", "trim"):
        for o in ("roa", "roa_pretax"):
            r = res["reg"][sl].get(o)
            if r:
                w(f"{sl}\t{o}\t{r['coef']:.5f}\t{r['cl_lo']:.5f}\t{r['cl_hi']:.5f}\t{r['cl_p']:.4f}\t{r['N']}\t{r['n_treated']}")
    w("")
    w("[RATIO] pre-tax coefficient over after-tax coefficient, by specification")
    for sl in ("raw", "ctrl", "cem", "trim"):
        a, b = res["reg"][sl].get("roa"), res["reg"][sl].get("roa_pretax")
        if a and b:
            w(f"{sl}\t{b['coef'] / a['coef']:.3f}")
    w("")
    w("[MEDIAN] conditional median of the cooperative coefficient (spec, outcome, value)")
    for sl in ("raw", "ctrl", "cem", "trim"):
        for o in ("roa", "roa_pretax"):
            m = res["median"][sl].get(o)
            if m is not None:
                val = m.get("coef", m) if isinstance(m, dict) else m
                w(f"{sl}\t{o}\t{val}")
    w("")
    w("[BOOTSTRAP] controlled specification, pre-tax outcome, restricted wild cluster bootstrap")
    w(str(boot))
    w("")
    # ---- tax burden and interest on member capital, on the analysis sample (unwinsorised flows)
    w("[TAX_BURDEN] institution-quarters of the analysis sample with a positive pre-tax result")
    w("group\tquarters\tshare_tax_zero\tmedian_effective_rate\tp75_effective_rate\tmean_net_over_pretax")
    for g, name in ((1, "cooperatives"), (0, "banks")):
        d = l2[(l2.is_coop == g) & (l2["pretax_q"] > 0)]
        rate = (-d["tax_q"] / d["pretax_q"]).clip(lower=0, upper=1)
        net = (d["lucro_j_q"] / d["pretax_q"]).clip(lower=-1, upper=2)
        w(f"{name}\t{len(d)}\t{(d['tax_q'].fillna(0) == 0).mean():.3f}\t{rate.median():.3f}\t{rate.quantile(0.75):.3f}\t{net.mean():.3f}")
    w("")
    w("[JUROS_CAPITAL] line (k) among cooperative quarters with a positive pre-tax result")
    d = l2[(l2.is_coop == 1) & (l2["pretax_q"] > 0)]
    k = d["juros_capital_q"].fillna(0).abs()
    w(f"quarters\t{len(d)}\tshare_nonzero\t{(k > 0).mean():.3f}\tmedian_k_over_g_when_nonzero\t"
      f"{(k[k > 0] / d.loc[k > 0, 'pretax_q']).median() if (k > 0).any() else float('nan'):.3f}")
    w("")
    w("[UNCONDITIONAL] mean and median of the two measures by group, analysis sample after winsorisation")
    for o in ("roa", "roa_pretax"):
        for g, name in ((1, "cooperatives"), (0, "banks")):
            s = l2w.loc[l2w.is_coop == g, o].dropna()
            w(f"{o}\t{name}\t{s.mean():.5f}\t{s.median():.5f}\t{len(s)}")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
