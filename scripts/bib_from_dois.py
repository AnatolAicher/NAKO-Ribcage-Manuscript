#!/usr/bin/env python3
"""Build references.bib from dois.txt via DOI content negotiation.

Reads `manuscript/dois.txt` (one DOI per line, optional `cite-key:` prefix),
fetches BibTeX from doi.org for each entry, and writes `manuscript/references.bib`.

If `manuscript/references-manual.bib` exists (EndNote export, non-DOI refs),
its contents are concatenated after the auto-generated entries.

Usage:
    python scripts/bib_from_dois.py           # from manuscript/ working dir
    python manuscript/scripts/bib_from_dois.py  # from repo root
"""
from __future__ import annotations

import html
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.request
from pathlib import Path

# Combining marks → LaTeX accent commands. Classic BibTeX is 8-bit
# byte-oriented and
# truncates multi-byte UTF-8 mid-sequence when shortening first names,
# producing invalid bytes in the .bbl. Decomposing to NFD and rewriting
# the marks as LaTeX commands keeps the input pure ASCII.
_COMBINING_TO_LATEX = {
    "̀": r"\`",   # grave
    "́": r"\'",   # acute
    "̂": r"\^",   # circumflex
    "̃": r"\~",   # tilde
    "̄": r"\=",   # macron
    "̆": r"\u",   # breve
    "̇": r"\.",   # dot above
    "̈": r'\"',   # diaeresis
    "̊": r"\r",   # ring above
    "̋": r"\H",   # double acute
    "̌": r"\v",   # caron / háček
    "̧": r"\c",   # cedilla
    "̨": r"\k",   # ogonek
}

# Non-ASCII letters with no NFD decomposition.
_STANDALONE_TO_LATEX = {
    "ß": r"\ss{}", "Æ": r"\AE{}", "æ": r"\ae{}",
    "Ø": r"\O{}", "ø": r"\o{}", "Å": r"\AA{}", "å": r"\aa{}",
    "Ł": r"\L{}", "ł": r"\l{}", "Œ": r"\OE{}", "œ": r"\oe{}",
    "Þ": r"\TH{}", "þ": r"\th{}", "Đ": r"\DH{}", "đ": r"\dh{}",
    "–": "--", "\u2014": "--", "’": "'", "‘": "`", "“": "``", "”": "''",
}

DOI_RE = re.compile(r"^(?:(?P<key>[A-Za-z][A-Za-z0-9_+:.-]*)\s*:\s*)?(?P<doi>10\.\d{4,9}/\S+)\s*$")


def _manuscript_dir() -> Path:
    here = Path(__file__).resolve().parent
    return here.parent if here.name == "scripts" else here


def parse_dois(text: str) -> list[tuple[str | None, str]]:
    entries: list[tuple[str | None, str]] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = DOI_RE.match(line)
        if not m:
            print(f"  skip (no DOI): {line!r}", file=sys.stderr)
            continue
        entries.append((m.group("key"), m.group("doi")))
    return entries


