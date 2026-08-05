"""OPTIM2FULL fixture and artifact path resolution (lane-isolated).

Authority root defaults to ``tests/dem_drone_vi/fixtures``. Override with
``RGMS_OPTIM2FULL_FIXTURES_DIR``. Do not point this at OPTIM1FULL / Atari fixtures.
"""

from __future__ import annotations

import os
from pathlib import Path

from tests.demo1.demo1_paths import demo1_repo_root


CAPTURE_OPTIM2FULL_F0 = "capture_optim2full_f0"
CAPTURE_OPTIM2FULL_RAND_LEDGER = "capture_optim2full_rand_ledger"
LEDGER_PROTOCOL = "optim2full_scalar_rand_log_v1"
REQUIRED_LEDGER_SEGMENTS = ("f0_scene", "pre_fsl", "fsl", "vb_1", "vb_2")



def optim2full_repo_root() -> Path:
    return demo1_repo_root()


def optim2full_shipped_fixtures_dir() -> Path:
    return optim2full_repo_root() / "tests" / "dem_drone_vi" / "fixtures"


def optim2full_fixtures_dir() -> Path:
    raw = str(os.getenv("RGMS_OPTIM2FULL_FIXTURES_DIR", "")).strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return optim2full_shipped_fixtures_dir()


def optim2full_matlab_custom_dir() -> Path:
    return optim2full_repo_root() / "matlab_custom" / "optim2full"


def optim2full_fence_mat(fence: str) -> Path:
    """Fence authority mat, e.g. ``F0`` … ``F6``."""
    return optim2full_fixtures_dir() / f"DEM_drone_VI_optim2full_{fence}.mat"


def optim2full_f0_mat() -> Path:
    return optim2full_fence_mat("F0")


def optim2full_f0_pkl() -> Path:
    """Python-side F0 export (produced once a Python spine runner exists)."""
    return optim2full_fixtures_dir() / "DEM_drone_VI_optim2full_F0.pkl"


def optim2full_f1_mat() -> Path:
    return optim2full_fence_mat("F1")


def optim2full_f1_pkl() -> Path:
    """Python-side F1 export (GDP assemble + PDP inject + Q from PDP.s)."""
    return optim2full_fixtures_dir() / "DEM_drone_VI_optim2full_F1.pkl"


def dem_drone_vi_rand_ledger_mat() -> Path:
    raw = str(os.getenv("RGMS_OPTIM2FULL_RAND_LEDGER_MAT", "")).strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return optim2full_fixtures_dir() / "optim2full_dem_drone_rand_buf.mat"


def optim2full_rand_manifest_json() -> Path:
    raw = str(os.getenv("RGMS_OPTIM2FULL_RAND_MANIFEST_JSON", "")).strip()
    if raw:
        return Path(raw).expanduser().resolve()
    return optim2full_fixtures_dir() / "optim2full_rand_manifest.json"


def optim2full_compare_f0_report() -> Path:
    return optim2full_repo_root() / "matlab_custom" / "dem_drone_vi_compare_fence_f0_output.txt"


def optim2full_compare_f1_report() -> Path:
    return optim2full_repo_root() / "matlab_custom" / "dem_drone_vi_compare_fence_f1_output.txt"


def optim2full_f2_mat() -> Path:
    return optim2full_fence_mat("F2")


def optim2full_f2_pkl() -> Path:
    """Python-side F2 export (FSL MDP)."""
    return optim2full_fixtures_dir() / "DEM_drone_VI_optim2full_F2.pkl"


def optim2full_f2_rgm_G_mat() -> Path:
    """Dump-once MATLAB ``spm_rgm_group`` ``G`` sequence for F2 inject."""
    return optim2full_fixtures_dir() / "DEM_drone_VI_optim2full_F2_rgm_G.mat"


def optim2full_compare_f2_report() -> Path:
    return optim2full_repo_root() / "matlab_custom" / "dem_drone_vi_compare_fence_f2_output.txt"


def optim2full_f3_mat() -> Path:
    return optim2full_fence_mat("F3")


def optim2full_f3_pkl() -> Path:
    """Python-side F3 export (post ``spm_mdp_a2A``)."""
    return optim2full_fixtures_dir() / "DEM_drone_VI_optim2full_F3.pkl"


def optim2full_compare_f3_report() -> Path:
    return optim2full_repo_root() / "matlab_custom" / "dem_drone_vi_compare_fence_f3_output.txt"


def optim2full_f4_mat() -> Path:
    return optim2full_fence_mat("F4")


def optim2full_f4_pkl() -> Path:
    """Python-side F4 export (post packing + ``spm_mdp2rdp``)."""
    return optim2full_fixtures_dir() / "DEM_drone_VI_optim2full_F4.pkl"


def optim2full_compare_f4_report() -> Path:
    return optim2full_repo_root() / "matlab_custom" / "dem_drone_vi_compare_fence_f4_output.txt"


def optim2full_f5_mat() -> Path:
    return optim2full_fence_mat("F5")


def optim2full_f5_pkl() -> Path:
    """Python-side F5 export (first VB under ``vb_1`` + ``spm_Q2mdp``)."""
    return optim2full_fixtures_dir() / "DEM_drone_VI_optim2full_F5.pkl"


def optim2full_compare_f5_report() -> Path:
    return optim2full_repo_root() / "matlab_custom" / "dem_drone_vi_compare_fence_f5_output.txt"


