#!/usr/bin/env python3
"""Post-render fix-ups for the Word outputs.

Removes the blank paragraphs the apaquarto docx writer emits ahead of the
title block (with a long keep-with-next author list they push the title page
onto page 2 and leave page 1 empty) and sets the document's Title property
from the source file's YAML title, so the Word-exported PDF carries it as
metadata.

Runs as a quarto `post-render` script (every `.docx` listed in
QUARTO_PROJECT_OUTPUT_FILES) or on explicit paths passed as arguments.
"""
from __future__ import annotations

import os
import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

import yaml

_PARA_RE = re.compile(r"\s*(?:<w:p(?:\s[^>]*)?/>|<w:p(?=[\s>]).*?</w:p>)", re.S)
_BOOKMARK_RE = re.compile(r"\s*<w:bookmark(?:Start|End)\b[^>]*/>")
_TEXT_RE = re.compile(r"<w:t(?:\s[^>]*)?>(.*?)</w:t>", re.S)
_TITLE_RE = re.compile(r'<w:pStyle w:val="(?:Heading1|Title)"')
_CORE_TITLE_RE = re.compile(r"<dc:title>.*?</dc:title>|<dc:title\s*/>", re.S)
_CONTENT_MARKERS = ("<w:drawing", "<w:br", "<w:sectPr", "<w:fldChar", "<w:tbl")


def _manuscript_dir() -> Path:
    here = Path(__file__).resolve().parent
    return here.parent if here.name == "scripts" else here


def _is_blank(paragraph: str) -> bool:
    if any(marker in paragraph for marker in _CONTENT_MARKERS):
        return False
    return "".join(_TEXT_RE.findall(paragraph)).strip() == ""


def trim_document_xml(xml: str) -> tuple[str, int]:
    """Return the XML with leading blank paragraphs removed, and how many went."""
    head, sep, body = xml.partition("<w:body>")
    if not sep:
        return xml, 0
    cut, removed = 0, 0
    while True:
        # Bookmark anchors between paragraphs stay in place; the cut never crosses them.
        probe = cut
        while (b := _BOOKMARK_RE.match(body, probe)):
            probe = b.end()
        m = _PARA_RE.match(body, probe)
        if not m:
            return xml, 0
        if _is_blank(m.group(0)) and probe == cut:
            cut, removed = m.end(), removed + 1
            continue
        if removed and _TITLE_RE.search(m.group(0)):
            return head + sep + body[cut:], removed
        return xml, 0


def source_title(docx: Path) -> str | None:
    """Title from the YAML front matter of the .qmd the document was rendered from."""
    qmd = _manuscript_dir() / f"{docx.stem}.qmd"
    if not qmd.is_file():
        return None
    parts = qmd.read_text(encoding="utf-8").split("---", 2)
    if len(parts) < 3:
        return None
    title = (yaml.safe_load(parts[1]) or {}).get("title")
    return str(title) if title else None


def set_core_title(xml: str, title: str) -> str:
    """Return docProps/core.xml with dc:title set to `title`."""
    element = f"<dc:title>{escape(title)}</dc:title>"
    if _CORE_TITLE_RE.search(xml):
        return _CORE_TITLE_RE.sub(element, xml, count=1)
    return xml.replace("</cp:coreProperties>", element + "</cp:coreProperties>")


def finalize_docx(path: Path, title: str | None) -> tuple[int, bool]:
    """Trim the title page and set the Title property; returns (paragraphs removed, title changed)."""
    with zipfile.ZipFile(path) as zin:
        parts: dict[str, str] = {}
        document = zin.read("word/document.xml").decode("utf-8")
        trimmed, removed = trim_document_xml(document)
        if removed:
            parts["word/document.xml"] = trimmed
        titled = False
        if title and "docProps/core.xml" in zin.namelist():
            core = zin.read("docProps/core.xml").decode("utf-8")
            new_core = set_core_title(core, title)
            titled = new_core != core
            if titled:
                parts["docProps/core.xml"] = new_core
        if not parts:
            return 0, False
        fd, tmp = tempfile.mkstemp(suffix=".docx", dir=path.parent)
        os.close(fd)
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                data = parts[item.filename].encode("utf-8") if item.filename in parts else zin.read(item.filename)
                zout.writestr(item, data)
    shutil.move(tmp, path)
    return removed, titled


def main(argv: list[str]) -> int:
    if argv:
        targets = [Path(a) for a in argv]
    else:
        listed = os.environ.get("QUARTO_PROJECT_OUTPUT_FILES", "")
        targets = [Path(p) for p in listed.splitlines() if p.endswith(".docx")]
    for docx in targets:
        if docx.is_file():
            removed, titled = finalize_docx(docx, source_title(docx))
            print(f"finalize_docx: {docx} – {removed} leading blank paragraph(s) removed, "
                  f"title {'set' if titled else 'unchanged'}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
