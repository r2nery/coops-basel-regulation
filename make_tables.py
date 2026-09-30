"""
TABLE GENERATOR — builds the paper's LaTeX tables by PARSING results/*.txt.

This does not re-run the pipeline. It reads the files paper.py already wrote, so the
tables cannot drift from the committed results, it finishes in under a second, and a
failure in one table does not stop the others from being written.

Inputs (produced by `python paper.py`):
    results/results_primary.txt        cooperatives vs banks, size-quintile coarsening
    results/results_broad_peers.txt    cooperatives vs all non-cooperatives
    results/results_within_market.txt  cooperatives vs banks, region-exact matching

Output: tables/t1..t5 as .tex fragments (tabular only, no float wrapper) plus .txt
mirrors carrying the table notes.

    python make_tables.py
"""
from __future__ import annotations
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"
TAB = ROOT / "tables"
TAB.mkdir(exist_ok=True, parents=True)

FILES = {
    "primary": RESULTS / "results_primary.txt",
    "broad": RESULTS / "results_broad_peers.txt",
    "within": RESULTS / "results_within_market.txt",
    "no_s12": RESULTS / "results_no_s12.txt",     # optional; see OPTIONAL below
    "subperiod": RESULTS / "subperiod.txt",       # optional; feeds t9
    "commercial": RESULTS / "results_commercial.txt",   # optional; t3 column 4
    "structural": RESULTS / "results_structural.txt",   # optional; t3 column 5
    "robustness": RESULTS / "robustness.txt",           # optional; winsorisation variants for the t2 tier
    "distribution": RESULTS / "gate_d_distribution.txt",  # optional; q20-q80 share for the t2 tier
}
OPTIONAL = {"no_s12", "subperiod", "commercial", "structural", "robustness", "distribution"}

SPECS = ["raw", "ctrl", "cem", "trim"]
SPEC_HEAD = {"raw": "(1) Raw", "ctrl": "(2) Controls", "cem": "(3) CEM", "trim": "(4) Trim"}

ORDER = [
    ("Basel Capital Ratio (%)", "Basel capital ratio (pp)"),
    ("Leverage (liabilities/assets)", "Leverage"),
    ("Return on Assets", "Return on assets"),
    ("Cost-to-Income Ratio", "Cost-to-income ratio"),
    ("Credit Portfolio / Assets", "Credit portfolio / assets"),
    ("Provisioning (provisions/gross credit)", "Provisioning ratio"),
    ("Net Interest Margin", "Intermediation margin"),
    ("Funding Ratio (captacoes/assets)", "Funding ratio"),
]

# Institution-level stability outcomes, appended to t2/t3/t5 only (not t1/t6). Their
# stars come from HC3, not the clustered p, because the unit is the institution.
STAB_ORDER = [
    ("Return on assets volatility", "Return on assets volatility"),
    ("Z-score", "Z-score"),
]
STAB_LABELS = {lab for lab, _ in STAB_ORDER}


# ------------------------------------------------------------------ parsing
def parse(path: Path) -> dict:
    """Split a results file into sections keyed by their [NAME] header."""
    sections, cur = {}, None
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\[([A-Z0-9_]+)\]", line)
        if m:
            cur = m.group(1)
            sections[cur] = []
            continue
        if cur is None or not line.strip() or line.lstrip().startswith("#"):
            continue
        sections[cur].append(line.split("\t"))
    return sections


def kv(sec):
    return {r[0]: r[1] for r in sec if len(r) >= 2}


def coefs(sections):
    out = {}
    for r in sections.get("MAIN_COEFFICIENTS", []):
        if len(r) < 11:
            continue
        cell = {"coef": float(r[2]), "p": float(r[5]), "hc_p": float(r[8]),
                "N": int(r[9]), "clusters": int(r[10]),
                "cl_lo": float(r[3]), "cl_hi": float(r[4]),
                "hc_lo": float(r[6]), "hc_hi": float(r[7])}
        if len(r) >= 12 and r[11] not in ("na", ""):
            cell["p_boot"] = float(r[11])
        if len(r) >= 15:
            cell["cl_se"], cell["hc_se"] = float(r[13]), float(r[14])
        out.setdefault(r[0], {})[r[1]] = cell
    return out


