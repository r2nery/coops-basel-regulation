"""Build the two Word documents for the ICA CCR 2026 proceedings on the conference template.

  python make_docx.py            # both documents
  python make_docx.py abstract   # paper/ICACCR2026_abstract_Nery_Victorino_Rangel.docx
  python make_docx.py paper      # paper/ICACCR2026_paper_Nery_Victorino_Rangel.docx

The abstract comes from expanded_abstract.md. The paper comes from paper/paper.tex,
tables/t2_main.tex, figures/*.png and paper/references.bib. Both documents are written by
filling the body of the template
"paper/FINAL ABSTRACT-Mandatory abstract for conference proceedings.docx", so its styles,
page size, running heads and first-page logos are kept. Citations and the reference list
follow APA 7th edition (author-year), generated from the bib file. Nothing here needs more
than the standard library and Pillow.
"""
import os
import re
import sys
import zipfile
from dataclasses import dataclass, field

from PIL import Image

ROOT = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(ROOT, "paper", "FINAL ABSTRACT-Mandatory abstract for conference proceedings.docx")
BIB = os.path.join(ROOT, "paper", "references.bib")
TEX = os.path.join(ROOT, "paper", "paper.tex")
MD = os.path.join(ROOT, "expanded_abstract.md")
OUT_ABSTRACT = os.path.join(ROOT, "paper", "ICACCR2026_abstract_Nery_Victorino_Rangel.docx")
OUT_PAPER = os.path.join(ROOT, "paper", "ICACCR2026_paper_Nery_Victorino_Rangel.docx")

TEXT_WIDTH = 9639 - 907 - 1134          # twips between the template's margins
EMU_PER_TWIP = 635

TITLE = ("Institutional Profiles Under a Common Prudential Framework: "
         "Evidence from Brazilian Credit Cooperatives and Banks")
SHORT_TITLE = "Institutional Profiles Under a Common Prudential Framework"
AUTHORS = [("Arthur Gomes Nery", "a"), ("Thiago de Oliveira Victorino", "b"), ("Rodrigo Lima Rangel", "c")]
AUTHORS_SHORT = "Nery, Victorino and Rangel"
AFFILIATIONS = [
    ("a", "Organization of Brazilian Cooperatives (OCB System), Brasília, Brazil, ORCID [0000-0000-0000-0000], arthurgomesqq@gmail.com"),
    ("b", "Organization of Brazilian Cooperatives (OCB System) and Department of Administration, University of Brasilia, Brasília, Brazil, ORCID [0000-0000-0000-0000], [email]"),
    ("c", "Organization of Brazilian Cooperatives (OCB System), Brasília, Brazil, ORCID [0000-0000-0000-0000], [email]"),
]
AWARD = "Best Young and Emerging Scholar Paper"

# APA 7 wants sentence case for titles of articles, books and reports. The bib keeps the
# published capitalisation, so the English titles are restated here.
TITLES = {
    "mckillop2020": "Cooperative financial institutions: A review of the literature",
    "hesse2007": "Cooperative banks and financial stability",
    "fonteyne2007": "Cooperative banks in Europe: Policy issues",
    "bulbul2013": "Savings banks and cooperative banks in Europe",
    "cuevas2006": "Cooperative financial institutions: Issues in governance, regulation, and supervision",
    "ferri2014": "Does bank ownership affect lending behavior? Evidence from the Euro area",
    "iannotta2007": "Ownership structure, risk and performance in the European banking industry",
    "beck2009": "Bank ownership and stability: Evidence from Germany",
    "ayadi2010": "Investigating diversity in the banking sector in Europe: Key developments, performance and role of cooperative banks",
    "fiordelisi2014": "Competition and financial stability in European cooperative banks",
    "becchetti2016": "The cooperative bank difference before and after the global financial crisis",
    "carvalho2015": "Exit and failure of credit unions in Brazil: A risk analysis",
    "cook1995": "The future of U.S. agricultural cooperatives: A neo-institutional approach",
    "hansmann1996": "The ownership of enterprise",
    "ayres1992": "Responsive regulation: Transcending the deregulation debate",
    "baldwin2008": "Really responsive regulation",
    "diamonddybvig1983": "Bank runs, deposit insurance, and liquidity",
    "iacus2012": "Causal inference without balance checking: Coarsened exact matching",
    "cameron2008": "Bootstrap-based improvements for inference with clustered errors",
    "cameron2015": "A practitioner's guide to cluster-robust inference",
    "mackinnon1985": "Some heteroskedasticity-consistent covariance matrix estimators with improved finite sample properties",
    "mackinnon2017": "Wild bootstrap inference for wildly different cluster sizes",
    "abadie2023": "When should you adjust standard errors for clustering?",
    "bcbs2011": "Basel III: A global regulatory framework for more resilient banks and banking systems",
    "bcbs2019": "Proportionality in bank regulation and supervision: A survey on current practices",
    "castrocarvalho2017": "Proportionality in banking regulation: A cross-country comparison",
    "hohl2018": "The Basel framework in 100 jurisdictions: Implementation status and proportionality practices",
    "coelho2019": "Regulation and supervision of financial cooperatives",
}


# ============================================================================ text model
@dataclass
class Seg:
    text: str
    b: bool = False
    i: bool = False
    sup: bool = False
    sub: bool = False
    mono: bool = False


@dataclass
class Foot:
    segs: list


class LineBreak:
    pass


def merge(segs):
    out = []
    for s in segs:
        if isinstance(s, Seg) and out and isinstance(out[-1], Seg) and \
                (s.b, s.i, s.sup, s.sub, s.mono) == (out[-1].b, out[-1].i, out[-1].sup, out[-1].sub, out[-1].mono):
            out[-1].text += s.text
        else:
            out.append(s)
    return [s for s in out if not (isinstance(s, Seg) and s.text == "")]


def plain(segs):
    return "".join(s.text for s in segs if isinstance(s, Seg))


