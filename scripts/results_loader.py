"""Numeric and tabular accessors that read from the active run directory.

Used by the setup chunks and inline `{python}` expressions of the site pages
(`manuscript.qmd`, `supplement.qmd`, `index.qmd`, `data.qmd`) so that the text stays in sync with whichever pipeline run is
currently staged. The loader reads from `results/_latest/`, a symlink to the
active run directory; updating the symlink (via `make figures`) is enough to
re-point the manuscript at a different run.

Outputs
-------
Class `Results`: lazy accessors keyed off `results/_latest/`.
"""
from __future__ import annotations

import json
import re
from functools import cached_property
from pathlib import Path

import numpy as np
import pandas as pd
import yaml
from scipy import stats

_MANUSCRIPT_DIR = Path(__file__).resolve().parent.parent
_DEFAULT_FIGURE_SPEC = _MANUSCRIPT_DIR / "figure_paths.yml"


def _read_table(path: Path) -> pd.DataFrame:
    """Pipeline CSV table; em dashes emitted by earlier runs are normalised to en dashes."""
    return pd.read_csv(path).replace("\u2014", "–", regex=True)


class FigureError(ValueError):
    """Unknown figure id, or a figure entry missing its required media."""


SHAPE_FEATURE_LABELS: dict[str, str] = {
    "original_shape_Elongation":              "Elongation",
    "original_shape_Flatness":                "Flatness",
    "original_shape_LeastAxisLength":         "Least axis length",
    "original_shape_MajorAxisLength":         "Major axis length",
    "original_shape_Maximum2DDiameterColumn": "Max 2D diameter (column)",
    "original_shape_Maximum2DDiameterRow":    "Max 2D diameter (row)",
    "original_shape_Maximum2DDiameterSlice":  "Max 2D diameter (slice)",
    "original_shape_Maximum3DDiameter":       "Max 3D diameter",
    "original_shape_MeshVolume":              "Mesh volume",
    "original_shape_MinorAxisLength":         "Minor axis length",
    "original_shape_Sphericity":              "Sphericity",
    "original_shape_SurfaceArea":             "Surface area",
    "original_shape_SurfaceVolumeRatio":      "Surface-to-volume ratio",
    "original_shape_VoxelVolume":             "Voxel volume",
    "rib_length":                             "Rib length",
}

PREDICTOR_LABELS: dict[str, str] = {
    "age":            "age",
    "bmi":            "BMI",
    "body_fat_pct":   "body fat (%)",
    "pack_years":     "pack-years",
    "height_cm":      "height",
    "weight_kg":      "body mass",
    "sex":            "sex",
    "smoking_status": "smoking status",
    "is_female":      "sex (female)",
    "ever_smoker":    "ever-smoker",
}

TABLE1_METADATA_LABELS: dict[str, str] = {
    "N":                  "N",
    "age":                "Age (years)",
    "bmi":                "BMI (kg/m²)",
    "body_fat_pct":       "Body fat (%)",
    "pack_years_ever":    "Pack-years (ever-smokers)",
    "height_cm":          "Height (cm)",
    "weight_kg":          "Body mass (kg)",
    "smoking_status":     "Smoking status",
}

TABLE1_METADATA_ORDER: list[str] = [
    "N",
    "age",
    "height_cm",
    "weight_kg",
    "bmi",
    "body_fat_pct",
    "smoking_status",
    "pack_years_ever",
]


def _format_count(n: int) -> str:
    return f"{n:,}"


# Standalone integer runs of ≥4 digits (not part of decimals) inside table cells.
_EMBEDDED_COUNT_RE = re.compile(r"(?<![\d.])(\d{4,})(?![\d.])")


def _format_embedded_counts(cell: str) -> str:
    return _EMBEDDED_COUNT_RE.sub(lambda m: _format_count(int(m.group(1))), cell)


def _format_pvalue(s: str) -> str:
    if s in ("", "–", "\u2014") or pd.isna(s):
        return "–"
    try:
        p = float(s)
    except ValueError:
        return s
    if p < 0.001:
        return "<0.001"
    return f"{p:.3f}"


