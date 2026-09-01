"""Regenerate `assets/reference.docx` with scientific-manuscript-draft styles.

Workflow:
1. Extract pandoc's bundled default reference.docx via `quarto pandoc`.
2. Adjust paragraph/character styles (fonts, sizes, line spacing) to a
   readable submission-draft look. Pandoc applies these definitions when
   rendering `supplement.qmd` to `.docx`; the reference document is
   referenced via `format.docx.reference-doc:` in `_quarto.yml`.
3. Save to `assets/reference.docx`.

Run after the project moves to a different Pandoc/Quarto release or when
you want to retune the supplement's Word styling.

Outputs
-------
`assets/reference.docx`
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from docx import Document
from docx.enum.text import WD_LINE_SPACING
from docx.shared import Cm, Pt

BODY_FONT = "Times New Roman"
BODY_SIZE_PT = 11
LINE_SPACING = 1.5
PAGE_MARGIN_CM = 2.5

STYLE_SPEC: dict[str, dict] = {
    "Normal":           {"font": BODY_FONT, "size": BODY_SIZE_PT},
    "Body Text":        {"font": BODY_FONT, "size": BODY_SIZE_PT},
    "First Paragraph":  {"font": BODY_FONT, "size": BODY_SIZE_PT},
    "Compact":          {"font": BODY_FONT, "size": BODY_SIZE_PT},
    "Title":            {"font": BODY_FONT, "size": 18, "bold": True},
    "Subtitle":         {"font": BODY_FONT, "size": 14, "italic": True},
    "Author":           {"font": BODY_FONT, "size": BODY_SIZE_PT},
    "Date":             {"font": BODY_FONT, "size": BODY_SIZE_PT},
    "Abstract Title":   {"font": BODY_FONT, "size": BODY_SIZE_PT, "bold": True},
    "Abstract":         {"font": BODY_FONT, "size": 10, "italic": True},
    "Bibliography":     {"font": BODY_FONT, "size": 10},
    "Heading 1":        {"font": BODY_FONT, "size": 14, "bold": True},
    "Heading 2":        {"font": BODY_FONT, "size": 12, "bold": True},
    "Heading 3":        {"font": BODY_FONT, "size": BODY_SIZE_PT, "bold": True, "italic": True},
    "Heading 4":        {"font": BODY_FONT, "size": BODY_SIZE_PT, "italic": True},
    "Heading 5":        {"font": BODY_FONT, "size": BODY_SIZE_PT, "italic": True},
    "Caption":          {"font": BODY_FONT, "size": 10, "italic": True},
    "Image Caption":    {"font": BODY_FONT, "size": 10, "italic": True},
    "Table Caption":    {"font": BODY_FONT, "size": 10, "italic": True},
    "Figure":           {"font": BODY_FONT, "size": 10},
    "Captioned Figure": {"font": BODY_FONT, "size": 10},
    "Footnote Text":    {"font": BODY_FONT, "size": 9},
    "Block Text":       {"font": BODY_FONT, "size": 10, "italic": True},
}


def _extract_default(target: Path) -> None:
    out = subprocess.run(
        ["quarto", "pandoc", "--print-default-data-file", "reference.docx"],
        capture_output=True, check=True,
    )
    target.write_bytes(out.stdout)


def _apply_style(style, spec: dict) -> None:
    font = style.font
    if "font" in spec:
        font.name = spec["font"]
    if "size" in spec:
        font.size = Pt(spec["size"])
    if "bold" in spec:
        font.bold = spec["bold"]
    if "italic" in spec:
        font.italic = spec["italic"]


def _apply_paragraph_format(style, line_spacing: float) -> None:
    pf = style.paragraph_format
    pf.line_spacing = line_spacing
    pf.line_spacing_rule = WD_LINE_SPACING.MULTIPLE


def _apply_margins(doc: Document, cm: float) -> None:
    margin = Cm(cm)
    for sec in doc.sections:
        sec.top_margin = margin
        sec.bottom_margin = margin
        sec.left_margin = margin
        sec.right_margin = margin


def build(target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    _extract_default(target)

    doc = Document(target)
    for name, spec in STYLE_SPEC.items():
        try:
            _apply_style(doc.styles[name], spec)
        except KeyError:
            print(f"warning: style {name!r} not present in reference.docx", file=sys.stderr)

    for style_name in ("Normal", "Body Text", "First Paragraph", "Abstract"):
        try:
            _apply_paragraph_format(doc.styles[style_name], LINE_SPACING)
        except KeyError:
            pass

    _apply_margins(doc, PAGE_MARGIN_CM)
    doc.save(target)
    print(f"wrote {target} ({target.stat().st_size:,} bytes)")


def _manuscript_dir() -> Path:
    here = Path(__file__).resolve().parent
    return here.parent if here.name == "scripts" else here


if __name__ == "__main__":
    build(_manuscript_dir() / "assets" / "reference.docx")