# ============================================================================ LaTeX reading
ACCENTS = {
    ("'", "a"): "á", ("'", "e"): "é", ("'", "i"): "í", ("'", "o"): "ó", ("'", "u"): "ú",
    ("'", "A"): "Á", ("'", "E"): "É", ("'", "I"): "Í", ("'", "O"): "Ó", ("'", "U"): "Ú",
    ("^", "a"): "â", ("^", "e"): "ê", ("^", "o"): "ô", ("^", "A"): "Â", ("^", "E"): "Ê", ("^", "O"): "Ô",
    ("~", "a"): "ã", ("~", "o"): "õ", ("~", "A"): "Ã", ("~", "O"): "Õ", ("~", "n"): "ñ",
    ('"', "u"): "ü", ('"', "o"): "ö", ('"', "a"): "ä", ('"', "U"): "Ü", ('"', "O"): "Ö", ('"', "A"): "Ä",
    ("`", "a"): "à", ("`", "e"): "è", ("`", "o"): "ò", ("`", "A"): "À",
    ("c", "c"): "ç", ("c", "C"): "Ç", ("v", "C"): "Č", ("v", "c"): "č", ("v", "S"): "Š", ("v", "s"): "š",
    ("v", "Z"): "Ž", ("v", "z"): "ž",
}
DROP_WORDS = {"noindent", "medskip", "smallskip", "bigskip", "centering", "raggedright", "footnotesize",
              "small", "large", "par", "toprule", "midrule", "bottomrule", "hline", "newpage", "maketitle",
              "onehalfspacing", "appendix"}


def read_group(s, j):
    """Return (content, index_after) of the brace group starting at or after s[j]."""
    while j < len(s) and s[j] in " \n\t":
        j += 1
    if j >= len(s) or s[j] != "{":
        return "", j
    depth = 0
    for k in range(j, len(s)):
        if s[k] == "{":
            depth += 1
        elif s[k] == "}":
            depth -= 1
            if depth == 0:
                return s[j + 1:k], k + 1
    raise ValueError("unbalanced braces: " + s[j:j + 60])


def accent(kind, arg):
    arg = arg.replace("\\i", "i").strip("{} ")
    return ACCENTS.get((kind, arg), arg)


class Ctx:
    """Resolves citations and cross-references while parsing."""

    def __init__(self, bib=None, cited=None, labels=None):
        self.bib = bib
        self.cited = cited if cited is not None else []
        self.labels = labels or {}

    def cite(self, keys, narrative):
        keys = [k.strip() for k in keys.split(",") if k.strip()]
        for k in keys:
            if k not in self.cited:
                self.cited.append(k)
        return self.bib.cite(keys, narrative)

    def ref(self, label):
        return self.labels.get(label.strip(), "??")


def parse_tex(s, fmt=None, ctx=None):
    fmt = dict(fmt or {})
    out, buf = [], []
    i, n = 0, len(s)

    def flush():
        if buf:
            out.append(Seg("".join(buf), **fmt))
            buf.clear()

    while i < n:
        c = s[i]
        if c == "\\":
            m = re.match(r"\\([a-zA-Z]+)\*?", s[i:])
            if m:
                name, j = m.group(1), i + m.end()
                if name in ("citep", "citet"):
                    arg, j = read_group(s, j)
                    buf.append(ctx.cite(arg, name == "citet"))
                elif name in ("textit", "emph"):
                    arg, j = read_group(s, j)
                    flush(); out += parse_tex(arg, {**fmt, "i": True}, ctx)
                elif name == "textbf":
                    arg, j = read_group(s, j)
                    flush(); out += parse_tex(arg, {**fmt, "b": True}, ctx)
                elif name == "texttt":
                    arg, j = read_group(s, j)
                    flush(); out += parse_tex(arg, {**fmt, "mono": True}, ctx)
                elif name == "textsuperscript":
                    arg, j = read_group(s, j)
                    flush(); out += parse_tex(arg, {**fmt, "sup": True}, ctx)
                elif name == "footnote":
                    arg, j = read_group(s, j)
                    flush(); out.append(Foot(merge(parse_tex(norm(arg), {}, ctx))))
                elif name == "ref":
                    arg, j = read_group(s, j)
                    buf.append(ctx.ref(arg))
                elif name in ("label", "vspace", "hspace", "bibliographystyle", "bibliography", "renewcommand", "pagestyle"):
                    arg, j = read_group(s, j)
                    if name == "renewcommand":
                        _, j = read_group(s, j)
                elif name == "setlength":
                    _, j = read_group(s, j)
                    _, j = read_group(s, j)
                elif name in ("c", "v", "u", "H", "k", "r") and j < n and s[j] == "{":
                    arg, j = read_group(s, j)
                    buf.append(accent(name, arg))
                elif name == "i":
                    buf.append("i")
                elif name in DROP_WORDS:
                    pass
                else:
                    pass                          # unknown command: dropped
                i = j
                # LaTeX swallows the space after a control word
                continue
            nxt = s[i + 1] if i + 1 < n else ""
            if nxt in "'^~\"`":
                j = i + 2
                if j < n and s[j] == "{":
                    arg, j = read_group(s, j)
                else:
                    arg, j = s[j:j + 1], j + 1
                buf.append(accent(nxt, arg))
                i = j
            elif nxt == "\\":
                flush(); out.append(LineBreak()); i += 2
            elif nxt in "&%$#_{}":
                buf.append(nxt); i += 2
            elif nxt == ",":
                buf.append("\u2009"); i += 2
            elif nxt == " ":
                buf.append(" "); i += 2
            else:
                i += 2
            continue
        if c == "{":
            arg, j = read_group(s, i)
            flush(); out += parse_tex(arg, fmt, ctx); i = j
            continue
        if c == "}":
            i += 1
            continue
        if c == "$":
            j = s.index("$", i + 1)
            flush(); out += math_segs(s[i + 1:j], fmt); i = j + 1
            continue
        if c == "~":
            buf.append("\u00a0"); i += 1
            continue
        if s.startswith("``", i):
            buf.append("\u201c"); i += 2
            continue
        if s.startswith("''", i):
            buf.append("\u201d"); i += 2
            continue
        if s.startswith("---", i):
            buf.append("\u2014"); i += 3
            continue
        if s.startswith("--", i):
            buf.append("\u2013"); i += 2
            continue
        buf.append(c)
        i += 1
    flush()
    return merge(out)