def pstar(v, key):
    """Significance stars: HC3 for the institution-level stability outcomes, clustered
    for the panel outcomes."""
    return st(v["hc_p"] if key in STAB_LABELS else v["p"])


def medians(sections):
    out = {}
    for r in sections.get("CONDITIONAL_MEDIAN", []):
        if len(r) < 6:
            continue
        out.setdefault(r[0], {})[r[1]] = {"ols": float(r[2]), "med": float(r[3]),
                                          "skew": float(r[5])}
    return out


def descriptives(sections):
    out = {}
    for r in sections.get("DESCRIPTIVE_MEANS", []):
        if len(r) < 7:
            continue
        out[r[0]] = dict(coop_mean=float(r[1]), nc_mean=float(r[2]),
                         coop_med=float(r[3]), nc_med=float(r[4]),
                         coop_n=int(r[5]), nc_n=int(r[6]))
    return out


def stability(sections):
    out = {}
    for r in sections.get("STABILITY", []):
        if len(r) < 8:
            continue
        out[r[0]] = {"rho": r[3], "tier": r[5], "sig": r[6], "amp": r[7]}
    return out


def winsor_variants(sections):
    """Controlled coefficient and clustered p for each outcome under every winsorisation rule."""
    out = {}
    for r in sections.get("WINSOR_VARIANTS", []):
        if len(r) < 6:
            continue
        out.setdefault(r[1], []).append({"coef": float(r[2]), "p": float(r[5])})
    return out


def mid_distribution_share():
    """Mean of the q20-q80 quantile coefficients as a share of the conditional mean, read
    from the gate_d report ('mean of q20-q80 is X, NN% of the OLS coefficient')."""
    path = FILES["distribution"]
    if not path.exists():
        return {}
    out, current = {}, None
    for line in path.read_text(encoding="utf-8").splitlines():
        name = line.strip()
        if any(name == key for key, _ in ORDER):
            current = name
            continue
        m = re.search(r"mean of q20-q80 is .*?, (-?\d+)% of the OLS coefficient", line)
        if m and current:
            out[current] = int(m.group(1)) / 100
            current = None
    return out


def tiers(P):
    """The classification rule stated in the paper (Section 3.4).

    null           unless significant at 5 percent, with one sign, in all four specifications
    stable         significant, keeps significance under every winsorisation rule, varies by
                   less than a factor of two across those rules, and the q20-q80 average of
                   the quantile coefficients is at least half the conditional mean
    stable in sign significant in all four specifications, but fails one of the tail or
                   distribution conditions above
    The institution-level stability outcomes have no winsorisation or quantile variants, so
    they are stable whenever they are significant in all four specifications.
    """
    c = coefs(P)
    wins = winsor_variants(parse(FILES["robustness"])) if FILES["robustness"].exists() else {}
    mid = mid_distribution_share()
    out = {}
    for key, _ in ORDER + STAB_ORDER:
        cells = [c.get(key, {}).get(sp) for sp in SPECS]
        if any(v is None for v in cells):
            continue
        pv = [v["hc_p"] if key in STAB_LABELS else v["p"] for v in cells]
        signs = {v["coef"] > 0 for v in cells}
        if max(pv) >= 0.05 or len(signs) > 1:
            out[key] = "null"
            continue
        if key in STAB_LABELS:
            out[key] = "stable"
            continue
        w = wins.get(key, [])
        mags = [abs(v["coef"]) for v in w]
        tail_ok = bool(w) and all(v["p"] < 0.05 and (v["coef"] > 0) in signs for v in w) \
            and max(mags) < 2 * min(mags)
        dist_ok = key in mid and mid[key] >= 0.5
        out[key] = "stable" if tail_ok and dist_ok else "stable in sign"
    return out


