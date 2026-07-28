"""Oracle: ``spm_sub2ind`` Pass-1 vs MATLAB Engine.

Dependency of the drone process-model handle ``spm_fg`` (OPTIM2FULL F5
callable-``A`` resolution). Covers 2-D and 3-D subscripts, scalar and array
inputs, and the drone call shape ``spm_sub2ind([Nx,Ny,Nz], x, y, z)``.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from python_src.toolbox.DEM.spm_sub2ind import spm_sub2ind

_REPO = Path(__file__).resolve().parents[4]
_DEM_M = _REPO / "matlab_src" / "toolbox" / "DEM"


def _mat_sub2ind(eng, siz, subs):
    eng.workspace["rgms_siz"] = eng.eval(
        "[" + ",".join(str(int(x)) for x in siz) + "]", nargout=1
    )
    args = "rgms_siz"
    for k, v in enumerate(subs):
        arr = np.atleast_1d(np.asarray(v, dtype=float))
        eng.workspace[f"rgms_v{k}"] = eng.eval(
            "[" + ",".join(repr(float(x)) for x in arr.tolist()) + "]", nargout=1
        )
        args += f", rgms_v{k}"
    eng.eval(f"rgms_out = spm_sub2ind({args});", nargout=0)
    return np.asarray(eng.workspace["rgms_out"], dtype=float).reshape(-1)


def _cases():
    return [
        ([4, 5], [2, 3]),
        ([4, 5], [1, 1]),
        ([4, 5], [4, 5]),
        ([3, 6, 2], [2, 4, 1]),
        ([3, 6, 2], [3, 6, 2]),
        ([8, 8, 4], [5, 7, 3]),
        # array subscripts (same size)
        ([4, 5], [[1, 2, 4], [1, 3, 5]]),
        ([3, 6, 2], [[1, 2, 3], [1, 4, 6], [1, 1, 2]]),
    ]


def test_spm_sub2ind_matches_matlab(eng):
    eng.addpath(str(_DEM_M), nargout=0)
    for siz, subs in _cases():
        out_py = np.atleast_1d(np.asarray(spm_sub2ind(siz, *subs), dtype=float)).reshape(-1)
        out_m = _mat_sub2ind(eng, siz, subs)
        assert out_py.shape == out_m.shape, f"shape siz={siz} subs={subs}"
        assert np.array_equal(out_py, out_m), (
            f"value siz={siz} subs={subs} py={out_py} matlab={out_m}"
        )


def test_spm_sub2ind_drone_shape(eng):
    """Drone ``spm_fg`` call shape: 3-D place index, scalar subscripts."""
    eng.addpath(str(_DEM_M), nargout=0)
    siz = [16, 16, 8]
    for x, y, z in [(1, 1, 1), (16, 16, 8), (9, 3, 5)]:
        py = float(spm_sub2ind(siz, x, y, z))
        m = _mat_sub2ind(eng, siz, [x, y, z])[0]
        assert py == m, f"({x},{y},{z}) py={py} matlab={m}"
