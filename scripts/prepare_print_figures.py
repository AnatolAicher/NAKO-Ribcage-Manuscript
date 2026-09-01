#!/usr/bin/env python3
"""Build the A4-capped print-PNG tree consumed by the docx/PDF figure branches.

For every figure in figure_paths.yml that has a print form, the source PNG under
`results/_latest/` is copied into `<print_root>/<stem>.png`, scaled down proportionally
(never up) to fit an A4 printable box at the figure's context DPI (main 600, supplement
300), and stamped with that DPI. Interactive (html) builds never reference this tree.

Usage:
    python scripts/prepare_print_figures.py [--force]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml
from PIL import Image


def _manuscript_dir() -> Path:
    here = Path(__file__).resolve().parent
    return here.parent if here.name == "scripts" else here


def _print_stems(figures: dict) -> list[tuple[str, str]]:
    """(run-relative PNG stem, context) for every figure with a print form."""
    out: list[tuple[str, str]] = []
    for entry in figures.values():
        kind = entry["kind"]
        ctx = entry.get("context", "main")
        if kind in ("single", "static"):
            out.append((entry["stem"], ctx))
        elif kind == "composite":
            out.extend((p["stem"], ctx) for p in entry["panels"])
        elif kind == "family":
            if "item_pattern" in entry:
                names = [entry["item_pattern"].format(i) for i in entry["print_items"]]
            elif entry["print_items"] == "all":
                names = list(entry["items"])
            else:
                names = list(entry["print_items"])
            out.extend((f"{entry['dir']}/{name}", ctx) for name in names)
        # html_only: no print form
    return out


def _box_px(box_mm: tuple[float, float], dpi: int) -> tuple[int, int]:
    return (round(box_mm[0] / 25.4 * dpi), round(box_mm[1] / 25.4 * dpi))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--force", action="store_true", help="rebuild even if the output is up to date")
    args = ap.parse_args()

    msd = _manuscript_dir()
    run_dir = msd / "results" / "_latest"
    spec = yaml.safe_load((msd / "figure_paths.yml").read_text(encoding="utf-8")) or {}
    defaults = spec.get("defaults", {})

    print_root = msd / defaults.get("print_root", "_print")
    box_mm = tuple(defaults.get("a4_box_mm", [160, 240]))
    dpi_by_context = {
        "main": int(defaults.get("print_dpi_main", 600)),
        "supplement": int(defaults.get("print_dpi_supplement", 300)),
    }

    if not run_dir.exists():
        print(f"prepare_print_figures: {run_dir} not found; run `make figures` first.", file=sys.stderr)
        return 1

    written = skipped = missing = 0
    for stem, ctx in _print_stems(spec.get("figures", {})):
        src = run_dir / f"{stem}.png"
        dst = print_root / f"{stem}.png"
        if not src.exists():
            print(f"  missing source: {src.relative_to(msd)}", file=sys.stderr)
            missing += 1
            continue
        if not args.force and dst.exists() and dst.stat().st_mtime >= src.stat().st_mtime:
            skipped += 1
            continue
        dpi = dpi_by_context.get(ctx, dpi_by_context["main"])
        dst.parent.mkdir(parents=True, exist_ok=True)
        with Image.open(src) as img:
            img.thumbnail(_box_px(box_mm, dpi), Image.LANCZOS)  # downscale-only, aspect-preserving
            img.save(dst, format="PNG", dpi=(dpi, dpi))
        written += 1

    print(
        f"prepare_print_figures: {written} written, {skipped} up-to-date, {missing} missing "
        f"→ {print_root.relative_to(msd)}/"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