def systems(sections):
    out = {}
    for r in sections.get("SYSTEM_COEFFICIENTS", []):
        if len(r) < 3:
            continue
        if len(r) < 5 or r[2].startswith("--"):
            out.setdefault(r[0], {"n": r[1], "cells": {}, "skip": True})
            continue
        e = out.setdefault(r[0], {"n": r[1], "cells": {}, "skip": False})
        e["skip"] = False
        cell = {"coef": float(r[3]), "p": float(r[4])}
        # appended by paper.py: p_boot, G, G_treated (na where the bootstrap did not run)
        if len(r) >= 8:
            if r[5] not in ("na", ""):
                cell["p_boot"] = float(r[5])
            if r[7] not in ("na", ""):
                cell["G_treated"] = int(r[7])
        e["cells"][r[2]] = cell
        if "G_treated" in cell:
            e["treated"] = cell["G_treated"]           # min over outcomes taken below
    return out


# ------------------------------------------------------------------ helpers
def esc(s):
    return str(s).replace("%", r"\%").replace("&", r"\&").replace("_", r"\_")


def st(p):
    return r"$^{***}$" if p < .001 else r"$^{**}$" if p < .01 else r"$^{*}$" if p < .05 else ""


def dec_for(key):
    return 2 if ("Basel" in key or key == "Z-score") else 4


def f(x, d=3):
    return f"{x:.{d}f}"


def texesc(s):
    """Escape a plain-text note for LaTeX."""
    out = (s.replace("\\", "").replace("&", r"\&").replace("%", r"\%")
            .replace("_", r"\_").replace("#", r"\#"))
    return out


def emit(name, body, note, small=False, colsep="4pt"):
    r"""Write the tabular plus a threeparttable note block.

    The note goes in the .tex file, not only the .txt mirror: the paper wraps each
    \input in a threeparttable, and without a tablenotes block the note never reaches
    the page. `small` shrinks wide tables so the final column is not pushed past the
    right margin.
    """
    size = {True: "small", False: None}.get(small, small)
    pre = (f"\\{size}\n\\setlength{{\\tabcolsep}}{{{colsep}}}\n" if size else "")
    notes = ("\\begin{tablenotes}[flushleft]\\footnotesize\n"
             f"\\item {texesc(note)}\n\\end{{tablenotes}}\n")
    (TAB / f"{name}.tex").write_text(pre + body + "\n" + notes, encoding="utf-8")
    (TAB / f"{name}.txt").write_text(body + "\n\nNOTE: " + note + "\n", encoding="utf-8")
    print(f"  tables/{name}.tex")


def guard(fn, *a):
    try:
        fn(*a)
    except Exception as e:                                     # noqa: BLE001
        print(f"  !! {fn.__name__} failed: {type(e).__name__}: {e}")


# ------------------------------------------------------------------ tables
def t1(P):
    d = descriptives(P)
    rows = []
    for key, lab in ORDER:
        v = d.get(key)
        if not v:
            continue
        k = dec_for(key)
        rows.append(f"{esc(lab)} & {f(v['coop_mean'],k)} & {f(v['coop_med'],k)} & "
                    f"{f(v['nc_mean'],k)} & {f(v['nc_med'],k)} & "
                    f"{v['coop_n']:,} & {v['nc_n']:,} \\\\")
    body = ("\\begin{tabular}{lrrrrrr}\n\\toprule\n"
            " & \\multicolumn{2}{c}{Cooperatives} & \\multicolumn{2}{c}{Banks} "
            "& \\multicolumn{2}{c}{Observations} \\\\\n"
            "\\cmidrule(lr){2-3}\\cmidrule(lr){4-5}\\cmidrule(lr){6-7}\n"
            "Outcome & Mean & Median & Mean & Median & Coop. & Banks \\\\\n\\midrule\n"
            + "\n".join(rows) + "\n\\bottomrule\n\\end{tabular}")
    emit("t1_descriptives", body,
         "Unconditional. The median cooperative Basel ratio exceeds the median bank "
         "ratio while the size-adjusted differential in Table 3 is negative: "
         "cooperatives are smaller than the banks in this population and capital "
         "ratios fall with size.")