GREEK = {"rho": "ρ", "beta": "β", "alpha": "α", "sigma": "σ", "mu": "μ", "times": "×", "pm": "±",
         "leq": "≤", "geq": "≥", "neq": "≠", "approx": "≈", "cdot": "·", "ldots": "…"}


def math_segs(m, fmt):
    """Small LaTeX math to text: Greek letters, sub/superscripts, minus signs, spacing."""
    fmt = dict(fmt or {})
    out, buf = [], []
    i, n = 0, len(m)

    def flush(**extra):
        if buf:
            out.append(Seg("".join(buf), **{**fmt, **extra}))
            buf.clear()

    while i < n:
        c = m[i]
        if c == "\\":
            mm = re.match(r"\\([a-zA-Z]+)", m[i:])
            if mm:
                name, j = mm.group(1), i + mm.end()
                if name in ("text", "mathrm", "textit", "textrm"):
                    arg, j = read_group(m, j)
                    flush(); out.append(Seg(arg, **fmt))
                elif name in GREEK:
                    buf.append(GREEK[name])
                i = j
                continue
            nxt = m[i + 1] if i + 1 < n else ""
            if nxt in ",;: ":
                buf.append(" ")
            elif nxt in "|{}":
                buf.append(nxt)
            i += 2
            continue
        if c in "_^":
            j = i + 1
            if j < n and m[j] == "{":
                arg, j = read_group(m, j)
            else:
                arg, j = m[j:j + 1], j + 1
            flush()
            inner = math_segs(arg, fmt)
            for s in inner:
                if c == "_":
                    s.sub = True
                else:
                    s.sup = True
                s.i = False
            out += inner
            i = j
            continue
        if c == "{":
            arg, j = read_group(m, i)
            flush(); out += math_segs(arg, fmt); i = j
            continue
        if c == "}":
            i += 1
            continue
        if c == "-":
            buf.append("\u2212")
        elif c in "=<>+/":
            buf.append(f" {c} ")
        elif c == " ":
            pass
        elif c.isalpha():
            flush(); out.append(Seg(c, **{**fmt, "i": True}))
        else:
            buf.append(c)
        i += 1
    flush()
    out = merge(out)
    for s in out:
        s.text = re.sub(r" {2,}", " ", s.text)
    return out


def norm(s):
    """Collapse whitespace the way TeX does, keeping paragraph content on one line."""
    return re.sub(r"\s+", " ", s).strip()


def strip_comments(tex):
    return "\n".join(re.sub(r"(?<!\\)%.*", "", ln) for ln in tex.split("\n"))


# ============================================================================ bibliography
@dataclass
class Person:
    surname: str
    given: str

    def initials(self):
        parts = []
        for tok in self.given.replace(".", ". ").split():
            if tok[0].islower():                     # particles: de, von
                parts.append(tok)
            else:
                parts.append("-".join(p[0] + "." for p in tok.split("-") if p))
        return " ".join(parts)


@dataclass
class Entry:
    key: str
    type: str
    fields: dict
    persons: list = field(default_factory=list)
    institution: str = ""
    suffix: str = ""

    def label(self, narrative):
        if self.institution:
            return self.institution
        names = [p.surname for p in self.persons]
        if len(names) == 1:
            return names[0]
        if len(names) == 2:
            return f"{names[0]} and {names[1]}" if narrative else f"{names[0]} & {names[1]}"
        return f"{names[0]} et al."

    def sort_key(self):
        head = self.institution or self.persons[0].surname
        return (head.lower(), self.fields.get("year", ""), self.suffix, self.title().lower())

    def title(self):
        return TITLES.get(self.key, self.fields["title"])

    def year(self):
        return self.fields.get("year", "n.d.") + self.suffix


