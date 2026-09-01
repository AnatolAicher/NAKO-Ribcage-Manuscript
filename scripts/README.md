# manuscript/scripts/

Helpers behind the Quarto build. Paths are relative to `manuscript/`.

| Script | Purpose | Invoked by |
| --- | --- | --- |
| `bib_from_dois.py` | Reads `dois.txt`, fetches BibTeX via DOI content negotiation, writes `references.bib`; appends `references-manual.bib` (EndNote bridge) if present. | `make bib` (also a prerequisite of `make render` and `make docx`) |
| `validate_figures.py` | Warns for every entry in `figure_paths.yml` that does not resolve under `results/_latest/`; exits 0 so the render proceeds. | Quarto `pre-render` |
| `copy_site_resources.py` | Copies the run's figure set and the public SSM viewer into `_site/results/_latest/`, and publishes `_docx/*.pdf` at the `_site/` root. | Quarto `post-render` |
| `finalize_docx.py` | Removes the blank leading paragraphs apaquarto emits ahead of the title block in `.docx` output and sets the document Title property from the source's YAML title. | Quarto `post-render` |
| `results_loader.py` | `Results` class read by every page's setup chunk: cohort counts, PCA numbers, association summaries, formatted tables, and the `fig_html` / `fig_print` figure embedding driven by `figure_paths.yml`. | imported from setup chunks |
| `site_meta.py` | Repository URL and the canonical-run provenance line shown on the Home and Data pages. | imported from setup chunks |
| `supplement_numbering.lua` | Numbers supplement headings S1, S1.1, … identically in HTML and docx. | `filters:` in `supplement.qmd` |
| `print_links.lua` | Rewrites cross-page links (`page.qmd#anchor`) to absolute site URLs in the Word and PDF outputs; HTML keeps the relative links. | `filters:` in `_quarto.yml` |
| `prepare_print_figures.py` | Builds the A4-capped print-PNG tree `_print/` that the docx figure branches reference. | `make print-figures` (auto-run by `make docx`) |
| `docx_to_pdf.py` | Exports `_docx/*.docx` to PDF through Microsoft Word (AppleScript). | `make pdf` |
| `build_reference_docx.py` | Regenerates `assets/reference.docx`, the Word styling template for the supplement. | manual |
| `make_dag_figure.py` | Renders the targeted-analysis causal DAG to `assets/dag.{svg,png}`. | manual |
| `make_pairplot_grid.py` | Composes the four continuous-exposure PC pair-plots into `assets/pc_scores_dag_grid.png`. | manual; re-run after a plotting run changes the panels |

The build expects `results/_latest/` to symlink the active pipeline run directory. Re-point it via `make figures RUN=<path>` or `make figures PRESET=<preset>`; prose numbers and figures follow on the next render.

## EndNote bridge

For references without DOIs (book chapters, theses, unpublished reports):

1. In EndNote, select the references.
2. **File → Export...**
3. **Output style: "BibTeX Export"** (install it from EndNote's style downloads if missing).
4. **Save as:** `references-manual.bib`.
5. Run `make bib` – it concatenates the auto-generated entries with the EndNote export.

The cite-keys you assign in EndNote (Tools → Change/Move/Copy Fields → Label) become the BibTeX keys. Pick stable ones; CSL formatting depends only on the entry contents, not the key, so renaming a key only affects in-document `[@key]` references.
