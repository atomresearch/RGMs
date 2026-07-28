"""Oracle: ``spm_Q2mdp`` Pass-1 vs MATLAB Engine (synthetic Q).

OPTIM2FULL F5 sign-off remains ``optim2full_parity_gate.py --fence-f5`` after F5.3.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from python_src.toolbox.DEM.spm_Q2mdp import spm_Q2mdp

_REPO = Path(__file__).resolve().parents[4]
_DEM_M = _REPO / "matlab_src" / "toolbox" / "DEM"


def _dense(a):
    # MATLAB Engine returns matlab.double; scipy sparse has toarray().
    if type(a).__module__.startswith("matlab"):
        return np.asarray(a, dtype=float)
    if hasattr(a, "toarray"):
        a = a.toarray()
    return np.asarray(a, dtype=np.float64)


def _mat_get(eng, expr: str, *, full: bool = False):
    # Avoid leading underscores in one-shot eval assignments.
    if full:
        eng.eval(f"rgms_tmp = full({expr});", nargout=0)
    else:
        eng.eval(f"rgms_tmp = {expr};", nargout=0)
    return eng.workspace["rgms_tmp"]


def test_spm_Q2mdp_synthetic_matches_matlab(eng):
    """Engine: synthetic hierarchical Q (nf=2, T=2) vs Python."""
    eng.addpath(str(_DEM_M), nargout=0)

    Xs = [
        [np.array([[1.0], [0.0]]), np.array([[0.0], [1.0]])],
        [np.array([[1.0], [1.0], [0.0]]), np.array([[0.0], [0.0], [1.0]])],
    ]
    Q_py = {
        "s": [np.array([[1.0, 2.0], [3.0, 4.0]], dtype=np.float64)],
        "u": [np.array([[0.0, 1.0]], dtype=np.float64)],
        "X": [Xs],
        "Y": [np.array([[9.0], [8.0]], dtype=np.float64)],
        "O": [[np.array([1.0, 0.0]), np.array([0.0, 1.0])]],
        "o": [np.array([[1.0, 2.0]], dtype=np.float64)],
        "j": [[np.array([1.0]), np.array([2.0])]],
    }
    out_py = spm_Q2mdp(Q_py, 1)

    eng.workspace["s1"] = np.array([[1.0, 2.0], [3.0, 4.0]], dtype=np.float64)
    eng.workspace["u1"] = np.array([[0.0, 1.0]], dtype=np.float64)
    eng.workspace["y1"] = np.array([[9.0], [8.0]], dtype=np.float64)
    eng.workspace["o1"] = np.array([[1.0, 2.0]], dtype=np.float64)
    eng.eval("Q = struct();", nargout=0)
    eng.eval("Q.s = {s1}; Q.u = {u1}; Q.Y = {y1}; Q.o = {o1};", nargout=0)
    eng.eval("Q.X = {cell(2,2)};", nargout=0)
    eng.workspace["x11"] = np.array([[1.0], [0.0]], dtype=np.float64)
    eng.workspace["x12"] = np.array([[0.0], [1.0]], dtype=np.float64)
    eng.workspace["x21"] = np.array([[1.0], [1.0], [0.0]], dtype=np.float64)
    eng.workspace["x22"] = np.array([[0.0], [0.0], [1.0]], dtype=np.float64)
    eng.eval("Q.X{1}{1,1}=x11; Q.X{1}{1,2}=x12;", nargout=0)
    eng.eval("Q.X{1}{2,1}=x21; Q.X{1}{2,2}=x22;", nargout=0)
    eng.eval("Q.O = {cell(1,2)}; Q.O{1}{1}=[1 0]; Q.O{1}{2}=[0 1];", nargout=0)
    eng.eval("Q.j = {cell(1,2)}; Q.j{1}{1}=1; Q.j{1}{2}=2;", nargout=0)
    eng.eval("mdp = spm_Q2mdp(Q,1);", nargout=0)

    s_m = _dense(_mat_get(eng, "mdp.s"))
    u_m = _dense(_mat_get(eng, "mdp.u"))
    y_m = _dense(_mat_get(eng, "mdp.Y"))
    o_m = _dense(_mat_get(eng, "mdp.o"))
    x1_m = _dense(_mat_get(eng, "mdp.X{1}", full=True))
    x2_m = _dense(_mat_get(eng, "mdp.X{2}", full=True))

    assert np.allclose(_dense(out_py["s"]), s_m, rtol=0.0, atol=0.0)
    assert np.allclose(_dense(out_py["u"]), u_m, rtol=0.0, atol=0.0)
    assert np.allclose(_dense(out_py["Y"]), y_m, rtol=0.0, atol=0.0)
    assert np.allclose(_dense(out_py["o"]), o_m, rtol=0.0, atol=0.0)
    assert np.allclose(_dense(out_py["X"][0]), x1_m, rtol=0.0, atol=0.0)
    assert np.allclose(_dense(out_py["X"][1]), x2_m, rtol=0.0, atol=0.0)
    assert x1_m.shape == (2, 2)
    assert x2_m.shape == (3, 2)


def test_spm_Q2mdp_default_n_is_one():
    Xs = [[np.eye(2, 1), np.eye(2, 1)[:, ::-1]]]
    Q = {
        "s": [np.ones((2, 1))],
        "u": [np.zeros((1, 1))],
        "X": [Xs],
        "Y": [np.ones((1, 1))],
        "O": [np.ones((1, 1))],
        "o": [np.ones((1, 1))],
        "j": [np.ones((1, 1))],
    }
    a = spm_Q2mdp(Q)
    b = spm_Q2mdp(Q, 1)
    assert np.allclose(_dense(a["s"]), _dense(b["s"]))
    assert np.allclose(_dense(a["X"][0]), _dense(b["X"][0]))