class Bib:
    def __init__(self, path):
        self.entries = {}
        src = open(path, encoding="utf-8").read()
        src = "\n".join(ln for ln in src.split("\n") if not ln.lstrip().startswith("%"))   # URLs carry '%'
        for m in re.finditer(r"@(\w+)\s*\{\s*([^,\s]+)\s*,", src):
            typ, key = m.group(1).lower(), m.group(2)
            body, _ = read_group(src, m.start() + m.group(0).index("{"))
            body = body[body.index(",") + 1:]
            fields = self._fields(body)
            e = Entry(key, typ, fields)
            self._authors(e)
            self.entries[key] = e

    @staticmethod
    def _fields(body):
        fields, i = {}, 0
        while True:
            m = re.compile(r"\s*(\w+)\s*=\s*").match(body, i)
            if not m:
                break
            name, j = m.group(1).lower(), m.end()
            if body[j] == "{":
                val, j = read_group(body, j)
            elif body[j] == '"':
                k = body.index('"', j + 1)
                val, j = body[j + 1:k], k + 1
            else:
                mm = re.compile(r"[^,\n]+").match(body, j)
                val, j = mm.group(0).strip(), mm.end()
            fields[name] = plain(parse_tex(norm(val.replace("\\textsuperscript{o}", "º")), {}, None))
            k = body.find(",", j)
            if k < 0:
                break
            i = k + 1
        return fields

    @staticmethod
    def _authors(e):
        raw = e.fields.get("author", "")
        if raw.startswith("{") or " and " not in raw and "," not in raw:
            e.institution = raw.strip("{}")
            return
        # protected institution inside double braces survives plain() as text without braces:
        # detect by absence of a comma
        parts = [p.strip() for p in re.split(r"\s+and\s+", raw)]
        if all("," not in p for p in parts):
            e.institution = raw
            return
        for p in parts:
            if "," in p:
                sur, giv = [x.strip() for x in p.split(",", 1)]
            else:
                toks = p.split()
                sur, giv = toks[-1], " ".join(toks[:-1])
            e.persons.append(Person(sur, giv))

    # ---------------------------------------------------------------- citations
    def assign_suffixes(self, keys):
        groups = {}
        for k in keys:
            e = self.entries[k]
            groups.setdefault((e.label(False), e.fields.get("year")), []).append(e)
        for es in groups.values():
            if len(es) > 1:
                for i, e in enumerate(sorted(es, key=lambda x: x.title().lower())):
                    e.suffix = "abcdefghijklmnopqrstuvwxyz"[i]

    def cite(self, keys, narrative):
        es = sorted((self.entries[k] for k in keys), key=lambda e: (e.label(narrative).lower(), e.year()))
        if narrative:
            return "; ".join(f"{e.label(True)} ({e.year()})" for e in es)
        groups = []
        for e in es:
            if groups and groups[-1][0] == e.label(False):
                groups[-1][1].append(e.year())
            else:
                groups.append((e.label(False), [e.year()]))
        return "(" + "; ".join(f"{lab}, {', '.join(ys)}" for lab, ys in groups) + ")"

    # ---------------------------------------------------------------- reference list
    def author_string(self, e):
        if e.institution:
            return e.institution + "."
        names = [f"{p.surname}, {p.initials()}" for p in e.persons]
        if len(names) == 1:
            s = names[0]
        elif len(names) <= 20:
            s = ", ".join(names[:-1]) + ", & " + names[-1]
        else:
            s = ", ".join(names[:19]) + ", … " + names[-1]
        return s if s.endswith(".") else s + "."

    def reference(self, e):
        f = e.fields
        segs = [Seg(f"{self.author_string(e)} ({e.year()}). ")]
        title = e.title()
        end = "" if title[-1] in "?!." else "."

        def source(doi_first=True):
            if f.get("doi"):
                segs.append(Seg(f"https://doi.org/{f['doi']}"))
            elif f.get("url"):
                segs.append(Seg(f["url"]))

        if e.type == "article":
            segs.append(Seg(title + end + " "))
            segs.append(Seg(f["journal"], i=True))
            if f.get("volume"):
                segs.append(Seg(", ")); segs.append(Seg(f["volume"], i=True))
            if f.get("number"):
                segs.append(Seg(f"({f['number']})"))
            if f.get("pages"):
                segs.append(Seg(", " + f["pages"].replace("--", "\u2013")))
            segs.append(Seg(". "))
            source()
        elif e.type == "techreport":
            segs.append(Seg(title, i=True))
            typ, num = f.get("type"), f.get("number")
            if typ or num:
                segs.append(Seg(f" ({typ or 'Report'} No. {num})" if num else f" ({typ})"))
            segs.append(Seg(". " + f["institution"] + ". "))
            source()
        elif e.type == "book":
            segs.append(Seg(title, i=True)); segs.append(Seg(". " + f["publisher"] + "."))
        elif e.type == "unpublished":
            inst = "Deutsche Bundesbank" if "Bundesbank" in f.get("note", "") else ""
            segs.append(Seg(title, i=True)); segs.append(Seg(" [Working paper]. " + inst + "."))
        else:                                        # misc: legislation and Central Bank reports
            segs.append(Seg(title, i=True)); segs.append(Seg(". "))
            pub = f.get("howpublished", "")
            if pub and pub != e.institution:
                segs.append(Seg(pub + ". "))
            source()
        return merge(segs)

    def reference_list(self, keys):
        es = sorted((self.entries[k] for k in keys), key=lambda e: e.sort_key())
        return [self.reference(e) for e in es]


# ============================================================================ docx XML
def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def run(text, b=False, i=False, sz=None, sup=False, sub=False, rstyle=None, font=None, i_off=False):
    rpr = ""
    if rstyle:
        rpr += f'<w:rStyle w:val="{rstyle}"/>'
    if font:
        rpr += f'<w:rFonts w:ascii="{font}" w:hAnsi="{font}" w:cs="{font}"/>'
    if b:
        rpr += "<w:b/><w:bCs/>"
    if i:
        rpr += "<w:i/><w:iCs/>"
    elif i_off:
        rpr += '<w:i w:val="0"/><w:iCs w:val="0"/>'
    if sz:
        rpr += f'<w:sz w:val="{sz}"/><w:szCs w:val="{sz}"/>'
    if sup:
        rpr += '<w:vertAlign w:val="superscript"/>'
    if sub:
        rpr += '<w:vertAlign w:val="subscript"/>'
    rpr = f"<w:rPr>{rpr}</w:rPr>" if rpr else ""
    return f'<w:r>{rpr}<w:t xml:space="preserve">{esc(text)}</w:t></w:r>'


def para(runs, style=None, jc=None, ind=None, spacing=None, keep_next=False, pbdr=None, numpr=None,
         page_break_before=False):
    ppr = ""
    if style:
        ppr += f'<w:pStyle w:val="{style}"/>'
    if keep_next:
        ppr += "<w:keepNext/>"
    if page_break_before:
        ppr += "<w:pageBreakBefore/>"
    if numpr:
        ppr += numpr
    if pbdr:
        ppr += pbdr
    if spacing:
        ppr += spacing
    if ind:
        ppr += ind
    if jc:
        ppr += f'<w:jc w:val="{jc}"/>'
    ppr = f"<w:pPr>{ppr}</w:pPr>" if ppr else ""
    return f"<w:p>{ppr}{runs}</w:p>"


