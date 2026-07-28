"""Oracle / sanity: Pass-1 ``spm_drone_unity`` (OPTIM2FULL native / COLAB2 N1).

Parity F0 still uses ``load_f0_scene_inject`` — this module must not change that.

Native RNG (NumPy) need **not** bit-match MATLAB ``rng(1)``. Tests check
structure / class inventory / D↔W consistency. Engine test checks the same
properties on the MATLAB twin under ``rng(1)`` (not py≡mat W).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from python_src.toolbox.DEM.DEM_drone_VI import map_from_drone_D, spm_drone_unity

_REPO = Path(__file__).resolve().parents[4]
_CUSTOM = _REPO / "matlab_custom" / "optim2full"
_SPM_DEM = Path(r"C:\Users\andre\Documents\MATLAB\spm-main\toolbox\DEM")


def _assert_scene_ok(D, W, *, Nx: int, Ny: int, Nz: int, Nc: int) -> None:
    W = np.asarray(W, dtype=np.float64)
    assert W.shape == (Nx, Ny, Nz), W.shape
    assert set(np.unique(W).astype(int)).issubset(set(range(1, Nc + 1)))
    # water base still mostly class 2 on z=1 (grass/target may overwrite some)
    assert np.any(W[:, :, 0] == 2.0), "expected water on z=1"
    assert np.any(W == 3.0), "expected grass"
    assert np.any(W == 4.0), "expected foliage"
    assert np.any(W == 5.0), "expected pillars"
    assert np.any(W == 7.0), "expected building"
    assert np.any(W == 8.0), "expected target"
    assert np.sum(W == 8.0) == 1, "exactly one target voxel"

    D_arr = np.asarray(D, dtype=object)
    assert D_arr.shape == (Nx, Ny, Nz)
    for i in range(Nx):
        for j in range(Ny):
            for k in range(Nz):
                col = np.asarray(D_arr[i, j, k], dtype=np.float64).reshape((-1,), order="F")
                assert col.size == Nc
                assert abs(float(col.sum()) - 1.0) < 1e-12
                cls = int(np.argmax(col)) + 1
                assert cls == int(W[i, j, k])

    MAP = map_from_drone_D(D)
    assert len(MAP) == Nx * Ny * Nz
    # MATLAB MAP = D(:); first voxel (1,1,1)
    c0 = np.asarray(MAP[0], dtype=np.float64).reshape((-1,), order="F")
    assert int(np.argmax(c0)) + 1 == int(W[0, 0, 0])


def test_spm_drone_unity_structure_seed1():
    """Python native path under ``np.random.seed(1)`` (COLAB2 Cell 0 RNG)."""
    Nx, Ny, Nz, Nc = 32, 32, 8, 8
    np.random.seed(1)
    D, W = spm_drone_unity(Nx, Ny, Nz, Nc)
    _assert_scene_ok(D, W, Nx=Nx, Ny=Ny, Nz=Nz, Nc=Nc)


def test_spm_drone_unity_reproducible_under_same_seed():
    Nx, Ny, Nz, Nc = 32, 32, 8, 8
    np.random.seed(1)
    _, W1 = spm_drone_unity(Nx, Ny, Nz, Nc)
    np.random.seed(1)
    _, W2 = spm_drone_unity(Nx, Ny, Nz, Nc)
    assert np.array_equal(W1, W2)


def test_spm_drone_unity_matlab_structure(eng):
    """Engine: MATLAB twin under ``rng(1)`` has the same structural properties."""
    if not (_CUSTOM / "spm_drone_unity.m").is_file():
        raise FileNotFoundError(_CUSTOM / "spm_drone_unity.m")
    eng.addpath(str(_CUSTOM), nargout=0)
    eng.addpath(str(_SPM_DEM), nargout=0)
    eng.eval("rng(1); [D,W] = spm_drone_unity(32,32,8,8);", nargout=0)
    W = np.asarray(eng.workspace["W"], dtype=np.float64)
    # D is a cell — pull W-derived checks only (avoid huge cell transfer)
    assert W.shape == (32, 32, 8)
    assert np.any(W[:, :, 0] == 2.0)
    assert np.any(W == 3.0)
    assert np.any(W == 4.0)
    assert np.any(W == 5.0)
    assert np.any(W == 7.0)
    assert np.any(W == 8.0)
    assert int(np.sum(W == 8.0)) == 1
    # class indices in 1..8
    assert set(np.unique(W).astype(int)).issubset(set(range(1, 9)))
