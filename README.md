# NAKO Ribcage SSM – manuscript

Quarto sources of the manuscript, the supplement and the companion website for
*How Sex, Age, Adiposity, and Smoking Shape the Human Rib Cage: Evidence from
26,275 Whole-Body MRIs across the German National Cohort (NAKO)*.

- Website (interactive manuscript, supplement, shape-model viewer):
  <https://anatolaicher.github.io/NAKO-Ribcage-Manuscript/>
- Code and released shape model:
  <https://github.com/AnatolAicher/NAKO-Ribcage-SSM>
  (DOI [10.5281/zenodo.22230693](https://doi.org/10.5281/zenodo.22230693))

## Layout

| Path | Content |
|---|---|
| `manuscript.qmd`, `supplement.qmd` | the paper; numbers and figures are read from the pipeline run at render time |
| `index.qmd`, `data.qmd`, `viewer.qmd`, `references.qmd` | website pages |
| `figure_paths.yml` | maps every figure ID to its files in the run directory, per output format |
| `dois.txt`, `references-manual.bib` → `references.bib` | bibliography sources (`make bib`) |
| `scripts/` | build helpers, described in `scripts/README.md` |
| `assets/`, `_csl/`, `_extensions/` | static figures, Word template, citation style, the apaquarto extension |
| `_freeze/` | cached execution results, so the text re-renders without the run directory (figures still need it) |

## Building

Requirements: Quarto ≥ 1.9; Python 3.13 with numpy, pandas, scipy, pyyaml,
tabulate, jupyter, matplotlib, Pillow and python-docx (the `nako_ribs`
environment of the code repository covers the analysis packages); Microsoft
Word for the PDF export (`scripts/docx_to_pdf.py`, macOS).

The pipeline run directory is not part of this repository. Point
`results/_latest` at it first:

```bash
make figures RUN=/path/to/full_analysis-ab26a74_20260809T225556Z
make render      # website → _site/
make             # docx → Word-exported PDF → website
make publish     # full build, then quarto publish gh-pages
```

`make -n` lists every target with its description.
