"""Sanity: native ``assemble_mdp_and_gdp_from_scene`` (OPTIM2FULL L2 / B5).

Parity still uses ``assemble_gdp_from_f0`` + ``load_f1_mdp_for_packing`` — those
paths are not exercised here except a light GDP-from-F0 smoke.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from python_src.toolbox.DEM.dem_drone_vi_lib import (
    assemble_gdp_from_f0,
    assemble_mdp_and_gdp_from_scene,
    load_f0_scene_inject,
    scene_dict_from_unity_sizes,
    spm_drone_unity,
)

_REPO = Path(__file__).resolve().parents[4]
_F0 = _REPO / "tests" / "demo1" / "optim2full" / "fixtures" / "DEM_drone_VI_optim2full_F0.mat"


def test_native_assemble_mdp_gdp_structure():
    np.random.seed(1)
    Nx = Ny = 32
    Nz = 8
    Nc = 8
    _D, W = spm_drone_unity(Nx, Ny, Nz, Nc)
    scene = scene_dict_from_unity_sizes(
        Nx=Nx,
        Ny=Ny,
        Nz=Nz,
        Nd=16,
        Nc=Nc,
        Nr=16,
        Na=12,
        No=1,
        Nu=4,
        Ns=6,
        W=W,
    )
    out = assemble_mdp_and_gdp_from_scene(scene)
    assert out["lane"] == "native"
    mdp = out["mdp"]
    GDP = out["GDP"]
    assert len(mdp["A"]) == 516
    assert callable(mdp["A"][0]) and callable(mdp["A"][256])
    assert callable(mdp["GA"][0]) and callable(mdp["GA"][256])
    assert len(mdp["B"]) == 8196
    assert len(mdp["GB"]) == 8200
    assert len(mdp["D"]) == 8196
    assert len(mdp["C"]) == 516
    assert int(np.asarray(mdp["C"][0]).size) == 17  # Nd+1
    assert int(np.asarray(mdp["C"][256]).size) == 8  # Nc
    assert float(mdp["U"].sum()) == 4.0
    assert float(GDP["U"].sum()) == 0.0
    # mdp.s object start 4 vs GDP training start 1 (MATLAB L336 vs L358)
    assert float(mdp["s"][4 + 8192]) == 4.0
    assert float(GDP["s"][4 + 8192]) == 1.0
    assert callable(mdp["id"]["fg"]) and callable(mdp["id"]["cid"])
    assert int(np.asarray(mdp["id"]["ge"]).size) == 16


def test_parity_assemble_gdp_from_f0_still_gdp_only():
    if not _F0.is_file():
        return
    f0 = load_f0_scene_inject(_F0)
    built = assemble_gdp_from_f0(f0)
    assert "mdp" not in built
    assert "GDP" in built and built["GDP"]["T"] == 64.0
    assert int(built["Np"]) == 8192
    assert int(built["Ng"]) == 256
