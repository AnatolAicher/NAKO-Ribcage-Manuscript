# NAKO Ribcage SSM – manuscript Makefile.
#
# Targets:
#   make / make all           Full site build: docx → pdf → render.
#   make bib                  Regenerate references.bib from dois.txt.
#   make figures              Re-point results/_latest at the latest run dir
#                             matching $(PRESET), or at $(RUN) if given.
#   make print-figures        Build the A4-capped print-PNG tree (_print/) that the
#                             docx figure branches reference (auto-run by docx).
#   make docx                 Render manuscript.qmd to .docx via the apaquarto
#                             extension (APA 7 title page, authors + affiliations);
#                             supplement.qmd to .docx using the styled reference
#                             template at assets/reference.docx (regenerate with
#                             `python scripts/build_reference_docx.py`).
#   make pdf                  Export _docx/*.docx to _docx/*.pdf through Microsoft
#                             Word. The site render publishes the PDFs (not the
#                             .docx files) at the root of _site/.
#   make render               Render the site to _site/ (includes _docx/*.pdf when
#                             present).
#   make preview              Live-reload preview at http://localhost:4848.
#   make publish              Full build, then push _site/ to the gh-pages branch
#                             via `quarto publish gh-pages`. Requires this
#                             directory to be a git repository with a GitHub
#                             remote; the first run creates _publish.yml.
#   make extensions           Install the apaquarto extension.
#   make clean                Remove _site/, _docx/, .quarto/, _print/.
#
# `make figures` examples:
#   make figures RUN=results/full_analysis_20260601T120000Z
#   make figures PRESET=30000
#   make figures                       # newest run in results/ wins

PRESET ?=
RUN    ?=
# Quarto picks `python3` from PATH for executing {python} chunks. When the
# Makefile is invoked from a shell that hasn't activated the project venv,
# that resolves to a system Python without `yaml` / `jupyter_client` and the
# render fails with `ModuleNotFoundError: No module named 'yaml'`.
#
# QUARTO_PYTHON below pins the interpreter to the project venv; override on
# the command line, e.g. `make docx QUARTO_PYTHON=/path/to/other/python3`.
QUARTO_PYTHON ?= $(HOME)/.venvs/nako_ribs/bin/python3
PYTHON        ?= $(QUARTO_PYTHON)
export QUARTO_PYTHON

.PHONY: all bib figures print-figures render preview publish docx pdf _docx_check_python extensions clean

all: docx pdf render

bib:
	$(PYTHON) scripts/bib_from_dois.py

# Build the A4-capped print-PNG tree (_print/) consumed by the docx figure branches.
print-figures:
	$(PYTHON) scripts/prepare_print_figures.py

# Point results/_latest at the active run directory.
# Resolution order:
#   1. RUN=<path>   – explicit run dir (absolute or relative to manuscript/)
#   2. PRESET=<n>   – newest results/<preset>_*/ matching the preset name
#   3. (no args)    – newest results/*/ directory
figures:
	@cd results && \
	if [ -n "$(RUN)" ]; then \
	  target="$$(basename $(RUN))"; \
	elif [ -n "$(PRESET)" ]; then \
	  target=$$(ls -td $(PRESET)_*/ 2>/dev/null | head -n 1); target=$${target%/}; \
	  [ -n "$$target" ] || { echo "no run matching PRESET=$(PRESET)"; exit 1; }; \
	else \
	  target=$$(ls -td */ 2>/dev/null | grep -v '^_latest/$$' | head -n 1); target=$${target%/}; \
	  [ -n "$$target" ] || { echo "no runs in results/"; exit 1; }; \
	fi; \
	if [ ! -d "$$target" ]; then \
	  echo "ERROR: results/$$target does not exist; refusing to create a dangling symlink."; \
	  echo "       Available run directories:"; \
	  ls -1d */ 2>/dev/null | grep -v '^_latest/$$' | sed 's|/$$||' | sed 's/^/         /'; \
	  exit 1; \
	fi; \
	ln -sfn "$$target" _latest; \
	echo "results/_latest → $$target"

render: bib
	quarto render --to html

preview:
	quarto preview

publish: all
	quarto publish gh-pages --no-render --no-browser

_docx_check_python:
	@if ! "$(QUARTO_PYTHON)" -c "import yaml, jupyter_client" >/dev/null 2>&1; then \
	  echo "ERROR: $(QUARTO_PYTHON) lacks yaml / jupyter_client."; \
	  echo "       Activate the project venv first, or override:"; \
	  echo "         make docx QUARTO_PYTHON=/abs/path/to/python3"; \
	  exit 1; \
	fi

docx: bib _docx_check_python print-figures
	quarto render manuscript.qmd --to apaquarto-docx --output-dir _docx
	quarto render supplement.qmd --to docx --output-dir _docx

pdf: docx
	$(PYTHON) scripts/docx_to_pdf.py

extensions:
	quarto add wjschne/apaquarto --no-prompt

clean:
	rm -rf _site _docx .quarto _print