def t2(P):
    c, m, s, tier = coefs(P), medians(P), stability(P), tiers(P)
    rows = []
    for key, lab in ORDER + STAB_ORDER:
        if key not in c:
            continue
        k = dec_for(key)
        cells = []
        for sp in SPECS:
            v = c[key].get(sp)
            cells.append(f"{f(v['coef'],k)}{pstar(v,key)}" if v else "")
        md = m.get(key, {}).get("ctrl")
        info = s.get(key, {})
        rho = info.get("rho", "")
        rho = "" if rho in ("na", "") else f"{float(rho):.2f}"
        if key == STAB_ORDER[0][0]:
            rows.append("\\midrule")
        rows.append(f"{esc(lab)} & " + " & ".join(cells)
                    + f" & {f(md['med'],k) if md else ''} & {rho}"
                      f" & {esc(tier.get(key, ''))} \\\\")
    body = ("\\begin{tabular}{lrrrrrrl}\n\\toprule\n"
            "Outcome & " + " & ".join(SPEC_HEAD[x] for x in SPECS)
            + " & Median (2) & $\\rho$ & Tier \\\\\n\\midrule\n"
            + "\n".join(rows) + "\n\\bottomrule\n\\end{tabular}")
    emit("t2_main", body, small="footnotesize", colsep="3pt", note=
         "Standard errors clustered by institution, HC3 for the last two rows; "
         "* p<0.05, ** p<0.01, *** p<0.001, confirmed by a wild cluster bootstrap. "
         "Median (2): conditional median of column (2). rho = |b_trim|/|b_raw|. "
         "Tier: see Section 3.4.")


def t2_ci(P):
    """Supplement version of the main table: every cell with its 95 percent interval."""
    c = coefs(P)
    rows = []
    for key, lab in ORDER + STAB_ORDER:
        if key not in c:
            continue
        k = dec_for(key)
        cells, cis = [], []
        for sp in SPECS:
            v = c[key].get(sp)
            if not v:
                cells.append("")
                cis.append("")
                continue
            lo, hi = ((v["hc_lo"], v["hc_hi"]) if key in STAB_LABELS
                      else (v["cl_lo"], v["cl_hi"]))
            cells.append(f"{f(v['coef'],k)}{pstar(v,key)}")
            cis.append(f"[{f(lo,k)}, {f(hi,k)}]")
        if key == STAB_ORDER[0][0]:
            rows.append("\\midrule")
        rows.append(f"{esc(lab)} & " + " & ".join(cells) + " \\\\")
        rows.append(" & " + " & ".join(cis) + " \\\\")
    body = ("\\begin{tabular}{lrrrr}\n\\toprule\n"
            "Outcome & " + " & ".join(SPEC_HEAD[x] for x in SPECS)
            + " \\\\\n\\midrule\n" + "\n".join(rows) + "\n\\bottomrule\n\\end{tabular}")
    emit("t2_main_ci", body, small="footnotesize", note=
         "Supplement version of the main table: each coefficient with its 95 percent "
         "confidence interval beneath it, clustered by institution for the eight panel "
         "outcomes and HC3 for the two institution-level stability rows. Stars as in the "
         "main table.")


