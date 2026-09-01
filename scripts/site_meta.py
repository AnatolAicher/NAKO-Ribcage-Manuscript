"""Site-wide constants and the canonical-run provenance line for the website pages."""
from __future__ import annotations

from datetime import datetime, timezone

from results_loader import Results

REPO_URL = "https://github.com/AnatolAicher/NAKO-Ribcage-SSM"


def run_info_md(r: Results) -> str:
    """Markdown sentence naming the pipeline run and code revision behind the site."""
    ts = datetime.strptime(r.run_timestamp(), "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
    rev = r.metadata.get("git_rev", "")
    return (
        f"Figures and numbers on this site were rendered from pipeline run "
        f"`{r.run_name()}` ({ts:%Y-%m-%d %H:%M} UTC), code revision "
        f"[`{r.git_sha_short()}`]({REPO_URL}/commit/{rev})."
    )