class Doc:
    """Collects body XML, footnotes and images, then writes them into the template."""

    def __init__(self):
        self.body = []
        self.footnotes = []          # (id, xml)
        self.images = []             # (rid, filename, bytes)
        self.docpr = 100
        self.bullet_num = None

    # ---- inline content -------------------------------------------------------------
    def runs(self, segs, sz=None, font=None):
        xml = ""
        for s in segs:
            if isinstance(s, Foot):
                fid = len(self.footnotes) + 1
                inner = self.runs(s.segs, sz=16)
                self.footnotes.append((fid, (
                    f'<w:footnote w:id="{fid}"><w:p><w:pPr><w:pStyle w:val="FootnoteText"/>'
                    f'<w:spacing w:after="40"/><w:jc w:val="both"/></w:pPr>'
                    f'<w:r><w:rPr><w:rStyle w:val="FootnoteReference"/></w:rPr><w:footnoteRef/></w:r>'
                    f'{run(" ", sz=16)}{inner}</w:p></w:footnote>')))
                xml += (f'<w:r><w:rPr><w:rStyle w:val="FootnoteReference"/></w:rPr>'
                        f'<w:footnoteReference w:id="{fid}"/></w:r>')
            elif isinstance(s, LineBreak):
                xml += "<w:r><w:br/></w:r>"
            else:
                xml += run(s.text, b=s.b, i=s.i, sup=s.sup, sub=s.sub, sz=sz,
                           font=("Consolas" if s.mono else font))
        return xml

    def add(self, xml):
        self.body.append(xml)

    @staticmethod
    def trim(segs):
        segs = [s for s in segs if not (isinstance(s, Seg) and s.text == "")]
        if segs and isinstance(segs[0], Seg):
            segs[0].text = segs[0].text.lstrip()
        if segs and isinstance(segs[-1], Seg):
            segs[-1].text = segs[-1].text.rstrip()
        return [s for s in segs if not (isinstance(s, Seg) and s.text == "")]

    def paragraph(self, segs, **kw):
        self.add(para(self.runs(self.trim(segs), sz=kw.pop("sz", None)), **kw))

    # ---- blocks ------------------------------------------------------------------------
    def title_block(self, award=None):
        self.add(para(run(TITLE, b=True, sz=24), jc="center", spacing='<w:spacing w:after="120"/>'))
        rs = ""
        for k, (name, letter) in enumerate(AUTHORS):
            if k == len(AUTHORS) - 1:
                rs += run(" and ")
            elif k:
                rs += run(", ")
            rs += run(name) + run(letter, sup=True)
        self.add(para(rs, style="Autor1", jc="center"))
        rs = ""
        for k, (letter, text) in enumerate(AFFILIATIONS):
            if k:
                rs += run("; " if k < len(AFFILIATIONS) - 1 else "; and ", rstyle="Autor2")
            rs += run(letter, rstyle="Autor2", sup=True) + run(text, rstyle="Autor2")
        self.add(para(rs, pbdr='<w:pBdr><w:bottom w:val="single" w:sz="12" w:space="1" w:color="auto"/></w:pBdr>',
                      spacing='<w:spacing w:after="240"/>'))
        if award:
            self.add(para(run("Award category: ", i=True) + run(award), jc="center",
                          spacing='<w:spacing w:after="240"/>'))

    def heading_template(self, text):
        """The template's 11-point bold heading (its 'Abstract' and 'References' lines)."""
        self.add(para(run(text, b=True, sz=22, i_off=True), style="Abstract",
                      ind='<w:ind w:left="0" w:right="284"/>', keep_next=True))

    def heading(self, text, level):
        style = "Heading1" if level == 1 else "Heading2"
        sp = '<w:spacing w:before="240" w:after="120"/>' if level == 1 else '<w:spacing w:before="200" w:after="80"/>'
        self.add(para(run(text), style=style, spacing=sp, ind='<w:ind w:left="0" w:firstLine="0"/>', keep_next=True,
                      numpr='<w:numPr><w:ilvl w:val="0"/><w:numId w:val="0"/></w:numPr>'))

    def references(self, seg_lists):
        for segs in seg_lists:
            self.add(para(self.runs(segs, sz=18), style="ReferenciasBibliogrficas", jc="left",
                          spacing='<w:spacing w:after="60" w:line="240" w:lineRule="auto"/>'))

    def bullet(self, segs):
        self.add(para(self.runs(self.trim(segs)), numpr=f'<w:numPr><w:ilvl w:val="0"/><w:numId w:val="{self.bullet_num}"/></w:numPr>',
                      ind='<w:ind w:left="567" w:hanging="283"/>', spacing='<w:spacing w:after="40"/>'))

    def figure(self, path, frac, number, caption_segs, note_segs):
        with Image.open(path) as im:
            w, h = im.size
        cx = int(TEXT_WIDTH * frac) * EMU_PER_TWIP
        cy = int(cx * h / w)
        rid = f"rIdImg{len(self.images) + 1}"
        self.images.append((rid, f"image{len(self.images) + 1}.png", open(path, "rb").read()))
        self.docpr += 1
        name = os.path.basename(path)
        drawing = (
            f'<w:r><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0"><wp:extent cx="{cx}" cy="{cy}"/>'
            f'<wp:docPr id="{self.docpr}" name="{name}"/><wp:cNvGraphicFramePr>'
            f'<a:graphicFrameLocks xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" noChangeAspect="1"/>'
            f'</wp:cNvGraphicFramePr><a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
            f'<a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
            f'<pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:nvPicPr>'
            f'<pic:cNvPr id="0" name="{name}"/><pic:cNvPicPr/></pic:nvPicPr><pic:blipFill><a:blip r:embed="{rid}"/>'
            f'<a:stretch><a:fillRect/></a:stretch></pic:blipFill><pic:spPr><a:xfrm><a:off x="0" y="0"/>'
            f'<a:ext cx="{cx}" cy="{cy}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr>'
            f'</pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r>')
        self.add(para(drawing, jc="center", keep_next=True, spacing='<w:spacing w:before="120" w:after="60"/>'))
        self.add(para(run(f"Figure {number}. ", b=True) + self.runs(caption_segs), style="TablaImagen-Ttulo",
                      keep_next=bool(note_segs), spacing='<w:spacing w:before="0" w:after="60"/>'))
        if note_segs:
            self.add(para(self.runs(note_segs, sz=16), jc="both", spacing='<w:spacing w:after="200" w:line="240" w:lineRule="auto"/>'))

    def table(self, number, caption_segs, rows, widths, aligns, rule_below, note_segs, sz):
        self.add(para(run(f"Table {number}. ", b=True) + self.runs(caption_segs), style="TablaImagen-Ttulo",
                      keep_next=True, spacing='<w:spacing w:before="200" w:after="60"/>'))
        total = sum(widths)
        xml = (f'<w:tbl><w:tblPr><w:tblW w:w="{total}" w:type="dxa"/><w:jc w:val="center"/>'
               f'<w:tblBorders><w:top w:val="nil"/><w:left w:val="nil"/><w:bottom w:val="nil"/><w:right w:val="nil"/>'
               f'<w:insideH w:val="nil"/><w:insideV w:val="nil"/></w:tblBorders><w:tblLayout w:type="fixed"/>'
               f'<w:tblCellMar><w:left w:w="40" w:type="dxa"/><w:right w:w="40" w:type="dxa"/></w:tblCellMar>'
               f'<w:tblLook w:val="0000" w:firstRow="0" w:lastRow="0" w:firstColumn="0" w:lastColumn="0" w:noHBand="0" w:noVBand="0"/>'
               f'</w:tblPr><w:tblGrid>' + "".join(f'<w:gridCol w:w="{w}"/>' for w in widths) + "</w:tblGrid>")
        last = len(rows) - 1
        for r, cells in enumerate(rows):
            xml += "<w:tr>" + ('<w:trPr><w:tblHeader/></w:trPr>' if r == 0 else "<w:trPr><w:cantSplit/></w:trPr>")
            for c, segs in enumerate(cells):
                borders = ""
                if r == 0:
                    borders += '<w:top w:val="single" w:sz="8" w:space="0" w:color="auto"/>'
                if r in rule_below or r == last:
                    borders += f'<w:bottom w:val="single" w:sz="{8 if r == last else 4}" w:space="0" w:color="auto"/>'
                tcpr = f'<w:tcPr><w:tcW w:w="{widths[c]}" w:type="dxa"/>' + \
                       (f"<w:tcBorders>{borders}</w:tcBorders>" if borders else "") + "</w:tcPr>"
                jc = {"l": "left", "r": "right", "c": "center"}[aligns[c]]
                xml += f"<w:tc>{tcpr}" + para(self.runs(segs, sz=sz), jc=jc,
                                             spacing='<w:spacing w:before="20" w:after="20" w:line="240" w:lineRule="auto"/>') + "</w:tc>"
            xml += "</w:tr>"
        xml += "</w:tbl>"
        self.add(xml)
        if note_segs:
            self.add(para(self.runs(note_segs, sz=16), jc="both",
                          spacing='<w:spacing w:before="60" w:after="200" w:line="240" w:lineRule="auto"/>'))
        else:
            self.add(para("", spacing='<w:spacing w:after="120"/>'))

    def page_break(self):
        self.add('<w:p><w:r><w:br w:type="page"/></w:r></w:p>')

    # ---- writing -----------------------------------------------------------------------
    def write(self, out_path, core_title):
        zin = zipfile.ZipFile(TEMPLATE)
        parts = {n: zin.read(n) for n in zin.namelist()}
        zin.close()
        doc = parts["word/document.xml"].decode("utf-8")
        head = doc[:doc.index("<w:body>") + len("<w:body>")]
        sect = re.findall(r"<w:sectPr[ >].*?</w:sectPr>", doc, re.S)[-1]
        parts["word/document.xml"] = (head + "".join(self.body) + sect + "</w:body></w:document>").encode("utf-8")
        # footnotes
        fn = parts["word/footnotes.xml"].decode("utf-8")
        fn = fn.replace("</w:footnotes>", "".join(x for _, x in self.footnotes) + "</w:footnotes>")
        parts["word/footnotes.xml"] = fn.encode("utf-8")
        # running heads
        for name, old, new in (("word/header1.xml", "Title of the presentation – Running Head", SHORT_TITLE),
                               ("word/header2.xml", "Authors", AUTHORS_SHORT)):
            parts[name] = parts[name].decode("utf-8").replace(f"<w:t>{old}</w:t>", f"<w:t>{esc(new)}</w:t>").encode("utf-8")
        # images
        if self.images:
            rels = parts["word/_rels/document.xml.rels"].decode("utf-8")
            add = "".join(f'<Relationship Id="{rid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/{fname}"/>'
                          for rid, fname, _ in self.images)
            parts["word/_rels/document.xml.rels"] = rels.replace("</Relationships>", add + "</Relationships>").encode("utf-8")
            ct = parts["[Content_Types].xml"].decode("utf-8")
            if 'Extension="png"' not in ct:
                ct = ct.replace("<Override", '<Default Extension="png" ContentType="image/png"/><Override', 1)
            parts["[Content_Types].xml"] = ct.encode("utf-8")
            for rid, fname, data in self.images:
                parts["word/media/" + fname] = data
        # document properties
        core = parts["docProps/core.xml"].decode("utf-8")
        core = re.sub(r"<dc:title>.*?</dc:title>|<dc:title/>", f"<dc:title>{esc(core_title)}</dc:title>", core, flags=re.S)
        core = re.sub(r"<dc:creator>.*?</dc:creator>|<dc:creator/>", f"<dc:creator>{esc(AUTHORS_SHORT)}</dc:creator>", core, flags=re.S)
        parts["docProps/core.xml"] = core.encode("utf-8")
        if os.path.exists(out_path):
            os.remove(out_path)
        with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("[Content_Types].xml", parts.pop("[Content_Types].xml"))
            for n, data in parts.items():
                z.writestr(n, data)

    def ensure_bullets(self):
        """Find or add a bullet numbering definition in the template's numbering part."""
        zin = zipfile.ZipFile(TEMPLATE)
        num = zin.read("word/numbering.xml").decode("utf-8")
        zin.close()
        for m in re.finditer(r"<w:abstractNum [^>]*w:abstractNumId=\"(\d+)\".*?</w:abstractNum>", num, re.S):
            if re.search(r'<w:lvl w:ilvl="0"[^>]*>.*?<w:numFmt w:val="bullet"/>', m.group(0), re.S):
                mm = re.search(rf'<w:num w:numId="(\d+)"[^>]*>\s*<w:abstractNumId w:val="{m.group(1)}"/>', num)
                if mm:
                    self.bullet_num = mm.group(1)
                    self._numbering = None
                    return
        ids = [int(x) for x in re.findall(r'w:abstractNumId="(\d+)"', num)] or [0]
        nids = [int(x) for x in re.findall(r'<w:num w:numId="(\d+)"', num)] or [0]
        aid, nid = max(ids) + 1, max(nids) + 1
        absnum = (f'<w:abstractNum w:abstractNumId="{aid}"><w:multiLevelType w:val="singleLevel"/>'
                  f'<w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="bullet"/><w:lvlText w:val="\u2022"/>'
                  f'<w:lvlJc w:val="left"/><w:pPr><w:ind w:left="567" w:hanging="283"/></w:pPr>'
                  f'<w:rPr><w:rFonts w:ascii="Times New Roman" w:hAnsi="Times New Roman" w:hint="default"/></w:rPr></w:lvl></w:abstractNum>')
        numdef = f'<w:num w:numId="{nid}"><w:abstractNumId w:val="{aid}"/></w:num>'
        k = num.find("<w:num ")
        num = (num[:k] + absnum + num[k:]) if k >= 0 else num.replace("</w:numbering>", absnum + "</w:numbering>")
        num = num.replace("</w:numbering>", numdef + "</w:numbering>")
        self.bullet_num = str(nid)
        self._numbering = num

    def write_with_numbering(self, out_path, core_title):
        self.write(out_path, core_title)
        if getattr(self, "_numbering", None):
            zin = zipfile.ZipFile(out_path)
            parts = {n: zin.read(n) for n in zin.namelist()}
            zin.close()
            parts["word/numbering.xml"] = self._numbering.encode("utf-8")
            os.remove(out_path)
            with zipfile.ZipFile(out_path, "w", zipfile.ZIP_DEFLATED) as z:
                z.writestr("[Content_Types].xml", parts.pop("[Content_Types].xml"))
                for n, data in parts.items():
                    z.writestr(n, data)


