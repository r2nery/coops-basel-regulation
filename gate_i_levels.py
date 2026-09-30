"""Gate I: two descriptive checks quoted in the text.

1. Network boundary. Banks enter the comparison partly as prudential conglomerates while
   cooperatives enter as singulars with their centrals excluded. This gate sizes the
   centrals against the singulars (assets, regulatory capital, equity, credit, and
   administrative plus personnel expenses) in the last quarter of the window, so the text
   can bound what a network-level aggregation could change.
2. Levels. The median annualised return on assets of the singular cooperatives by year,
   for comparison with the Central Bank's published Panorama figures.

    python gate_i_levels.py        -> results/network_levels.txt
"""
from __future__ import annotations
import paper as P

OUT = P.RESULTS / "network_levels.txt"


def main():
    panel, _, _ = P.build_panel()
    coop = panel[panel["coop_class"].isin(["singular", "central"])].copy()
    last = coop[coop["date"] == coop["date"].max()]
    cols = ["ativo_total", "pat_referencia", "patrimonio_liquido", "carteira_credito"]
    g = last.groupby("coop_class")[cols].sum()
    opex = last.assign(opex=last["despesas_admin"].abs() + last["despesas_pessoal"].abs()) \
        .groupby("coop_class")["opex"].sum()
    lines = ["GATE I: network boundary and levels", ""]
    lines.append(f"[CENTRALS_VS_SINGULARS] last quarter {last['date'].max().date()}, sums over institutions")
    lines.append("item\tcentrals\tsingulars\tratio_central_over_singular")
    for c in cols:
        lines.append(f"{c}\t{g.loc['central', c]:.0f}\t{g.loc['singular', c]:.0f}\t{g.loc['central', c] / g.loc['singular', c]:.3f}")
    lines.append(f"admin_plus_personnel_expenses\t{opex['central']:.0f}\t{opex['singular']:.0f}\t{opex['central'] / opex['singular']:.3f}")
    lines.append(f"n_institutions\t{last.loc[last.coop_class == 'central', 'codigo'].nunique()}\t"
                 f"{last.loc[last.coop_class == 'singular', 'codigo'].nunique()}\t")
    lines.append("")
    lines.append("[MEDIAN_ROA_BY_YEAR] annualised de-cumulated return on assets, median over institution-quarters")
    lines.append("year\tall_singulars\tfull_method_singulars")
    s = coop[coop["coop_class"] == "singular"]
    fm = s[s["full_method"] == 1]
    for y in sorted(s["date"].dt.year.unique()):
        a = s.loc[s["date"].dt.year == y, "roa_ann"].median()
        b = fm.loc[fm["date"].dt.year == y, "roa_ann"].median()
        lines.append(f"{y}\t{a:.4f}\t{b:.4f}")
    lines.append("")
    lines.append("# Panorama do SNCC (BCB, 2025 edition): singulars' ROA 2.9% in 2023 and 2.4% in 2024; "
                 "2026 edition: 2.5% at end 2025.")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
