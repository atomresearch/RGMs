"""Oracle: drone process-model handles ``spm_depth`` / ``spm_state`` / ``spm_fg``.

These are subfunctions of the authority ``DEM_drone_vi.m`` (staged verbatim into
``matlab_src`` as standalone ``.m`` with ``global PG``). They are the procedural
likelihood / parent-graph handles the MATLAB VB evaluates for the drone level-0
process model (OPTIM2FULL F5 callable-``A`` resolution). This oracle retires the
prior unverified Python reconstructions by proving value-for-value equality
against the MATLAB Engine on real F1 ``PG`` geometry.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

import python_src.toolbox.DEM.dem_drone_vi_lib as drone
from tests.demo1.optim2full.optim2full_paths import optim2full_f1_mat

_REPO = Path(__file__).resolve().parents[4]
_DEM_M = _REPO / "matlab_src" / "toolbox" / "DEM"
_SPM_M = Path(r"C:\Users\andre\Documents\MATLAB\spm-main\toolbox\DEM")


def _load_pg() -> dict:
    from scipy.io import loadmat

    raw = loadmat(str(optim2full_f1_mat()), simplify_cells=True)
    pg = raw["PG"]

    def gi(k):
        return int(np.asarray(pg[k]).reshape(-1)[0])

    return {
        "Nx": gi("Nx"), "Ny": gi("Ny"), "Nz": gi("Nz"), "Na": gi("Na"),
        "Nd": gi("Nd"), "Nr": gi("Nr"), "Nc": gi("Nc"), "Nu": gi("Nu"),
        "No": gi("No"),
        "phi": np.asarray(pg["phi"], dtype=np.float64).ravel(order="F"),
        "FOV": np.asarray(pg["FOV"], dtype=np.float64).ravel(order="F"),
    }


def _set_engine_pg(eng, pg: dict) -> None:
    import matlab

    eng.eval("clear global PG; global PG; PG = struct();", nargout=0)
    for k in ("Nx", "Ny", "Nz", "Na", "Nd", "Nr", "Nc", "Nu", "No"):
        eng.eval(f"PG.{k} = {int(pg[k])};", nargout=0)
    eng.workspace["rgms_phi"] = matlab.double(pg["phi"].tolist())
    eng.workspace["rgms_fov"] = matlab.double(pg["FOV"].tolist())
    eng.eval("PG.phi = rgms_phi(:)'; PG.FOV = rgms_fov(:)';", nargout=0)


def _install_python_pg(pg: dict) -> None:
    drone._PG = dict(pg)


def _mat_call(eng, expr: str):
    eng.eval(f"rgms_out = {expr};", nargout=0)
    return np.asarray(eng.workspace["rgms_out"], dtype=np.float64).reshape(-1)


def _mat_vec(eng, name: str, vec) -> None:
    import matlab

    eng.workspace[name] = matlab.double([float(x) for x in np.atleast_1d(vec).tolist()])
    eng.eval(f"{name} = {name}(:)';", nargout=0)


def _mat_cell_of_cols(eng, name: str, cols) -> None:
    """``name`` becomes a 1xN MATLAB cell of Ns x 1 doubles (as ``P(j)`` in VBX)."""
    import matlab

    mat = np.column_stack([np.asarray(c, dtype=np.float64).ravel() for c in cols])
    eng.workspace[f"{name}_m"] = matlab.double(mat.tolist())
    eng.eval(f"{name} = num2cell({name}_m, 1);", nargout=0)


def _mat_cell_of_masks(eng, name: str, masks) -> None:
    """``name`` becomes a 1xN MATLAB cell of Ns x 1 logicals (as ``s`` in VBX)."""
    import matlab

    mat = np.column_stack([np.asarray(m, dtype=np.float64).ravel() for m in masks])
    eng.workspace[f"{name}_m"] = matlab.double(mat.tolist())
    eng.eval(f"{name} = num2cell(logical({name}_m), 1);", nargout=0)


def _mat_get_cell_vecs(eng, name: str) -> list[np.ndarray]:
    """Fetch a MATLAB cell of vectors as a list of 1-D float arrays."""
    eng.eval(
        f"rgms_tmp = cellfun(@(x) full(double(x(:)))', {name}, 'UniformOutput', false);",
        nargout=0,
    )
    out = eng.workspace["rgms_tmp"]
    vals = list(out) if not isinstance(out, (list, tuple)) else out
    return [np.asarray(v, dtype=np.float64).reshape(-1) for v in vals]


def _ray_marginals(rng, nc: int, n_loc: int, *, sharp: bool) -> list[np.ndarray]:
    """Normalised marginals over classes at each location along a ray."""
    cols = []
    for _ in range(n_loc):
        if sharp:
            v = np.full(nc, 1e-8)
            v[rng.integers(0, nc)] = 1.0
        else:
            v = rng.random(nc) + 1e-3
        cols.append(v / v.sum())
    return cols


@pytest.fixture(scope="module")
def pg():
    if not optim2full_f1_mat().is_file():
        pytest.skip("F1.mat not present")
    return _load_pg()


def test_spm_depth_matches_matlab(eng, pg):
    eng.addpath(str(_SPM_M), nargout=0)
    eng.addpath(str(_DEM_M), nargout=0)
    _set_engine_pg(eng, pg)
    _install_python_pg(pg)

    nd = pg["Nd"]
    rays = [
        np.ones(nd + 1),                         # all empty (<=1)
        np.array([1, 3, 1, 2, 1][: nd + 1]),     # first nonempty mid
        np.array([2] + [1] * nd),                # nonempty at head
        np.array([1, 1, 1, 1, 5][: nd + 1]),     # nonempty at tail-ish
    ]
    for s in rays:
        _mat_vec(eng, "rgms_s", s)
        m = _mat_call(eng, "spm_depth(rgms_s)")
        p = np.asarray(drone._spm_depth(s), dtype=np.float64).reshape(-1)
        assert p.shape == m.shape, f"depth shape s={s}"
        assert np.array_equal(p, m), f"depth s={s} py={p} m={m}"


def test_spm_state_matches_matlab(eng, pg):
    eng.addpath(str(_SPM_M), nargout=0)
    eng.addpath(str(_DEM_M), nargout=0)
    _set_engine_pg(eng, pg)
    _install_python_pg(pg)

    nc = pg["Nc"]
    rays = [
        np.ones(5),                              # all empty -> O(1)
        np.array([1, 2, 1]),                     # class 2 first nonempty
        np.array([3, 1, 1]),                     # class 3 at head
        np.array([1, 1, min(nc, 4)]),            # class at tail
    ]
    for s in rays:
        _mat_vec(eng, "rgms_s", s)
        m = _mat_call(eng, "spm_state(rgms_s)")
        p = np.asarray(drone._spm_state(s), dtype=np.float64).reshape(-1)
        assert p.shape == m.shape, f"state shape s={s}"
        assert np.array_equal(p, m), f"state s={s} py={p} m={m}"


def test_spm_fg_matches_matlab(eng, pg):
    eng.addpath(str(_SPM_M), nargout=0)
    eng.addpath(str(_DEM_M), nargout=0)
    _set_engine_pg(eng, pg)
    _install_python_pg(pg)

    Nu = pg["Nu"]
    Ng = pg["Nr"] * pg["Nr"]
    Na = pg["Na"]
    # Base domain state: drone at a place + angle, no objects (numel=Nu).
    base_states = [
        np.array([1, 1, 1, 1][:Nu]),
        np.array([pg["Nx"] // 2, pg["Ny"] // 2, 1, max(1, Na // 2)][:Nu]),
        np.array([pg["Nx"], pg["Ny"], pg["Nz"], Na][:Nu]),
    ]
    # With one object appended (3 place coords) -> numel = Nu + 3.
    obj_states = [
        np.concatenate([np.array([2, 2, 1, 1][:Nu]), np.array([3, 3, 1])]),
    ]
    all_states = base_states + obj_states

    # Modalities to probe: depth (g<=Ng), class (Ng<g<=2Ng), telemetry (g>2Ng).
    mod_gs = [1, 2, Ng, Ng + 1, 2 * Ng, 2 * Ng + 1, 2 * Ng + Nu]

    for s in all_states:
        for g in mod_gs:
            _mat_vec(eng, "rgms_s", s)
            m = _mat_call(eng, f"double(spm_fg({int(g)}, rgms_s))")
            p = np.asarray(drone._spm_fg(g, s), dtype=np.float64).reshape(-1)
            assert p.shape == m.shape, f"fg shape g={g} s={s} py={p.shape} m={m.shape}"
            assert np.array_equal(p, m), f"fg g={g} s={s} py={p} m={m}"


# --------------------------------------------------------------------------
# Dual-use model handles A_depth / A_state — the branches the VB likelihood
# uses (spm_VBX ``A(O{o},s,P(j))`` and spm_VBX_update_L ``A{g}(P(f))``).
# --------------------------------------------------------------------------


def _ray_case_ids(pg):
    nd = pg["Nd"]
    return [1, 3, nd - 1, nd, nd + 1, nd + 3]


def test_A_depth_cell_branch_matches_matlab(eng, pg):
    """``qo = A{g}(P(f))`` — posterior predictive over depth outcomes."""
    eng.addpath(str(_SPM_M), nargout=0)
    eng.addpath(str(_DEM_M), nargout=0)
    _set_engine_pg(eng, pg)
    _install_python_pg(pg)

    rng = np.random.default_rng(20260725)
    nc = pg["Nc"]
    for n_loc in _ray_case_ids(pg):
        for sharp in (True, False):
            cols = _ray_marginals(rng, nc, n_loc, sharp=sharp)
            _mat_cell_of_cols(eng, "rgms_P", cols)
            m = _mat_call(eng, "full(A_depth(rgms_P))")
            p = np.asarray(drone._A_depth(list(cols)), dtype=np.float64).reshape(-1)
            assert p.shape == m.shape, (
                f"A_depth cell shape n_loc={n_loc} sharp={sharp} py={p.shape} m={m.shape}"
            )
            assert np.allclose(p, m, rtol=0, atol=1e-12), (
                f"A_depth cell n_loc={n_loc} sharp={sharp} maxabs={np.abs(p - m).max():.6g}"
            )


def test_A_state_cell_branch_matches_matlab(eng, pg):
    """``qo = A{g}(P(f))`` — posterior predictive over class outcomes."""
    eng.addpath(str(_SPM_M), nargout=0)
    eng.addpath(str(_DEM_M), nargout=0)
    _set_engine_pg(eng, pg)
    _install_python_pg(pg)

    rng = np.random.default_rng(20260726)
    nc = pg["Nc"]
    for n_loc in _ray_case_ids(pg):
        for sharp in (True, False):
            cols = _ray_marginals(rng, nc, n_loc, sharp=sharp)
            _mat_cell_of_cols(eng, "rgms_P", cols)
            m = _mat_call(eng, "full(A_state(rgms_P))")
            p = np.asarray(drone._A_state(list(cols)), dtype=np.float64).reshape(-1)
            assert p.shape == m.shape, (
                f"A_state cell shape n_loc={n_loc} sharp={sharp} py={p.shape} m={m.shape}"
            )
            assert np.allclose(p, m, rtol=0, atol=1e-12), (
                f"A_state cell n_loc={n_loc} sharp={sharp} maxabs={np.abs(p - m).max():.6g}"
            )


def test_A_depth_marginal_branch_matches_matlab(eng, pg):
    """``[U,r] = A(O{o},s,P(j))`` — marginal likelihoods with logical ``s`` masks."""
    eng.addpath(str(_SPM_M), nargout=0)
    eng.addpath(str(_DEM_M), nargout=0)
    _set_engine_pg(eng, pg)
    _install_python_pg(pg)

    rng = np.random.default_rng(20260727)
    nc, nd = pg["Nc"], pg["Nd"]
    for n_loc in (3, nd, nd + 1):
        cols = _ray_marginals(rng, nc, n_loc, sharp=True)
        masks = [np.asarray(c) > np.exp(-16.0) for c in cols]
        _mat_cell_of_cols(eng, "rgms_Q", cols)
        _mat_cell_of_masks(eng, "rgms_f", masks)
        for depth in (1, 2, min(nd, 5), nd, nd + 1):
            obs = np.zeros(nd + 1)
            obs[depth - 1] = 1.0
            _mat_vec(eng, "rgms_O", obs)
            eng.eval("[rgms_U, rgms_r] = A_depth(rgms_O(:), rgms_f, rgms_Q);", nargout=0)
            m_U = _mat_get_cell_vecs(eng, "rgms_U")
            m_r = np.asarray(eng.workspace["rgms_r"], dtype=np.float64).reshape(-1)

            p_U, p_r = drone._A_depth(obs.reshape(-1, 1), list(masks), list(cols))
            p_U = [np.asarray(u, dtype=np.float64).reshape(-1) for u in p_U]
            p_r = np.asarray(p_r, dtype=np.float64).reshape(-1)

            tag = f"n_loc={n_loc} depth={depth}"
            assert len(p_U) == len(m_U), f"A_depth marg nU {tag} py={len(p_U)} m={len(m_U)}"
            assert np.array_equal(p_r, m_r), f"A_depth marg r {tag} py={p_r} m={m_r}"
            for k, (pu, mu) in enumerate(zip(p_U, m_U)):
                assert pu.shape == mu.shape, f"A_depth marg U{{{k}}} shape {tag}"
                assert np.array_equal(pu, mu), f"A_depth marg U{{{k}}} {tag} py={pu} m={mu}"


def test_A_state_marginal_branch_matches_matlab(eng, pg):
    """``[U,r] = A(O{o},s,P(j))`` for the class modality (selects first occluder)."""
    eng.addpath(str(_SPM_M), nargout=0)
    eng.addpath(str(_DEM_M), nargout=0)
    _set_engine_pg(eng, pg)
    _install_python_pg(pg)

    rng = np.random.default_rng(20260728)
    nc, nd = pg["Nc"], pg["Nd"]
    for n_loc in (3, nd, nd + 1):
        for sharp in (True, False):
            cols = _ray_marginals(rng, nc, n_loc, sharp=sharp)
            masks = [np.asarray(c) > np.exp(-16.0) for c in cols]
            _mat_cell_of_cols(eng, "rgms_Q", cols)
            _mat_cell_of_masks(eng, "rgms_f", masks)
            for cls in (1, 2, nc):
                obs = np.zeros(nc)
                obs[cls - 1] = 1.0
                _mat_vec(eng, "rgms_O", obs)
                eng.eval(
                    "[rgms_U, rgms_r] = A_state(rgms_O(:), rgms_f, rgms_Q);", nargout=0
                )
                m_U = _mat_get_cell_vecs(eng, "rgms_U")
                m_r = np.asarray(eng.workspace["rgms_r"], dtype=np.float64).reshape(-1)

                p_U, p_r = drone._A_state(obs.reshape(-1, 1), list(masks), list(cols))
                p_U = [np.asarray(u, dtype=np.float64).reshape(-1) for u in p_U]
                p_r = np.asarray(p_r, dtype=np.float64).reshape(-1)

                tag = f"n_loc={n_loc} sharp={sharp} cls={cls}"
                assert len(p_U) == len(m_U), f"A_state marg nU {tag} py={len(p_U)} m={len(m_U)}"
                assert np.array_equal(p_r, m_r), f"A_state marg r {tag} py={p_r} m={m_r}"
                for k, (pu, mu) in enumerate(zip(p_U, m_U)):
                    assert pu.shape == mu.shape, f"A_state marg U{{{k}}} shape {tag}"
                    assert np.allclose(pu, mu, rtol=0, atol=1e-12), (
                        f"A_state marg U{{{k}}} {tag} py={pu} m={mu}"
                    )