# ============================================================================ the abstract
def md_inline(s):
    """**bold** and *italic* markers to segments."""
    out = []
    for tok in re.split(r"(\*\*.+?\*\*|\*[^*]+?\*)", s):
        if not tok:
            continue
        if tok.startswith("**"):
            out.append(Seg(tok[2:-2], b=True))
        elif tok.startswith("*"):
            out.append(Seg(tok[1:-1], i=True))
        else:
            out.append(Seg(tok))
    return merge(out)


def build_abstract(bib):
    md = open(MD, encoding="utf-8").read()
    md = re.sub(r"<!--.*?-->", "", md, flags=re.S)
    title = re.search(r"^# (.+)$", md, re.M).group(1).strip()
    keywords = re.search(r"^\*\*Keywords:\*\*\s*(.+)$", md, re.M).group(1).strip()
    body_md = md.split("## Abstract", 1)[1].split("## Key References", 1)[0]
    paras = [norm(p) for p in re.split(r"\n\s*\n", body_md) if p.strip()]
    keys = re.search(r"keys:\s*(.+)", md.split("## Key References", 1)[1]).group(1)
    keys = [k.strip() for k in keys.split(",") if k.strip()]
    bib.assign_suffixes(keys)
    refs = bib.reference_list(keys)

    words_body = sum(len(p.split()) for p in paras)
    words_refs = sum(len(plain(r).split()) for r in refs)
    print(f"abstract: title {len(title.split())} words; body {words_body}; references {words_refs}; "
          f"body+references {words_body + words_refs} (limit 800 to 1,500); keywords {len(keywords.split(';'))}")
    assert title == TITLE, "title in expanded_abstract.md differs from TITLE"

    d = Doc()
    d.title_block()
    d.heading_template("Abstract")
    for p in paras:
        d.paragraph(md_inline(p), jc="both")
    d.heading_template("Keywords")
    d.add(para(run(keywords, b=True, i_off=True), style="Abstract", ind='<w:ind w:left="0" w:right="284"/>'))
    d.heading_template("Key References")
    d.references(refs)
    d.write(OUT_ABSTRACT, TITLE)
    print("wrote", os.path.relpath(OUT_ABSTRACT, ROOT))


