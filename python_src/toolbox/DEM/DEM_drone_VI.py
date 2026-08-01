"""DEM_drone_VI — OPTIM2FULL Python spine helpers (Pass-1, plots omitted).

**Two lanes (do not conflate):**

- **Parity:** F0 ``W``/``D``/``MAP`` via ``load_f0_scene_inject``; GDP via
  ``assemble_gdp_from_f0``; packing via ``load_f1_mdp_for_packing``; ledger /
  PG-angle / ``G``-override / VB-ledger as fence runners specify.
- **Native / COLAB2:** ``spm_drone_unity`` → ``assemble_mdp_and_gdp_from_scene``
  (live ``mdp``+``GDP``); no F*.mat injects; no ledger kwargs.

Shared geometry lives in ``_assemble_drone_process_model``. See ``OPTIM2FULL.md``
§ COLAB2 (durable) / local-native-first.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from scipy import sparse

from python_src.spm_cat import spm_cat
from python_src.spm_combinations import spm_combinations
from python_src.spm_dir_norm import spm_dir_norm
from python_src.spm_speye import spm_speye
from python_src.toolbox.DEM.spm_index import spm_index

# Module PG (MATLAB ``global PG``) for local likelihood / geometry helpers.
_PG: dict[str, Any] = {}


def load_f0_scene_inject(f0_mat: Path) -> dict[str, Any]:
    """Load same-session MATLAB F0 scene authority (non-scalar parity policy)."""
    from scipy.io import loadmat

    raw = loadmat(str(f0_mat), squeeze_me=True, struct_as_record=False)
    meta = raw["meta"]
    capture = str(getattr(meta, "capture", "")).strip()
    W = np.asarray(raw["W"], dtype=float)
    return {
        "W": W,
        "MAP": raw["MAP"],
        "D": raw["D"],
        "Nx": int(np.asarray(raw["Nx"]).reshape(-1)[0]),
        "Ny": int(np.asarray(raw["Ny"]).reshape(-1)[0]),
        "Nz": int(np.asarray(raw["Nz"]).reshape(-1)[0]),
        "Nd": int(np.asarray(raw["Nd"]).reshape(-1)[0]),
        "Nc": int(np.asarray(raw["Nc"]).reshape(-1)[0]),
        "Nr": int(np.asarray(raw["Nr"]).reshape(-1)[0]),
        "Na": int(np.asarray(raw["Na"]).reshape(-1)[0]),
        "No": int(np.asarray(raw["No"]).reshape(-1)[0]),
        "Nu": int(np.asarray(raw["Nu"]).reshape(-1)[0]),
        "Ns": int(np.asarray(raw["Ns"]).reshape(-1)[0]),
        "capture": capture,
        "fence": "F0",
        "nonscalar_policy": "same_session_WD_inject",
    }


def export_fence_f0_pkl(out_pkl: Path, f0_mat: Path) -> dict[str, Any]:
    """Export Python F0 fence blob from MATLAB F0 inject (parity spine start)."""
    import pickle
    import time

    from tests.demo1.optim2full.optim2full_timing import timing_log

    t0 = time.perf_counter()
    timing_log("export_fence_f0_pkl", "START")
    blob = load_f0_scene_inject(f0_mat)
    out_pkl.parent.mkdir(parents=True, exist_ok=True)
    with out_pkl.open("wb") as f:
        pickle.dump(blob, f, protocol=4)
    timing_log(
        "export_fence_f0_pkl",
        f"END elapsed_s={time.perf_counter()-t0:.3f}",
    )
    return blob


def spm_drone_unity(Nx: int, Ny: int, Nz: int, Nc: int):
    """Pass-1 ``spm_drone_unity`` (``DEM_drone_VI.m`` ~L900–975) — native / COLAB2.

    Returns ``(D, W)`` like MATLAB. Uses the **current** NumPy RNG stream
    (``randperm`` / scalar ``rand`` / array ``rand``). Scene need **not**
    bit-match MATLAB under ``rng(1)`` vs ``np.random.seed(1)``.

    **Parity:** keep using ``load_f0_scene_inject`` — do not call this from
    ``run_fence_f0`` / ``run_fence_f1``.
    """
    Nx = int(Nx)
    Ny = int(Ny)
    Nz = int(Nz)
    Nc = int(Nc)

    xyz = np.asarray(spm_combinations(np.asarray([Nx, Ny, Nz], dtype=np.float64)), dtype=np.float64)
    # Fortran layout so linear ``W(d)`` matches MATLAB / ``xyz`` row order.
    W = np.ones((Nx, Ny, Nz), dtype=np.float64, order="F")
    W[:, :, 0] = 2.0  # water base (MATLAB W(:,:,1))

    # land (grass): outside circle in xy, z < 3
    xy = xyz[:, 0:2]
    center = np.asarray([Nx / 2.0, Ny / 3.0], dtype=np.float64)
    d = np.sqrt(np.sum((xy - center) ** 2, axis=1)) > (Nx / 4.0)
    d = d & (xyz[:, 2] < 3.0)
    W.ravel(order="F")[d] = 3.0

    # foliage blobs on grass at z==2 (MATLAB W(:,:,2))
    c = np.flatnonzero((W[:, :, 1] == 3.0).ravel(order="F")) + 1  # 1-based
    if c.size < 10:
        raise RuntimeError(
            f"spm_drone_unity: need >=10 grass cells at z=2 for foliage, got {c.size}"
        )
    c = c[np.random.permutation(c.size)[:10]]
    for ci in c:
        ind = np.asarray(spm_index([Nx, Ny], float(ci)), dtype=np.float64).ravel()
        z0 = 4.0 + float(np.random.rand())
        d = np.sum((xyz - np.asarray([ind[0], ind[1], z0], dtype=np.float64)) ** 2, axis=1)
        d = np.sqrt(d) < (Nx / (9.0 + float(np.random.rand())))
        d = d & (np.random.rand(d.size) > 0.6)
        W.ravel(order="F")[d] = 4.0

    # building (brick)
    d = (
        (xyz[:, 0] > 2.0)
        & (xyz[:, 0] < 6.0)
        & (xyz[:, 1] > (Ny - 10.0))
        & (xyz[:, 1] < (Ny - 2.0))
        & (xyz[:, 2] < 6.0)
    )
    W.ravel(order="F")[d] = 7.0

    # pillars on grass at z==2
    c = np.flatnonzero((W[:, :, 1] == 3.0).ravel(order="F")) + 1
    if c.size < 4:
        raise RuntimeError(
            f"spm_drone_unity: need >=4 grass cells at z=2 for pillars, got {c.size}"
        )
    c = c[np.random.permutation(c.size)[:4]]
    for ci in c:
        ind = np.asarray(spm_index([Nx, Ny], float(ci)), dtype=np.float64).ravel()
        zmax = float(Nz) - float(np.random.rand())
        d = (
            (xyz[:, 0] == ind[0])
            & (xyz[:, 1] == ind[1])
            & (xyz[:, 2] < zmax)
        )
        W.ravel(order="F")[d] = 5.0

    # target in pond (water on z==1)
    c = np.flatnonzero((W[:, :, 0] == 2.0).ravel(order="F")) + 1
    if c.size < 1:
        raise RuntimeError("spm_drone_unity: no water cells for target")
    c = int(c[np.random.permutation(c.size)[:1][0]])
    ind = np.asarray(spm_index([Nx, Ny], float(c)), dtype=np.float64).ravel()
    d = (
        (xyz[:, 0] == ind[0])
        & (xyz[:, 1] == ind[1])
        & (xyz[:, 2] == 2.0)
    )
    W.ravel(order="F")[d] = 8.0

    # MAP cells: one-hot class at each voxel (dense float64; same values as sparse)
    D = np.empty((Nx, Ny, Nz), dtype=object)
    for i in range(Nx):
        for j in range(Ny):
            for k in range(Nz):
                cls = int(W[i, j, k])
                col = np.zeros((Nc, 1), dtype=np.float64)
                col[cls - 1, 0] = 1.0
                D[i, j, k] = col

    return D, W


def map_from_drone_D(D: Any) -> list[Any]:
    """MATLAB ``MAP = D(:)`` — column-major flatten of the voxel cell array."""
    arr = np.asarray(D, dtype=object)
    if arr.ndim != 3:
        raise ValueError(f"map_from_drone_D: expected 3-D D, got shape {arr.shape}")
    flat = arr.ravel(order="F")
    return [flat[i] for i in range(flat.size)]


# ---------------------------------------------------------------------------
# Local subfunctions (DEM_drone_vi.m / optim2full spine) — private to this module
# ---------------------------------------------------------------------------


def spm_sub2ind(siz, *subs) -> float:
    """MATLAB ``spm_sub2ind`` (DEM toolbox) — linear index from subscripts (1-based)."""
    siz_a = np.asarray(siz, dtype=np.float64).ravel(order="F")
    lensiz = int(siz_a.size)
    num = len(subs)
    if lensiz < num:
        siz_a = np.concatenate(
            [siz_a, np.ones(num - lensiz, dtype=np.float64)]
        )
    elif lensiz > num:
        siz_a = np.concatenate(
            [
                siz_a[: num - 1],
                np.array([float(np.prod(siz_a[num - 1 :]))], dtype=np.float64),
            ]
        )
    ndx = float(subs[0])
    if num >= 2:
        ndx = ndx + (float(subs[1]) - 1.0) * float(siz_a[0])
    if num > 2:
        k = np.cumprod(siz_a)
        for i in range(3, num + 1):
            v = float(subs[i - 1])
            ndx = ndx + (v - 1.0) * float(k[i - 2])
    return float(ndx)


def _spm_depth(s: Any) -> np.ndarray:
    """Local ``spm_depth`` — outcome depth given classes along a ray."""
    s_arr = np.asarray(s, dtype=np.float64).ravel(order="F")
    nd = int(_PG["Nd"])
    O = np.zeros((nd + 1, 1), dtype=np.float64)
    hits = np.flatnonzero(s_arr > 1.0)
    if hits.size:
        O[int(hits[0]), 0] = 1.0
    else:
        O[nd, 0] = 1.0
    return O


def _spm_state(s: Any) -> np.ndarray:
    """Local ``spm_state`` — outcome class given classes along a ray."""
    s_arr = np.asarray(s, dtype=np.float64).ravel(order="F")
    nc = int(_PG["Nc"])
    O = np.zeros((nc, 1), dtype=np.float64)
    hits = np.flatnonzero(s_arr > 1.0)
    if hits.size:
        d = int(hits[0])
        cls = int(s_arr[d])
        O[cls - 1, 0] = 1.0
    else:
        O[0, 0] = 1.0
    return O


def _is_matlab_cell_arg(x: Any) -> bool:
    """MATLAB ``iscell(P)`` for dual-use ``A_depth`` / ``A_state`` first args."""
    return isinstance(x, (list, tuple))


def _dense_float(x: Any) -> np.ndarray:
    """MATLAB numeric/sparse value as a dense float64 array."""
    if sparse.issparse(x):
        x = x.toarray()
    return np.asarray(x, dtype=np.float64)


def _spm_cat_columns(cells: Any) -> Any:
    """``spm_cat`` over MATLAB column-vector cell entries."""
    cols: list[Any] = []
    for x in list(cells):
        if sparse.issparse(x):
            if x.shape[0] == 1 and x.shape[1] > 1:
                x = x.T
        else:
            arr = np.asarray(x)
            if arr.ndim == 1:
                x = arr.reshape((-1, 1), order="F")
        cols.append(x)
    return spm_cat(cols)


def _A_depth(P: Any, f: Any = None, Q: Any = None):
    """Local ``A_depth`` — dual-use model likelihood (VBX / generate / predict).

    MATLAB ``DEM_drone_vi.m`` L547–612. ``nargout`` is 2 → VBX calls
    ``[U,r]=A(O,s,P(j))``. Process ``GA`` stays ``_spm_depth`` (1-arg only).
    """
    nd = int(_PG["Nd"])
    nc = int(_PG["Nc"])
    if _is_matlab_cell_arg(P):
        q = _dense_float(_spm_cat_columns(P))
        if q.ndim == 1:
            q = q.reshape((-1, 1), order="F")
        q_empty = np.asarray(q[0, :], dtype=np.float64).ravel(order="F")
        p_occ = 1.0 - q_empty
        cum = np.concatenate(
            [np.asarray([1.0], dtype=np.float64), q_empty[:-1]]
        )
        O = (p_occ * np.cumprod(cum)).reshape((-1, 1), order="F")
        if O.shape[0] < nd + 1:
            O2 = np.zeros((nd + 1, 1), dtype=np.float64)
            O2[: O.shape[0], 0] = O[:, 0]
            O = O2
        O[nd, 0] = max(1.0 - float(np.sum(O)), 0.0)
        O = O / float(np.sum(O))
        return O
    if f is None:
        return _spm_depth(P)

    Pv = _dense_float(P).ravel(order="F")
    hits = np.flatnonzero(Pv)
    d = int(hits[0]) + 1 if hits.size else 0
    if d > nd:
        o = np.zeros((nc, nd), dtype=bool)
        o[0, :] = True
    else:
        o = np.zeros((nc, d), dtype=bool)
        if d >= 2:
            o[0, 0 : d - 1] = True
        if d >= 1:
            o[1:, d - 1] = True
    n_f = len(f) if isinstance(f, (list, tuple)) else int(np.asarray(f).size)
    d_out = min(int(o.shape[1]), int(n_f))
    O_cell: list[Any] = [None] * d_out
    for j in range(d_out):
        fj = f[j]
        mask = _dense_float(fj).ravel(order="F")
        if mask.dtype == bool or (
            np.issubdtype(mask.dtype, np.number)
            and mask.size == o.shape[0]
            and set(np.unique(mask.astype(float)).tolist()).issubset({0.0, 1.0})
        ):
            rows = np.asarray(mask, dtype=bool).ravel()
            O_cell[j] = np.asarray(o[rows, j], dtype=bool).reshape((-1, 1), order="F")
        else:
            idx = np.asarray(mask, dtype=np.int64).ravel() - 1
            O_cell[j] = np.asarray(o[idx, j], dtype=bool).reshape((-1, 1), order="F")
    r = np.arange(1, d_out + 1, dtype=np.float64)
    return O_cell, r


def _A_state(P: Any, f: Any = None, Q: Any = None):
    """Local ``A_state`` — dual-use model class likelihood (``DEM_drone_vi.m`` L614–669)."""
    nd = int(_PG["Nd"])
    if _is_matlab_cell_arg(P):
        d = _A_depth(P)
        d = np.asarray(d, dtype=np.float64).reshape((-1, 1), order="F")
        q = _dense_float(_spm_cat_columns(P))
        if q.ndim == 1:
            q = q.reshape((-1, 1), order="F")
        q = q.copy()
        q[0, :] = 0.0
        if q.shape[1] > nd:
            q[0, nd] = 1.0
        elif q.shape[1] == nd:
            # out-of-range column may be absent; pad like MATLAB q(1,Nd+1)=1
            q2 = np.zeros((q.shape[0], nd + 1), dtype=np.float64)
            q2[:, :nd] = q
            q2[0, nd] = 1.0
            q = q2
        else:
            q2 = np.zeros((q.shape[0], nd + 1), dtype=np.float64)
            q2[:, : q.shape[1]] = q
            q2[0, nd] = 1.0
            q = q2
        q = np.asarray(spm_dir_norm(q), dtype=np.float64)
        O = q @ d
        return np.asarray(O, dtype=np.float64).reshape((-1, 1), order="F")
    if f is None:
        return _spm_state(P)

    Pv = _dense_float(P).ravel(order="F")
    O_cell: list[Any] = []
    r: list[float] = []
    d_dist = _A_depth(Q)
    d_arr = np.asarray(d_dist, dtype=np.float64).ravel(order="F")
    hits = np.flatnonzero(d_arr > (1.0 - 1.0 / 32.0))
    if hits.size:
        d = int(hits[0]) + 1
        n_f = len(f) if isinstance(f, (list, tuple)) else 0
        if d <= nd and d <= n_f:
            r = [float(d)]
            fj = f[d - 1]
            mask = _dense_float(fj).ravel(order="F")
            if mask.dtype == bool or (
                np.issubdtype(mask.dtype, np.number)
                and mask.size == Pv.size
                and set(np.unique(mask.astype(float)).tolist()).issubset({0.0, 1.0})
            ):
                O_cell = [
                    np.asarray(
                        Pv[np.asarray(mask, dtype=bool)], dtype=np.float64
                    ).reshape((-1, 1), order="F")
                ]
            else:
                idx = np.asarray(mask, dtype=np.int64).ravel() - 1
                O_cell = [
                    np.asarray(Pv[idx], dtype=np.float64).reshape((-1, 1), order="F")
                ]
    return O_cell, np.asarray(r, dtype=np.float64)


# VBX: MATLAB ``nargout(@A_depth)>1`` → ``[U,r]=A(O,s,P(j))``
_A_depth._rgms_vbx_nout = 2  # type: ignore[attr-defined]
_A_state._rgms_vbx_nout = 2  # type: ignore[attr-defined]


def _spm_cid(Q: Any):
    """Local ``spm_cid`` constraint handle (``DEM_drone_vi.m`` L671–693)."""
    nx = int(_PG["Nx"])
    ny = int(_PG["Ny"])
    nz = int(_PG["Nz"])
    nu = int(_PG["Nu"])
    np_ = nx * ny * nz
    q = _dense_float(_spm_cat_columns(list(Q)[nu : nu + np_]))
    D = np.asarray(q[0, :] > (1.0 - 1.0 / 32.0), dtype=bool).reshape(
        (nx, ny, nz), order="F"
    )
    hif = np.arange(1, 4, dtype=np.float64).reshape(1, -1)
    return D, hif


_spm_cid._rgms_cid_hif = np.arange(1, 4, dtype=np.int64)  # type: ignore[attr-defined]


def _spm_spherical2rectang(origin, ph, th, d) -> np.ndarray:
    origin = np.asarray(origin, dtype=np.float64).ravel(order="F")
    x = float(origin[0]) + float(d) * np.cos(ph) * np.cos(th)
    y = float(origin[1]) + float(d) * np.sin(ph) * np.cos(th)
    z = float(origin[2]) - float(d) * np.sin(th)
    return np.asarray([x, y, z], dtype=np.float64)


def _uint8_saturate(v: float) -> int:
    """MATLAB ``uint8`` saturation to ``[0, 255]`` (integer result)."""
    c = float(v)
    if c < 0.0:
        return 0
    if c > 255.0:
        return 255
    return int(c)


def _spm_fg(g: int, s: Any) -> np.ndarray:
    """Local ``spm_fg`` — projective parents of modality ``g`` given domain states ``s``."""
    g = int(g)
    s_arr = np.asarray(s, dtype=np.float64).ravel(order="F")
    Nu = int(_PG["Nu"])
    Ng = int(_PG["Nr"]) * int(_PG["Nr"])
    Np = int(_PG["Nx"]) * int(_PG["Ny"]) * int(_PG["Nz"])

    if g > (Ng + Ng):
        par = g - (Ng + Ng)
        return np.asarray([par], dtype=np.uint16)

    if g > Ng:
        g = g - Ng

    origin = s_arr[0:3]
    angle = float(np.asarray(_PG["phi"], dtype=np.float64).ravel()[int(s_arr[3]) - 1])
    theta = np.asarray(_PG["FOV"], dtype=np.float64).ravel()
    d_idx = spm_index([_PG["Nr"], _PG["Nr"]], g).ravel()
    ph = angle - float(theta[int(d_idx[1]) - 1])
    th = float(theta[int(d_idx[0]) - 1]) - float(theta[0])

    No = int((s_arr.size - Nu) / 3)
    fo = np.zeros(max(No, 0), dtype=np.float64)
    jo = np.zeros(max(No, 0), dtype=np.float64)
    for o in range(No):
        so = s_arr[Nu + o * 3 : Nu + o * 3 + 3]
        fo[o] = Nu + Np + (o + 1) * 4
        jo[o] = spm_sub2ind(
            [_PG["Nx"], _PG["Ny"], _PG["Nz"]], so[0], so[1], so[2]
        )

    par_list: list[float] = []
    for d in range(1, int(_PG["Nd"]) + 1):
        # MATLAB: xyz = ceil(spm_spherical2rectang(...)); x = uint8(xyz(1)); ...
        xyz = np.ceil(_spm_spherical2rectang(origin, ph, th, d))
        x = _uint8_saturate(float(xyz[0]))
        y = _uint8_saturate(float(xyz[1]))
        z = _uint8_saturate(float(xyz[2]))
        if (
            x > 0
            and x <= int(_PG["Nx"])
            and y > 0
            and y <= int(_PG["Ny"])
            and z > 0
            and z <= int(_PG["Nz"])
        ):
            j = spm_sub2ind([_PG["Nx"], _PG["Ny"], _PG["Nz"]], x, y, z)
            p = j + Nu
            for o in range(No):
                if j == jo[o]:
                    p = fo[o]
            par_list.append(float(p))
        else:
            break
    if not par_list:
        return np.zeros((0,), dtype=np.uint16)
    return np.asarray(par_list, dtype=np.uint16)


def apply_pg_angles(phi: Any, FOV: Any) -> None:
    """Install ``PG.phi`` / ``PG.FOV`` into module ``_PG`` (MATLAB ``global PG``).

    ``np.linspace`` is **not** bit-identical to MATLAB ``linspace`` at ULP scale.
    Those ULPs change ``ph``/``th`` enough that plain ``ceil`` on ray coords
    diverges from MATLAB ``spm_fg``. For F1 generate parity, install the same-
    session F1 ``PG.phi`` / ``PG.FOV`` (Engine ``linspace`` authority) before
    calling ``spm_MDP_generate``. Do **not** snap ``ceil`` inputs — that
    fights IEEE when angles already match (see translation-issues note).
    """
    global _PG
    if not _PG:
        raise RuntimeError("apply_pg_angles: assemble_gdp_from_f0 must run first")
    _PG["phi"] = np.asarray(phi, dtype=np.float64).ravel(order="F")
    _PG["FOV"] = np.asarray(FOV, dtype=np.float64).ravel(order="F")


def load_f1_pg_angles(f1_mat: Path) -> dict[str, np.ndarray]:
    """Load same-session F1 ``PG.phi`` / ``PG.FOV`` (MATLAB linspace authority)."""
    from scipy.io import loadmat

    raw = loadmat(str(f1_mat), squeeze_me=True, struct_as_record=False)
    pg = raw["PG"]
    return {
        "phi": np.asarray(getattr(pg, "phi"), dtype=np.float64).ravel(order="F"),
        "FOV": np.asarray(getattr(pg, "FOV"), dtype=np.float64).ravel(order="F"),
    }


def _full_speye(*args) -> np.ndarray:
    return np.asarray(spm_speye(*args).toarray(), dtype=np.float64)


def _assemble_drone_process_model(scene: dict[str, Any]) -> dict[str, Any]:
    """Shared geometry for **parity GDP** and **native mdp+GDP** (``.m`` ~L115–370).

    Builds process ``GA``/``GB``/``ID`` and model ``A``/``B``/``C``/``D``/``id`` once.
    Model ``B`` is the pre-animate GB snapshot; animate factors append to process
    ``GB`` only (MATLAB L278–297).

    ``C`` for handle modalities uses ``Nd+1`` / ``Nc`` rows (F1 authority / packing
    repair), not MATLAB ``size(@fh,1)==1``.
    """
    global _PG

    Nx = int(scene["Nx"])
    Ny = int(scene["Ny"])
    Nz = int(scene["Nz"])
    Nd = int(scene["Nd"])
    Nc = int(scene["Nc"])
    Nr = int(scene["Nr"])
    Na = int(scene["Na"])
    No = int(scene["No"])
    Nu = int(scene["Nu"])
    Ns = int(scene["Ns"])
    W = np.asarray(scene["W"], dtype=np.float64)
    if W.shape != (Nx, Ny, Nz):
        W = W.reshape((Nx, Ny, Nz), order="F")

    # Formula matches MATLAB ``linspace``; not bit-identical (parity may
    # ``apply_pg_angles`` after). Native keeps these values.
    phi = scene.get("phi")
    FOV = scene.get("FOV")
    if phi is None:
        phi = np.linspace(0.0, 2.0 * np.pi * (1.0 - 1.0 / Na), Na)
    else:
        phi = np.asarray(phi, dtype=np.float64).ravel(order="F")
    if FOV is None:
        FOV = np.linspace(-np.pi / float(Ns), np.pi / float(Ns), Nr)
    else:
        FOV = np.asarray(FOV, dtype=np.float64).ravel(order="F")

    _PG = {
        "Nx": Nx,
        "Ny": Ny,
        "Nz": Nz,
        "Na": Na,
        "Nd": Nd,
        "Nr": Nr,
        "Nc": Nc,
        "Nu": Nu,
        "No": No,
        "phi": phi,
        "FOV": FOV,
    }

    XYZ = spm_combinations(np.asarray([Nx, Ny, Nz], dtype=np.float64))
    Np = int(np.asarray(XYZ).shape[0])
    Ng = Nr * Nr

    # Process likelihood GA
    GA: list[Any] = [None] * (Ng + Ng + Nu)
    for g in range(Ng):
        GA[g] = _spm_depth
        GA[g + Ng] = _spm_state
    GA[Ng + Ng + 0] = np.eye(Nx, Nx, dtype=bool)
    GA[Ng + Ng + 1] = np.eye(Ny, Ny, dtype=bool)
    GA[Ng + Ng + 2] = np.eye(Nz, Nz, dtype=bool)
    GA[Ng + Ng + 3] = np.eye(Na, Na, dtype=bool)

    ID: dict[str, Any] = {
        "control": np.arange(Ng + Ng + 1, Ng + Ng + Nu + 1, dtype=np.float64),
        "ff": np.arange(1, Nu + 1, dtype=np.float64),
        "fg": _spm_fg,
    }
    for o in range(No):
        ff = Nu + Np + o * 4 + np.arange(1, 4, dtype=np.float64)
        ID["ff"] = np.concatenate([ID["ff"], ff])

    # Model likelihood A (handles + telemetry eyes)
    A: list[Any] = [None] * (Ng + Ng + Nu)
    for g in range(Ng):
        A[g] = _A_depth
        A[g + Ng] = _A_state
    A[Ng + Ng + 0] = np.eye(Nx, Nx, dtype=bool)
    A[Ng + Ng + 1] = np.eye(Ny, Ny, dtype=bool)
    A[Ng + Ng + 2] = np.eye(Nz, Nz, dtype=bool)
    A[Ng + Ng + 3] = np.eye(Na, Na, dtype=bool)

    # PG.cen / PG.per / id.ge
    xy_r = spm_combinations(np.asarray([Nr, Nr], dtype=np.float64))
    mid = np.asarray([(Nr + 1) / 2.0, (Nr + 1) / 2.0], dtype=np.float64)
    d2 = np.sum((xy_r - mid) ** 2, axis=1)
    d_cut = (Nr - 1) ** 2 / 2.0
    cen = np.flatnonzero(d2 < 2.0) + 1  # 1-based
    per = np.flatnonzero(d2 >= d_cut) + 1
    _PG["cen"] = cen.astype(np.float64)
    _PG["per"] = per.astype(np.float64)
    id_ge = np.unique(
        np.concatenate(
            [
                cen,
                Ng + cen,
                per,
                Ng + per,
            ]
        )
    ).astype(np.float64)

    # Transitions BX/BY/BZ/BA → GB control factors
    d_perim = 4
    u_vals = [-1, 0, 1]
    BX = np.zeros((Nx, Nx, 3), dtype=np.float64)
    BY = np.zeros((Ny, Ny, 3), dtype=np.float64)
    BZ = np.zeros((Nz, Nz, 3), dtype=np.float64)
    BA = np.zeros((Na, Na, 3), dtype=np.float64)
    for i, u in enumerate(u_vals):
        BX[:, :, i] = _full_speye(Nx, Nx, u, 1)
        for j in range(1, Nx + 1):
            if j < d_perim:
                BX[:, j - 1, i] = 0.0
                BX[d_perim - 1, j - 1, i] = 1.0
            if j > (Nx - d_perim + 1):
                BX[:, j - 1, i] = 0.0
                BX[Nx - d_perim, j - 1, i] = 1.0
        BY[:, :, i] = _full_speye(Ny, Ny, u, 2)
        for j in range(1, Ny + 1):
            if j < d_perim:
                BY[:, j - 1, i] = 0.0
                BY[d_perim - 1, j - 1, i] = 1.0
            if j > (Ny - d_perim + 1):
                BY[:, j - 1, i] = 0.0
                BY[Ny - d_perim, j - 1, i] = 1.0
        BZ[:, :, i] = _full_speye(Nz, Nz, u, 2)
        for j in range(1, Nz + 1):
            if j < 3:
                BZ[:, j - 1, i] = 0.0
                BZ[2, j - 1, i] = 1.0
        BA[:, :, i] = _full_speye(Na, Na, u, 1)

    GB: list[Any] = [BX, BY, BZ, BA]
    n_noise = np.asarray([1 / 16, 1 / 16, 1 / 64, 0], dtype=np.float64) / 128.0
    for f in range(len(n_noise)):
        b = np.asarray(GB[f], dtype=np.float64).copy()
        c = float(n_noise[f])
        b0 = b[:, :, 0].copy()
        b1 = b[:, :, 1].copy()
        b2 = b[:, :, 2].copy()
        out = np.empty_like(b)
        out[:, :, 0] = b0 + c * b1 + c * (b0 @ b0)
        out[:, :, 1] = b1 + c * b0 + c * b2
        out[:, :, 2] = b2 + c * b1 + c * (b2 @ b2)
        GB[f] = spm_dir_norm(out)

    Bp = np.eye(Nc, Nc, dtype=bool)
    for _ in range(Np):
        GB.append(Bp.copy())

    # Model B = snapshot before animate append (MATLAB L281)
    B: list[Any] = list(GB)

    # Animate object transitions (process GB only)
    d0 = 1
    e0 = 12
    Bx = np.zeros((Nx, Nx, 1), dtype=np.float64)
    Bx[:, :, 0] = _full_speye(Nx, Nx, -1, 1)
    Bx[:, 0:d0, 0] = 0.0
    Bx[d0, 0:d0, 0] = 1.0
    Bx[:, e0 - 1 :, 0] = 0.0
    Bx[d0, e0 - 1 :, 0] = 1.0
    By = _full_speye(Ny, Ny).reshape(Ny, Ny, 1)
    Bz = _full_speye(Nz, Nz).reshape(Nz, Nz, 1)
    Bc = _full_speye(Nc, Nc).reshape(Nc, Nc, 1)
    for _ in range(No):
        GB.extend([Bx.copy(), By.copy(), Bz.copy(), Bc.copy()])

    # Model priors D / C / U
    D_m: list[Any] = []
    for b in B:
        n_state = int(np.asarray(b).shape[0])
        D_m.append(np.ones((n_state, 1), dtype=np.float64))
    V = np.asarray(
        [int(Nx / 2), int(Ny / 2), Nz, int(2 * Na / 3)], dtype=np.float64
    )
    for i, dim in enumerate([Nx, Ny, Nz, Na]):
        col = np.zeros((dim, 1), dtype=np.float64)
        col[int(V[i]) - 1, 0] = 1.0
        D_m[i] = col

    C: list[Any] = [None] * (Ng + Ng + Nu)
    for g in range(Ng):
        C[g] = np.asarray(
            spm_dir_norm(np.ones((Nd + 1, 1), dtype=np.float64)), dtype=np.float64
        )
        C[g + Ng] = np.asarray(
            spm_dir_norm(np.ones((Nc, 1), dtype=np.float64)), dtype=np.float64
        )
    for i, dim in enumerate([Nx, Ny, Nz, Na]):
        C[Ng + Ng + i] = np.asarray(
            spm_dir_norm(np.ones((dim, 1), dtype=np.float64)), dtype=np.float64
        )

    U = np.zeros(len(B), dtype=np.float64)
    U[0:Nu] = 1.0
    GU = np.zeros(len(GB), dtype=np.float64)
    GU[0:Nu] = 1.0

    id_model: dict[str, Any] = {
        "ff": np.arange(1, Nu + 1, dtype=np.float64),
        "fg": _spm_fg,
        "cid": _spm_cid,
        "ge": id_ge,
    }

    # mdp.s — object prior start [4, Ny/3, 3, 6]
    P_mdp = np.tile(
        np.asarray([4.0, float(int(Ny / 3)), 3.0, 6.0], dtype=np.float64),
        (1, No),
    ).ravel(order="F")
    s_mdp = np.concatenate(
        [V.ravel(order="F"), W.ravel(order="F"), P_mdp.ravel(order="F")]
    )

    # GDP.s — training start [1, Ny/3, 3, 6]
    P_gdp = np.tile(
        np.asarray([1.0, float(int(Ny / 3)), 3.0, 6.0], dtype=np.float64),
        (1, No),
    ).ravel(order="F")
    s_gdp = np.concatenate(
        [V.ravel(order="F"), W.ravel(order="F"), P_gdp.ravel(order="F")]
    )

    mdp: dict[str, Any] = {
        "A": A,
        "B": B,
        "C": C,
        "D": D_m,
        "N": 0.0,
        "U": U,
        "id": id_model,
        "GA": GA,
        "GB": GB,
        "GU": GU,
        "ID": ID,
        "s": s_mdp.ravel(order="F"),
    }

    GDP = {
        "T": 64.0,
        "A": GA,
        "B": GB,
        "U": GU * 0.0,
        "id": ID,
        "s": s_gdp.ravel(order="F"),
    }

    # Induction cid factor range (packing / VB native)
    _spm_cid._rgms_cid_q_factors = np.arange(  # type: ignore[attr-defined]
        Nu, Nu + Np, dtype=np.int64
    )

    return {
        "mdp": mdp,
        "GDP": GDP,
        "PG": dict(_PG),
        "Np": Np,
        "Ng": Ng,
        "V": V,
        "s_mdp": s_mdp,
        "s_gdp": s_gdp,
        "Nx": Nx,
        "Ny": Ny,
        "Nz": Nz,
        "Nu": Nu,
        "No": No,
        "Nc": Nc,
    }


def assemble_gdp_from_f0(f0: dict[str, Any]) -> dict[str, Any]:
    """**Parity** path: build generative process ``GDP`` (and ``PG``) from F0 inject.

    Same return shape as before L2. Does **not** expose ``mdp`` — packing still
    uses ``load_f1_mdp_for_packing``. For native, use
    ``assemble_mdp_and_gdp_from_scene``.
    """
    core = _assemble_drone_process_model(f0)
    return {
        "GDP": core["GDP"],
        "PG": core["PG"],
        "Np": core["Np"],
        "Ng": core["Ng"],
        "V": core["V"],
        "s": core["s_gdp"],
    }


def assemble_mdp_and_gdp_from_scene(scene: dict[str, Any]) -> dict[str, Any]:
    """**Native / COLAB2** path: generative model ``mdp`` + process ``GDP``.

    Authority: ``DEM_drone_VI.m`` ~L115–370. Input ``scene`` must include sizes
    (``Nx…Ns``, ``No``, ``Nu``, …) and ``W`` (e.g. from ``spm_drone_unity``).
    Does **not** read F1.mat / parity injects.

    Distinguishes ``mdp.s`` (object start ``[4,Ny/3,3,6]``) from ``GDP.s``
    (training ``[1,Ny/3,3,6]``) as in MATLAB.
    """
    required = (
        "Nx",
        "Ny",
        "Nz",
        "Nd",
        "Nc",
        "Nr",
        "Na",
        "No",
        "Nu",
        "Ns",
        "W",
    )
    missing = [k for k in required if k not in scene]
    if missing:
        raise KeyError(
            f"assemble_mdp_and_gdp_from_scene missing keys: {missing}"
        )
    core = _assemble_drone_process_model(scene)
    return {
        "mdp": core["mdp"],
        "GDP": core["GDP"],
        "PG": core["PG"],
        "Np": core["Np"],
        "Ng": core["Ng"],
        "V": core["V"],
        "s_mdp": core["s_mdp"],
        "s_gdp": core["s_gdp"],
        "Nx": core["Nx"],
        "Ny": core["Ny"],
        "Nz": core["Nz"],
        "Nu": core["Nu"],
        "No": core["No"],
        "Nc": core["Nc"],
        "lane": "native",
    }


def scene_dict_from_unity_sizes(
    *,
    Nx: int,
    Ny: int,
    Nz: int,
    Nd: int,
    Nc: int,
    Nr: int,
    Na: int,
    No: int,
    Nu: int,
    Ns: int,
    W: Any,
) -> dict[str, Any]:
    """Build the ``scene`` dict for ``assemble_mdp_and_gdp_from_scene`` (native)."""
    return {
        "Nx": int(Nx),
        "Ny": int(Ny),
        "Nz": int(Nz),
        "Nd": int(Nd),
        "Nc": int(Nc),
        "Nr": int(Nr),
        "Na": int(Na),
        "No": int(No),
        "Nu": int(Nu),
        "Ns": int(Ns),
        "W": np.asarray(W, dtype=np.float64),
    }


def _q_onehot_col(cls_1based: int, Nc: int) -> np.ndarray:
    """Dense float64 one-hot column — same values as MATLAB ``sparse(cls,1,1,Nc,1)``.

    Python FSL / Entry4 MI bridges use ``np.asarray(..., float64)`` (Atari O path).
    Emitting dense here keeps the Q *producer* compatible with that shared pipeline;
    do not densify inside ``spm_faster_structure_learning``.
    """
    col = np.zeros((int(Nc), 1), dtype=np.float64)
    col[int(cls_1based) - 1, 0] = 1.0
    return col


def assemble_Q_from_pdp(PDP: dict[str, Any], pg: dict[str, Any], Nu: int, No: int, Np: int):
    """MATLAB F1 Q assembly from ``PDP.s`` (~L396–411).

    MATLAB stores ``Q{f,t}`` as sparse one-hots; Python emits dense float64 columns
    with identical values so downstream ``spm_faster_structure_learning`` /
    Entry4 MI hooks (OPTIM1FULL-proven) receive the same cell type as Atari ``O``.
    """
    T = int(PDP["T"])
    Nc = int(pg["Nc"])
    s_mat = np.asarray(PDP["s"], dtype=np.float64)
    if s_mat.ndim == 1:
        s_mat = s_mat.reshape((-1, 1), order="F")
    Q: list[list[Any]] = [[None for _ in range(T)] for _ in range(Np)]
    for t in range(T):
        for f in range(Np):
            cls = int(s_mat[f + Nu, t])
            Q[f][t] = _q_onehot_col(cls, Nc)
        for o in range(No):
            sl = s_mat[Nu + Np + o * 4 : Nu + Np + o * 4 + 4, t]
            f_lin = int(
                spm_sub2ind(
                    [pg["Nx"], pg["Ny"], pg["Nz"]], sl[0], sl[1], sl[2]
                )
            )
            cls = int(sl[3])
            Q[f_lin - 1][t] = _q_onehot_col(cls, Nc)
    return Q


def load_f1_pdp_q_inject(f1_mat: Path) -> dict[str, Any]:
    """Load same-session F1 ``PDP``/``Q`` (locked non-scalar generate policy)."""
    from scipy.io import loadmat

    raw = loadmat(str(f1_mat), squeeze_me=True, struct_as_record=False)
    meta = raw["meta"]
    capture = str(getattr(meta, "capture", "")).strip()
    return {
        "PDP": raw["PDP"],
        "Q": raw["Q"],
        "GDP_mat": raw["GDP"],
        "capture": capture,
        "fence": "F1",
        "nonscalar_policy": "same_session_F1_PDP_Q_for_generate",
    }


def _mat_struct_to_dict(obj: Any) -> dict[str, Any]:
    """Convert ``scipy.io`` mat_struct / dict to a plain dict."""
    if isinstance(obj, dict):
        return obj
    out: dict[str, Any] = {}
    for name in getattr(obj, "_fieldnames", ()) or ():
        out[name] = getattr(obj, name)
    return out


def run_fence_f1(
    f0_mat: Path,
    f1_mat: Path,
    *,
    try_generate: bool = True,
) -> dict[str, Any]:
    """F0 inject → GDP assemble → F1 PG angles → ``spm_MDP_generate`` + ``pre_fsl``.

    F1.mat is post-generate + Q. Default path is ledger generate (optim), not PDP inject.
    Same-session F1 ``PG.phi``/``FOV`` are required for ``spm_fg`` / ``PDP.o`` parity.
    """
    import time

    from tests.demo1.optim2full.optim2full_timing import timing_log

    t_all0 = time.perf_counter()
    timing_log("run_fence_f1", "START")

    t0 = time.perf_counter()
    f0 = load_f0_scene_inject(f0_mat)
    timing_log("run_fence_f1", f"load_f0 elapsed_s={time.perf_counter()-t0:.3f}")

    t0 = time.perf_counter()
    built = assemble_gdp_from_f0(f0)
    GDP = built["GDP"]
    timing_log("run_fence_f1", f"assemble_gdp elapsed_s={time.perf_counter()-t0:.3f}")

    # Same-session F1 PG angles (MATLAB linspace) — required for ``spm_fg`` /
    # ``PDP.o`` bit parity under generate; also keeps exported PG aligned.
    t0 = time.perf_counter()
    angles = load_f1_pg_angles(f1_mat)
    apply_pg_angles(angles["phi"], angles["FOV"])
    built["PG"]["phi"] = np.asarray(_PG["phi"], dtype=np.float64).copy()
    built["PG"]["FOV"] = np.asarray(_PG["FOV"], dtype=np.float64).copy()
    timing_log("run_fence_f1", f"pg_angles elapsed_s={time.perf_counter()-t0:.3f}")

    nonscalar_policy = "same_session_F0_WD_and_F1_PG_angles_generate"
    pg_angles_policy = "same_session_F1_PG_phi_FOV"

    if not try_generate:
        # Debug-only inject path (not the F1 fence sign-off).
        inj = load_f1_pdp_q_inject(f1_mat)
        PDP = _mat_struct_to_dict(inj["PDP"])
        Q = assemble_Q_from_pdp(
            PDP, built["PG"], int(f0["Nu"]), int(f0["No"]), int(built["Np"])
        )
        timing_log(
            "run_fence_f1",
            f"END inject-path elapsed_s={time.perf_counter()-t_all0:.3f}",
        )
        return {
            "GDP": GDP,
            "PDP": PDP,
            "Q": Q,
            "PG": built["PG"],
            "f0": f0,
            "Np": built["Np"],
            "Ng": built["Ng"],
            "pre_fsl_k": 0,
            "draws_used": 0,
            "capture": f0.get("capture"),
            "fence": "F1",
            "generate_entry": "spm_MDP_generate",
            "rng_policy": "F1_PDP_inject",
            "generate_note": "skipped_pdp_inject",
            "nonscalar_policy": "same_session_F1_PDP_Q_inject_debug",
            "pg_angles_policy": pg_angles_policy,
        }

    from tests.demo1.optim1.optim1_replay_rand import optim1_replay_matlab_draws
    from tests.demo1.optim2full.optim2full_rand_ledger import (
        load2full_rand_buf,
        load2full_rand_manifest,
    )
    from python_src.toolbox.DEM.spm_MDP_generate import (
        spm_MDP_generate,
    )

    buf, _ = load2full_rand_buf()
    seg = load2full_rand_manifest().segment("pre_fsl")
    pre_fsl_k = int(seg.k)
    slice_ = buf[int(seg.start) : int(seg.start) + pre_fsl_k]
    t0 = time.perf_counter()
    timing_log("run_fence_f1", f"generate START pre_fsl_k={pre_fsl_k}")
    with optim1_replay_matlab_draws(pre_fsl_k, slice_) as ctr:
        PDP = spm_MDP_generate(GDP)
    draws_used = int(ctr[0])
    timing_log(
        "run_fence_f1",
        f"generate END elapsed_s={time.perf_counter()-t0:.3f} draws={draws_used}",
    )
    if draws_used != pre_fsl_k:
        raise RuntimeError(
            f"pre_fsl draw audit failed: used={draws_used} expected={pre_fsl_k}"
        )

    t0 = time.perf_counter()
    Q = assemble_Q_from_pdp(
        PDP, built["PG"], int(f0["Nu"]), int(f0["No"]), int(built["Np"])
    )
    timing_log(
        "run_fence_f1",
        f"assemble_Q elapsed_s={time.perf_counter()-t0:.3f}",
    )
    timing_log(
        "run_fence_f1",
        f"END total_s={time.perf_counter()-t_all0:.3f}",
    )
    return {
        "GDP": GDP,
        "PDP": PDP,
        "Q": Q,
        "PG": built["PG"],
        "f0": f0,
        "Np": built["Np"],
        "Ng": built["Ng"],
        "pre_fsl_k": pre_fsl_k,
        "draws_used": draws_used,
        "capture": f0.get("capture"),
        "fence": "F1",
        "generate_entry": "spm_MDP_generate",
        "rng_policy": "pre_fsl_replay+F1_PG_angles",
        "generate_note": "spm_MDP_generate_pre_fsl",
        "nonscalar_policy": nonscalar_policy,
        "pg_angles_policy": pg_angles_policy,
    }


def export_fence_f1_pkl(out_pkl: Path, f0_mat: Path, f1_mat: Path) -> dict[str, Any]:
    """Run F1 generate spine and pickle the fence blob."""
    import pickle
    import time

    from tests.demo1.optim2full.optim2full_timing import timing_log

    t0 = time.perf_counter()
    timing_log("export_fence_f1_pkl", "START")
    blob = run_fence_f1(f0_mat, f1_mat, try_generate=True)
    out = dict(blob)
    out_pkl.parent.mkdir(parents=True, exist_ok=True)
    with out_pkl.open("wb") as f:
        pickle.dump(out, f, protocol=4)
    timing_log(
        "export_fence_f1_pkl",
        f"END elapsed_s={time.perf_counter()-t0:.3f}",
    )
    return out


def _q_object_array_to_nested(Q: Any) -> list[list[Any]]:
    """Convert MATLAB ``Q{f,t}`` object array to nested Python ``Q[f][t]``."""
    qa = np.asarray(Q, dtype=object)
    if qa.ndim != 2:
        raise ValueError(f"Q must be 2-D object array, got shape={qa.shape}")
    n_f, n_t = int(qa.shape[0]), int(qa.shape[1])
    out: list[list[Any]] = []
    for f in range(n_f):
        row: list[Any] = []
        for t in range(n_t):
            row.append(qa[f, t])
        out.append(row)
    return out


def _q_cell_dense_float64(cell: Any) -> np.ndarray:
    """Dense float64 column when loading MATLAB-sparse ``Q`` from F2.mat.

    Authority ``.mat`` cells are sparse; adapt at the load boundary (not inside
    shared ``spm_faster_structure_learning``) so Entry4 MI / FSL see Atari-like
    dense columns. Values unchanged vs ``sparse(cls,1,1,Nc,1)``.
    """
    if hasattr(cell, "toarray"):
        cell = cell.toarray()
    arr = np.asarray(cell, dtype=np.float64)
    if arr.ndim == 1:
        arr = arr.reshape(-1, 1)
    return arr


def load_f2_q_for_fsl(f2_mat: Path, f1_pkl: Path | None = None) -> list[list[Any]]:
    """FSL input ``Q``: prefer F2.mat ``Q`` (same session as F2 ``MDP`` authority).

    Prefer F1 pkl ``Q`` when present (same capture; already dense from
    ``assemble_Q_from_pdp``). Otherwise densify F2.mat sparse cells at this boundary.
    """
    from scipy.io import loadmat

    if f1_pkl is not None and f1_pkl.is_file():
        import pickle

        with f1_pkl.open("rb") as f:
            blob = pickle.load(f)
        q1 = blob.get("Q")
        if q1 is not None:
            # Ensure dense float64 even for older sparse F1 pkls.
            Q = [[_q_cell_dense_float64(c) for c in row] for row in q1]
            raw = loadmat(str(f2_mat), simplify_cells=True)
            Qm = _q_object_array_to_nested(raw["Q"])
            if len(Qm) != len(Q) or (Q and len(Qm[0]) != len(Q[0])):
                raise RuntimeError(
                    f"F1/F2 Q shape mismatch F1=({len(Q)},"
                    f"{len(Q[0]) if Q else 0}) F2=({len(Qm)},{len(Qm[0])})"
                )
            return Q

    raw = loadmat(str(f2_mat), simplify_cells=True)
    Q = _q_object_array_to_nested(raw["Q"])
    return [[_q_cell_dense_float64(c) for c in row] for row in Q]


def run_fence_f2(
    f2_mat: Path,
    *,
    f1_pkl: Path | None = None,
    rgm_G_mat: Path | None = None,
) -> dict[str, Any]:
    """F2: ``spm_faster_structure_learning(Q,[Nx,Ny,Nz],[1,64])`` + dump-once ``G``.

    Call contract matches MATLAB ``DEM_drone_vi.m`` / spine. Day-to-day parity uses
    dump-once MATLAB ``spm_rgm_group`` ``G`` inject (``rgm_group_override_fn``) —
    **no** live Entry4 per-cell Engine MI push. OPTIM1FULL callers never pass the
    override (default ``None``).

    Requires ``DEM_drone_VI2full_F2_rgm_G.mat`` from
    ``optim2full_capture_fsl_rgm_G`` (same-session F2 ``Q``).
    """
    import time

    from scipy.io import loadmat

    from python_src.toolbox.DEM.spm_faster_structure_learning import (
        spm_faster_structure_learning,
    )
    from tests.demo1.optim2full.optim2full_fsl_g_dump import (
        load_f2_rgm_G_dump,
        make_rgm_group_override_from_dump,
    )
    from tests.demo1.optim2full.optim2full_paths import optim2full_f2_rgm_G_mat
    from tests.demo1.optim2full.optim2full_signoff_env import optim2full_signoff_env
    from tests.demo1.optim2full.optim2full_timing import timing_log

    t_all0 = time.perf_counter()
    timing_log("run_fence_f2", "START")

    if rgm_G_mat is None:
        rgm_G_mat = optim2full_f2_rgm_G_mat()
    if not rgm_G_mat.is_file():
        raise FileNotFoundError(
            f"F2 rgm G dump missing: {rgm_G_mat}. "
            "Run once: python tests/demo1/optim2full/optim2full_capture_fsl_rgm_G.py "
            "(native MATLAB FSL on same-session F2 Q; do not use live Entry4 cell-push)."
        )

    t0 = time.perf_counter()
    raw = loadmat(str(f2_mat), simplify_cells=True)
    meta = raw.get("meta")
    capture = ""
    if meta is not None:
        capture = str(
            meta["capture"] if isinstance(meta, dict) else getattr(meta, "capture", "")
        ).strip()
    Nx = int(np.asarray(raw["Nx"]).reshape(-1)[0])
    Ny = int(np.asarray(raw["Ny"]).reshape(-1)[0])
    Nz = int(np.asarray(raw["Nz"]).reshape(-1)[0])
    timing_log("run_fence_f2", f"loadmat_meta elapsed_s={time.perf_counter()-t0:.3f}")

    t0 = time.perf_counter()
    Q = load_f2_q_for_fsl(f2_mat, f1_pkl=f1_pkl)
    timing_log(
        "run_fence_f2",
        f"load_Q elapsed_s={time.perf_counter()-t0:.3f} "
        f"shape=({len(Q)},{len(Q[0]) if Q else 0})",
    )
    S = np.asarray([Nx, Ny, Nz], dtype=np.float64)
    # MATLAB DEM_drone_vi: spm_faster_structure_learning(Q,[Nx,Ny,Nz],[1 64]).
    # Shared optim pads via MATLAB ``[dx repmat(dx(end),1,16)]`` (scalar Atari + vector drone).
    dx = np.asarray([1.0, 64.0], dtype=np.float64)

    t0 = time.perf_counter()
    g_dump = load_f2_rgm_G_dump(rgm_G_mat)
    g_override = make_rgm_group_override_from_dump(g_dump)
    hooks_meta: dict[str, Any] = {
        "g_dump": str(rgm_G_mat),
        "g_n_calls": int(g_dump["n_calls"]),
        "g_capture": str(g_dump.get("capture") or ""),
        "mi_source": "skipped_g_override",
        "eig_source": "skipped_g_override",
        "link_dir_mi_source": "native_python",
    }
    timing_log(
        "run_fence_f2",
        f"g_dump ready elapsed_s={time.perf_counter()-t0:.3f} {hooks_meta}",
    )

    with optim2full_signoff_env():
        t0 = time.perf_counter()
        timing_log(
            "run_fence_f2",
            "spm_faster_structure_learning START "
            "(G override; no Engine MI/eig; see [fsl_timing] if env on)",
        )
        MDP = spm_faster_structure_learning(
            Q,
            S,
            dx,
            None,
            rgm_group_override_fn=g_override,
        )
        elapsed = float(time.perf_counter() - t0)
        timing_log(
            "run_fence_f2",
            f"spm_faster_structure_learning END elapsed_s={elapsed:.3f}",
        )

    timing_log(
        "run_fence_f2",
        f"END total_s={time.perf_counter()-t_all0:.3f}",
    )

    return {
        "MDP": MDP,
        "Q": Q,
        "Nx": Nx,
        "Ny": Ny,
        "Nz": Nz,
        "dx": dx,
        "capture": capture,
        "fence": "F2",
        "generate_entry": "spm_faster_structure_learning",
        "fsl_hooks": hooks_meta,
        "fsl_elapsed_s": elapsed,
        "nonscalar_policy": "same_session_F2_Q_plus_dump_once_rgm_G",
    }


def export_fence_f2_pkl(
    out_pkl: Path,
    f2_mat: Path,
    f1_pkl: Path | None = None,
    *,
    rgm_G_mat: Path | None = None,
) -> dict[str, Any]:
    """Run F2 FSL spine (dump-once ``G`` inject) and pickle the fence blob."""
    import pickle
    import time

    from tests.demo1.optim2full.optim2full_timing import timing_log

    t0 = time.perf_counter()
    timing_log("export_fence_f2_pkl", "START")
    blob = run_fence_f2(f2_mat, f1_pkl=f1_pkl, rgm_G_mat=rgm_G_mat)
    out_pkl.parent.mkdir(parents=True, exist_ok=True)
    with out_pkl.open("wb") as f:
        pickle.dump(blob, f, protocol=4)
    timing_log(
        "export_fence_f2_pkl",
        f"END elapsed_s={time.perf_counter()-t0:.3f} "
        f"fsl_elapsed_s={blob.get('fsl_elapsed_s')}",
    )
    return blob


def _peel_fsl_factor_cell(cell: Any) -> list[Any]:
    """Python FSL stores ``a{g}=[tensor]``; MATLAB ``a{g}`` is the tensor."""
    out: list[Any] = []
    for item in cell:
        x = item
        while isinstance(x, (list, tuple)) and len(x) == 1:
            x = x[0]
        out.append(x)
    return out


def _mdp_levels_for_a2A(mdp: Any) -> list[dict[str, Any]]:
    """Shallow-copy F2 MDP levels with peeled ``a``/``b`` for ``spm_mdp_a2A``."""
    if isinstance(mdp, list):
        levels = mdp
    else:
        arr = np.asarray(mdp, dtype=object).ravel(order="F")
        levels = [arr[i] for i in range(arr.size)]
    out: list[dict[str, Any]] = []
    for lev in levels:
        if not isinstance(lev, dict):
            raise TypeError(f"F2 MDP level must be dict, got {type(lev)}")
        m = dict(lev)
        if "a" not in m or "b" not in m:
            raise KeyError("F2 MDP level missing a/b for spm_mdp_a2A")
        m["a"] = _peel_fsl_factor_cell(list(m["a"]))
        m["b"] = _peel_fsl_factor_cell(list(m["b"]))
        out.append(m)
    return out


def run_fence_f3(
    f2_pkl: Path,
    *,
    f2_mat: Path | None = None,
) -> dict[str, Any]:
    """F3: ``spm_mdp_a2A(MDP)`` on same-session F2 MDP (post-FSL counts → A/B).

    Prefer green F2 pkl (spine chain). ``f2_mat`` is only for capture/meta
    cross-check. Does **not** run packing / ``spm_mdp2rdp`` (that is F4).
    """
    import pickle
    import time

    from python_src.toolbox.DEM.spm_mdp_a2A import spm_mdp_a2A
    from tests.demo1.optim2full.optim2full_signoff_env import optim2full_signoff_env
    from tests.demo1.optim2full.optim2full_timing import timing_log

    t_all0 = time.perf_counter()
    timing_log("run_fence_f3", "START")
    if not f2_pkl.is_file():
        raise FileNotFoundError(
            f"F2 pkl missing: {f2_pkl}. Run --fence-f2 export first "
            "(F3 consumes post-FSL MDP)."
        )

    t0 = time.perf_counter()
    with f2_pkl.open("rb") as f:
        f2_blob = pickle.load(f)
    if not isinstance(f2_blob, dict) or "MDP" not in f2_blob:
        raise TypeError("F2 pkl must be dict with MDP")
    capture = str(f2_blob.get("capture") or "").strip()
    mdp_in = _mdp_levels_for_a2A(f2_blob["MDP"])
    timing_log(
        "run_fence_f3",
        f"load_F2_pkl elapsed_s={time.perf_counter()-t0:.3f} "
        f"n_levels={len(mdp_in)} capture={capture!r}",
    )

    with optim2full_signoff_env():
        t0 = time.perf_counter()
        timing_log("run_fence_f3", "spm_mdp_a2A START")
        MDP = spm_mdp_a2A(mdp_in)
        elapsed = float(time.perf_counter() - t0)
        timing_log(
            "run_fence_f3",
            f"spm_mdp_a2A END elapsed_s={elapsed:.3f}",
        )

    timing_log(
        "run_fence_f3",
        f"END total_s={time.perf_counter()-t_all0:.3f}",
    )
    return {
        "MDP": MDP,
        "capture": capture,
        "fence": "F3",
        "generate_entry": "spm_mdp_a2A",
        "a2A_elapsed_s": elapsed,
        "f2_pkl": str(f2_pkl),
        "f2_mat": str(f2_mat) if f2_mat is not None else "",
        "nonscalar_policy": "same_session_F2_MDP_then_spm_mdp_a2A",
    }


def export_fence_f3_pkl(
    out_pkl: Path,
    f2_pkl: Path,
    *,
    f2_mat: Path | None = None,
) -> dict[str, Any]:
    """Run F3 ``spm_mdp_a2A`` and pickle the fence blob."""
    import pickle
    import time

    from tests.demo1.optim2full.optim2full_timing import timing_log

    t0 = time.perf_counter()
    timing_log("export_fence_f3_pkl", "START")
    blob = run_fence_f3(f2_pkl, f2_mat=f2_mat)
    out_pkl.parent.mkdir(parents=True, exist_ok=True)
    with out_pkl.open("wb") as f:
        pickle.dump(blob, f, protocol=4)
    timing_log(
        "export_fence_f3_pkl",
        f"END elapsed_s={time.perf_counter()-t0:.3f} "
        f"a2A_elapsed_s={blob.get('a2A_elapsed_s')}",
    )
    return blob


# ---------------------------------------------------------------------------
# F4 — id.A-linked packing + ``spm_mdp2rdp`` (spine / packtest contract)
# ---------------------------------------------------------------------------


def _as_cell_list(x: Any) -> list[Any]:
    """Normalize MATLAB cell / ``simplify_cells`` collapse to a Python list."""
    if x is None:
        return []
    if isinstance(x, list):
        return list(x)
    if isinstance(x, np.ndarray) and x.dtype == object:
        return [x.flat[i] for i in range(x.size)]
    if isinstance(x, np.ndarray):
        return [x]
    return [x]


def _is_matlab_function(x: Any) -> bool:
    return type(x).__name__ == "MatlabFunction"


def _restore_matlab_logical_array(x: Any) -> Any:
    """Restore MATLAB ``logical`` after scipy ``loadmat`` (uint8 0/1) / binary float.

    Mirrors spine ``DEM_drone_vi.m`` / ``DEM_drone_VI2full_spine.m``::

        if isnumeric(GA{g}), GA{g} = logical(GA{g}); end

    Handles stay unchanged. Float transition tensors with non-{0,1} values are
    left untouched (not blanket-``logical`` of probabilities).
    """
    if x is None:
        return x
    if callable(x) and not isinstance(x, (np.ndarray, np.generic)):
        return x
    if sparse.issparse(x):
        # Sparse logical from MATLAB is uncommon here; densify only if 0/1 data.
        d = x.dtype
        if d == bool or np.issubdtype(d, np.bool_):
            return x
        if np.issubdtype(d, np.integer) or np.issubdtype(d, np.floating):
            # Avoid densifying huge sparse floats; only convert if already 0/1 pattern
            # is cheap to test via data attribute when available.
            data = np.asarray(x.data)
            if data.size == 0 or (
                np.all(np.isfinite(data)) and np.all((data == 0) | (data == 1))
            ):
                return x.astype(bool)
        return x
    a = np.asarray(x)
    if a.dtype == bool or np.issubdtype(a.dtype, np.bool_):
        return np.asarray(a, dtype=bool)
    if a.size == 0:
        return a
    if np.issubdtype(a.dtype, np.integer) or np.issubdtype(a.dtype, np.floating):
        if not np.all(np.isfinite(a)):
            return x
        if np.all((a == 0) | (a == 1)):
            return a.astype(bool)
    return x


def _restore_matlab_logical_cells(cells: list[Any]) -> list[Any]:
    """Apply ``_restore_matlab_logical_array`` to each cell entry."""
    return [_restore_matlab_logical_array(c) for c in cells]


def _is_binary_01_array(a: np.ndarray) -> bool:
    if a.size == 0:
        return True
    if not (np.issubdtype(a.dtype, np.integer) or np.issubdtype(a.dtype, np.floating)):
        return False
    if not np.all(np.isfinite(a)):
        return False
    return bool(np.all((a == 0) | (a == 1)))


def _restore_matlab_gb_b_cells(cells: list[Any], *, Nu: int) -> list[Any]:
    """Restore ``GB``/``B`` with scipy ``uint8`` vs MATLAB ``double``/``logical`` split.

    scipy ``loadmat`` maps some MATLAB **double** 0/1 tensors to ``uint8`` (same as
    true ``logical``). Blanket ``uint8→bool`` then burns the wrong ``spm_sample``
    branch (OPTIM2FULL F4.mat Engine pin: ``GB{4}`` and trailing ``Nu`` eyes are
    ``double``; place ``GB{5:end-Nu}`` are ``logical``).

    Policy (MATLAB-faithful for drone process tensors):
    - binary ``ndim >= 3`` → ``float64`` (transition cubes, incl. 0/1-valued)
    - binary trailing ``Nu`` cells → ``float64`` (telemetry eyes stored as double)
    - other binary cells → ``bool`` (true MATLAB logical places)
    - non-binary floats unchanged
    """
    n = len(cells)
    nu = max(0, int(Nu))
    out: list[Any] = []
    for i, c in enumerate(cells):
        if c is None or (callable(c) and not isinstance(c, (np.ndarray, np.generic))):
            out.append(c)
            continue
        if sparse.issparse(c):
            out.append(_restore_matlab_logical_array(c))
            continue
        a = np.asarray(c)
        if a.dtype == bool or np.issubdtype(a.dtype, np.bool_):
            # Already bool — but trailing Nu / 3-D may need float if mis-restored upstream.
            if a.ndim >= 3 or (nu > 0 and i >= n - nu):
                out.append(a.astype(np.float64))
            else:
                out.append(np.asarray(a, dtype=bool))
            continue
        if _is_binary_01_array(a) and (
            a.ndim >= 3 or (nu > 0 and i >= n - nu)
        ):
            out.append(np.asarray(a, dtype=np.float64))
            continue
        out.append(_restore_matlab_logical_array(c))
    return out


def _id_cell_nonempty(v: Any) -> bool:
    if v is None:
        return False
    if isinstance(v, (list, tuple)):
        return len(v) > 0 and _id_cell_nonempty(v[0] if len(v) == 1 else v)
    arr = np.asarray(v)
    return arr.size > 0


def _id_first_index_1based(v: Any) -> int:
    arr = np.asarray(v).ravel(order="F")
    if arr.size == 0:
        raise ValueError("empty id index cell")
    return int(arr.flat[0])


def _ensure_pg_from_f1(f1_mat: Path) -> dict[str, Any]:
    """Load F1 ``PG`` into module ``_PG`` (dims + same-session angles)."""
    from scipy.io import loadmat

    global _PG
    raw = loadmat(str(f1_mat), simplify_cells=True)
    pg = raw["PG"]
    if not isinstance(pg, dict):
        raise TypeError(f"F1.mat PG must be dict, got {type(pg)}")
    _PG = {
        "Nx": int(np.asarray(pg["Nx"]).reshape(-1)[0]),
        "Ny": int(np.asarray(pg["Ny"]).reshape(-1)[0]),
        "Nz": int(np.asarray(pg["Nz"]).reshape(-1)[0]),
        "Na": int(np.asarray(pg["Na"]).reshape(-1)[0]),
        "Nd": int(np.asarray(pg["Nd"]).reshape(-1)[0]),
        "Nr": int(np.asarray(pg["Nr"]).reshape(-1)[0]),
        "Nc": int(np.asarray(pg["Nc"]).reshape(-1)[0]),
        "Nu": int(np.asarray(pg["Nu"]).reshape(-1)[0]),
        "No": int(np.asarray(pg["No"]).reshape(-1)[0]),
        "phi": np.asarray(pg["phi"], dtype=np.float64).ravel(order="F"),
        "FOV": np.asarray(pg["FOV"], dtype=np.float64).ravel(order="F"),
    }
    apply_pg_angles(_PG["phi"], _PG["FOV"])
    return dict(_PG)


def load_f1_mdp_for_packing(f1_mat: Path) -> dict[str, Any]:
    """Load same-session F1 process ``mdp``; rebind ``MatlabFunction`` → locals.

    F1 pkl does not export ``mdp``; F4 must load F1.mat. ``spm_mdp2rdp`` keeps
    callable ``A`` cells; scipy ``MatlabFunction`` is not callable and would be
    treated as numeric — rebind like the live spine
    (``DEM_drone_VI2full_spine.m`` L558–570):

    - ``mdp.A`` → ``@A_depth`` / ``@A_state`` (VB / VBX dual-use model likelihood)
    - ``mdp.GA`` → ``@spm_depth`` / ``@spm_state`` (process generate)
    - ``mdp.id.fg`` → ``@spm_fg``
    - numeric ``GA``/``GB`` 0/1 cells → ``bool`` (spine ``logical(GA)``; scipy
      maps MATLAB ``logical`` → ``uint8``)
    """
    from scipy.io import loadmat

    _ensure_pg_from_f1(f1_mat)
    _spm_cid._rgms_cid_q_factors = np.arange(  # type: ignore[attr-defined]
        int(_PG["Nu"]),
        int(_PG["Nu"]) + int(_PG["Nx"]) * int(_PG["Ny"]) * int(_PG["Nz"]),
        dtype=np.int64,
    )
    raw = loadmat(str(f1_mat), simplify_cells=True)
    mdp_in = raw["mdp"]
    if not isinstance(mdp_in, dict):
        raise TypeError(f"F1.mat mdp must be dict, got {type(mdp_in)}")

    mdp: dict[str, Any] = dict(mdp_in)
    Ng = int(_PG["Nr"]) * int(_PG["Nr"])
    A = _as_cell_list(mdp.get("A"))
    if len(A) < Ng + Ng:
        raise ValueError(f"F1 mdp.A len={len(A)} < 2*Ng={2 * Ng}")
    for g in range(Ng):
        # Always rebind model A to dual-use handles (never process spm_depth/state).
        A[g] = _A_depth
        A[g + Ng] = _A_state
    mdp["A"] = A
    mdp["B"] = _as_cell_list(mdp.get("B"))
    if "C" in mdp:
        C = _as_cell_list(mdp["C"])
        # Spine L571–585: repair C rows for handle modalities (size(@fh,1)==1 bug)
        for g in range(len(A)):
            if callable(A[g]) and not isinstance(A[g], (np.ndarray, np.generic)):
                if g < Ng:
                    no_g = int(_PG["Nd"]) + 1
                elif g < Ng + Ng:
                    no_g = int(_PG["Nc"])
                else:
                    continue
                cg = np.asarray(C[g], dtype=np.float64).reshape((-1,), order="F")
                if cg.size != no_g:
                    C[g] = np.asarray(
                        spm_dir_norm(np.ones((no_g, 1), dtype=np.float64)),
                        dtype=np.float64,
                    )
        mdp["C"] = C
    if "D" in mdp:
        # Initial-state priors are often MATLAB logical ones/eyes → scipy uint8.
        # MATLAB local ``spm_norm`` is a no-op on logical (``isnumeric`` false), so
        # ``spm_sample(spm_norm(D{f}))`` stays on the ``randperm`` / L0 path.
        mdp["D"] = _restore_matlab_logical_cells(_as_cell_list(mdp["D"]))
    if "E" in mdp:
        mdp["E"] = _restore_matlab_logical_cells(_as_cell_list(mdp["E"]))
    if "A" in mdp:
        # Packed likelihood cells: callables unchanged; binary eyes → bool.
        mdp["A"] = _restore_matlab_logical_cells(_as_cell_list(mdp["A"]))
    if "B" in mdp:
        # Same scipy uint8/double split as GB (see ``_restore_matlab_gb_b_cells``).
        mdp["B"] = _restore_matlab_gb_b_cells(
            _as_cell_list(mdp["B"]), Nu=int(_PG.get("Nu", 4))
        )
    if "GA" in mdp:
        GA = _as_cell_list(mdp["GA"])
        for g in range(min(Ng, len(GA))):
            if _is_matlab_function(GA[g]) or not callable(GA[g]):
                GA[g] = _spm_depth
        for g in range(Ng, min(Ng + Ng, len(GA))):
            if _is_matlab_function(GA[g]) or not callable(GA[g]):
                GA[g] = _spm_state
        # Spine L190–194: numeric GA → logical (telemetry eyes survive loadmat as uint8).
        mdp["GA"] = _restore_matlab_logical_cells(GA)
    if "GB" in mdp:
        mdp["GB"] = _restore_matlab_gb_b_cells(
            _as_cell_list(mdp["GB"]), Nu=int(_PG.get("Nu", 4))
        )

    id_in = mdp.get("id")
    if not isinstance(id_in, dict):
        raise TypeError("F1 mdp.id must be dict")
    id_out = dict(id_in)
    id_out["fg"] = _spm_fg
    if "cid" in id_out:
        id_out["cid"] = _spm_cid
    for key in ("D", "E", "A", "ge", "ff", "fg", "cid"):
        if key in id_out and key not in ("fg",):
            if isinstance(id_out[key], (list, np.ndarray)) and key in ("D", "E", "A"):
                id_out[key] = _as_cell_list(id_out[key])
    mdp["id"] = id_out
    if "ID" in mdp and isinstance(mdp["ID"], dict):
        ID = dict(mdp["ID"])
        if "fg" in ID or _is_matlab_function(ID.get("fg")):
            ID["fg"] = _spm_fg
        mdp["ID"] = ID
    return mdp


def pack_mdp_ida_linked(
    mdp: dict[str, Any],
    MDP: list[dict[str, Any]],
    *,
    Nu: int = 4,
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    """Spine/packtest packing: id.A-linked ``Af``, empty-``id.D`` parent skip.

    Mutates copies of ``mdp`` / ``MDP``; returns ``(mdp_packed, MDP_packed, meta)``.
    """
    import copy

    if not MDP:
        raise ValueError("MDP levels empty")
    mdp_out = copy.deepcopy(mdp)
    mdp_levels = [copy.deepcopy(lev) for lev in MDP]
    m1 = mdp_levels[0]
    m2 = mdp_levels[1] if len(mdp_levels) > 1 else None

    B1 = _as_cell_list(m1["B"])
    A1 = _as_cell_list(m1["A"])
    m1["B"] = B1
    m1["A"] = A1
    id1 = m1["id"]
    if not isinstance(id1, dict):
        raise TypeError("MDP{1}.id must be dict")
    id1 = dict(id1)
    id1["A"] = _as_cell_list(id1.get("A"))
    id1["D"] = _as_cell_list(id1.get("D"))
    id1["E"] = _as_cell_list(id1.get("E"))
    m1["id"] = id1

    nB1 = len(B1)
    kid = np.zeros(nB1, dtype=np.int64)
    for g, v in enumerate(id1["A"]):
        if not _id_cell_nonempty(v):
            continue
        ff = _id_first_index_1based(v)
        if 1 <= ff <= nB1 and kid[ff - 1] == 0:
            kid[ff - 1] = g + 1
    missing = int(np.count_nonzero(kid < 1))
    if missing:
        raise RuntimeError(f"id.A packing: {missing} factors missing kid")

    nB_mdp = len(_as_cell_list(mdp_out["B"]))
    mdp_out["B"] = _as_cell_list(mdp_out["B"])
    if "id" not in mdp_out or not isinstance(mdp_out["id"], dict):
        mdp_out["id"] = {}
    mdp_out["id"] = dict(mdp_out["id"])
    # MATLAB: mdp.id.D/E = cell(1, numel(mdp.B))
    mdp_out["id"]["D"] = [np.array([], dtype=np.float64) for _ in range(nB_mdp)]
    mdp_out["id"]["E"] = [np.array([], dtype=np.float64) for _ in range(nB_mdp)]

    if m2 is not None:
        m2["A"] = _as_cell_list(m2["A"])

    n_parent = 0
    n_skip = 0
    for f in range(1, nB1 + 1):
        gk = int(kid[f - 1])
        Af = np.asarray(A1[gk - 1], dtype=np.float64)
        Bf = np.asarray(B1[f - 1], dtype=np.float64)
        if Bf.ndim == 2:
            Bf = Bf.reshape(Bf.shape[0], Bf.shape[1], 1, order="F")
        if Af.shape[1] != Bf.shape[0]:
            raise RuntimeError(
                f"dim fail f={f} A{Af.shape} B{Bf.shape} kid={gk}"
            )
        nu = int(Bf.shape[2])
        out_b = np.zeros((Af.shape[0], Af.shape[0], nu), dtype=np.float64)
        for u in range(nu):
            b = Af @ Bf[:, :, u] @ Af.T
            out_b[:, :, u] = np.asarray(spm_dir_norm(b), dtype=np.float64)
        idx_b = Nu + f - 1
        if idx_b >= len(mdp_out["B"]):
            raise RuntimeError(
                f"mdp.B too short for Nu+f={Nu + f} (len={len(mdp_out['B'])})"
            )
        mdp_out["B"][idx_b] = out_b

        g = id1["D"][f - 1] if f - 1 < len(id1["D"]) else None
        if m2 is not None and _id_cell_nonempty(g):
            g1 = _id_first_index_1based(g)
            a2 = np.asarray(m2["A"][g1 - 1], dtype=np.float64)
            a = Af @ a2
            m2["A"][g1 - 1] = np.asarray(spm_dir_norm(a), dtype=np.float64)
            n_parent += 1
        else:
            n_skip += 1

        # copy id.D / id.E cells (may be empty)
        d_src = id1["D"][f - 1] if f - 1 < len(id1["D"]) else np.array([])
        e_src = id1["E"][f - 1] if f - 1 < len(id1["E"]) else np.array([])
        mdp_out["id"]["D"][idx_b] = (
            np.asarray(d_src).copy() if _id_cell_nonempty(d_src) else np.array([], dtype=np.float64)
        )
        mdp_out["id"]["E"][idx_b] = (
            np.asarray(e_src).copy() if _id_cell_nonempty(e_src) else np.array([], dtype=np.float64)
        )

    meta = {
        "n_factors": nB1,
        "n_parent": n_parent,
        "n_skip_empty_idD": n_skip,
        "Nu": int(Nu),
        "packing": "idA_linked_Af",
    }
    return mdp_out, mdp_levels, meta


def run_fence_f4(
    f3_pkl: Path,
    f1_mat: Path,
    *,
    Nu: int | None = None,
) -> dict[str, Any]:
    """F4: id.A packing on F1 ``mdp`` + F3 ``MDP``, then fidelity ``spm_mdp2rdp``."""
    import pickle
    import time

    from python_src.toolbox.DEM.spm_mdp2rdp import spm_mdp2rdp
    from tests.demo1.optim2full.optim2full_signoff_env import optim2full_signoff_env
    from tests.demo1.optim2full.optim2full_timing import timing_log

    t_all0 = time.perf_counter()
    timing_log("run_fence_f4", "START")
    if not f3_pkl.is_file():
        raise FileNotFoundError(
            f"F3 pkl missing: {f3_pkl}. Run --fence-f3 export first."
        )
    if not f1_mat.is_file():
        raise FileNotFoundError(f"F1.mat missing: {f1_mat}")

    t0 = time.perf_counter()
    with f3_pkl.open("rb") as f:
        f3_blob = pickle.load(f)
    if not isinstance(f3_blob, dict) or "MDP" not in f3_blob:
        raise TypeError("F3 pkl must be dict with MDP")
    capture = str(f3_blob.get("capture") or "").strip()
    MDP_in = f3_blob["MDP"]
    if isinstance(MDP_in, list):
        mdp_levels_in = MDP_in
    else:
        arr = np.asarray(MDP_in, dtype=object).ravel(order="F")
        mdp_levels_in = [arr[i] for i in range(arr.size)]
    timing_log(
        "run_fence_f4",
        f"load_F3_pkl elapsed_s={time.perf_counter()-t0:.3f} "
        f"n_levels={len(mdp_levels_in)} capture={capture!r}",
    )

    t0 = time.perf_counter()
    mdp0 = load_f1_mdp_for_packing(f1_mat)
    nu = int(Nu if Nu is not None else int(_PG.get("Nu", 4)))
    timing_log(
        "run_fence_f4",
        f"load_F1_mdp elapsed_s={time.perf_counter()-t0:.3f} Nu={nu}",
    )

    with optim2full_signoff_env():
        t0 = time.perf_counter()
        timing_log("run_fence_f4", "pack_mdp_ida_linked START")
        mdp_p, mdp_levels, pack_meta = pack_mdp_ida_linked(
            mdp0, mdp_levels_in, Nu=nu
        )
        timing_log(
            "run_fence_f4",
            f"pack_mdp_ida_linked END elapsed_s={time.perf_counter()-t0:.3f} "
            f"parents={pack_meta['n_parent']} skip={pack_meta['n_skip_empty_idD']}",
        )

        t0 = time.perf_counter()
        timing_log("run_fence_f4", "spm_mdp2rdp START")
        # MATLAB: RDP = [{mdp} MDP(2:end)]
        cell_in = [mdp_p] + list(mdp_levels[1:])
        RDP = spm_mdp2rdp(cell_in)
        elapsed = float(time.perf_counter() - t0)
        timing_log(
            "run_fence_f4",
            f"spm_mdp2rdp END elapsed_s={elapsed:.3f}",
        )

    timing_log(
        "run_fence_f4",
        f"END total_s={time.perf_counter()-t_all0:.3f}",
    )
    return {
        "RDP": RDP,
        "capture": capture,
        "fence": "F4",
        "generate_entry": "pack_mdp_ida_linked+spm_mdp2rdp",
        "pack_meta": pack_meta,
        "mdp2rdp_elapsed_s": elapsed,
        "f3_pkl": str(f3_pkl),
        "f1_mat": str(f1_mat),
        "Nu": nu,
        "nonscalar_policy": "same_session_F1_mdp_F3_MDP_ida_pack_mdp2rdp",
    }


def export_fence_f4_pkl(
    out_pkl: Path,
    f3_pkl: Path,
    f1_mat: Path,
    *,
    Nu: int | None = None,
) -> dict[str, Any]:
    """Run F4 packing + ``spm_mdp2rdp`` and pickle the fence blob."""
    import pickle
    import time

    from tests.demo1.optim2full.optim2full_timing import timing_log

    t0 = time.perf_counter()
    timing_log("export_fence_f4_pkl", "START")
    blob = run_fence_f4(f3_pkl, f1_mat, Nu=Nu)
    out_pkl.parent.mkdir(parents=True, exist_ok=True)
    with out_pkl.open("wb") as f:
        pickle.dump(blob, f, protocol=4)
    timing_log(
        "export_fence_f4_pkl",
        f"END elapsed_s={time.perf_counter()-t0:.3f} "
        f"mdp2rdp_elapsed_s={blob.get('mdp2rdp_elapsed_s')}",
    )
    return blob


# ---------------------------------------------------------------------------
# F5 — first surveillance VB (``spm_MDP_VB_XXX`` under ``vb_1``) + ``spm_Q2mdp``
# ---------------------------------------------------------------------------


def _pack_mdp_levels_from_f3_f1(
    f3_pkl: Path,
    f1_mat: Path,
    *,
    Nu: int | None = None,
):
    """Shared F4/F5/F6 pack: F3 pkl + F1 mdp → id.A pack (no ``mdp2rdp`` yet).

    Returns ``(mdp_p, mdp_levels, pack_meta, capture, nu)``. ``mdp_p`` is the
    packed level-0 process model **before** ``spm_mdp2rdp``.
    """
    import pickle

    if not f3_pkl.is_file():
        raise FileNotFoundError(f"F3 pkl missing: {f3_pkl}. Run --fence-f3 first.")
    if not f1_mat.is_file():
        raise FileNotFoundError(f"F1.mat missing: {f1_mat}")

    with f3_pkl.open("rb") as f:
        f3_blob = pickle.load(f)
    if not isinstance(f3_blob, dict) or "MDP" not in f3_blob:
        raise TypeError("F3 pkl must be dict with MDP")
    capture = str(f3_blob.get("capture") or "").strip()
    MDP_in = f3_blob["MDP"]
    if isinstance(MDP_in, list):
        mdp_levels_in = MDP_in
    else:
        arr = np.asarray(MDP_in, dtype=object).ravel(order="F")
        mdp_levels_in = [arr[i] for i in range(arr.size)]

    mdp0 = load_f1_mdp_for_packing(f1_mat)
    nu = int(Nu if Nu is not None else int(_PG.get("Nu", 4)))
    mdp_p, mdp_levels, pack_meta = pack_mdp_ida_linked(mdp0, mdp_levels_in, Nu=nu)
    return mdp_p, mdp_levels, pack_meta, capture, nu


def _build_packed_rdp_from_f3_f1(
    f3_pkl: Path,
    f1_mat: Path,
    *,
    Nu: int | None = None,
):
    """Shared F4/F5 builder: F3 pkl + F1 mdp → id.A pack → ``spm_mdp2rdp``.

    Returns ``(RDP, mdp_p, pack_meta, capture, nu)``. ``mdp_p`` is the packed
    level-0 process model **before** ``spm_mdp2rdp`` — F5 needs ``mdp_p['id']``
    for ``QDP.id`` (MATLAB spine ``QDP.id = mdp.id``).
    """
    from python_src.toolbox.DEM.spm_mdp2rdp import spm_mdp2rdp

    mdp_p, mdp_levels, pack_meta, capture, nu = _pack_mdp_levels_from_f3_f1(
        f3_pkl, f1_mat, Nu=Nu
    )
    cell_in = [mdp_p] + list(mdp_levels[1:])
    RDP = spm_mdp2rdp(cell_in)
    return RDP, mdp_p, pack_meta, capture, nu


# Spine wayfinding goal (MATLAB ``sT = [28,12,3]``); also saved on F6.mat.
_F6_ST = np.asarray([28, 12, 3], dtype=np.float64)


def _dense_map_prior_cell(x: Any) -> np.ndarray:
    """Densify one F1 ``MAP`` place prior to a float64 column (``D`` cell)."""
    if sparse.issparse(x):
        x = x.toarray()
    a = np.asarray(x)
    # loadmat may wrap a sparse as object scalar
    if a.dtype == object and a.size == 1:
        return _dense_map_prior_cell(a.reshape(-1)[0])
    a = np.asarray(a, dtype=np.float64)
    if a.ndim == 0:
        a = a.reshape((1, 1), order="F")
    elif a.ndim == 1:
        a = a.reshape((-1, 1), order="F")
    return a


def _build_pdp_wayfinding_from_packed(
    mdp_p: dict[str, Any],
    *,
    nu: int,
    f1_mat: Path,
    sT: np.ndarray | None = None,
) -> tuple[dict[str, Any], np.ndarray, int]:
    """MATLAB spine F6: ``pdp=mdp``; ``pdp.D((1:Np)+Nu)=MAP``; ``pdp.id.hid=sT(:)``."""
    import copy

    from scipy.io import loadmat

    raw = loadmat(str(f1_mat), simplify_cells=True)
    if "MAP" not in raw or "PG" not in raw:
        raise KeyError(f"F1.mat missing MAP/PG: {f1_mat}")
    pg = raw["PG"]
    if not isinstance(pg, dict):
        raise TypeError("F1 PG must be dict")
    np_places = int(pg["Nx"]) * int(pg["Ny"]) * int(pg["Nz"])
    map_cells = np.asarray(raw["MAP"], dtype=object).reshape(-1, order="F")
    if int(map_cells.size) != np_places:
        raise RuntimeError(
            f"MAP size {map_cells.size} != Np={np_places} from PG Nx*Ny*Nz"
        )

    pdp = copy.deepcopy(mdp_p)
    D = list(pdp["D"]) if isinstance(pdp.get("D"), (list, tuple)) else [
        np.asarray(pdp["D"], dtype=object).flat[i] for i in range(np_places + nu)
    ]
    if len(D) < nu + np_places:
        raise RuntimeError(
            f"packed mdp.D len={len(D)} < Nu+Np={nu + np_places}"
        )
    for i in range(np_places):
        # MATLAB: pdp.D((1:Np)+Nu) = MAP  → 1-based Nu+i → 0-based nu+i
        D[nu + i] = _dense_map_prior_cell(map_cells[i])
    pdp["D"] = D

    st = np.asarray(_F6_ST if sT is None else sT, dtype=np.float64).reshape(-1)
    if st.size != 3:
        raise ValueError(f"sT must have 3 elements, got {st.size}")
    if "id" not in pdp or not isinstance(pdp["id"], dict):
        pdp["id"] = {}
    pdp["id"] = dict(pdp["id"])
    # MATLAB sT(:) — column
    pdp["id"]["hid"] = st.reshape((-1, 1), order="F")
    return pdp, st.copy(), np_places


def run_fence_f6(
    f3_pkl: Path,
    f1_mat: Path,
    *,
    Nu: int | None = None,
    T: int = 4,
) -> dict[str, Any]:
    """F6: pack → ``pdp`` (MAP + ``id.hid``) → ``mdp2rdp`` → ``T=4`` →
    ``spm_MDP_VB_XXX`` under ledger ``vb_2`` → ``spm_Q2mdp`` →
    ``QDP.id = pdp.id``.
    """
    import time

    from python_src.toolbox.DEM.spm_MDP_VB_XXX import (
        spm_MDP_VB_XXX,
    )
    from python_src.toolbox.DEM.spm_mdp2rdp import spm_mdp2rdp
    from python_src.toolbox.DEM.spm_Q2mdp import spm_Q2mdp
    from tests.demo1.optim2full.optim2full_rand_ledger import (
        optim2full_rand_segment_slice,
    )
    from tests.demo1.optim2full.optim2full_signoff_env import optim2full_signoff_env
    from tests.demo1.optim2full.optim2full_timing import timing_log

    t_all0 = time.perf_counter()
    timing_log("run_fence_f6", "START")

    t0 = time.perf_counter()
    mdp_p, mdp_levels, pack_meta, capture, nu = _pack_mdp_levels_from_f3_f1(
        f3_pkl, f1_mat, Nu=Nu
    )
    pdp, sT, np_places = _build_pdp_wayfinding_from_packed(
        mdp_p, nu=nu, f1_mat=f1_mat
    )
    RDP = spm_mdp2rdp([pdp] + list(mdp_levels[1:]))
    timing_log(
        "run_fence_f6",
        f"build_pdp_rdp elapsed_s={time.perf_counter()-t0:.3f} "
        f"parents={pack_meta['n_parent']} skip={pack_meta['n_skip_empty_idD']} "
        f"Np={np_places}",
    )

    # MATLAB spine: RDP.T = 4 (wayfinding horizon)
    RDP["T"] = float(T)

    vb_slice, vb_seg = optim2full_rand_segment_slice("vb_2")
    timing_log("run_fence_f6", f"vb_2 slice k={int(vb_seg.k)}")

    with optim2full_signoff_env():
        t0 = time.perf_counter()
        timing_log("run_fence_f6", "spm_MDP_VB_XXX START")
        RDP_out = spm_MDP_VB_XXX(
            RDP,
            reuse_matlab_draws_drone=True,
            matlab_rand_buf=vb_slice,
        )
        vb_elapsed = float(time.perf_counter() - t0)
        timing_log(
            "run_fence_f6",
            f"spm_MDP_VB_XXX END elapsed_s={vb_elapsed:.3f}",
        )

        t0 = time.perf_counter()
        timing_log("run_fence_f6", "spm_Q2mdp START")
        Q_rec = RDP_out["Q"] if isinstance(RDP_out, dict) else _field_get(RDP_out, "Q")
        QDP = spm_Q2mdp(Q_rec, 1)
        # MATLAB spine: QDP.id = pdp.id
        QDP["id"] = pdp["id"]
        timing_log(
            "run_fence_f6",
            f"spm_Q2mdp END elapsed_s={time.perf_counter()-t0:.3f}",
        )

    timing_log(
        "run_fence_f6",
        f"END total_s={time.perf_counter()-t_all0:.3f}",
    )
    return {
        "RDP": RDP_out,
        "QDP": QDP,
        "sT": sT,
        "capture": capture,
        "fence": "F6",
        "generate_entry": "pdp_MAP_hid+spm_mdp2rdp+spm_MDP_VB_XXX+spm_Q2mdp",
        "pack_meta": pack_meta,
        "vb_2_k": int(vb_seg.k),
        "vb_elapsed_s": vb_elapsed,
        "T": float(T),
        "Nu": nu,
        "Np": np_places,
        "f3_pkl": str(f3_pkl),
        "f1_mat": str(f1_mat),
        "nonscalar_policy": (
            "same_session_F1_mdp_F3_MDP_pack_pdp_MAP_hid_VBoptim_vb2_Q2mdp"
        ),
    }


def export_fence_f6_pkl(
    out_pkl: Path,
    f3_pkl: Path,
    f1_mat: Path,
    *,
    Nu: int | None = None,
    T: int = 4,
) -> dict[str, Any]:
    """Run F6 wayfinding VB + ``spm_Q2mdp`` and pickle the fence blob."""
    import pickle
    import time

    from tests.demo1.optim2full.optim2full_timing import timing_log

    t0 = time.perf_counter()
    timing_log("export_fence_f6_pkl", "START")
    blob = run_fence_f6(f3_pkl, f1_mat, Nu=Nu, T=T)
    out_pkl.parent.mkdir(parents=True, exist_ok=True)
    with out_pkl.open("wb") as f:
        pickle.dump(blob, f, protocol=4)
    timing_log(
        "export_fence_f6_pkl",
        f"END elapsed_s={time.perf_counter()-t0:.3f} "
        f"vb_elapsed_s={blob.get('vb_elapsed_s')}",
    )
    return blob


def build_pdp_wayfinding(
    mdp_p: dict[str, Any],
    MAP: list[Any] | np.ndarray,
    *,
    Nu: int,
    Np: int,
    sT: np.ndarray | None = None,
) -> tuple[dict[str, Any], np.ndarray]:
    """**Native** wayfinding priors: ``pdp.D((1:Np)+Nu)=MAP``; ``pdp.id.hid=sT``.

    Parity F6 keeps ``_build_pdp_wayfinding_from_packed(..., f1_mat=...)``.
    """
    import copy

    map_cells = (
        list(MAP)
        if isinstance(MAP, (list, tuple))
        else list(np.asarray(MAP, dtype=object).reshape(-1, order="F"))
    )
    if int(len(map_cells)) != int(Np):
        raise RuntimeError(f"MAP len {len(map_cells)} != Np={Np}")

    pdp = copy.deepcopy(mdp_p)
    D = list(pdp["D"]) if isinstance(pdp.get("D"), (list, tuple)) else [
        np.asarray(pdp["D"], dtype=object).flat[i] for i in range(Np + Nu)
    ]
    if len(D) < Nu + Np:
        raise RuntimeError(f"packed mdp.D len={len(D)} < Nu+Np={Nu + Np}")
    for i in range(Np):
        D[Nu + i] = _dense_map_prior_cell(map_cells[i])
    pdp["D"] = D

    st = np.asarray(_F6_ST if sT is None else sT, dtype=np.float64).reshape(-1)
    if st.size != 3:
        raise ValueError(f"sT must have 3 elements, got {st.size}")
    if "id" not in pdp or not isinstance(pdp["id"], dict):
        pdp["id"] = {}
    pdp["id"] = dict(pdp["id"])
    pdp["id"]["hid"] = st.reshape((-1, 1), order="F")
    return pdp, st.copy()


def run_dem_drone_vi_native(
    *,
    seed: int = 1,
    T_surveillance: int = 16,
    T_wayfinding: int = 4,
    sT: np.ndarray | None = None,
    rgm_time_segments: bool = False,
    do_plot: bool | None = None,
) -> dict[str, Any]:
    """**OPTIM2FULL Python-native** full ``DEM_drone_VI`` compute spine.

    Script order ~L49–495. **No** F*.mat injects, **no** scalar ledger, **no**
    F2 ``G`` override, **no** ``reuse_matlab_draws_drone``.

    When ``do_plot`` is True (or ``RGMS_OPTIM2FULL_NATIVE_PLOT=1``), writes six
    final-frame PNGs via library ``dem_drone_vi_plot_*`` under
    ``visualizations/optim2full_native/`` (L4 — not MATLAB plot oracles).

    Parity fence runners (``run_fence_f*``) are a separate lane — do not call them
    from this path.

    Prints ``[native]`` START/END lines for every significant segment (flush) so
    long FSL/VB walls are observable live. Set ``RGMS_OPTIM2FULL_FSL_TIMING=1``
    for finer FSL internal ``[fsl_timing]`` lines. Set ``rgm_time_segments=True``
    for live ``[rgm_timing]`` inside ``spm_rgm_group`` (OPTIM2FULL FSL profiling).
    """
    import copy
    import time
    from datetime import datetime

    from python_src.toolbox.DEM.spm_faster_structure_learning import (
        spm_faster_structure_learning,
    )
    from python_src.toolbox.DEM.spm_MDP_generate import (
        spm_MDP_generate,
    )
    from python_src.toolbox.DEM.spm_MDP_VB_XXX import (
        spm_MDP_VB_XXX,
    )
    from python_src.toolbox.DEM.optim2full_native_plot import (
        NativePlotSession,
        mdp_fsl_end,
        optim2full_native_plot_requested,
    )
    from python_src.toolbox.DEM.spm_mdp_a2A import spm_mdp_a2A
    from python_src.toolbox.DEM.spm_mdp2rdp import spm_mdp2rdp
    from python_src.toolbox.DEM.spm_Q2mdp import spm_Q2mdp

    plot_enabled = (
        bool(do_plot)
        if do_plot is not None
        else optim2full_native_plot_requested()
    )
    plot_sess = NativePlotSession() if plot_enabled else None

    t_all0 = time.perf_counter()
    timing: dict[str, float] = {}

    def _ts() -> str:
        return datetime.now().strftime("%H:%M:%S")

    def _cum() -> float:
        return float(time.perf_counter() - t_all0)

    def _seg_start(name: str, detail: str = "") -> float:
        extra = f" {detail}" if detail else ""
        print(
            f"[native] {_ts()} START {name}{extra} cum_s={_cum():.1f}",
            flush=True,
        )
        return time.perf_counter()

    def _seg_end(name: str, t0: float, detail: str = "") -> float:
        dt = float(time.perf_counter() - t0)
        timing[name] = dt
        extra = f" {detail}" if detail else ""
        print(
            f"[native] {_ts()} END   {name}{extra} "
            f"elapsed_s={dt:.3f} cum_s={_cum():.1f}",
            flush=True,
        )
        return dt

    print(
        f"[native] {_ts()} BEGIN seed={int(seed)} "
        f"T_s={int(T_surveillance)} T_w={int(T_wayfinding)} "
        f"rgm_time_segments={bool(rgm_time_segments)} "
        f"do_plot={bool(plot_enabled)}",
        flush=True,
    )

    np.random.seed(int(seed))

    Nx = Ny = 32
    Nz = 8
    Nd = 16
    Nc = 8
    Nr = 16
    Na = 12
    No = 1
    Nu = 4
    Ns = 6

    t0 = _seg_start("unity", f"Nx={Nx} Ny={Ny} Nz={Nz} Nc={Nc}")
    _D_vox, W = spm_drone_unity(Nx, Ny, Nz, Nc)
    MAP = map_from_drone_D(_D_vox)
    _seg_end("unity", t0, f"MAP_len={len(MAP)} W={tuple(W.shape)}")
    if plot_sess is not None:
        plot_sess.write(
            "true_env_early",
            {
                "MAP": MAP,
                "W": W,
                "Nx": Nx,
                "Ny": Ny,
                "Nz": Nz,
                "Nc": Nc,
            },
        )

    t0 = _seg_start("assemble", "mdp+GDP from scene (no F*.mat)")
    scene = scene_dict_from_unity_sizes(
        Nx=Nx,
        Ny=Ny,
        Nz=Nz,
        Nd=Nd,
        Nc=Nc,
        Nr=Nr,
        Na=Na,
        No=No,
        Nu=Nu,
        Ns=Ns,
        W=W,
    )
    built = assemble_mdp_and_gdp_from_scene(scene)
    mdp0 = built["mdp"]
    GDP = built["GDP"]
    PG = built["PG"]
    Np = int(built["Np"])
    _seg_end("assemble", t0, f"Np={Np}")

    t0 = _seg_start("generate", "spm_MDP_generate (no ledger)")
    PDP = spm_MDP_generate(GDP)
    _seg_end("generate", t0, f"T={int(PDP['T'])}")

    t0 = _seg_start("assemble_Q", f"from PDP.s Nu={Nu} No={No} Np={Np}")
    Q = assemble_Q_from_pdp(PDP, PG, Nu, No, Np)
    _seg_end("assemble_Q", t0, f"Q_rows={len(Q)}")
    if plot_sess is not None:
        plot_sess.write(
            "true_scene_post_generate",
            {"Q": Q, "PG": PG},
        )

    t0 = _seg_start(
        "fsl",
        "spm_faster_structure_learning (no G override; may be tens of min)",
    )
    S = np.asarray([Nx, Ny, Nz], dtype=np.float64)
    dx = np.asarray([1.0, 64.0], dtype=np.float64)
    # Native: no rgm_group_override_fn (parity F2 uses dump-once G)
    MDP_fsl = spm_faster_structure_learning(
        Q, S, dx, rgm_time_segments=bool(rgm_time_segments)
    )
    n_lev = (
        len(MDP_fsl)
        if isinstance(MDP_fsl, list)
        else int(np.asarray(MDP_fsl, dtype=object).size)
    )
    _seg_end("fsl", t0, f"n_levels={n_lev}")
    if plot_sess is not None:
        plot_sess.write("mdp_params", {"MDP_end": mdp_fsl_end(MDP_fsl)})

    t0 = _seg_start("a2A", "spm_mdp_a2A")
    MDP_a2A = spm_mdp_a2A(_mdp_levels_for_a2A(MDP_fsl))
    _seg_end("a2A", t0)

    t0 = _seg_start("pack_ida", "pack_mdp_ida_linked(live mdp)")
    if isinstance(MDP_a2A, list):
        mdp_levels_in = MDP_a2A
    else:
        arr = np.asarray(MDP_a2A, dtype=object).ravel(order="F")
        mdp_levels_in = [arr[i] for i in range(arr.size)]
    mdp_p, mdp_levels, pack_meta = pack_mdp_ida_linked(
        mdp0, mdp_levels_in, Nu=Nu
    )
    _seg_end(
        "pack_ida",
        t0,
        f"parents={pack_meta.get('n_parent')} skip={pack_meta.get('n_skip_empty_idD')}",
    )

    t0 = _seg_start("mdp2rdp_surveillance", "spm_mdp2rdp")
    RDP = spm_mdp2rdp([mdp_p] + list(mdp_levels[1:]))
    _seg_end("mdp2rdp_surveillance", t0)

    t0 = _seg_start(
        "vb_surveillance",
        f"spm_MDP_VB_XXX T={int(T_surveillance)} (no ledger)",
    )
    RDP["T"] = float(T_surveillance)
    # Native VB: defaults (reuse_matlab_draws_drone=False)
    RDP_s = spm_MDP_VB_XXX(RDP)
    _seg_end("vb_surveillance", t0)
    if plot_sess is not None:
        plot_sess.write("rgm", {"RDP": RDP_s})

    t0 = _seg_start("q2mdp_surveillance", "spm_Q2mdp")
    Q_rec = RDP_s["Q"] if isinstance(RDP_s, dict) else _field_get(RDP_s, "Q")
    QDP_s = spm_Q2mdp(Q_rec, 1)
    QDP_s["id"] = mdp_p["id"]
    _seg_end("q2mdp_surveillance", t0)
    if plot_sess is not None:
        plot_sess.write(
            "active_inference",
            {"QDP": QDP_s, "PG": PG},
        )

    t0 = _seg_start("wayfinding_pdp", "MAP priors + id.hid=sT")
    pdp, sT_out = build_pdp_wayfinding(
        mdp_p, MAP, Nu=Nu, Np=Np, sT=sT
    )
    _seg_end("wayfinding_pdp", t0, f"sT={sT_out.ravel().tolist()}")

    t0 = _seg_start("mdp2rdp_wayfinding", "spm_mdp2rdp")
    # Reuse post-pack higher levels (MATLAB MDP(2:end) after first pack)
    RDP_w = spm_mdp2rdp([pdp] + list(copy.deepcopy(mdp_levels[1:])))
    _seg_end("mdp2rdp_wayfinding", t0)

    t0 = _seg_start(
        "vb_wayfinding",
        f"spm_MDP_VB_XXX T={int(T_wayfinding)} (no ledger)",
    )
    RDP_w["T"] = float(T_wayfinding)
    RDP_w = spm_MDP_VB_XXX(RDP_w)
    _seg_end("vb_wayfinding", t0)

    t0 = _seg_start("q2mdp_wayfinding", "spm_Q2mdp")
    Q_rec_w = RDP_w["Q"] if isinstance(RDP_w, dict) else _field_get(RDP_w, "Q")
    QDP_w = spm_Q2mdp(Q_rec_w, 1)
    QDP_w["id"] = pdp["id"]
    _seg_end("q2mdp_wayfinding", t0)
    if plot_sess is not None:
        plot_sess.write(
            "wayfinding",
            {"QDP": QDP_w, "PG": PG, "sT": sT_out},
        )

    timing["total"] = float(time.perf_counter() - t_all0)
    print(
        f"[native] {_ts()} DONE total_s={timing['total']:.3f}",
        flush=True,
    )
    out: dict[str, Any] = {
        "lane": "native",
        "seed": int(seed),
        "W": W,
        "MAP": MAP,
        "PG": PG,
        "mdp": mdp0,
        "GDP": GDP,
        "PDP": PDP,
        "Q": Q,
        "MDP_fsl": MDP_fsl,
        "MDP_a2A": MDP_a2A,
        "mdp_packed": mdp_p,
        "mdp_levels": mdp_levels,
        "pack_meta": pack_meta,
        "RDP_surveillance": RDP_s,
        "QDP_surveillance": QDP_s,
        "RDP_wayfinding": RDP_w,
        "QDP_wayfinding": QDP_w,
        "pdp": pdp,
        "sT": sT_out,
        "Nx": Nx,
        "Ny": Ny,
        "Nz": Nz,
        "Nc": Nc,
        "Nu": Nu,
        "No": No,
        "Np": Np,
        "timing_s": timing,
    }
    if plot_sess is not None:
        plot_meta = plot_sess.meta()
        out["2full_native_plot"] = plot_meta
        print(
            f"[native] {_ts()} plots png_count={plot_meta['png_count']} "
            f"out_dir={plot_meta['out_dir']}",
            flush=True,
        )
    return out


def _field_get(obj: Any, name: str) -> Any:
    if isinstance(obj, dict):
        return obj[name]
    return getattr(obj, name)


def run_fence_f5(
    f3_pkl: Path,
    f1_mat: Path,
    *,
    Nu: int | None = None,
    T: int = 16,
) -> dict[str, Any]:
    """F5: pack (F4 build) → ``T=16`` → ``spm_MDP_VB_XXX`` under ledger
    ``vb_1`` drone replay → ``spm_Q2mdp`` → attach ``QDP.id = mdp_p.id``.
    """
    import time

    from python_src.toolbox.DEM.spm_MDP_VB_XXX import (
        spm_MDP_VB_XXX,
    )
    from python_src.toolbox.DEM.spm_Q2mdp import spm_Q2mdp
    from tests.demo1.optim2full.optim2full_rand_ledger import (
        optim2full_rand_segment_slice,
    )
    from tests.demo1.optim2full.optim2full_signoff_env import optim2full_signoff_env
    from tests.demo1.optim2full.optim2full_timing import timing_log

    t_all0 = time.perf_counter()
    timing_log("run_fence_f5", "START")

    t0 = time.perf_counter()
    RDP, mdp_p, pack_meta, capture, nu = _build_packed_rdp_from_f3_f1(
        f3_pkl, f1_mat, Nu=Nu
    )
    timing_log(
        "run_fence_f5",
        f"build_rdp elapsed_s={time.perf_counter()-t0:.3f} "
        f"parents={pack_meta['n_parent']} skip={pack_meta['n_skip_empty_idD']}",
    )

    # MATLAB spine: RDP.T = 16 (surveillance horizon)
    RDP["T"] = float(T)

    vb_slice, vb_seg = optim2full_rand_segment_slice("vb_1")
    timing_log("run_fence_f5", f"vb_1 slice k={int(vb_seg.k)}")

    with optim2full_signoff_env():
        t0 = time.perf_counter()
        timing_log("run_fence_f5", "spm_MDP_VB_XXX START")
        RDP_out = spm_MDP_VB_XXX(
            RDP,
            reuse_matlab_draws_drone=True,
            matlab_rand_buf=vb_slice,
        )
        vb_elapsed = float(time.perf_counter() - t0)
        timing_log(
            "run_fence_f5",
            f"spm_MDP_VB_XXX END elapsed_s={vb_elapsed:.3f}",
        )

        t0 = time.perf_counter()
        timing_log("run_fence_f5", "spm_Q2mdp START")
        Q_rec = RDP_out["Q"] if isinstance(RDP_out, dict) else _field_get(RDP_out, "Q")
        QDP = spm_Q2mdp(Q_rec, 1)
        # MATLAB spine: QDP.id = mdp.id (packed pre-mdp2rdp process model id)
        QDP["id"] = mdp_p["id"]
        timing_log(
            "run_fence_f5",
            f"spm_Q2mdp END elapsed_s={time.perf_counter()-t0:.3f}",
        )

    timing_log(
        "run_fence_f5",
        f"END total_s={time.perf_counter()-t_all0:.3f}",
    )
    return {
        "RDP": RDP_out,
        "QDP": QDP,
        "capture": capture,
        "fence": "F5",
        "generate_entry": "spm_MDP_VB_XXX+spm_Q2mdp",
        "pack_meta": pack_meta,
        "vb_1_k": int(vb_seg.k),
        "vb_elapsed_s": vb_elapsed,
        "T": float(T),
        "Nu": nu,
        "f3_pkl": str(f3_pkl),
        "f1_mat": str(f1_mat),
        "nonscalar_policy": "same_session_F1_mdp_F3_MDP_pack_VBoptim_vb1_Q2mdp",
    }


def export_fence_f5_pkl(
    out_pkl: Path,
    f3_pkl: Path,
    f1_mat: Path,
    *,
    Nu: int | None = None,
    T: int = 16,
) -> dict[str, Any]:
    """Run F5 VB + ``spm_Q2mdp`` and pickle the fence blob."""
    import pickle
    import time

    from tests.demo1.optim2full.optim2full_timing import timing_log

    t0 = time.perf_counter()
    timing_log("export_fence_f5_pkl", "START")
    blob = run_fence_f5(f3_pkl, f1_mat, Nu=Nu, T=T)
    out_pkl.parent.mkdir(parents=True, exist_ok=True)
    with out_pkl.open("wb") as f:
        pickle.dump(blob, f, protocol=4)
    timing_log(
        "export_fence_f5_pkl",
        f"END elapsed_s={time.perf_counter()-t0:.3f} "
        f"vb_elapsed_s={blob.get('vb_elapsed_s')}",
    )
    return blob
