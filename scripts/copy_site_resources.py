#!/usr/bin/env python3
"""Post-render: publish the run figures the site references and the Word-exported PDFs.

Quarto's `resources:` globs do not expand through the `results/_latest`
symlink, so run figures are copied here instead. Only files reachable from
the rendered pages are published: every `results/_latest/…` reference in
`_site/*.html` is copied, and copied HTML files (figure-family index pages)
are scanned in turn for the items they embed. Files under
`_site/results/_latest/` that nothing references are removed.

Altair figure files each embed the same vega-embed bundle (~0.9 MB); it is
written once to `_site/site_libs/vega-embed/` and every copied figure is
rewritten to load it from there.

Also publishes `_docx/*.pdf` (built by `make pdf`) at the root of `_site/`;
the `.docx` files themselves stay off the site. Exits quietly when the
render did not produce `_site/`.
"""
from __future__ import annotations

import hashlib
import os
import re
import shutil
import sys
from pathlib import Path

_REF = re.compile(r'(?:src|href|value)="([^"#?]+\.(?:html|png|svg|json|csv))(?:[#?][^"]*)?"')
_SKIP = ("http://", "https://", "data:", "mailto:", "${")
_VEGA_BUNDLE = re.compile(r'<script type="text/javascript">(\s*// vega-embed\.js bundle.*?)</script>', re.S)
_RUN_PREFIX = "results/_latest/"


def _manuscript_dir() -> Path:
    here = Path(__file__).resolve().parent
    return here.parent if here.name == "scripts" else here


def _refs(html_path: Path) -> set[str]:
    text = html_path.read_text(encoding="utf-8", errors="replace")
    return {m.group(1) for m in _REF.finditer(text) if not m.group(1).startswith(_SKIP)}


def _copy(src: Path, dst: Path) -> bool:
    if dst.exists() and dst.stat().st_mtime >= src.stat().st_mtime:
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return True


def _share_vega_bundle(html_path: Path, libs_dir: Path) -> bool:
    text = html_path.read_text(encoding="utf-8")
    m = _VEGA_BUNDLE.search(text)
    if not m:
        return False
    bundle = m.group(1)
    digest = hashlib.sha256(bundle.encode("utf-8")).hexdigest()[:12]
    bundle_path = libs_dir / f"vega-embed-{digest}.js"
    if not bundle_path.exists():
        bundle_path.parent.mkdir(parents=True, exist_ok=True)
        bundle_path.write_text(bundle, encoding="utf-8")
    rel = os.path.relpath(bundle_path, start=html_path.parent)
    html_path.write_text(text[: m.start()] + f'<script src="{rel}"></script>' + text[m.end():],
                         encoding="utf-8")
    return True


def _publish_run_files(site: Path, run: Path) -> tuple[int, int, int]:
    dest_root = site / "results" / "_latest"
    libs_dir = site / "site_libs" / "vega-embed"
    pending = {r[len(_RUN_PREFIX):] for page in site.glob("*.html")
               for r in _refs(page) if r.startswith(_RUN_PREFIX)}
    wanted: set[str] = set()
    n_copied = n_rewritten = 0
    while pending:
        rel = pending.pop()
        if rel in wanted:
            continue
        src = run / rel
        if not src.is_file():
            print(f"copy_site_resources: WARNING missing {_RUN_PREFIX}{rel}", file=sys.stderr)
            continue
        wanted.add(rel)
        dst = dest_root / rel
        n_copied += _copy(src, dst)
        if src.suffix == ".html":
            n_rewritten += _share_vega_bundle(dst, libs_dir)
            for r in _refs(src):
                nested = os.path.normpath(os.path.join(os.path.dirname(rel), r))
                if not nested.startswith(".."):
                    pending.add(nested)

    n_pruned = 0
    if dest_root.is_dir():
        for path in sorted(dest_root.rglob("*"), reverse=True):
            if path.is_file() and str(path.relative_to(dest_root)) not in wanted:
                path.unlink()
                n_pruned += 1
            elif path.is_dir() and not any(path.iterdir()):
                path.rmdir()
    size_mb = sum((dest_root / rel).stat().st_size for rel in wanted) / 1e6
    print(f"copy_site_resources: {len(wanted)} run files referenced ({size_mb:.0f} MB), "
          f"{n_copied} copied, {n_rewritten} rewritten to the shared vega bundle, {n_pruned} pruned")
    return len(wanted), n_copied, n_pruned


def main() -> int:
    msd = _manuscript_dir()
    site = msd / "_site"
    run = msd / "results" / "_latest"
    if not site.is_dir() or not run.is_dir():
        return 0
    _publish_run_files(site, run.resolve())

    pdfs = sorted((msd / "_docx").glob("*.pdf"))
    for src in pdfs:
        _copy(src, site / src.name)
    print(f"copy_site_resources: {len(pdfs)} PDF(s) published at _site/ root")
    return 0


if __name__ == "__main__":
    sys.exit(main())