# ============================================================================ the paper
def tex_body():
    tex = strip_comments(open(TEX, encoding="utf-8").read())
    return tex[tex.index(r"\begin{document}") + len(r"\begin{document}"):tex.index(r"\end{document}")]


def number_labels(body):
    """Section, figure and table numbers by order of appearance, as LaTeX would assign them."""
    labels, sec, sub, fig, tab = {}, 0, 0, 0, 0
    appendix = False
    for m in re.finditer(r"\\(section|subsection|appendix|begin\{figure\}|begin\{table\})|\\label\{([^}]*)\}", body):
        tok, lab = m.group(1), m.group(2)
        if tok == "appendix":
            appendix, sec = True, 0
        elif tok == "section":
            sec, sub = sec + 1, 0
            current = ("Appendix " + "ABCDEFG"[sec - 1]) if appendix else str(sec)
        elif tok == "subsection":
            sub += 1
            current = f"{sec}.{sub}"
        elif tok == "begin{figure}":
            fig += 1
            current = str(fig)
        elif tok == "begin{table}":
            tab += 1
            current = str(tab)
        elif lab is not None:
            labels[lab] = current
    return labels


def parse_tabular(spec_and_body, ctx):
    """A booktabs tabular to (rows, aligns, rule_below)."""
    spec, j = read_group(spec_and_body, 0)
    rest = spec_and_body[j:]
    aligns = [c for c in re.sub(r"p\{[^}]*\}", "l", spec) if c in "lrc"]
    rest = rest.replace("\\toprule", "")
    rows, rule_below = [], set()
    for chunk in re.split(r"\\\\", rest):
        if "\\bottomrule" in chunk:
            chunk = chunk.replace("\\bottomrule", "")
        if "\\midrule" in chunk:
            chunk = chunk.replace("\\midrule", "")
            if rows:
                rule_below.add(len(rows) - 1)
        if not chunk.strip():
            continue
        cells = [merge(parse_tex(norm(c), {}, ctx)) for c in chunk.split("&")]
        rows.append(cells)
    return rows, aligns, rule_below


