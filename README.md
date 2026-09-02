# NAKO Ribcage SSM – manuscript

Quarto sources of the manuscript, the supplement and the companion website for
*How Sex, Age, Adiposity, and Smoking Shape the Human Rib Cage: Evidence from
26,275 Whole-Body MRIs across the German National Cohort (NAKO)*.

- Website (interactive manuscript, supplement, shape-model viewer):
  <https://anatolaicher.github.io/NAKO-Ribcage-Manuscript/>
- Code and released shape model:
  <https://github.com/AnatolAicher/NAKO-Ribcage-SSM>
  (DOI [10.5281/zenodo.22230693](https://doi.org/10.5281/zenodo.22230693))

## Cite this work

**Zenodo (model data)**

```text
Aicher A, Graf R, Kirschke J, Frauenfelder T, Ensle F, Menze B, Decker J, Kröncke T, Haubold J, Ringhof S, Bamberg F, Schmidt CO, Wielpütz M, Leitzmann M, Willich SN, Keil T, Niendorf T, Pischon T, Schlett C, Möller H. NAKO Human Ribcage Statistical Shape Model (version 1.1.0) [data set]. Zenodo; 2026. https://doi.org/10.5281/zenodo.22230693
```

**GitHub (software)**

```text
Aicher A, Graf R, Kirschke J, Frauenfelder T, Ensle F, Menze B, Decker J, Kröncke T, Haubold J, Ringhof S, Bamberg F, Schmidt CO, Wielpütz M, Leitzmann M, Willich SN, Keil T, Niendorf T, Pischon T, Schlett C, Möller H. NAKO Human Ribcage Statistical Shape Model (version 1.1.0) [software]. GitHub; 2026. https://github.com/AnatolAicher/NAKO-Ribcage-SSM
```

**Preprint:** tbd · **Peer-reviewed article:** tbd

<details>
<summary>BibTeX</summary>

```bibtex
@software{Aicher2026NAKORibcageSSM,
  author    = {Aicher, Anatol and Graf, Robert and Kirschke, Jan and Frauenfelder, Thomas and
               Ensle, Falko and Menze, Bjoern and Decker, Josua and Kr{\"o}ncke, Thomas and
               Haubold, Johannes and Ringhof, Steffen and Bamberg, Fabian and Schmidt, Carsten Oliver and
               Wielp{\"u}tz, Mark and Leitzmann, Michael and Willich, Stefan N. and Keil, Thomas and
               Niendorf, Thoralf and Pischon, Tobias and Schlett, Christopher and M{\"o}ller, Hendrik},
  title     = {{NAKO} Human Ribcage Statistical Shape Model},
  version   = {1.1.0},
  year      = {2026},
  publisher = {Zenodo},
  doi       = {10.5281/zenodo.22230693},
  url       = {https://github.com/AnatolAicher/NAKO-Ribcage-SSM}
}
```

</details>

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

## Licence

The manuscript, supplement, website text and figures are licensed under
[CC BY-NC-ND 4.0](https://creativecommons.org/licenses/by-nc-nd/4.0/); the build
scripts, Makefile and Quarto configuration under the [MIT License](scripts/LICENSE).
[LICENSE](LICENSE) states the scope and lists the third-party components, which
keep their own licences.