def t3(P, B, W, C=None, S=None):
    """Peer ladder: broad, banks, banks within region, and, when their results files
    exist, commercial (b1) and structural (b1 with positive deposits in every quarter).
    Clustered standard errors (HC3 for the stability rows) under every coefficient."""
    srcs = [("All non-cooperatives", coefs(B), "ctrl", B),
            ("Banks", coefs(P), "ctrl", P),
            ("Banks, within region", coefs(W), "cem", W)]
    if C is not None:
        srcs.append(("Commercial", coefs(C), "ctrl", C))
    if S is not None:
        srcs.append(("Structural", coefs(S), "ctrl", S))
    rows = []
    for key, lab in ORDER + STAB_ORDER:
        k = dec_for(key)
        cells, ses = [], []
        for _, src, spec, _ in srcs:
            v = src.get(key, {}).get(spec)
            cells.append(f"{f(v['coef'],k)}{pstar(v,key)}" if v else "")
            se = None
            if v:
                se = v.get("hc_se") if key in STAB_LABELS else v.get("cl_se")
            ses.append(f"({f(se,k)})" if se is not None and se == se else "")
        if key == STAB_ORDER[0][0]:
            rows.append("\\midrule")
        rows.append(f"{esc(lab)} & " + " & ".join(cells) + " \\\\")
        rows.append(" & " + " & ".join(ses) + " \\\\")
    counts = [kv(s.get("SAMPLE", [])).get("analysis_noncoops", "") for *_, s in srcs]
    body = ("\\setlength{\\tabcolsep}{3pt}\n"
            "\\begin{tabular}{l" + "r" * len(srcs) + "}\n\\toprule\n"
            "Outcome & " + " & ".join(h for h, *_ in srcs) + " \\\\\n"
            "\\midrule\n" + "\n".join(rows) + "\n\\midrule\n"
            "Comparison institutions & " + " & ".join(counts) + " \\\\\n"
            "\\bottomrule\n\\end{tabular}")
    emit("t3_peer_ladder", body, small="footnotesize", note=
         "Controlled specification (log assets and quarter fixed effects) in every column "
         "except the third, which additionally exact-matches on macro-region. Standard "
         "errors clustered by institution in parentheses; HC3 for the two institution-level "
         "stability rows. The broad group includes 158 institutions with a median of zero "
         "credit and zero funds raised. Commercial: b1 banks only. Structural: b1 banks with strictly "
         "positive total deposits in every full-methodology quarter of their presence in "
         "the sample, an ex-ante business-model definition of a deposit-funded bank.")


def t4(P):
    sysd = systems(P)
    order = ["Basel Capital Ratio (%)", "Leverage (liabilities/assets)",
             "Return on Assets", "Provisioning (provisions/gross credit)"]
    short = {"Basel Capital Ratio (%)": "Basel (pp)",
             "Leverage (liabilities/assets)": "Leverage",
             "Return on Assets": "ROA",
             "Provisioning (provisions/gross credit)": "Provisioning"}
    def sp(v):
        # stars from the wild cluster bootstrap p-value where available, else asymptotic
        return st(v.get("p_boot", v["p"]))

    rows = []
    marg = {}
    for name, e in sysd.items():
        if e.get("skip"):
            rows.append(f"{esc(name)} & {e['n']} & -- & \\multicolumn{{{len(order)}}}{{c}}"
                        f"{{fewer than five institutions, not estimated}} \\\\")
            continue
        gt = [c["G_treated"] for c in e["cells"].values() if "G_treated" in c]
        treated = str(max(gt)) if gt else "--"
        cells = []
        for o in order:
            v = e["cells"].get(o)
            cells.append(f"{f(v['coef'],dec_for(o))}{sp(v)}" if v else "")
            if v and "p_boot" in v:
                marg[(name, o)] = v["p_boot"]
        rows.append(f"{esc(name)} & {e['n']} & {treated} & " + " & ".join(cells) + " \\\\")
    body = ("\\begin{tabular}{lrr" + "r" * len(order) + "}\n\\toprule\n"
            "System & Inst. & Treated & " + " & ".join(short[o] for o in order)
            + " \\\\\n\\midrule\n" + "\n".join(rows) + "\n\\bottomrule\n\\end{tabular}")
    sicoob = marg.get(("Sicoob", "Basel Capital Ratio (%)"))
    indroa = marg.get(("Independent", "Return on Assets"))
    note = (
        "Each system estimated against the same bank comparison group under the "
        "controlled specification. Stars are from a restricted wild cluster bootstrap "
        "(Rademacher weights): * p<0.05, ** p<0.01, *** p<0.001. 'Inst.' is the number "
        "of cooperatives; 'Treated' is the number of treated clusters that carry a usable "
        "observation, which governs reliability. The independent group lists six "
        "cooperatives but one contributes no usable observation, so five treated clusters "
        "enter every estimate; with five treated clusters the smallest attainable "
        "bootstrap p-value is about 0.03.")
    if sicoob is not None:
        note += f" Sicoob's capital coefficient has a bootstrap p-value of {sicoob:.3f}."
    if indroa is not None:
        note += (f" The independent return-on-assets coefficient carries an asymptotic "
                 f"p-value below 0.001 but a bootstrap p-value of {indroa:.3f}, the "
                 f"expected gap when only five clusters are treated.")
    emit("t4_systems", body, note)


