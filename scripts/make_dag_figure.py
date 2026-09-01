"""Render the targeted-analysis causal DAG to manuscript/assets/dag.{svg,png}.

Layout: four equidistant columns – {Sex, Age} · {Height, Body fat, Smoking} ·
{Body mass} · {Rib cage shape} – plus an intermediate column holding the latent
"Unknown" confounder above the others. Sex and age are exogenous; height, body
fat and smoking are caused by sex+age; body mass is downstream of sex, age,
height and body fat; every exposure acts on shape. Dashed grey edges encode the
latent confounder (caused by sex+age) acting on the non-exogenous exposures and
on shape – the no-unmeasured-confounding assumption their adjusted associations
rest on.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib.cm as cm
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

ASSETS = Path(__file__).resolve().parent.parent / "assets"

DARK = cm.PuBu(1.0)   # roots + outcome
MID = cm.PuBu(0.5)    # intermediate exposures
GREY = "#888888"      # latent box + dashed edges

# key: (x, y, label, facecolor, textcolor, latent)
NODES = {
    "sex":     (0.0,  0.7, "Sex",             DARK,    "white", False),
    "age":     (0.0, -0.7, "Age",             DARK,    "white", False),
    "height":  (3.2,  1.4, "Height",          MID,     "black", False),
    "bodyfat": (3.2,  0.0, "Body fat",        MID,     "black", False),
    "smoking": (3.2, -1.4, "Smoking",         MID,     "black", False),
    "U":       (4.8,  2.5, "Unknown",         "white", GREY,    True),
    "weight":  (6.4,  0.0, "Body mass",       MID,     "black", False),
    "shape":   (9.6,  0.0, "Rib cage\nshape", DARK,    "white", False),
}

SOLID = [
    ("sex", "height"), ("sex", "bodyfat"), ("sex", "smoking"), ("sex", "weight"), ("sex", "shape"),
    ("age", "height"), ("age", "bodyfat"), ("age", "smoking"), ("age", "weight"), ("age", "shape"),
    ("height", "weight"), ("bodyfat", "weight"),
    ("height", "shape"), ("bodyfat", "shape"), ("smoking", "shape"), ("weight", "shape"),
]
DASHED = [
    ("sex", "U"), ("age", "U"),
    ("U", "height"), ("U", "bodyfat"), ("U", "smoking"), ("U", "weight"), ("U", "shape"),
]

HW, HH = 0.64, 0.30  # box half-width / half-height


def _draw() -> None:
    fig, ax = plt.subplots(figsize=(12.0, 5.4))
    ax.set_xlim(-1.0, 10.6)
    ax.set_ylim(-1.95, 3.15)
    ax.axis("off")
    ax.set_aspect("equal")

    boxes = {}
    for key, (x, y, label, fc, tc, latent) in NODES.items():
        box = FancyBboxPatch(
            (x - HW, y - HH), 2 * HW, 2 * HH,
            boxstyle="round,pad=0.02,rounding_size=0.10",
            linewidth=1.3, linestyle="--" if latent else "-",
            edgecolor=GREY if latent else "#333333", facecolor=fc, zorder=3,
        )
        ax.add_patch(box)
        boxes[key] = box
        ax.text(x, y, label, ha="center", va="center", fontsize=9.5,
                color=tc, fontstyle="italic" if latent else "normal", zorder=4)

    def arrow(a, b, dashed):
        ax.add_patch(FancyArrowPatch(
            (NODES[a][0], NODES[a][1]), (NODES[b][0], NODES[b][1]),
            patchA=boxes[a], patchB=boxes[b],
            connectionstyle="arc3,rad=0", arrowstyle="-|>", mutation_scale=16,
            shrinkA=1, shrinkB=4,
            lw=1.0 if dashed else 1.3,
            color=GREY if dashed else "black",
            linestyle=(0, (4, 3)) if dashed else "-",
            zorder=2,
        ))

    for a, b in SOLID:
        arrow(a, b, dashed=False)
    for a, b in DASHED:
        arrow(a, b, dashed=True)

    ASSETS.mkdir(exist_ok=True)
    for ext in ("svg", "png"):
        fig.savefig(ASSETS / f"dag.{ext}", bbox_inches="tight", dpi=300)
    plt.close(fig)


if __name__ == "__main__":
    _draw()
    print(f"wrote {ASSETS/'dag.svg'} and dag.png")