class Results:
    def __init__(
        self,
        snapshot: Path | str = "results/_latest",
        *,
        figure_spec: Path | str = _DEFAULT_FIGURE_SPEC,
        print_root: Path | str | None = None,
    ) -> None:
        self.root = Path(snapshot)
        self._figure_spec = Path(figure_spec)
        self._print_root_override = None if print_root is None else Path(print_root)

    # ── ingestion: cohort + Table 1 ─────────────────────────────────────
    @cached_property
    def _table1_meta(self) -> pd.DataFrame:
        df = _read_table(self.root / "ingestion" / "table1_metadata.csv")
        return df.set_index("Variable")

    @cached_property
    def _table1_shape(self) -> pd.DataFrame:
        df = _read_table(self.root / "ingestion" / "table1_shape.csv")
        return df.set_index("Variable")

    @cached_property
    def _analytic(self) -> pd.DataFrame:
        return pd.read_parquet(self.root / "ingestion" / "analytic_clean.parquet")

    @cached_property
    def _join_stats(self) -> dict:
        return json.loads((self.root / "ingestion" / "join_stats.json").read_text())

    def _table1_cell(self, variable: str, col: str = "Overall") -> str:
        return str(self._table1_meta.loc[variable, col])

    def _cohort_n_int(self) -> int:
        return int(self._table1_cell("N"))

    def cohort_n(self) -> str:
        return _format_count(self._cohort_n_int())

    def n_male(self) -> int:
        return int(self._table1_meta.loc["N", "Male"])

    def n_female(self) -> int:
        return int(self._table1_meta.loc["N", "Female"])

    def cohort_sex_breakdown(self) -> str:
        return f"{_format_count(self.n_male())} male, {_format_count(self.n_female())} female"

    def age_mean_sd(self) -> str:
        return self._table1_cell("age")

    def bmi_mean_sd(self) -> str:
        return self._table1_cell("bmi")

    def body_fat_summary(self) -> str:
        return self._table1_cell("body_fat_pct")

    def pack_years_mean_sd(self) -> str:
        return self._table1_cell("pack_years")

    def smoking_breakdown(self) -> str:
        return self._table1_cell("smoking_status")

    def age_range(self) -> str:
        pl = self._analytic.drop_duplicates("patient_id")
        lo, hi = pl["age"].min(), pl["age"].max()
        return f"{lo:.0f}–{hi:.0f}"

    def n_join_source(self) -> int:
        return int(self._join_stats["n_metadata_patients"])

    def _n_join_inner_int(self) -> int:
        return int(self._join_stats["n_inner_join_patients"])

    def n_join_inner(self) -> str:
        return _format_count(self._n_join_inner_int())

    def n_join_analytics(self) -> int:
        return int(self._join_stats["n_analytics_patients"])

    # ── ingestion: exclusions + rib yield ───────────────────────────────
    @cached_property
    def _exclusions(self) -> pd.DataFrame:
        return pd.read_csv(self.root / "ingestion" / "exclusions.csv")

    def n_excluded(self) -> int:
        return int(self._exclusions["excluded"].sum())

    def n_excluded_rib_count(self) -> int:
        return int(self._exclusions["reason_rib_count"].notna().sum())

    def n_excluded_missing_metadata(self) -> int:
        return int(self._exclusions["reason_missing_metadata"].notna().sum())

    def n_excluded_seg_border(self) -> int:
        return int(self._exclusions["reason_seg_at_border"].notna().sum())

    def n_excluded_split(self) -> int:
        return int(self._exclusions["reason_split"].notna().sum())

    @cached_property
    def _ssm_pids(self) -> set[int]:
        pcs = pd.read_csv(self.root / "ssm_pca" / "pc_scores_surface.csv")
        return set(pcs["patient_id"].astype(int).unique())

    def n_excluded_too_few_ribs(self) -> int:
        ex = self._exclusions
        passed_qc = ex.loc[~ex["excluded"]]
        return int(((passed_qc["n_rib_sides"] < 24) & (~passed_qc["patient_id"].isin(self._ssm_pids))).sum())

    def n_excluded_registration(self) -> int:
        ex = self._exclusions
        passed_qc = ex.loc[~ex["excluded"]]
        return int(((passed_qc["n_rib_sides"] >= 24) & (~passed_qc["patient_id"].isin(self._ssm_pids))).sum())

    def n_excluded_total(self) -> int:
        return self.n_excluded() + self.n_excluded_too_few_ribs() + self.n_excluded_registration()

    def exclusions_summary_df(self) -> pd.DataFrame:
        denom = self._n_join_inner_int()

        def pct(n: int) -> str:
            if n == 0:
                return "0.0%"
            p = 100 * n / denom
            return "<0.1%" if p < 0.1 else f"{p:.1f}%"

        rows = [
            ("Joined cohort",                                        denom),
            ("Excluded – rib-side count outside 24",                 self.n_excluded_rib_count()),
            ("Excluded – missing baseline metadata",                 self.n_excluded_missing_metadata()),
            ("Excluded – segmentation touching FOV boundary",        self.n_excluded_seg_border()),
            ("Excluded – bifurcated proximal/distal rib end",        self.n_excluded_split()),
            ("Post-ingestion cohort",                                self._cohort_n_int()),
            ("Excluded – incomplete or failed surface registration", self.n_excluded_registration()),
            ("Analytic cohort",                                      self._n_ssm_patients_int()),
        ]
        return pd.DataFrame(
            [(label, n, pct(n)) for label, n in rows],
            columns=["Step", "n", "%"],
        )

    def exclusions_summary_md(self) -> str:
        return self.exclusions_summary_df().to_markdown(index=False, intfmt=",")

    def _n_rib_complete_int(self) -> int:
        return int((self._exclusions["n_rib_sides"] == 24).sum())

    def n_rib_complete(self) -> str:
        return _format_count(self._n_rib_complete_int())

    def pct_rib_complete(self) -> str:
        return f"{100 * self._n_rib_complete_int() / self._n_join_inner_int():.1f}%"

    def rib_count_distribution_df(self) -> pd.DataFrame:
        vc = self._exclusions["n_rib_sides"].value_counts().sort_index()
        n_total = int(vc.sum())
        return pd.DataFrame(
            {
                "Rib sides per participant": [int(k) for k in vc.index],
                "n participants":        [int(v) for v in vc.values],
                "%":                     [f"{100 * v / n_total:.1f}%" for v in vc.values],
            }
        )

    def rib_count_distribution_md(self) -> str:
        return self.rib_count_distribution_df().to_markdown(index=False, intfmt=",")

    # ── ssm / pca ───────────────────────────────────────────────────────
    @cached_property
    def _pca(self) -> dict[str, np.ndarray]:
        with np.load(self.root / "ssm_pca" / "pca_surface.npz") as z:
            return {k: z[k].copy() for k in z.files}

    @cached_property
    def _pc_lm(self) -> pd.DataFrame:
        return pd.read_csv(self.root / "ssm_pca" / "pc_adjusted.csv")

    @cached_property
    def _pc_unadjusted(self) -> pd.DataFrame:
        return pd.read_csv(self.root / "ssm_pca" / "pc_unadjusted.csv")

    @cached_property
    def _pc_ttest(self) -> pd.DataFrame:
        return pd.read_csv(self.root / "ssm_pca" / "pc_ttest_surface.csv")

    @cached_property
    def _geometry_holdout(self) -> pd.DataFrame:
        return pd.read_csv(self.root / "ssm_pca" / "geometry_generator_holdout.csv")

    def geometry_holdout_mm(self, stat: str = "mean", n_modes: int | None = None) -> str:
        """Held-out demographics→geometry per-vertex error (mm); stat in {mean, p95}."""
        df = self._geometry_holdout
        k = int(df["n_modes"].max()) if n_modes is None else n_modes
        row = df[df["n_modes"] == k].iloc[0]
        return f"{float(row['mean_mm' if stat == 'mean' else 'p95_mm']):.2f}"

    def variance_threshold(self) -> float:
        return float(self._pca["variance_threshold"])

    def variance_threshold_pct(self) -> str:
        return f"{self.variance_threshold() * 100:.0f}%"

    def pc_count(self) -> int:
        return int(len(self._pca["explained_variance_ratio"]))

    def pc_variance_ratio(self, k: int) -> float:
        return float(self._pca["explained_variance_ratio"][k - 1])

    def pc_cumulative_variance(self, k: int) -> float:
        return float(np.cumsum(self._pca["explained_variance_ratio"])[k - 1])

    def pc_variance_pct(self, k: int) -> str:
        return f"{self.pc_variance_ratio(k) * 100:.1f}%"

    def pc_cumulative_variance_pct(self, k: int) -> str:
        return f"{self.pc_cumulative_variance(k) * 100:.1f}%"

    def _n_ssm_patients_int(self) -> int:
        return len(self._ssm_pids)

    def n_ssm_patients(self) -> str:
        return _format_count(self._n_ssm_patients_int())

    def top_metadata_for_pc(self, pc: int = 1, k: int = 3, alpha: float = 0.05) -> pd.DataFrame:
        df = self._pc_lm[self._pc_lm["pc"] == f"PC_{pc}"].copy()
        df = df[df["p_value_fdr"] < alpha].copy()
        df["abs_b"] = df["beta_std"].abs()
        return df.nlargest(k, "abs_b")[["predictor", "beta_std"]].reset_index(drop=True)

    def top_metadata_phrase_for_pc(self, pc: int = 1, k: int = 3) -> str:
        df = self.top_metadata_for_pc(pc, k=k)
        parts: list[str] = []
        for _, row in df.iterrows():
            label = PREDICTOR_LABELS.get(row["predictor"], row["predictor"])
            beta = float(row["beta_std"])
            sign = "−" if beta < 0 else ""
            parts.append(f"{label} (β = {sign}{abs(beta):.2f})")
        return ", ".join(parts)

    def pc_model_r2(self, pc: int) -> str:
        row = self._pc_lm[self._pc_lm["pc"] == f"PC_{pc}"].iloc[0]
        return f"{float(row['r_squared']):.2f}"

    def demographics_variance_explained(self) -> float:
        """Fraction of total shape variance the demographics generator explains (Σ evr_k · R²_k)."""
        with np.load(self.root / "ssm_pca" / "geometry_generator.npz") as g:
            r2 = g["r2"].copy()
        evr = self._pca["explained_variance_ratio"]
        return float((evr * r2[: len(evr)]).sum())

    def demographics_variance_explained_pct(self) -> str:
        return f"{self.demographics_variance_explained() * 100:.0f}%"

    @cached_property
    def _pc_targeted(self) -> pd.DataFrame:
        return pd.read_csv(self.root / "ssm_pca" / "pc_targeted.csv")

    def pc_beta_std(self, pc: int, predictor: str, layer: str = "targeted") -> float:
        df = {"unadjusted": self._pc_unadjusted, "adjusted": self._pc_lm, "targeted": self._pc_targeted}[layer]
        s = df[(df["pc"] == f"PC_{pc}") & (df["predictor"] == predictor)]
        return float(s["beta_std"].iloc[0]) if len(s) else float("nan")

    def pc_estimand_table_df(self, pc: int = 1) -> pd.DataFrame:
        """Per-predictor standardised β under all three estimands for one PC; targeted (DAG) column bold."""
        order = ["is_female", "age", "height_cm", "weight_kg", "body_fat_pct", "ever_smoker", "pack_years"]
        est_label = {"total_effect": "Total effect", "adjusted_association": "Adjusted assoc."}
        rows = []
        for p in order:
            t = self._pc_targeted[(self._pc_targeted["pc"] == f"PC_{pc}") & (self._pc_targeted["predictor"] == p)]
            est = est_label.get(t["estimand"].iloc[0], "") if len(t) else ""
            rows.append((
                PREDICTOR_LABELS.get(p, p),
                f"{self.pc_beta_std(pc, p, 'unadjusted'):+.2f}",
                f"{self.pc_beta_std(pc, p, 'adjusted'):+.2f}",
                f"**{self.pc_beta_std(pc, p, 'targeted'):+.2f}**",
                est,
            ))
        return pd.DataFrame(rows, columns=["Predictor", "Unadjusted β", "Adjusted β", "Targeted β (DAG)", "Estimand"])

    def pc_estimand_table_md(self, pc: int = 1) -> str:
        return self.pc_estimand_table_df(pc).to_markdown(index=False, disable_numparse=True)

    # ── ssm qa: Styner metrics ──────────────────────────────────────────
    @cached_property
    def _styner(self) -> dict:
        return json.loads((self.root / "ssm_qa_metrics" / "eval_styner.json").read_text())

    def styner_generalisation_mm(self, n_modes: int | None = None, rib: str = "whole_cage") -> float:
        if n_modes is None:
            n_modes = self.pc_count()
        entry = self._styner[rib] if rib == "whole_cage" else self._styner["per_rib"][rib]
        modes = entry["mode_counts"]
        idx = modes.index(n_modes) if n_modes in modes else len(modes) - 1
        return float(entry["generalisation_mm"][idx])

    def styner_specificity_mm(self, n_modes: int | None = None, rib: str = "whole_cage") -> float:
        if n_modes is None:
            n_modes = self.pc_count()
        entry = self._styner[rib] if rib == "whole_cage" else self._styner["per_rib"][rib]
        modes = entry["mode_counts"]
        idx = modes.index(n_modes) if n_modes in modes else len(modes) - 1
        return float(entry["specificity_mm"][idx])

    def styner_compactness(self, n_modes: int | None = None, rib: str = "whole_cage") -> float:
        if n_modes is None:
            n_modes = self.pc_count()
        entry = self._styner[rib] if rib == "whole_cage" else self._styner["per_rib"][rib]
        modes = entry["mode_counts"]
        idx = modes.index(n_modes) if n_modes in modes else len(modes) - 1
        return float(entry["compactness"][idx])

    def count_fdr_significant(self, df: pd.DataFrame, p_col: str = "p_value_fdr", alpha: float = 0.05) -> int:
        return int((df[p_col] < alpha).sum())

    def n_sig_pc_lm(self, alpha: float = 0.05) -> int:
        return self.count_fdr_significant(self._pc_lm, alpha=alpha)

    def n_sig_pc_ttest(self, alpha: float = 0.05) -> int:
        return self.count_fdr_significant(self._pc_ttest, alpha=alpha)

    def n_sig_pc_anova(self, alpha: float = 0.05) -> int:
        # Ever-smoker FDR-significant PC modes under the adjusted (mutually-adjusted) model.
        df = self._pc_lm[self._pc_lm["predictor"] == "ever_smoker"]
        return int((df["p_value_fdr"] < alpha).sum())

    def n_sig_pc_smoking_targeted(self, alpha: float = 0.05) -> int:
        # Ever-smoker FDR-significant PC modes under the targeted (primary) specification.
        df = self._pc_targeted[self._pc_targeted["predictor"] == "ever_smoker"]
        return int((df["p_value_fdr"] < alpha).sum())

    def n_pc_lm_total(self) -> int:
        return int(len(self._pc_lm))

    # ── adjusted ────────────────────────────────────────────────────────
    @cached_property
    def _descriptor_adjusted(self) -> pd.DataFrame:
        return pd.read_csv(self.root / "adjusted" / "descriptor_adjusted.csv")

    @cached_property
    def _descriptor_unadjusted(self) -> pd.DataFrame:
        return pd.read_csv(self.root / "adjusted" / "descriptor_unadjusted.csv")

    @cached_property
    def _descriptor_targeted(self) -> pd.DataFrame:
        return pd.read_csv(self.root / "adjusted" / "descriptor_targeted.csv")

    def n_sig_targeted(self, alpha: float = 0.05) -> int:
        return self.count_fdr_significant(self._descriptor_targeted, alpha=alpha)

    def n_targeted_total(self) -> int:
        return int(len(self._descriptor_targeted))

    def max_partial_r2_targeted(self) -> str:
        return f"{float(self._descriptor_targeted['partial_r2'].max()):.3f}"

    def top_targeted_phrase_str(self, k: int = 3, by: str = "partial_r2") -> str:
        df = self._descriptor_targeted.copy()
        df["abs_beta_std"] = df["beta_std"].abs()
        sort_col = "abs_beta_std" if by == "beta_std" else by
        parts: list[str] = []
        for _, row in df.nlargest(k, sort_col).iterrows():
            feat = SHAPE_FEATURE_LABELS.get(row["shape_param"], row["shape_param"])
            pred = PREDICTOR_LABELS.get(row["predictor"], row["predictor"])
            beta = float(row["beta_std"])
            sign = "−" if beta < 0 else "+"
            parts.append(f"{feat.lower()} × {pred} (partial R² = {float(row['partial_r2']):.3f}, β = {sign}{abs(beta):.2f})")
        return "; ".join(parts)

    def adjusted_model(self) -> pd.DataFrame:
        return self._descriptor_adjusted

    def n_sig_adjusted(self, alpha: float = 0.05) -> int:
        return self.count_fdr_significant(self._descriptor_adjusted, alpha=alpha)

    def top_adjusted(self, k: int = 5, by: str = "partial_r2") -> pd.DataFrame:
        df = self._descriptor_adjusted.copy()
        df["abs_beta_std"] = df["beta_std"].abs()
        sort_col = "abs_beta_std" if by == "beta_std" else by
        cols = ["shape_param", "predictor", "beta_std", "p_value_fdr", "partial_r2"]
        return df.nlargest(k, sort_col)[cols].reset_index(drop=True)

    def top_adjusted_phrases(self, alpha: float = 0.05, k: int = 3) -> list[tuple]:
        df = self._descriptor_adjusted
        sig = df[df["p_value_fdr"] < alpha].copy()
        if sig.empty:
            return []
        sig["abs_beta_std"] = sig["beta_std"].abs()
        sig = sig.nlargest(k, "abs_beta_std")
        out: list[tuple] = []
        for _, row in sig.iterrows():
            feat = SHAPE_FEATURE_LABELS.get(row["shape_param"], row["shape_param"])
            pred = PREDICTOR_LABELS.get(row["predictor"], row["predictor"])
            out.append((feat, pred, float(row["beta_std"]), float(row["partial_r2"])))
        return out

    def top_adjusted_phrase_str(self, k: int = 3, by: str = "partial_r2") -> str:
        if by == "partial_r2":
            rows = self.top_adjusted(k=k, by="partial_r2")
            parts: list[str] = []
            for _, row in rows.iterrows():
                feat = SHAPE_FEATURE_LABELS.get(row["shape_param"], row["shape_param"])
                pred = PREDICTOR_LABELS.get(row["predictor"], row["predictor"])
                beta = float(row["beta_std"])
                pr2 = float(row["partial_r2"])
                sign = "−" if beta < 0 else "+"
                parts.append(f"{feat.lower()} × {pred} (partial R² = {pr2:.3f}, β = {sign}{abs(beta):.2f})")
            return "; ".join(parts)
        items = self.top_adjusted_phrases(k=k)
        parts = []
        for feat, pred, beta, pr2 in items:
            sign = "−" if beta < 0 else "+"
            parts.append(f"{feat.lower()} × {pred} (partial R² = {pr2:.3f}, β = {sign}{abs(beta):.2f})")
        return "; ".join(parts)

    def max_partial_r2(self) -> str:
        return f"{float(self._descriptor_adjusted['partial_r2'].max()):.3f}"

    # ── PC ↔ metadata ───────────────────────────────────────────────────
    def pc_sex_effect(self, pc: int = 1) -> dict[str, float]:
        row = self._pc_ttest[self._pc_ttest["pc"] == f"PC_{pc}"].iloc[0]
        return {
            "cohen_d": float(row["cohen_d"]),
            "p_value_fdr": float(row["p_value_fdr"]),
            "mean_male": float(row["mean_male"]),
            "mean_female": float(row["mean_female"]),
        }

    def pc_sex_d(self, pc: int = 1) -> str:
        return f"{self.pc_sex_effect(pc=pc)['cohen_d']:.2f}"

    def pc_sex_p_fdr(self, pc: int = 1) -> str:
        return f"{self.pc_sex_effect(pc=pc)['p_value_fdr']:.1e}"

    # ── radiomics ↔ PC ──────────────────────────────────────────────────
    @cached_property
    def _radiomics_top(self) -> pd.DataFrame:
        return pd.read_csv(self.root / "radiomics_correlation" / "effects_top_by_abs_std.csv")

    def top_radiomics_for_pc(self, pc: int = 1, k: int = 5) -> pd.DataFrame:
        df = self._radiomics_top[self._radiomics_top["pc"] == f"PC_{pc}"].copy()
        df["abs_beta_std"] = df["beta_std"].abs()
        return df.nlargest(k, "abs_beta_std")[
            ["pc", "anatomical_rib", "side", "feature", "beta_std", "q_value"]
        ].reset_index(drop=True)

    def _pack_years_ever_row(self) -> dict[str, str]:
        pl = self._analytic.drop_duplicates("patient_id")
        sub = pl.loc[pl["smoking_status"].isin(["Ex-smoker", "Current"])]

        def _fmt(s: pd.Series) -> str:
            s = s.dropna()
            q25, q50, q75 = s.quantile([0.25, 0.50, 0.75])
            return f"{q50:.2f} [{q25:.2f}–{q75:.2f}]"

        a = sub.loc[sub["sex"] == "Male",   "pack_years"].dropna()
        b = sub.loc[sub["sex"] == "Female", "pack_years"].dropna()
        if len(a) > 1 and len(b) > 1 and a.var() > 0 and b.var() > 0:
            _, p = stats.ttest_ind(a, b, equal_var=False)
            p_str = "<0.001" if p < 0.001 else f"{p:.3f}"
        else:
            p_str = "–"

        return {
            "Variable": "pack_years_ever",
            "Overall":  _fmt(sub["pack_years"]),
            "Male":     _fmt(a),
            "Female":   _fmt(b),
            "p-value":  p_str,
            "Note":     "median [IQR], ever-smokers",
        }

    # ── tables for embedding (DataFrame; Quarto picks the format) ──────
    def table1_metadata_df(self) -> pd.DataFrame:
        df = _read_table(self.root / "ingestion" / "table1_metadata.csv").fillna("")

        df = df[~df["Variable"].isin(["sex", "pack_years"])].reset_index(drop=True)
        df = pd.concat(
            [df, pd.DataFrame([self._pack_years_ever_row()], columns=df.columns)],
            ignore_index=True,
        )

        n_row = df.index[df["Variable"] == "N"][0]
        overall_n = int(df.loc[n_row, "Overall"])
        df.loc[n_row, "Overall"] = _format_count(overall_n)
        for col in ("Male", "Female"):
            n = int(df.loc[n_row, col])
            df.loc[n_row, col] = f"{_format_count(n)} ({100 * n / overall_n:.1f}%)"

        # Cell-internal line breaks render across pipe-separated category labels;
        # category counts (e.g. smoking status) carry thousands separators.
        for col in ("Overall", "Male", "Female"):
            df[col] = df[col].str.replace(" | ", "<br>", regex=False)
            df[col] = df[col].map(_format_embedded_counts)

        df["p-value"] = df["p-value"].map(_format_pvalue)
        df = df.set_index("Variable").reindex(TABLE1_METADATA_ORDER).reset_index()
        df["Variable"] = df["Variable"].map(lambda v: TABLE1_METADATA_LABELS.get(v, v))
        return df

    def table1_shape_df(self) -> pd.DataFrame:
        df = _read_table(self.root / "ingestion" / "table1_shape.csv").fillna("")
        df["Variable"] = df["Variable"].map(lambda v: SHAPE_FEATURE_LABELS.get(v, v))
        return df

    def table1_metadata_md(self) -> str:
        return self.table1_metadata_df().to_markdown(index=False)

    def table1_shape_md(self) -> str:
        return self.table1_shape_df().to_markdown(index=False)

    # ── provenance ─────────────────────────────────────────────────────
    @cached_property
    def metadata(self) -> dict:
        return json.loads((self.root / "metadata.json").read_text())

    def run_name(self) -> str:
        return self.metadata.get("name", "unknown")

    def run_timestamp(self) -> str:
        return self.metadata.get("timestamp_utc", "unknown")

    def git_sha_short(self) -> str:
        return self.metadata.get("git_rev", "")[:7]

    # ── figure embedding (figure_paths.yml) ─────────────────────────────
    @cached_property
    def _figspec(self) -> dict:
        return yaml.safe_load(self._figure_spec.read_text(encoding="utf-8")) or {}

    @property
    def _fig_defaults(self) -> dict:
        return self._figspec.get("defaults", {})

    @property
    def _figures(self) -> dict:
        return self._figspec.get("figures", {})

    def _entry(self, fig_id: str) -> dict:
        try:
            return self._figures[fig_id]
        except KeyError as exc:
            raise FigureError(f"unknown figure id {fig_id!r}") from exc

    @property
    def _results_root(self) -> str:
        return self._fig_defaults.get("results_root", "results/_latest")

    @property
    def _print_root(self) -> str:
        if self._print_root_override is not None:
            return str(self._print_root_override)
        return self._fig_defaults.get("print_root", "_print")

    @staticmethod
    def _sanitize_id(raw: str) -> str:
        return re.sub(r"[^0-9a-zA-Z]+", "-", raw).strip("-").lower()

    @staticmethod
    def _img(path: str, *, alt: str = "", caption: str = "", sub_id: str = "") -> str:
        attrs = []
        if sub_id:
            attrs.append(f"#{sub_id}")
        attrs.append('fig-align="center"')
        if alt:
            attrs.append(f'fig-alt="{alt}"')
        return f"![{caption}]({path})" + "{" + " ".join(attrs) + "}"

    def _iframe(self, src: str, alt: str, height: str | None = None) -> str:
        height = height or self._fig_defaults.get("iframe_height", "640px")
        title = (alt or "").replace('"', "&quot;")
        return (
            f'<iframe src="{src}" title="{title}" width="100%" height="{height}" '
            f'loading="lazy" style="border:1px solid #ccc;border-radius:4px;"></iframe>'
        )

    def _composite_iframes(self, entry: dict, root: str) -> str:
        """HTML build: each composite panel as an interactive iframe sub-float.

        Each panel keeps its ``#sub_id`` and ``label``, so it still arranges under
        the parent float's ``layout-ncol`` and any subpanel cross-reference (e.g.
        ``@fig-pc-anatomy-pc1``) keeps resolving – the only change from
        :meth:`_composite_panels` is the static PNG becoming the interactive .html
        twin. Used instead of the PNG panels whenever the composite has html twins.
        """
        height = entry.get("iframe_height")
        blocks = []
        for p in entry["panels"]:
            frame = self._iframe(f"{root}/{p['stem']}.html", p.get("alt", ""), height)
            blocks.append(f"::: {{#{p['sub_id']}}}\n{frame}\n\n{p.get('label', '')}\n:::")
        return "\n\n".join(blocks)

    def _composite_panels(self, entry: dict, root: str) -> str:
        return "\n\n".join(
            self._img(
                f"{root}/{p['stem']}.png",
                caption=p.get("label", ""),
                sub_id=p["sub_id"],
                alt=p.get("alt", ""),
            )
            for p in entry["panels"]
        )

    def _family_items(self, entry: dict, which: str) -> list[tuple[str, str, str]]:
        """Return (filename_stem, panel_label, id_key) per item; which in {'print', 'all'}."""
        if "item_pattern" in entry:
            pattern = entry["item_pattern"]
            label_tmpl = entry.get("item_label", "{n}")
            nums = entry["print_items"] if which == "print" else range(1, int(entry["item_count"]) + 1)
            return [(pattern.format(i), label_tmpl.format(n=i), f"pc{i}") for i in nums]
        names = list(entry["items"])
        if which == "print" and entry["print_items"] != "all":
            names = list(entry["print_items"])
        return [(n, n.replace("_native", ""), self._sanitize_id(n.replace("_native", ""))) for n in names]

    def fig_html(self, fig_id: str) -> str:
        """Interactive-build markup: iframe to the .html twin / meta-wrapper, else a static image."""
        entry = self._entry(fig_id)
        kind = entry["kind"]
        root = self._results_root
        alt = entry.get("alt", "")
        if kind == "static":
            return self._img(f"{root}/{entry['stem']}.png", alt=alt)
        if kind == "single":
            if "html" in entry.get("has", []):
                return self._iframe(f"{root}/{entry['stem']}.html", alt)
            ext = "png" if "png" in entry.get("has", []) else entry["has"][0]
            return self._img(f"{root}/{entry['stem']}.{ext}", alt=alt)
        if kind == "composite":
            # Multi-panel composites with html twins render as a grid of interactive
            # iframe sub-floats; those without twins stay static PNG panels.
            if "html" in entry.get("has", []):
                return self._composite_iframes(entry, root)
            return self._composite_panels(entry, root)
        if kind in ("family", "html_only"):
            src = f"{root}/{entry['dir']}/{entry['index']}" if kind == "family" else f"{root}/{entry['stem']}.html"
            return self._iframe(src, alt)
        raise FigureError(f"figure {fig_id!r} has unknown kind {kind!r}")

    def fig_print(self, fig_id: str) -> str:
        """Print-build markup: A4-capped PNG(s) under the print tree; '' for interactive-only figures."""
        entry = self._entry(fig_id)
        kind = entry["kind"]
        root = self._print_root
        alt = entry.get("alt", "")
        if kind in ("static", "single"):
            return self._img(f"{root}/{entry['stem']}.png", alt=alt)
        if kind == "composite":
            return self._composite_panels(entry, root)
        if kind == "family":
            prefix = entry["sub_id_prefix"]
            return "\n\n".join(
                self._img(
                    f"{root}/{entry['dir']}/{name}.png",
                    caption=label,
                    sub_id=self._sanitize_id(f"{prefix}-{key}"),
                    alt=alt,
                )
                for name, label, key in self._family_items(entry, "print")
            )
        if kind == "html_only":
            return ""
        raise FigureError(f"figure {fig_id!r} has unknown kind {kind!r}")
