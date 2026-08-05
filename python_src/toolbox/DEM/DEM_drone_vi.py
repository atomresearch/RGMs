#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DEM_drone_vi — native Python script walk matching ``DEM_drone_vi.m``.

Adapted from ``tests/demo1/optim2full/COLAB2.py`` (COLAB2 cell markers retained
for notebook lineage). Library imports/calls use only live
``python_src.toolbox.DEM`` MATLAB-matching names (no ``python_src.optimized``,
no ``*_optim``, no ``python_src.fidelity``).

Shared drone library / fence-export / native-entry APIs:
``python_src.toolbox.DEM.dem_drone_vi_lib`` — not this file.

Run (conda ``rgms``)::

    python python_src/toolbox/DEM/DEM_drone_vi.py
"""
from __future__ import annotations

import copy
import os
import sys
import time
from pathlib import Path

# =============================================================================
# COLAB2 Cell 0 — setup (local: no git clone / pip; all imports here)
# =============================================================================
_colab2_t0 = time.perf_counter()
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

from python_src.toolbox.DEM.dem_drone_vi_lib import (
    assemble_mdp_and_gdp_from_scene,
    assemble_Q_from_pdp,
    build_pdp_wayfinding,
    map_from_drone_D,
    pack_mdp_ida_linked,
    scene_dict_from_unity_sizes,
    spm_drone_unity,
    _mdp_levels_for_a2A,
)
from python_src.toolbox.DEM.dem_drone_vi_plot_true_env_early import (
    dem_drone_vi_plot_true_env_early,
)
from python_src.toolbox.DEM.spm_behaviour import spm_behaviour
from python_src.toolbox.DEM.spm_MDP_generate import spm_MDP_generate
from python_src.toolbox.DEM.dem_drone_vi_plot_true_scene_post_generate import (
    dem_drone_vi_plot_true_scene_post_generate,
)
from python_src.toolbox.DEM.spm_faster_structure_learning import (
    spm_faster_structure_learning,
)
from python_src.toolbox.DEM.dem_drone_vi_plot_mdp_params import dem_drone_vi_plot_mdp_params
from python_src.toolbox.DEM.optim2full_native_plot import mdp_fsl_end
from python_src.toolbox.DEM.spm_MDP_VB_XXX import spm_MDP_VB_XXX
from python_src.toolbox.DEM.spm_mdp_a2A import spm_mdp_a2A
from python_src.toolbox.DEM.spm_mdp2rdp import spm_mdp2rdp
from python_src.toolbox.DEM.dem_drone_vi_plot_rgm import dem_drone_vi_plot_rgm
from python_src.toolbox.DEM.spm_Q2mdp import spm_Q2mdp
from python_src.toolbox.DEM.dem_drone_vi_plot_active_inference import (
    dem_drone_vi_plot_active_inference,
)
from python_src.toolbox.DEM.dem_drone_vi_plot_wayfinding import dem_drone_vi_plot_wayfinding

try:
    from IPython.display import Image, Video, display
except Exception:  # plain script / no IPython
    Image = Video = display = None  # type: ignore


def _show_png(path) -> None:
    """Notebook: show saved PNG (plot helpers Agg-close the figure)."""
    if display is None or Image is None:
        return
    display(Image(filename=str(path)))


def _show_mp4(path) -> None:
    """Notebook: embed saved MP4."""
    if display is None or Video is None:
        return
    display(Video(str(path), embed=True, html_attributes="controls"))


# MATLAB DEM_drone_VI.m ~L54: rng(1)
np.random.seed(1)

out_dir = REPO / "visualizations" / "DEM_drone_vi"
out_dir.mkdir(parents=True, exist_ok=True)
_cell_walls: dict[str, float] = {}
_cell_walls["0"] = time.perf_counter() - _t_cell0
print(
    "COLAB2 Cell 0 OK",
    "repo=",
    REPO,
    "tip has spm_behaviour + canonical library",
    f"wall_s={_cell_walls['0']:.3f}",
    flush=True,
)

# =============================================================================
# COLAB2 Cell 1 — DEM_drone_VI.m ~L49–109
# =============================================================================
_t_cell0 = time.perf_counter()

Nx = Ny = 32
Nz = 8
Nd = 16
Nc = 8
Nr = 16
Na = 12
No = 1
Nu = 4
Ns = 6

PG = {
    "Nx": float(Nx),
    "Ny": float(Ny),
    "Nz": float(Nz),
    "Nd": float(Nd),
    "Nc": float(Nc),
    "Nr": float(Nr),
    "Na": float(Na),
    "No": float(No),
    "Nu": float(Nu),
    "Ns": float(Ns),
}

_t0 = time.perf_counter()
D, W = spm_drone_unity(Nx, Ny, Nz, Nc)
_t_unity = time.perf_counter() - _t0
print(f"Cell 1 timing: spm_drone_unity  {_t_unity:.3f} s", flush=True)

_t0 = time.perf_counter()
MAP = map_from_drone_D(D)
_t_map = time.perf_counter() - _t0
print(
    f"Cell 1 timing: map_from_drone_D   {_t_map:.3f} s  "
    f"MAP_len={len(MAP)} W.shape={tuple(np.asarray(W).shape)}",
    flush=True,
)

png_path = out_dir / "DEM_drone_VI_colab2_true_env_early.png"
_t0 = time.perf_counter()
written = dem_drone_vi_plot_true_env_early(
    MAP,
    W,
    Nx=Nx,
    Ny=Ny,
    Nz=Nz,
    Nc=Nc,
    save_png=True,
    png_path=png_path,
    fig_title="Active inference",
)
_t_plot = time.perf_counter() - _t0
print(f"Cell 1 timing: dem_drone_vi_plot_true_env_early  {_t_plot:.3f} s", flush=True)
assert written is not None and Path(written).is_file(), written
_show_png(written)
_cell_walls["1"] = time.perf_counter() - _t_cell0
print(
    "Cell 1 OK",
    f"total={_cell_walls['1']:.3f}s",
    f"unity={_t_unity:.3f}s",
    f"map={_t_map:.3f}s",
    f"plot={_t_plot:.3f}s",
    "png=",
    written,
    flush=True,
)

# =============================================================================
# COLAB2 Cell 2 — DEM_drone_VI.m ~L111–370
# =============================================================================
_t_cell0 = time.perf_counter()
_t0 = time.perf_counter()
scene = scene_dict_from_unity_sizes(
    Nx=int(Nx),
    Ny=int(Ny),
    Nz=int(Nz),
    Nd=int(Nd),
    Nc=int(Nc),
    Nr=int(Nr),
    Na=int(Na),
    No=int(No),
    Nu=int(Nu),
    Ns=int(Ns),
    W=W,
)
_t_scene = time.perf_counter() - _t0
print(f"Cell 2 timing: scene_dict_from_unity_sizes  {_t_scene:.3f} s", flush=True)

_t0 = time.perf_counter()
built = assemble_mdp_and_gdp_from_scene(scene)
_t_assemble = time.perf_counter() - _t0
print(f"Cell 2 timing: assemble_mdp_and_gdp_from_scene  {_t_assemble:.3f} s", flush=True)

mdp = built["mdp"]
GDP = built["GDP"]
PG = built["PG"]
Np = int(built["Np"])
Ng = int(built["Ng"])
V = built["V"]
s_mdp = built["s_mdp"]
s_gdp = built["s_gdp"]

assert built.get("lane") == "native", built.get("lane")
assert isinstance(mdp, dict) and "A" in mdp and "B" in mdp and "id" in mdp
assert isinstance(GDP, dict) and "A" in GDP and "B" in GDP and "T" in GDP
assert isinstance(PG, dict) and "Nx" in PG
_cell_walls["2"] = time.perf_counter() - _t_cell0
print(
    "Cell 2 OK",
    f"total={_cell_walls['2']:.3f}s",
    f"scene={_t_scene:.3f}s",
    f"assemble={_t_assemble:.3f}s",
    f"Np={Np}",
    f"Ng={Ng}",
    f"GDP.T={GDP.get('T')}",
    f"mdp.keys_sample={list(mdp.keys())[:8]}",
    f"PG.Nx={PG.get('Nx')}",
    flush=True,
)

# =============================================================================
# COLAB2 Cell 3 — DEM_drone_VI.m ~L371–394
# =============================================================================
_t_cell0 = time.perf_counter()
_t0 = time.perf_counter()
PDP = spm_MDP_generate(GDP)
_t_gen = time.perf_counter() - _t0
print(
    f"Cell 3 timing: spm_MDP_generate  {_t_gen:.3f} s  "
    f"T={PDP.get('T')} o.shape={np.asarray(PDP.get('o')).shape}",
    flush=True,
)

_t0 = time.perf_counter()
Q = assemble_Q_from_pdp(PDP, PG, int(Nu), int(No), int(Np))
_t_Q = time.perf_counter() - _t0
print(
    f"Cell 3 timing: assemble_Q_from_pdp  {_t_Q:.3f} s  "
    f"Q_rows={len(Q)} Q_T={len(Q[0]) if Q else 0}",
    flush=True,
)

png_path = out_dir / "DEM_drone_VI_colab2_true_scene_post_generate.png"
_t0 = time.perf_counter()
written = dem_drone_vi_plot_true_scene_post_generate(
    Q,
    PG,
    save_png=True,
    png_path=png_path,
    fig_title="True scene",
    loop_all_t=True,
)
_t_plot = time.perf_counter() - _t0
print(
    f"Cell 3 timing: dem_drone_vi_plot_true_scene_post_generate  {_t_plot:.3f} s",
    flush=True,
)
assert written is not None and Path(written).is_file(), written
_show_png(written)
_cell_walls["3"] = time.perf_counter() - _t_cell0
print(
    "Cell 3 OK",
    f"total={_cell_walls['3']:.3f}s",
    f"generate={_t_gen:.3f}s",
    f"assemble_Q={_t_Q:.3f}s",
    f"plot={_t_plot:.3f}s",
    "png=",
    written,
    flush=True,
)

# =============================================================================
# COLAB2 Cell 4 — DEM_drone_VI.m ~L397–404
# =============================================================================
_t_cell0 = time.perf_counter()
S = np.asarray([float(Nx), float(Ny), float(Nz)], dtype=np.float64)
dx = np.asarray([1.0, 64.0], dtype=np.float64)

_t0 = time.perf_counter()
MDP = spm_faster_structure_learning(Q, S, dx)
_t_fsl = time.perf_counter() - _t0
n_lev = len(MDP) if isinstance(MDP, list) else int(np.asarray(MDP, dtype=object).size)
print(
    f"Cell 4 timing: spm_faster_structure_learning  {_t_fsl:.3f} s  n_levels={n_lev}",
    flush=True,
)

_t0 = time.perf_counter()
MDP_end = mdp_fsl_end(MDP)
_t_end = time.perf_counter() - _t0
print(f"Cell 4 timing: mdp_fsl_end  {_t_end:.3f} s", flush=True)

png_path = out_dir / "DEM_drone_VI_colab2_mdp_params.png"
_t0 = time.perf_counter()
written = dem_drone_vi_plot_mdp_params(
    MDP_end,
    OPT="norm",
    save_png=True,
    png_path=png_path,
    fig_title="Paramters: level 2",
)
_t_plot = time.perf_counter() - _t0
print(f"Cell 4 timing: dem_drone_vi_plot_mdp_params  {_t_plot:.3f} s", flush=True)
assert written is not None and Path(written).is_file(), written
_show_png(written)
_cell_walls["4"] = time.perf_counter() - _t_cell0
print(
    "Cell 4 OK",
    f"total={_cell_walls['4']:.3f}s",
    f"fsl={_t_fsl:.3f}s",
    f"mdp_end={_t_end:.3f}s",
    f"plot={_t_plot:.3f}s",
    f"n_levels={n_lev}",
    "png=",
    written,
    flush=True,
)

# =============================================================================
# COLAB2 Cell 5 — DEM_drone_VI.m ~L408–455
# =============================================================================
_t_cell0 = time.perf_counter()
T_surveillance = 16

_t0 = time.perf_counter()
MDP_a2A = spm_mdp_a2A(_mdp_levels_for_a2A(MDP))
_t_a2A = time.perf_counter() - _t0
print(f"Cell 5 timing: spm_mdp_a2A  {_t_a2A:.3f} s", flush=True)

if isinstance(MDP_a2A, list):
    mdp_levels_in = MDP_a2A
else:
    arr = np.asarray(MDP_a2A, dtype=object).ravel(order="F")
    mdp_levels_in = [arr[i] for i in range(arr.size)]

_t0 = time.perf_counter()
mdp_p, mdp_levels, pack_meta = pack_mdp_ida_linked(mdp, mdp_levels_in, Nu=int(Nu))
_t_pack = time.perf_counter() - _t0
print(
    f"Cell 5 timing: pack_mdp_ida_linked  {_t_pack:.3f} s  "
    f"parents={pack_meta.get('n_parent')} skip={pack_meta.get('n_skip_empty_idD')}",
    flush=True,
)

_t0 = time.perf_counter()
RDP = spm_mdp2rdp([mdp_p] + list(mdp_levels[1:]))
_t_mdp2rdp = time.perf_counter() - _t0
print(f"Cell 5 timing: spm_mdp2rdp  {_t_mdp2rdp:.3f} s", flush=True)

RDP["T"] = float(T_surveillance)
_t0 = time.perf_counter()
RDP = spm_MDP_VB_XXX(RDP)
_t_vb = time.perf_counter() - _t0
print(f"Cell 5 timing: spm_MDP_VB_XXX(T={T_surveillance})  {_t_vb:.3f} s", flush=True)

png_path = out_dir / "DEM_drone_VI_colab2_rgm.png"
_t0 = time.perf_counter()
written = dem_drone_vi_plot_rgm(RDP, save_png=True, png_path=png_path, fig_title="RGM")
_t_plot = time.perf_counter() - _t0
print(f"Cell 5 timing: dem_drone_vi_plot_rgm  {_t_plot:.3f} s", flush=True)
assert written is not None and Path(written).is_file(), written
_show_png(written)
_cell_walls["5"] = time.perf_counter() - _t_cell0
print(
    "Cell 5 OK",
    f"total={_cell_walls['5']:.3f}s",
    f"a2A={_t_a2A:.3f}s",
    f"pack={_t_pack:.3f}s",
    f"mdp2rdp={_t_mdp2rdp:.3f}s",
    f"vb={_t_vb:.3f}s",
    f"plot={_t_plot:.3f}s",
    "png=",
    written,
    flush=True,
)

# =============================================================================
# COLAB2 Cell 6 — DEM_drone_VI.m ~L459–464
# =============================================================================
_t_cell0 = time.perf_counter()
_t0 = time.perf_counter()
Q_rec = RDP["Q"]
QDP = spm_Q2mdp(Q_rec, 1)
QDP["id"] = mdp_p["id"]
_t_q2mdp = time.perf_counter() - _t0
print(
    f"Cell 6 timing: spm_Q2mdp  {_t_q2mdp:.3f} s  QDP.keys={sorted(QDP.keys())}",
    flush=True,
)

png_path = out_dir / "DEM_drone_VI_colab2_active_inference.png"
_t0 = time.perf_counter()
written = dem_drone_vi_plot_active_inference(
    QDP,
    PG,
    save_png=True,
    png_path=png_path,
    fig_title="Active inference",
)
_t_plot = time.perf_counter() - _t0
print(f"Cell 6 timing: dem_drone_vi_plot_active_inference  {_t_plot:.3f} s", flush=True)
assert written is not None and Path(written).is_file(), written
_show_png(written)
_cell_walls["6"] = time.perf_counter() - _t_cell0
print(
    "Cell 6 OK",
    f"total={_cell_walls['6']:.3f}s",
    f"q2mdp={_t_q2mdp:.3f}s",
    f"plot={_t_plot:.3f}s",
    "png=",
    written,
    flush=True,
)

# =============================================================================
# COLAB2 Cell 7 — DEM_drone_VI.m ~L467–495
# =============================================================================
_t_cell0 = time.perf_counter()
T_wayfinding = 4

_t0 = time.perf_counter()
pdp, sT = build_pdp_wayfinding(mdp_p, MAP, Nu=int(Nu), Np=int(Np), sT=None)
_t_pdp = time.perf_counter() - _t0
print(
    f"Cell 7 timing: build_pdp_wayfinding  {_t_pdp:.3f} s  sT={sT.ravel().tolist()}",
    flush=True,
)

_t0 = time.perf_counter()
RDP_w = spm_mdp2rdp([pdp] + list(copy.deepcopy(mdp_levels[1:])))
_t_mdp2rdp = time.perf_counter() - _t0
print(f"Cell 7 timing: spm_mdp2rdp  {_t_mdp2rdp:.3f} s", flush=True)

RDP_w["T"] = float(T_wayfinding)
_t0 = time.perf_counter()
RDP_w = spm_MDP_VB_XXX(RDP_w)
_t_vb = time.perf_counter() - _t0
print(f"Cell 7 timing: spm_MDP_VB_XXX(T={T_wayfinding})  {_t_vb:.3f} s", flush=True)

_t0 = time.perf_counter()
QDP_w = spm_Q2mdp(RDP_w["Q"], 1)
QDP_w["id"] = pdp["id"]
_t_q2mdp = time.perf_counter() - _t0
print(
    f"Cell 7 timing: spm_Q2mdp  {_t_q2mdp:.3f} s  QDP_w.keys={sorted(QDP_w.keys())}",
    flush=True,
)

png_path = out_dir / "DEM_drone_VI_colab2_wayfinding.png"
_t0 = time.perf_counter()
written = dem_drone_vi_plot_wayfinding(
    QDP_w,
    PG,
    sT,
    save_png=True,
    png_path=png_path,
    fig_title="Wayfinding",
)
_t_plot = time.perf_counter() - _t0
print(f"Cell 7 timing: dem_drone_vi_plot_wayfinding  {_t_plot:.3f} s", flush=True)
assert written is not None and Path(written).is_file(), written
_show_png(written)
_cell_walls["7"] = time.perf_counter() - _t_cell0
print(
    "Cell 7 OK",
    f"total={_cell_walls['7']:.3f}s",
    f"wayfinding_pdp={_t_pdp:.3f}s",
    f"mdp2rdp={_t_mdp2rdp:.3f}s",
    f"vb={_t_vb:.3f}s",
    f"q2mdp={_t_q2mdp:.3f}s",
    f"plot={_t_plot:.3f}s",
    "png=",
    written,
    flush=True,
)
print("COLAB2 DEM_drone_VI.m script walk complete (Cells 0–7).", flush=True)

# =============================================================================
# COLAB2 Cell 8 — full multi-panel spm_behaviour movie
# =============================================================================
_t0 = time.perf_counter()
mp4_path = out_dir / "DEM_drone_VI_colab2_behaviour.mp4"
out = spm_behaviour(
    QDP_w,
    PG,
    sT,
    save_mp4=True,
    mp4_path=mp4_path,
    fig_title="Wayfinding",
    fps=2.0,
)
_cell_walls["8"] = time.perf_counter() - _t0
assert out["mp4"] is not None and Path(out["mp4"]).is_file(), out
_show_mp4(out["mp4"])
print(
    "Cell 8 OK",
    f"mp4_wall={_cell_walls['8']:.3f}s",
    "mp4=",
    out["mp4"],
    flush=True,
)

_total = time.perf_counter() - _colab2_t0
print("[COLAB2 local] per-cell wall_s:", flush=True)
for k in sorted(_cell_walls.keys(), key=lambda x: int(x)):
    print(f"  Cell {k}: {_cell_walls[k]:.3f} s", flush=True)
print(f"COLAB2 total wall: {_total:.3f} s", flush=True)
print("COLAB2_LOCAL_PASS", flush=True)
