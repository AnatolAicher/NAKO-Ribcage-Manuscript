"""Compose the four continuous DAG PC-score pair-plots into a single 2×2 grid.

Quarto's ``layout-ncol`` is unreliable in the docx build, so the four panels are
merged into one image (assets/pc_scores_dag_grid.png) that renders as a true 2×2
grid in every output format. Re-run after a plotting run that changes the panels.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
FIGS = ROOT / "results" / "_latest" / "ssm_pca" / "figures"
ASSETS = ROOT / "assets"

PANELS = [
    ("pc_scores_pairs_dag_age",          "A – age"),
    ("pc_scores_pairs_dag_height_cm",    "B – standing height"),
    ("pc_scores_pairs_dag_weight_kg",    "C – body mass"),
    ("pc_scores_pairs_dag_body_fat_pct", "D – body-fat %"),
]


def _draw() -> None:
    fig, axes = plt.subplots(2, 2, figsize=(8.0, 8.2))
    for ax, (stem, label) in zip(axes.flat, PANELS):
        ax.imshow(plt.imread(FIGS / f"{stem}.png"))
        ax.axis("off")
        ax.set_title(label, fontsize=11, fontweight="bold", loc="left")
    fig.subplots_adjust(left=0.01, right=0.99, top=0.96, bottom=0.01, wspace=0.02, hspace=0.07)
    ASSETS.mkdir(exist_ok=True)
    fig.savefig(ASSETS / "pc_scores_dag_grid.png", dpi=260, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    _draw()
    print(f"wrote {ASSETS/'pc_scores_dag_grid.png'}")