def t5(P):
    m, c = medians(P), coefs(P)
    rows = []
    for key, lab in ORDER + STAB_ORDER:
        md = m.get(key, {}).get("ctrl")
        cf = c.get(key, {}).get("ctrl")
        if not (md and cf):
            continue
        k = dec_for(key)
        ratio = md["med"] / cf["coef"] if abs(cf["coef"]) > 1e-12 else float("nan")
        agree = "yes" if (md["med"] > 0) == (cf["coef"] > 0) else "\\textbf{no}"
        if key == STAB_ORDER[0][0]:
            rows.append("\\midrule")
        rows.append(f"{esc(lab)} & {f(cf['coef'],k)}{pstar(cf,key)} & "
                    f"{f(md['med'],k)} & {ratio:.2f} & {md['skew']:.2f} & {agree} \\\\")
    body = ("\\begin{tabular}{lrrrrc}\n\\toprule\n"
            "Outcome & Conditional mean & Conditional median & Ratio & Skewness "
            "& Same sign \\\\\n\\midrule\n" + "\n".join(rows)
            + "\n\\bottomrule\n\\end{tabular}")
    emit("t5_mean_vs_median", body, small=True, note=
         "Controlled specification, cooperatives against banks. A ratio well below one "
         "means the mean differential is produced by the tail of the outcome "
         "distribution rather than by the typical institution; a sign disagreement "
         "means the mean result does not describe the centre of the distribution.")


def t6(P, S):
    """Segment-restricted robustness: primary against the same specification with
    modal-S1 and modal-S2 institutions removed."""
    a, b = coefs(P), coefs(S)
    rows = []
    for key, lab in ORDER:
        x = a.get(key, {}).get("ctrl")
        y = b.get(key, {}).get("ctrl")
        if not (x and y):
            continue
        k = dec_for(key)
        rows.append(f"{esc(lab)} & {f(x['coef'],k)}{st(x['p'])} & "
                    f"{f(y['coef'],k)}{st(y['p'])} \\\\")
    body = ("\\begin{tabular}{lrr}\n\\toprule\n"
            "Outcome & All segments & Excluding S1 and S2 \\\\\n\\midrule\n"
            + "\n".join(rows) + "\n\\bottomrule\n\\end{tabular}")
    ss = kv(S.get("SAMPLE", []))
    excl_note = ""
    if ss.get("analysis_noncoops") and ss.get("analysis_obs"):
        excl_note = (f" The restricted column compares the 130 cooperatives with "
                     f"{ss['analysis_noncoops']} banks over {int(ss['analysis_obs']):,} "
                     f"institution-quarters.")
    emit("t6_segment_restricted", body,
         "Controlled specification. Segments 1 and 2 carry the systemic capital buffer, "
         "the liquidity ratios and eligibility for internal models under Res. CMN "
         "4.553/2017, and contain no cooperatives. Institutions are excluded on their "
         "modal segment." + excl_note)


def subper_coefs(sections):
    out = {}
    for r in sections.get("SUBPERIOD_COEFFICIENTS", []):
        if len(r) < 6:
            continue
        cell = {"coef": float(r[2]), "p": float(r[5])}
        if len(r) >= 7 and r[6] not in ("na", ""):
            cell["p_boot"] = float(r[6])
        out.setdefault(r[0], {})[r[1]] = cell
    return out


def subper_counts(sections):
    out = {}
    for r in sections.get("SUBPERIOD_COUNTS", []):
        if len(r) < 4:
            continue
        out[r[0]] = {"obs": r[1], "n_coop": r[2], "n_bank": r[3]}
    return out


