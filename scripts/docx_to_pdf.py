#!/usr/bin/env python3
"""Export the rendered Word documents in `_docx/` to PDF through Microsoft Word.

Drives Word over AppleScript. Word's sandbox restricts scripted opens and
saves to locations it has been granted, and its own container is always
among them: each document is staged in the container's `tmp/`, opened and
saved as PDF there, and the PDF is then moved next to the source document.

Usage:
    python scripts/docx_to_pdf.py                 # every .docx in _docx/
    python scripts/docx_to_pdf.py path/to/x.docx  # explicit files
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

TIMEOUT_S = 1800
WORD_TMP = Path.home() / "Library/Containers/com.microsoft.Word/Data/tmp"

_SCRIPT = """
with timeout of {timeout} seconds
    tell application "Microsoft Word"
        set docPath to "{docx}"
        repeat with d in documents
            if name of d is "{name}" then close d saving no
        end repeat
        open file name docPath
        if not (exists active document) then error "Word did not open " & docPath
        set theDoc to active document
        save as theDoc file name "{pdf}" file format format PDF
        close theDoc saving no
    end tell
end timeout
"""


def _manuscript_dir() -> Path:
    here = Path(__file__).resolve().parent
    return here.parent if here.name == "scripts" else here


def export(docx: Path) -> Path:
    docx = docx.resolve()
    WORD_TMP.mkdir(parents=True, exist_ok=True)
    staged_docx = WORD_TMP / docx.name
    staged_pdf = staged_docx.with_suffix(".pdf")
    shutil.copy2(docx, staged_docx)
    staged_pdf.unlink(missing_ok=True)
    script = _SCRIPT.format(timeout=TIMEOUT_S, docx=staged_docx, name=docx.name, pdf=staged_pdf)
    try:
        subprocess.run(["osascript", "-e", script], check=True, timeout=TIMEOUT_S + 60)
        if not staged_pdf.is_file():
            raise RuntimeError(f"Word reported success but {staged_pdf} is missing")
        pdf = docx.with_suffix(".pdf")
        shutil.move(staged_pdf, pdf)
    finally:
        staged_docx.unlink(missing_ok=True)
    return pdf


def main(argv: list[str]) -> int:
    targets = [Path(a) for a in argv] or sorted((_manuscript_dir() / "_docx").glob("*.docx"))
    if not targets:
        print("docx_to_pdf: nothing to export (run `make docx` first)", file=sys.stderr)
        return 1
    for docx in targets:
        pdf = export(docx)
        print(f"docx_to_pdf: {docx.name} → {pdf.relative_to(_manuscript_dir()) if pdf.is_relative_to(_manuscript_dir()) else pdf} ({pdf.stat().st_size / 1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
