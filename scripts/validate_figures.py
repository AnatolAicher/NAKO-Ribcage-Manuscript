#!/usr/bin/env python3
"""Pre-render check: warn for every figure/table in figure_paths.yml that doesn't resolve on disk.

Run by quarto as `pre-render` (see `_quarto.yml`). Prints missing items to stderr but
exits 0 so the render proceeds; HTML output then shows broken-image icons / blank iframes
for missing source figures, and PDF/DOCX renders fail later at the image-embed step.

Only source figures under `results/_latest/` are checked. The derived print tree
(`_print/`, built by prepare_print_figures.py for docx/PDF) is not checked here.

Usage:
    python scripts/validate_figures.py
"""
from __future__ import annotations

import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("validate_figures: PyYAML not installed; skipping check.", file=sys.stderr)
    sys.exit(0)


def _manuscript_dir() -> Path:
    here = Path(__file__).resolve().parent
    return here.parent if here.name == "scripts" else here


def _family_item_names(entry: dict) -> list[str]:
    if "item_pattern" in entry:
        return [entry["item_pattern"].format(i) for i in range(1, int(entry["item_count"]) + 1)]
    return list(entry["items"])


def _expected_files(figures: dict) -> list[str]:
    """Run-relative paths every figure entry requires (one per available format)."""
    expected: list[str] = []
    for entry in figures.values():
        kind = entry["kind"]
        exts = list(entry.get("has", ["png"]))
        if kind in ("single", "static", "html_only"):
            stems = [entry["stem"]]
        elif kind == "composite":
            stems = [p["stem"] for p in entry["panels"]]
        elif kind == "family":
            expected.append(f"{entry['dir']}/{entry['index']}")
            stems = [f"{entry['dir']}/{name}" for name in _family_item_names(entry)]
        else:
            continue
        expected.extend(f"{stem}.{ext}" for stem in stems for ext in exts)
    return expected


def main() -> int:
    msd = _manuscript_dir()
    paths_file = msd / "figure_paths.yml"
    run_dir = msd / "results" / "_latest"

    if not paths_file.exists():
        print(f"validate_figures: {paths_file} missing", file=sys.stderr)
        return 1
    if not run_dir.exists():
        print(
            f"validate_figures: {run_dir} not found – point the `_latest` symlink at "
            f"an active run directory (e.g. `make figures PRESET=<preset>`).",
            file=sys.stderr,
        )
        return 1

    spec = yaml.safe_load(paths_file.read_text(encoding="utf-8")) or {}
    figures = spec.get("figures", {})
    tables = spec.get("tables", {})

    expected = _expected_files(figures) + list(tables.values())
    missing = [rel for rel in expected if not (run_dir / rel).exists()]

    if missing:
        print(
            f"validate_figures: WARNING – {len(missing)} of {len(expected)} expected files missing "
            f"under {run_dir.relative_to(msd)}:",
            file=sys.stderr,
        )
        for rel in missing:
            print(f"  - {rel}", file=sys.stderr)
        print(
            "\nRender will proceed; HTML output will show broken-image icons / blank iframes. "
            "Re-point `results/_latest` (via `make figures`) or fix figure_paths.yml.",
            file=sys.stderr,
        )
        return 0

    print(f"validate_figures: ok ({len(figures)} figures, {len(tables)} tables, {len(expected)} files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