def t9(SP):
    c = subper_coefs(SP)
    n = subper_counts(SP)
    cols = ("full", "p1", "p2")
    head = {"full": "Full sample", "p1": "2017Q1--2021Q4", "p2": "2022Q1--2024Q4"}
    rows, disagree = [], 0
    for key, lab in ORDER:
        k = dec_for(key)
        cells = []
        for w in cols:
            v = c.get(key, {}).get(w)
            cells.append(f"{f(v['coef'],k)}{st(v['p'])}" if v else "")
            if v and "p_boot" in v and (v["p"] < 0.05) != (v["p_boot"] < 0.05):
                disagree += 1
        rows.append(f"{esc(lab)} & " + " & ".join(cells) + " \\\\")
    foot = []
    for label, field in (("Observations", "obs"), ("Cooperatives", "n_coop"), ("Banks", "n_bank")):
        vals = " & ".join(f"{int(n[w][field]):,}" if w in n else "" for w in cols)
        foot.append(f"{label} & {vals} \\\\")
    body = ("\\begin{tabular}{lrrr}\n\\toprule\n"
            "Outcome & " + " & ".join(head[w] for w in cols) + " \\\\\n\\midrule\n"
            + "\n".join(rows) + "\n\\midrule\n" + "\n".join(foot)
            + "\n\\bottomrule\n\\end{tabular}")
    boot_note = ("Bootstrap p-values (1,999 replications) agree with the clustered stars "
                 "in every cell." if disagree == 0 else
                 f"The bootstrap and clustered tests disagree at the 5 percent level in "
                 f"{disagree} of the twenty-four cells.")
    emit("t9_subperiod", body,
         "Controlled specification (log assets and quarter fixed effects), cooperatives "
         "against banks, estimated on the full sample and on each subperiod. Standard "
         "errors clustered by institution. The boundary is 3 January 2022, the entry "
         "into force of Resolutions CMN 4.955 and 4.958 of 2021, which consolidated the "
         "capital and minimum-requirement rules. " + boot_note)


# ------------------------------------------------------------------ main
def main():
    missing = [str(p) for k, p in FILES.items()
               if not p.exists() and k not in OPTIONAL]
    if missing:
        print("Missing results files. Run `python paper.py` first.\n  "
              + "\n  ".join(missing))
        sys.exit(1)

    P, B, W = (parse(FILES[k]) for k in ("primary", "broad", "within"))
    S = parse(FILES["no_s12"]) if FILES["no_s12"].exists() else None
    C = parse(FILES["commercial"]) if FILES["commercial"].exists() else None
    S2 = parse(FILES["structural"]) if FILES["structural"].exists() else None
    s = kv(P.get("SAMPLE", []))
    print(f"primary: {s.get('analysis_coops')} cooperatives, "
          f"{s.get('analysis_noncoops')} banks, {s.get('analysis_obs')} observations")
    print("writing tables:")

    guard(t1, P)
    guard(t2, P)
    guard(t2_ci, P)
    guard(t3, P, B, W, C, S2)
    guard(t4, P)
    guard(t5, P)
    if S is not None:
        guard(t6, P, S)
    if FILES["subperiod"].exists():
        guard(t9, parse(FILES["subperiod"]))

    ov = kv(P.get("OVERLAP", []))
    cw = kv(P.get("CEM_WEIGHTING", []))
    (TAB / "MANIFEST.txt").write_text(
        "TABLE MANIFEST\n"
        "built by make_tables.py from results/*.txt (no recomputation)\n\n"
        f"primary sample: {s.get('analysis_coops')} cooperatives, "
        f"{s.get('analysis_noncoops')} banks, {s.get('analysis_obs')} obs, "
        f"{s.get('date_range')}\n"
        f"common support: [{ov.get('log_assets_lo')}, {ov.get('log_assets_hi')}], "
        f"coop inside {ov.get('coop_inside_pct')}%, "
        f"banks inside {ov.get('nc_inside_pct')}%\n"
        f"CEM effective control sample: {cw.get('effective_n_controls')}\n\n"
        "t1_descriptives     unconditional means and medians\n"
        "t2_main             cooperative differential, four specifications\n"
        "t3_peer_ladder      sensitivity to the comparison group\n"
        "t4_systems          heterogeneity by cooperative system\n"
        "t5_mean_vs_median   conditional mean against conditional median\n",
        encoding="utf-8")
    print(f"\nwrote {TAB}")


if __name__ == "__main__":
    main()