def optim2full_f6_mat() -> Path:
    return optim2full_fence_mat("F6")


def optim2full_f6_pkl() -> Path:
    """Python-side F6 export (second VB under ``vb_2`` + ``spm_Q2mdp``)."""
    return optim2full_fixtures_dir() / "DEM_drone_VI_optim2full_F6.pkl"


def optim2full_compare_f6_report() -> Path:
    return optim2full_repo_root() / "matlab_custom" / "dem_drone_vi_compare_fence_f6_output.txt"


def optim2full_spine_e2e_report() -> Path:
    """Phase-2 fresh F0→F6 parity witness tee (per-fence + total timing)."""
    return optim2full_repo_root() / "matlab_custom" / "optim2full_spine_e2e_output.txt"


def optim2full_visualizations_dir() -> Path:
    """Phase 2b plot PNG output root (gitignored class; under visualizations/)."""
    return optim2full_repo_root() / "visualizations" / "optim2full"


def optim2full_wayfinding_matlab_png() -> Path:
    return optim2full_visualizations_dir() / "DEM_drone_VI_optim2full_wayfinding_matlab.png"


def optim2full_wayfinding_python_png() -> Path:
    return optim2full_visualizations_dir() / "DEM_drone_VI_optim2full_wayfinding_python.png"


def optim2full_wayfinding_compare_png() -> Path:
    """Side-by-side: MATLAB (left) | Python (right) for Wayfinding final frame."""
    return (
        optim2full_visualizations_dir()
        / "DEM_drone_VI_optim2full_wayfinding_compare.png"
    )


def optim2full_active_inference_matlab_png() -> Path:
    return (
        optim2full_visualizations_dir()
        / "DEM_drone_VI_optim2full_active_inference_matlab.png"
    )


def optim2full_active_inference_python_png() -> Path:
    return (
        optim2full_visualizations_dir()
        / "DEM_drone_VI_optim2full_active_inference_python.png"
    )


def optim2full_active_inference_compare_png() -> Path:
    """Side-by-side: MATLAB (left) | Python (right) for Active-inference final frame."""
    return (
        optim2full_visualizations_dir()
        / "DEM_drone_VI_optim2full_active_inference_compare.png"
    )


def optim2full_rgm_matlab_png() -> Path:
    return optim2full_visualizations_dir() / "DEM_drone_VI_optim2full_rgm_matlab.png"


def optim2full_rgm_python_png() -> Path:
    return optim2full_visualizations_dir() / "DEM_drone_VI_optim2full_rgm_python.png"


def optim2full_rgm_compare_png() -> Path:
    """Side-by-side: MATLAB (left) | Python (right) for RGM (``spm_show_RGM``)."""
    return optim2full_visualizations_dir() / "DEM_drone_VI_optim2full_rgm_compare.png"


def optim2full_true_env_early_matlab_png() -> Path:
    return (
        optim2full_visualizations_dir()
        / "DEM_drone_VI_optim2full_true_env_early_matlab.png"
    )


def optim2full_true_env_early_python_png() -> Path:
    return (
        optim2full_visualizations_dir()
        / "DEM_drone_VI_optim2full_true_env_early_python.png"
    )


def optim2full_true_env_early_compare_png() -> Path:
    """Side-by-side: MATLAB (left) | Python (right) for early true environment."""
    return (
        optim2full_visualizations_dir()
        / "DEM_drone_VI_optim2full_true_env_early_compare.png"
    )


def optim2full_mdp_params_matlab_png() -> Path:
    return (
        optim2full_visualizations_dir()
        / "DEM_drone_VI_optim2full_mdp_params_matlab.png"
    )


def optim2full_mdp_params_python_png() -> Path:
    return (
        optim2full_visualizations_dir()
        / "DEM_drone_VI_optim2full_mdp_params_python.png"
    )


def optim2full_mdp_params_compare_png() -> Path:
    """Side-by-side: MATLAB (left) | Python (right) for ``spm_MDP_params``."""
    return (
        optim2full_visualizations_dir()
        / "DEM_drone_VI_optim2full_mdp_params_compare.png"
    )


def optim2full_true_scene_post_generate_matlab_png() -> Path:
    return (
        optim2full_visualizations_dir()
        / "DEM_drone_VI_optim2full_true_scene_post_generate_matlab.png"
    )


def optim2full_true_scene_post_generate_python_png() -> Path:
    return (
        optim2full_visualizations_dir()
        / "DEM_drone_VI_optim2full_true_scene_post_generate_python.png"
    )


def optim2full_true_scene_post_generate_compare_png() -> Path:
    """Side-by-side: MATLAB (left) | Python (right) for post-generate True scene."""
    return (
        optim2full_visualizations_dir()
        / "DEM_drone_VI_optim2full_true_scene_post_generate_compare.png"
    )


def optim2full_f5_action_nest8_json() -> Path:
    """U1 durable dump: nest_j=8 hierarchical ``spm_action`` pre-action corpus (F5 / ``vb_1``)."""
    return optim2full_fixtures_dir() / "optim2full_f5_action_nest8.json"


def optim2full_f5_orch_q_producer_json() -> Path:
    """Step 2 durable dump: Q/P/u inputs that build the failing orch ``spm_action`` belief."""
    return optim2full_fixtures_dir() / "optim2full_f5_orch_q_producer.json"
