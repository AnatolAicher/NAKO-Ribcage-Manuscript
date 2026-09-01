# manuscript/_csl/

Citation Style Language files pinned locally so the build does not depend on `citationstyles.org` being reachable.

`_quarto.yml` sets `csl: _csl/elsevier.csl` for the manuscript and supplement; `references.qmd` uses the APA style bundled with the apaquarto extension (`_extensions/wjschne/apaquarto/apa.csl`).

To refresh the file:

```bash
curl -L -o _csl/elsevier.csl https://www.zotero.org/styles/elsevier-with-titles
```
