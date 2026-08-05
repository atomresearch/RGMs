#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DEM_AtariIII — native Python script walk matching ``DEM_AtariIII.m``.

Adapted from ``tests/demo1/optim1full/COLAB1.py`` (COLAB1 cell markers retained
for notebook lineage). Library imports/calls use only live
``python_src.toolbox.DEM`` MATLAB-matching names (no ``python_src.optimized``,
no ``*_optim``, no ``python_src.fidelity``).

Staged-ledger / spine API: ``python_src.toolbox.DEM.run_dem_atariiii`` — not this file.

Run (conda ``rgms``)::

    python python_src/toolbox/DEM/DEM_AtariIII.py
"""
from __future__ import annotations

import copy
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# =============================================================================
# COLAB1 Cell 0 — setup (local: no git clone / pip; all imports here)
# =============================================================================
_t_script0 = time.perf_counter()
_t_cell0 = time.perf_counter()

REPO = Path(__file__).resolve().parents[3]
assert REPO.is_dir(), f"missing repo: {REPO}"
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

os.environ.setdefault("MPLBACKEND", "Agg")
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from python_src.toolbox.DEM.native_driver_rng import seed_native_driver_rng
from python_src.toolbox.DEM.spm_MDP_pong import spm_MDP_pong
from python_src.toolbox.DEM.spm_MDP_generate import spm_MDP_generate
from python_src.toolbox.DEM.dem_atariiii_plot_gameplay import dem_atariiii_plot_gameplay
from python_src.toolbox.DEM.spm_faster_structure_learning import (
    spm_faster_structure_learning,
)
from python_src.toolbox.DEM.spm_merge_structure_learning import (
    spm_merge_structure_learning,
)
from python_src.toolbox.DEM.spm_RDP_basin import spm_RDP_basin
from python_src.toolbox.DEM.dem_atariiii_plot_attractors_basin import (
    dem_atariiii_plot_attractors_basin,
)
from python_src.toolbox.DEM.spm_RDP_sort import spm_RDP_sort
from python_src.toolbox.DEM.spm_set_goals import spm_set_goals
from python_src.toolbox.DEM.dem_atariiii_plot_attractors_mdp_post_sort import (
    dem_atariiii_plot_attractors_mdp_post_sort,
)
from python_src.toolbox.DEM.spm_set_costs import spm_set_costs
from python_src.toolbox.DEM.spm_mdp2rdp import spm_mdp2rdp
from python_src.toolbox.DEM.spm_MDP_VB_XXX import spm_MDP_VB_XXX
from python_src.toolbox.DEM.dem_atariiii_plot_generative_ai import (
    dem_atariiii_plot_generative_ai,
)
from python_src.toolbox.DEM.dem_atariiii_structure_learning_f import (
    structure_learning_f_column,
)
from python_src.toolbox.DEM.dem_atariiii_plot_active_inference_nr import (
    dem_atariiii_plot_active_inference_nr,
)
from python_src.toolbox.DEM.dem_atariiii_plot_structure_learning import (
    dem_atariiii_plot_structure_learning,
)
from python_src.toolbox.DEM.dem_atariiii_plot_before_compression_rgb import (
    dem_atariiii_plot_before_compression_rgb,
)
from python_src.toolbox.DEM.dem_atariiii_plot_orbits_before import (
    dem_atariiii_plot_orbits_before,
)
from python_src.toolbox.DEM.spm_RDP_MI import spm_RDP_MI
from python_src.toolbox.DEM.dem_atariiii_plot_with_compression_rgb import (
    dem_atariiii_plot_with_compression_rgb,
)
from python_src.toolbox.DEM.dem_atariiii_plot_orbits_after import (
    dem_atariiii_plot_orbits_after,
)
from python_src.toolbox.DEM.dem_atariiii_post12 import count_mdp_parameters

for name in ("baseball.png", "bat.png"):
    p = REPO / "matlab_src" / "toolbox" / "DEM" / name
    assert p.is_file(), f"missing DEM asset {p}"

out_dir = REPO / "visualizations" / "DEM_AtariIII"
out_dir.mkdir(parents=True, exist_ok=True)
_cell_walls: dict[str, float] = {}
_cell_walls["0"] = time.perf_counter() - _t_cell0
print("COLAB1 Cell 0 OK", "repo=", REPO, f"wall_s={_cell_walls['0']:.3f}", flush=True)

# =============================================================================
# COLAB1 Cell 1 — DEM_AtariIII.m ~51–65
# =============================================================================
_t_cell = time.perf_counter()
seed = seed_native_driver_rng()
print("native RNG seed=", seed, flush=True)

Nr = 12
Nc = 9
Sc = 9
Nd = 4
C = 32

GDP, _hid, _cid, _con, RGB, _nP = spm_MDP_pong(Nr, Nc, Nd, 1, 0)
_cell_walls["1"] = time.perf_counter() - _t_cell
print(
    "Cell 1 OK",
    "GDP keys sample=",
    list(GDP.keys())[:8],
    "RGB type=",
    type(RGB),
    f"wall_s={_cell_walls['1']:.3f}",
    flush=True,
)

# =============================================================================
# COLAB1 Cell 2 — DEM_AtariIII.m ~67–86
# =============================================================================
_t_cell = time.perf_counter()
S = np.ones((4, 3), dtype=np.float64)
S[0, :] = [float(Nr), float(Nc), 1.0]


def spm_get_hits(o, id_):
    """MATLAB: find(o(id.reward,:) > 1) — 1-based time indices."""
    ridx = int(np.asarray(id_["reward"], dtype=np.int64).ravel()[0]) - 1
    return (np.flatnonzero(np.asarray(o[ridx, :], dtype=np.float64) > 1.0) + 1).astype(
        np.int64
    )


def spm_get_miss(o, id_):
    """MATLAB: find(o(id.contraint,:) > 1) — note SPM spelling contraint."""
    cidx = int(np.asarray(id_["contraint"], dtype=np.int64).ravel()[0]) - 1
    return (np.flatnonzero(np.asarray(o[cidx, :], dtype=np.float64) > 1.0) + 1).astype(
        np.int64
    )


GDP = copy.deepcopy(GDP)
GDP["tau"] = 1.0
GDP["T"] = 10000.0
print("Cell 2: calling spm_MDP_generate (T=10000) …", flush=True)
PDP = spm_MDP_generate(GDP)
assert isinstance(PDP, dict), type(PDP)
assert "O" in PDP and "o" in PDP and "id" in PDP
_cell_walls["2"] = time.perf_counter() - _t_cell
print(
    "Cell 2 OK",
    "S.shape=",
    S.shape,
    "PDP.T=",
    PDP.get("T"),
    "o.shape=",
    np.asarray(PDP["o"]).shape,
    "O streams×?",
    len(PDP["O"]),
    f"wall_s={_cell_walls['2']:.3f}",
    flush=True,
)

# =============================================================================
# COLAB1 Cell 3 — DEM_AtariIII.m ~88–97 (final frame only)
# =============================================================================
_t_cell = time.perf_counter()
png_path = out_dir / "AtariIII_colab1_dem_gameplay.png"
plot_ctx = {"RGB": RGB}
frame_rgb, control, written = dem_atariiii_plot_gameplay(
    PDP, plot_ctx, t=128, save_png=True, png_path=png_path
)
plt.show()
assert written is not None and Path(written).is_file(), written
_cell_walls["3"] = time.perf_counter() - _t_cell
print(
    "Cell 3 OK",
    "png=",
    written,
    "frame_rgb.shape=",
    getattr(frame_rgb, "shape", None),
    "control.shape=",
    getattr(control, "shape", None),
    f"wall_s={_cell_walls['3']:.3f}",
    flush=True,
)

# =============================================================================
# COLAB1 Cell 4 — DEM_AtariIII.m ~99–134
# =============================================================================
_t_cell = time.perf_counter()
O_1000 = [[row[t] for t in range(1000)] for row in PDP["O"]]
print("Cell 4: spm_faster_structure_learning (O(:,1:1000), S, Sc) …", flush=True)
MDP = spm_faster_structure_learning(O_1000, S, Sc)

Nm = len(MDP)
Ne = max(2 ** (Nm - 1), 1)
_EMPTY = np.zeros((0, 0), dtype=np.float64)
for n in range(Nm):
    for g in range(len(MDP[n]["a"])):
        MDP[n]["a"][g] = _EMPTY.copy()
    for f in range(len(MDP[n]["b"])):
        MDP[n]["b"][f] = _EMPTY.copy()

r = spm_get_hits(PDP["o"], GDP["id"])
c = spm_get_miss(PDP["o"], GDP["id"])
print("Cell 4: merge rewarded windows … n_hits=", len(r), "Ne=", Ne, flush=True)

n_merged = 0
for i in range(len(r)):
    ri = int(r[i])
    prev = c[c < ri]
    if prev.size == 0:
        continue
    s0 = int(prev[-1])
    t = np.arange(s0 + Ne, ri + Ne + 1, dtype=np.int64)
    if t.size == 0:
        continue
    for s in range(1, Ne + 1):
        cols = (t + int(s)).astype(np.int64)
        O_seg = [
            [PDP["O"][g][int(col) - 1] for col in cols.tolist()]
            for g in range(len(PDP["O"]))
        ]
        MDP = spm_merge_structure_learning(O_seg, MDP)
        n_merged += 1

_cell_walls["4"] = time.perf_counter() - _t_cell
print(
    "Cell 4 OK",
    "Nm=",
    Nm,
    "Ne=",
    Ne,
    "n_hits=",
    len(r),
    "n_miss=",
    len(c),
    "n_merge_calls=",
    n_merged,
    "deep_b_cols=",
    np.asarray(MDP[Nm - 1]["b"][0]).shape if MDP[Nm - 1].get("b") else None,
    f"wall_s={_cell_walls['4']:.3f}",
    flush=True,
)

# =============================================================================
# COLAB1 Cell 5 — DEM_AtariIII.m ~136–177
# =============================================================================
_t_cell = time.perf_counter()


def _b1_matrix(mdp_level):
    """MATLAB MDP{Nm}.b{1} — unwrap one-cell wrappers if present."""
    b = mdp_level["b"][0]
    if isinstance(b, (list, tuple)):
        b = b[0]
    return np.asarray(b, dtype=np.float64)


NT = 100
NS, NU, NA, NO, NH = [], [], [], [], []
print("Cell 5: basin training loop (up to 128; early break when all(d)) …", flush=True)
for i in range(1, 129):
    offset = int(np.remainder(i, 100 - 1)) * NT
    t = np.arange(0, NT + Ne + 1, dtype=np.int64) + offset
    for s in range(1, Ne + 1):
        cols = (t + int(s)).astype(np.int64)
        O_seg = [
            [PDP["O"][g][int(col) - 1] for col in cols.tolist()]
            for g in range(len(PDP["O"]))
        ]
        MDP = spm_merge_structure_learning(O_seg, MDP)
    MDP, d, o, h, _c = spm_RDP_basin(MDP, [2, 3], [float(C), -float(C)])
    b1 = _b1_matrix(MDP[Nm - 1])
    NS.append(int(b1.shape[1]) if b1.ndim >= 2 else 1)
    NU.append(int(b1.shape[2]) if b1.ndim >= 3 else 1)
    NA.append(int(np.sum(~np.asarray(d, dtype=bool).ravel())))
    NO.append(int(np.sum(~np.asarray(o, dtype=bool).ravel())))
    NH.append(int(np.asarray(h, dtype=np.int64).ravel().size))
    if i == 1 or i % 8 == 0:
        print(
            f"  i={i} NS={NS[-1]} NU={NU[-1]} NA={NA[-1]} NO={NO[-1]} NH={NH[-1]}",
            flush=True,
        )
    if np.all(np.asarray(d, dtype=bool).ravel()):
        print(f"  break at i={i} (all deep states transient)", flush=True)
        break

png_path = out_dir / "AtariIII_colab1_dem_attractors_basin.png"
series = {"NS": NS, "NU": NU, "NA": NA, "NO": NO, "NH": NH}
*_ser, written = dem_atariiii_plot_attractors_basin(
    series, {"RGB": RGB, "GDP": GDP, "Nm": Nm}, save_png=True, png_path=png_path
)
plt.show()
assert written is not None and Path(written).is_file(), written
_cell_walls["5"] = time.perf_counter() - _t_cell
print(
    "Cell 5 OK",
    "n_iters=",
    len(NS),
    "final NS/NU/NA/NO/NH=",
    NS[-1],
    NU[-1],
    NA[-1],
    NO[-1],
    NH[-1],
    "png=",
    written,
    f"wall_s={_cell_walls['5']:.3f}",
    flush=True,
)

# =============================================================================
# COLAB1 Cell 6 — DEM_AtariIII.m ~179–206
# =============================================================================
_t_cell = time.perf_counter()
print("Cell 6: spm_RDP_sort …", flush=True)
MDP, _j = spm_RDP_sort(MDP)
Nm = len(MDP)
MDP = spm_set_goals(MDP, [2, 3], [float(C), -float(C)])
hid = MDP[Nm - 1]["id"].get("hid", [])
hid = np.asarray(hid, dtype=np.int64).ravel()
b0 = MDP[Nm - 1]["b"][0]
b1 = np.asarray(b0[0] if isinstance(b0, list) else b0, dtype=np.float64)
png_path = out_dir / "AtariIII_colab1_dem_attractors_mdp_post_sort.png"
u, I, HID, written = dem_atariiii_plot_attractors_mdp_post_sort(
    {"b1": b1, "hid": hid},
    {"RGB": RGB, "GDP": GDP, "Nm": Nm},
    save_png=True,
    png_path=png_path,
    eig=None,
    svd=None,
)
plt.show()
assert written is not None and Path(written).is_file(), written
_cell_walls["6"] = time.perf_counter() - _t_cell
print(
    "Cell 6 OK",
    "Nm=",
    Nm,
    "b1.shape=",
    b1.shape,
    "n_hid=",
    hid.size,
    "I.shape=",
    getattr(I, "shape", None),
    "png=",
    written,
    f"wall_s={_cell_walls['6']:.3f}",
    flush=True,
)

# =============================================================================
# COLAB1 Cell 7 — DEM_AtariIII.m ~208–229
# =============================================================================
_t_cell = time.perf_counter()
print("Cell 7: assemble RDP …", flush=True)
RDP = spm_set_goals(copy.deepcopy(MDP), [2, 3], [float(C), -float(C)])
RDP = spm_set_costs(RDP, [2, 3], [float(C), -float(C)])
RDP = spm_mdp2rdp(RDP)
RDP["T"] = 64.0
print("Cell 7: spm_MDP_VB_XXX (generative, T=64) …", flush=True)
PDP = spm_MDP_VB_XXX(RDP)
png_path = out_dir / "AtariIII_colab1_dem_generative_ai.png"
plot_ctx = {"RGB": RGB, "GDP": GDP, "Nm": Nm}
J, K, h_hits, written = dem_atariiii_plot_generative_ai(
    PDP, plot_ctx, save_png=True, png_path=png_path
)
plt.show()
assert written is not None and Path(written).is_file(), written
_cell_walls["7"] = time.perf_counter() - _t_cell
print(
    "Cell 7 OK",
    "RDP.T=",
    RDP.get("T"),
    "PDP keys has Q=",
    "Q" in PDP,
    "n_hits=",
    len(np.asarray(h_hits).ravel()),
    "png=",
    written,
    f"wall_s={_cell_walls['7']:.3f}",
    flush=True,
)

# =============================================================================
# COLAB1 Cell 8 — DEM_AtariIII.m ~232–325
# =============================================================================
_t_cell = time.perf_counter()


def _q_o_level1_cells(pdp):
    """MATLAB PDP.Q.O{1} as list-of-stream rows for merge."""
    q = pdp["Q"]
    level1 = q.get("O", q.get("o"))[0]
    out = []
    for row in level1:
        r = []
        for col in row:
            arr = np.asarray(col, dtype=np.float64)
            if arr.ndim == 1:
                arr = arr.reshape((-1, 1), order="F")
            elif arr.ndim == 0:
                arr = np.reshape(arr, (1, 1), order="F")
            r.append(arr)
        out.append(r)
    return out


MDP = copy.deepcopy(MDP)
MDP[0]["GA"] = GDP["A"]
MDP[0]["GB"] = GDP["B"]
MDP[0]["GU"] = GDP["U"]
MDP[0]["GD"] = GDP["D"]
MDP[0]["ID"] = GDP["id"]
MDP[0]["chi"] = 512.0

NT = 256
NR = 32
NS = 256
Nm = len(MDP)
F_cols = []
plot_ctx = {"RGB": RGB, "GDP": GDP, "Nm": Nm}
vb_secs: list[float] = []

print(f"Cell 8: NR loop {NR} games, T=floor(NT/Ne)={NT // Ne} …", flush=True)
for i in range(1, NR + 1):
    t0 = time.perf_counter()

    RDP = spm_set_goals(MDP, [2, 3], [float(C), -float(C)])
    RDP = spm_set_costs(RDP, [2, 3], [float(C), -float(C)])
    RDP = spm_mdp2rdp(RDP, 0, 1.0 / float(NS))
    RDP["T"] = float(int(NT / Ne))

    xxx_start_time = datetime.now()
    PDP = spm_MDP_VB_XXX(RDP, {})
    vb_dt = (datetime.now() - xxx_start_time).total_seconds()
    vb_secs.append(vb_dt)
    print(f"i={i}: spm_MDP_VB_XXX runtime = {datetime.now() - xxx_start_time}", flush=True)

    F_cols.append(structure_learning_f_column(PDP, MDP, GDP["id"]))

    if i == NR:
        png_ai = out_dir / "AtariIII_colab1_dem_active_inference_nr.png"
        dem_atariiii_plot_active_inference_nr(
            PDP, plot_ctx, save_png=True, png_path=png_ai
        )
        plt.show()
        print("  active-inference PNG=", png_ai, flush=True)

    O = _q_o_level1_cells(PDP)
    t = np.arange(0, NT - Ne + 1, dtype=np.int64)
    for s in range(1, Ne + 1):
        cols = (t + int(s)).astype(np.int64)
        O_seg = [[O[g][int(c) - 1] for c in cols.tolist()] for g in range(len(O))]
        mfsl_start_time = datetime.now()
        MDP = spm_merge_structure_learning(O_seg, MDP)
        print(
            f"i={i},s={s}: spm_merge_structure_learning runtime = "
            f"{datetime.now() - mfsl_start_time}",
            flush=True,
        )
    rbs_start_time = datetime.now()
    MDP, *_ = spm_RDP_basin(MDP, [2, 3], [float(C), -float(C)])
    print(f"i={i}: spm_RDP_basin runtime = {datetime.now() - rbs_start_time}", flush=True)
    print(
        f"  game {i}/{NR} wall_s={time.perf_counter() - t0:.1f} F4_hits={F_cols[-1][3]}",
        flush=True,
    )

F = np.column_stack(F_cols)
png_sl = out_dir / "AtariIII_colab1_dem_structure_learning.png"
dem_atariiii_plot_structure_learning(
    {"F": F}, plot_ctx, save_png=True, png_path=png_sl, nt=NT
)
plt.show()
_cell_walls["8"] = time.perf_counter() - _t_cell
vb_mean = float(np.mean(vb_secs)) if vb_secs else float("nan")
vb_med = float(np.median(vb_secs)) if vb_secs else float("nan")
print(
    "Cell 8 OK",
    "F.shape=",
    F.shape,
    "last hits=",
    F[3, -1],
    "png_structure=",
    png_sl,
    f"wall_s={_cell_walls['8']:.3f}",
    flush=True,
)
print(
    f"[COLAB1 local] Cell 8 VB_ONLY n={len(vb_secs)} "
    f"mean_s={vb_mean:.3f} median_s={vb_med:.3f} "
    f"min_s={min(vb_secs):.3f} max_s={max(vb_secs):.3f}",
    flush=True,
)

# =============================================================================
# COLAB1 Cell 9 — DEM_AtariIII.m ~327–373 (before compression)
# =============================================================================
_t_cell = time.perf_counter()
Nm = len(MDP)
plot_ctx = {"RGB": RGB, "GDP": GDP, "Nm": Nm}
print("Cell 9: assemble before-compression RDP …", flush=True)
RDP, _j = spm_RDP_sort(MDP)
RDP = spm_set_goals(RDP, [2, 3], [float(C), -float(C)])
RDP = spm_set_costs(RDP, [2, 3], [float(C), -float(C)])
RDP = spm_mdp2rdp(RDP, 0, 1.0 / float(NS))
RDP["T"] = 128.0
print("Cell 9: spm_MDP_VB_XXX (before compression, T=128) …", flush=True)
t9 = datetime.now()
PDP = spm_MDP_VB_XXX(RDP, {})
print(f"[COLAB1 local] Cell 9 VB runtime = {datetime.now() - t9}", flush=True)
png_rgb = out_dir / "AtariIII_colab1_dem_before_compression_rgb.png"
dem_atariiii_plot_before_compression_rgb(
    PDP, plot_ctx, save_png=True, png_path=png_rgb
)
plt.show()
print("  before-compression RGB=", png_rgb, flush=True)
png_orb = out_dir / "AtariIII_colab1_dem_orbits_before.png"
dem_atariiii_plot_orbits_before(
    PDP, plot_ctx, save_png=True, png_path=png_orb, eig=None, svd=None
)
plt.show()
print("  orbits before=", png_orb, flush=True)
_cell_walls["9"] = time.perf_counter() - _t_cell
print(
    "Cell 9 OK",
    "RDP.T=",
    RDP.get("T"),
    "PDP has Q=",
    "Q" in PDP,
    "png_rgb=",
    png_rgb,
    "png_orbits=",
    png_orb,
    f"wall_s={_cell_walls['9']:.3f}",
    flush=True,
)

# =============================================================================
# COLAB1 Cell 10 — DEM_AtariIII.m ~375–425 (with compression)
# =============================================================================
_t_cell = time.perf_counter()
Nm = len(MDP)
plot_ctx = {"RGB": RGB, "GDP": GDP, "Nm": Nm}
print("Cell 10: assemble with-compression RDP …", flush=True)
RDP, _j = spm_RDP_sort(MDP)
RDP = spm_RDP_MI(RDP)
RDP = spm_set_goals(RDP, [2, 3], [float(C), -float(C)])
RDP = spm_set_costs(RDP, [2, 3], [float(C), -float(C)])
RDP = spm_mdp2rdp(RDP, 0, 1.0 / float(NS))
RDP["T"] = 128.0
print("Cell 10: spm_MDP_VB_XXX (with compression, T=128) …", flush=True)
t10 = datetime.now()
PDP = spm_MDP_VB_XXX(RDP, {})
print(f"[COLAB1 local] Cell 10 VB runtime = {datetime.now() - t10}", flush=True)
png_rgb = out_dir / "AtariIII_colab1_dem_with_compression_rgb.png"
dem_atariiii_plot_with_compression_rgb(
    PDP, plot_ctx, save_png=True, png_path=png_rgb
)
plt.show()
print("  with-compression RGB=", png_rgb, flush=True)
png_orb = out_dir / "AtariIII_colab1_dem_orbits_after.png"
dem_atariiii_plot_orbits_after(
    PDP, plot_ctx, save_png=True, png_path=png_orb, eig=None, svd=None
)
plt.show()
print("  orbits after=", png_orb, flush=True)
_cell_walls["10"] = time.perf_counter() - _t_cell
print(
    "Cell 10 OK",
    "RDP.T=",
    RDP.get("T"),
    "PDP has Q=",
    "Q" in PDP,
    "png_rgb=",
    png_rgb,
    "png_orbits=",
    png_orb,
    f"wall_s={_cell_walls['10']:.3f}",
    flush=True,
)

# =============================================================================
# COLAB1 Cell 11 — DEM_AtariIII.m ~427–441 (number of parameters)
# =============================================================================
_t_cell = time.perf_counter()
np_count = count_mdp_parameters(MDP)
print("number of parameters", flush=True)
print(np_count, flush=True)
_cell_walls["11"] = time.perf_counter() - _t_cell
print(
    "Cell 11 OK optim1full_np=",
    np_count,
    f"wall_s={_cell_walls['11']:.3f}",
    flush=True,
)

_total = time.perf_counter() - _t_script0
print("COLAB1 DEM_AtariIII.m script walk complete (Cells 0–11).", flush=True)
print("[COLAB1 local] per-cell wall_s:", flush=True)
for k in sorted(_cell_walls.keys(), key=lambda x: int(x)):
    print(f"  Cell {k}: {_cell_walls[k]:.3f} s", flush=True)
print(f"[COLAB1 local] TOTAL wall_s={_total:.3f}", flush=True)
print("COLAB1_LOCAL_PASS", flush=True)