def fetch_bibtex(doi: str, timeout: float = 15.0) -> str:
    req = urllib.request.Request(
        f"https://doi.org/{doi}",
        headers={
            "Accept": "application/x-bibtex; charset=utf-8",
            "User-Agent": "nako-rib-manuscript/0.1 (mailto:aicheranatol@gmail.com)",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return _normalize_entry(_sanitize_for_latex(resp.read().decode("utf-8")))


def _sanitize_for_latex(bibtex: str) -> str:
    # 1. HTML-decode entities (BMJ et al. return `&amp;`, `&lt;`, ...).
    text = html.unescape(bibtex)
    # 2. Convert UTF-8 letters to LaTeX accent commands.
    text = _ascii_safe_latex(text)
    # 3. Escape bare `&` so LaTeX doesn't see an alignment tab.
    text = re.sub(r"(?<!\\)&", r"\\&", text)
    # 4. Strip dangling commas in author lists ("X, and Y" / "Z, }"),
    #    which Zenodo emits and elsarticle.bst rejects with "comma at the end".
    text = re.sub(r",(\s+(?:and\b|\}))", r"\1", text)
    return text


_BIBTEX_MONTHS = {"jan", "feb", "mar", "apr", "may", "jun",
                  "jul", "aug", "sep", "oct", "nov", "dec"}
_MONTH_RE = re.compile(r"(\bmonth\s*=\s*)\{?([A-Za-z]+)\}?")


def _normalize_entry(bibtex: str) -> str:
    # doi.org emits long month names (`month=June`, `month=Sept`) that are
    # not BibTeX macros; every English month name shortens to its macro.
    def _month(m: re.Match) -> str:
        macro = m.group(2).lower()[:3]
        return f"{m.group(1)}{macro}" if macro in _BIBTEX_MONTHS else m.group(0)

    bibtex = _MONTH_RE.sub(_month, bibtex)
    # doi.org types book chapters as @inbook while supplying `booktitle`;
    # @incollection is the type whose formatting includes the book title.
    if re.match(r"\s*@inbook\b", bibtex, re.I) and re.search(r"\bbooktitle\s*=", bibtex, re.I):
        bibtex = re.sub(r"^\s*@inbook", "@incollection", bibtex, count=1, flags=re.I)
    return bibtex


def _ascii_safe_latex(s: str) -> str:
    decomposed = unicodedata.normalize("NFD", s)
    out: list[str] = []
    i = 0
    while i < len(decomposed):
        ch = decomposed[i]
        i += 1
        if unicodedata.category(ch) == "Mn":
            # Stray combining mark without a base – keep verbatim.
            out.append(_COMBINING_TO_LATEX.get(ch, ch))
            continue
        base = _STANDALONE_TO_LATEX.get(ch, ch) if ord(ch) >= 128 else ch
        while i < len(decomposed) and unicodedata.category(decomposed[i]) == "Mn":
            mark = decomposed[i]
            i += 1
            if mark in _COMBINING_TO_LATEX:
                base = f"{_COMBINING_TO_LATEX[mark]}{{{base}}}"
        out.append(base)
    return "".join(out)


def rekey(bibtex: str, new_key: str | None) -> str:
    if not new_key:
        return bibtex
    return re.sub(
        r"(@\w+\s*\{)\s*[^,]+,",
        lambda m: f"{m.group(1)}{new_key},",
        bibtex.lstrip(),
        count=1,
    )


def build_bib(manuscript_dir: Path) -> int:
    dois_file = manuscript_dir / "dois.txt"
    out_bib = manuscript_dir / "references.bib"
    manual_bib = manuscript_dir / "references-manual.bib"

    if not dois_file.exists():
        print(f"error: {dois_file} not found", file=sys.stderr)
        return 1

    entries = parse_dois(dois_file.read_text(encoding="utf-8"))
    if not entries:
        print("no DOIs in dois.txt; writing header only")

    out_lines: list[str] = [
        "% Generated by scripts/bib_from_dois.py from dois.txt – do not edit by hand.",
        "% Manual / EndNote entries belong in references-manual.bib and are appended below.",
        "",
    ]

    failures = 0
    for key, doi in entries:
        print(f"  fetching {doi}{f' as @{key}' if key else ''}")
        try:
            bib = fetch_bibtex(doi)
        except (urllib.error.URLError, TimeoutError) as exc:
            print(f"  ! failed: {exc}", file=sys.stderr)
            failures += 1
            continue
        out_lines.append(rekey(bib, key).strip())
        out_lines.append("")
        time.sleep(0.2)  # polite to doi.org

    if manual_bib.exists():
        out_lines.append("% --- Manual / EndNote entries (references-manual.bib) ---")
        out_lines.append(manual_bib.read_text(encoding="utf-8").rstrip())
        out_lines.append("")

    out_bib.write_text("\n".join(out_lines), encoding="utf-8")
    print(f"wrote {out_bib} ({len(entries) - failures} DOI entries, {failures} failures)")
    return 1 if failures and not entries else 0


if __name__ == "__main__":
    sys.exit(build_bib(_manuscript_dir()))
