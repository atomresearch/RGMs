"""
OPTIM2FULL L4 — Python-native final-frame plot hooks for ``DEM_drone_VI``.

Calls existing library ``dem_drone_vi_plot_*`` modules on **live** native tensors.
No Model-B ledger, no F*.mat plot authority, no MATLAB plot-oracle asserts.

Env: ``RGMS_OPTIM2FULL_NATIVE_PLOT=1`` (distinct from parity Ord visual runners).
PNGs → ``visualizations/optim2full_native/`` (gitignored under ``visualizations/``).

See ``OPTIM2FULL.md`` § COLAB2 / Local-native build order **L4**.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import numpy as np

_NATIVE_PLOT_ENV = "RGMS_OPTIM2FULL_NATIVE_PLOT"

# Script / COLAB2 plot order (Ord map: 4→6→5→3→2→1).
NATIVE_PLOT_SITE_ORDER: tuple[str, ...] = (
    "true_env_early",
    "true_scene_post_generate",
    "mdp_params",
    "rgm",
    "active_inference",
    "wayfinding",
)


def optim2full_native_plot_requested() -> bool:
    return os.getenv(_NATIVE_PLOT_ENV, "").strip().lower() in ("1", "true", "yes")


def native_plot_png_dir(repo_root: Path | None = None) -> Path:
    root = repo_root or Path(__file__).resolve().parents[3]
    out = root / "visualizations" / "optim2full_native"
    out.mkdir(parents=True, exist_ok=True)
    return out


def _png_path(out_dir: Path, site_id: str) -> Path:
    return out_dir / f"DEM_drone_VI_native_{site_id}.png"


def mdp_fsl_end(MDP_fsl: Any) -> dict[str, Any]:
    """MATLAB ``MDP{end}`` after FSL."""
    if isinstance(MDP_fsl, list):
        if not MDP_fsl:
            raise ValueError("MDP_fsl is empty")
        end = MDP_fsl[-1]
    else:
        arr = np.asarray(MDP_fsl, dtype=object).ravel(order="F")
        if arr.size == 0:
            raise ValueError("MDP_fsl is empty")
        end = arr[-1]
    if not isinstance(end, dict):
        raise TypeError(f"MDP{{end}} expected dict, got {type(end)}")
    return end


def write_native_plot_site(
    site_id: str,
    payload: dict[str, Any],
    *,
    out_dir: Path,
) -> Path:
    """Run one native plot site; save PNG under ``out_dir``."""
    import matplotlib

    matplotlib.use("Agg")

    png = _png_path(out_dir, site_id)
    print(
        f"[OPTIM2FULL native plot] {site_id} → {png.name}",
        file=sys.stderr,
        flush=True,
    )

    if site_id == "true_env_early":
        from python_src.toolbox.DEM.dem_drone_vi_plot_true_env_early import (
            dem_drone_vi_plot_true_env_early,
        )

        dem_drone_vi_plot_true_env_early(
            payload["MAP"],
            payload["W"],
            Nx=int(payload["Nx"]),
            Ny=int(payload["Ny"]),
            Nz=int(payload["Nz"]),
            Nc=int(payload["Nc"]),
            save_png=True,
            png_path=png,
            fig_title="Active inference",
        )
    elif site_id == "true_scene_post_generate":
        from python_src.toolbox.DEM.dem_drone_vi_plot_true_scene_post_generate import (
            dem_drone_vi_plot_true_scene_post_generate,
        )

        dem_drone_vi_plot_true_scene_post_generate(
            payload["Q"],
            payload["PG"],
            save_png=True,
            png_path=png,
            fig_title="True scene",
        )
    elif site_id == "mdp_params":
        from python_src.toolbox.DEM.dem_drone_vi_plot_mdp_params import (
            dem_drone_vi_plot_mdp_params,
        )

        dem_drone_vi_plot_mdp_params(
            payload["MDP_end"],
            OPT="norm",
            save_png=True,
            png_path=png,
            fig_title="Paramters: level 2",
        )
    elif site_id == "rgm":
        from python_src.toolbox.DEM.dem_drone_vi_plot_rgm import dem_drone_vi_plot_rgm

        dem_drone_vi_plot_rgm(
            payload["RDP"],
            save_png=True,
            png_path=png,
            fig_title="RGM",
        )
    elif site_id == "active_inference":
        from python_src.toolbox.DEM.dem_drone_vi_plot_active_inference import (
            dem_drone_vi_plot_active_inference,
        )

        dem_drone_vi_plot_active_inference(
            payload["QDP"],
            payload["PG"],
            save_png=True,
            png_path=png,
            fig_title="Active inference",
        )
    elif site_id == "wayfinding":
        from python_src.toolbox.DEM.dem_drone_vi_plot_wayfinding import (
            dem_drone_vi_plot_wayfinding,
        )

        dem_drone_vi_plot_wayfinding(
            payload["QDP"],
            payload["PG"],
            payload.get("sT"),
            save_png=True,
            png_path=png,
            fig_title="Wayfinding",
        )
    else:
        raise ValueError(f"unknown native plot site_id={site_id!r}")

    if not png.is_file():
        raise RuntimeError(f"native plot did not write PNG: {png}")
    return png


def run_all_native_plots_from_blob(
    blob: dict[str, Any],
    *,
    out_dir: Path | None = None,
) -> dict[str, Any]:
    """Write all six native PNGs from a ``run_dem_drone_vi_native`` result blob."""
    out = out_dir or native_plot_png_dir()
    required = (
        "MAP",
        "W",
        "Nx",
        "Ny",
        "Nz",
        "Nc",
        "Q",
        "PG",
        "MDP_fsl",
        "RDP_surveillance",
        "QDP_surveillance",
        "QDP_wayfinding",
        "sT",
    )
    missing = [k for k in required if k not in blob]
    if missing:
        raise KeyError(f"native plot blob missing keys: {missing}")

    written: list[str] = []
    payloads: dict[str, dict[str, Any]] = {
        "true_env_early": {
            "MAP": blob["MAP"],
            "W": blob["W"],
            "Nx": blob["Nx"],
            "Ny": blob["Ny"],
            "Nz": blob["Nz"],
            "Nc": blob["Nc"],
        },
        "true_scene_post_generate": {"Q": blob["Q"], "PG": blob["PG"]},
        "mdp_params": {"MDP_end": mdp_fsl_end(blob["MDP_fsl"])},
        "rgm": {"RDP": blob["RDP_surveillance"]},
        "active_inference": {
            "QDP": blob["QDP_surveillance"],
            "PG": blob["PG"],
        },
        "wayfinding": {
            "QDP": blob["QDP_wayfinding"],
            "PG": blob["PG"],
            "sT": blob["sT"],
        },
    }
    for site_id in NATIVE_PLOT_SITE_ORDER:
        p = write_native_plot_site(site_id, payloads[site_id], out_dir=out)
        written.append(str(p))

    meta = {
        "out_dir": str(out),
        "pngs": written,
        "png_count": len(written),
        "sites": list(NATIVE_PLOT_SITE_ORDER),
    }
    return meta


class NativePlotSession:
    """Mid-spine plot writer (COLAB2 cell order) during ``run_dem_drone_vi_native``."""

    def __init__(self, out_dir: Path | None = None) -> None:
        self.out_dir = out_dir or native_plot_png_dir()
        self.pngs: list[str] = []

    def write(self, site_id: str, payload: dict[str, Any]) -> Path:
        p = write_native_plot_site(site_id, payload, out_dir=self.out_dir)
        self.pngs.append(str(p))
        return p

    def meta(self) -> dict[str, Any]:
        return {
            "out_dir": str(self.out_dir),
            "pngs": list(self.pngs),
            "png_count": len(self.pngs),
            "sites": list(NATIVE_PLOT_SITE_ORDER),
        }