def build_paper(bib):
    body = tex_body()
    labels = number_labels(body)
    ctx = Ctx(bib, [], labels)
    # first pass: collect the cited keys so that year suffixes are known before rendering
    for m in re.finditer(r"\\cite[pt]\{([^}]*)\}", body):
        ctx.cite(m.group(1), False)
    bib.assign_suffixes(ctx.cited)
    cited = list(ctx.cited)

    d = Doc()
    d.ensure_bullets()
    d.title_block()                      # the award line comes from the tex's own center block

    lines = body.split("\n")
    i, n = 0, len(lines)
    par_lines = []
    sec_no, sub_no, fig_no, tab_no, appendix = 0, 0, 0, 0, False

    def flush_par():
        nonlocal par_lines
        text = norm(" ".join(par_lines))
        par_lines = []
        if text:
            segs = parse_tex(text, {}, ctx)
            if any(isinstance(s, Foot) or (isinstance(s, Seg) and s.text.strip()) for s in segs):
                d.paragraph(segs, jc="both")          # a bare \label line leaves nothing to print

    def env_block(start, name):
        depth, k = 0, start
        while k < n:
            depth += lines[k].count(f"\\begin{{{name}}}") - lines[k].count(f"\\end{{{name}}}")
            if depth == 0:
                return "\n".join(lines[start:k + 1]), k + 1
            k += 1
        raise ValueError("unterminated " + name)

    while i < n:
        ln = lines[i]
        s = ln.strip()
        if not s:
            flush_par(); i += 1; continue
        if s.startswith("\\maketitle") or s.startswith("\\vspace") or s.startswith("\\renewcommand") or \
                s.startswith("\\bibliographystyle") or s.startswith("\\bibliography"):
            i += 1; continue
        if s.startswith("\\newpage"):
            flush_par(); d.page_break(); i += 1; continue
        if s.startswith("\\appendix"):
            flush_par(); appendix, sec_no = True, 0; i += 1; continue
        m = re.match(r"\\(section|subsection)\*?\{", s)
        if m:
            flush_par()
            title, _ = read_group(s, m.end() - 1)
            if m.group(1) == "section":
                sec_no, sub_no = sec_no + 1, 0
                num = ("Appendix " + "ABCDEFG"[sec_no - 1] + ".") if appendix else str(sec_no)
                d.heading(f"{num} {plain(parse_tex(title, {}, ctx))}", 1)
                if title.strip() == "Key References":
                    d.references(bib.reference_list(cited))
            else:
                sub_no += 1
                d.heading(f"{sec_no}.{sub_no} {plain(parse_tex(title, {}, ctx))}", 2)
            i += 1; continue
        m = re.match(r"\\begin\{(abstract|center|itemize|figure|table)\}", s)
        if m:
            flush_par()
            name = m.group(1)
            block, i = env_block(i, name)
            inner = block[block.index("}") + 1:block.rindex(f"\\end{{{name}}}")]
            if name == "abstract":
                d.heading_template("Abstract")
                for p in re.split(r"\n\s*\n|\\medskip", inner):
                    if not p.strip():
                        continue
                    segs = parse_tex(norm(p), {}, ctx)
                    cur = []
                    for sg in segs + [LineBreak()]:
                        if isinstance(sg, LineBreak):
                            if cur:
                                d.paragraph(merge(cur), jc="both")
                            cur = []
                        else:
                            cur.append(sg)
            elif name == "center":
                d.paragraph(parse_tex(norm(inner), {}, ctx), jc="center", spacing='<w:spacing w:after="240"/>')
            elif name == "itemize":
                for item in re.split(r"\\item\b", inner)[1:]:
                    d.bullet(parse_tex(norm(item), {}, ctx))
            elif name == "figure":
                fig_no += 1
                g = re.search(r"\\includegraphics\[width=([\d.]*)\\textwidth\]\{([^}]*)\}", inner)
                frac = float(g.group(1)) if g.group(1) else 1.0
                cap, _ = read_group(inner, inner.index("\\caption") + len("\\caption"))
                note = re.search(r"\\raggedright\s*(.*?)\\par\}", inner, re.S)
                d.figure(os.path.join(ROOT, g.group(2)), frac, fig_no, parse_tex(norm(cap), {}, ctx),
                         parse_tex(norm(note.group(1)), {}, ctx) if note else None)
            elif name == "table":
                tab_no += 1
                cap, _ = read_group(inner, inner.index("\\caption") + len("\\caption"))
                if "\\input{" in inner:
                    path, _ = read_group(inner, inner.index("\\input{") + len("\\input"))
                    src = strip_comments(open(os.path.join(ROOT, path), encoding="utf-8").read())
                else:
                    src = inner
                tb = src[src.index("\\begin{tabular}") + len("\\begin{tabular}"):src.index("\\end{tabular}")]
                rows, aligns, rules = parse_tabular(tb, ctx)
                notes = re.search(r"\\begin\{tablenotes\}.*?\\item\s*(.*?)\\end\{tablenotes\}", src, re.S)
                note_segs = parse_tex(norm(notes.group(1)), {}, ctx) if notes else None
                if len(aligns) == 2:
                    widths, sz = [2000, TEXT_WIDTH - 2000], 18
                else:
                    widths = [1960] + [770] * 4 + [800, 560]
                    widths.append(TEXT_WIDTH - sum(widths))
                    sz = 16
                d.table(tab_no, parse_tex(norm(cap), {}, ctx), rows, widths, aligns, rules, note_segs, sz)
            continue
        par_lines.append(ln)
        i += 1
    flush_par()
    d.write_with_numbering(OUT_PAPER, TITLE)
    print(f"paper: {len(cited)} references cited, {len(d.footnotes)} footnotes, {len(d.images)} figures; wrote",
          os.path.relpath(OUT_PAPER, ROOT))


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "both"
    bib = Bib(BIB)
    if what in ("abstract", "both"):
        build_abstract(Bib(BIB))
    if what in ("paper", "both"):
        build_paper(Bib(BIB))
