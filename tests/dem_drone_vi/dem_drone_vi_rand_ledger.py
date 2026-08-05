"""OPTIM2FULL — scalar ``rand()`` ledger load / validate (Model-B class).

Protocol: ``optim2full_scalar_rand_log_v1`` (see ``OPTIM2FULL.md`` § Parity version —
RNG / eig / MI / sort reuse).

**F0 caveat:** ``spm_drone_unity`` also uses ``randperm`` and array ``rand(...)``.
Those are **not** logged by the scalar ``fsl_backward/rand.m`` shadow. F0 authority
for scene tensors is therefore the MATLAB ``DEM_drone_VI_optim2full_F0.mat`` dump;
scalar ledger audit remains required for honesty of logged draws and for later
spine segments that are scalar-``rand()`` dominated (VB / FSL).
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from tests.dem_drone_vi.dem_drone_vi_paths import (
    LEDGER_PROTOCOL,
    dem_drone_vi_rand_ledger_mat,
    optim2full_rand_manifest_json,
)

_BUF_VAR = "dem_drone_rand_buf"


@dataclass(frozen=True)
class Optim2fullRandSegment:
    id: str
    start: int
    k: int

    @property
    def end(self) -> int:
        return self.start + self.k


@dataclass(frozen=True)
class Optim2fullRandManifest:
    protocol: str
    rng_seed: int
    plotting: str
    segments: tuple[Optim2fullRandSegment, ...]
    k_total: int
    capture_mode: str

    def segment(self, seg_id: str) -> Optim2fullRandSegment:
        for seg in self.segments:
            if seg.id == seg_id:
                return seg
        known = ", ".join(s.id for s in self.segments)
        raise KeyError(f"manifest segment {seg_id!r} not found (known: {known})")


def ledger_artifacts_present() -> bool:
    return dem_drone_vi_rand_ledger_mat().is_file() and optim2full_rand_manifest_json().is_file()


def load_optim2full_rand_buf() -> tuple[np.ndarray, int]:
    from scipy.io import loadmat

    p = dem_drone_vi_rand_ledger_mat()
    if not p.is_file():
        raise FileNotFoundError(
            f"missing OPTIM2FULL ledger: {p} — run dem_drone_vi_capture_f0.py"
        )
    raw = loadmat(str(p))
    if _BUF_VAR not in raw:
        keys = sorted(k for k in raw if not str(k).startswith("__"))
        raise KeyError(f"expected {_BUF_VAR} in {p}, keys={keys}")
    buf = np.asarray(raw[_BUF_VAR], dtype=np.float64).ravel()
    k_total = int(np.asarray(raw.get("K_total", [[buf.size]]), dtype=np.float64).reshape(-1)[0])
    return buf, k_total


def _parse_segment(raw: dict[str, Any]) -> Optim2fullRandSegment:
    return Optim2fullRandSegment(
        id=str(raw["id"]),
        start=int(raw["start"]),
        k=int(raw["k"]),
    )


def load_optim2full_rand_manifest() -> Optim2fullRandManifest:
    p = optim2full_rand_manifest_json()
    if not p.is_file():
        raise FileNotFoundError(
            f"missing OPTIM2FULL manifest: {p} — run dem_drone_vi_capture_f0.py"
        )
    data = json.loads(p.read_text(encoding="utf-8"))
    raw_segs = data["segments"]
    # MATLAB jsonencode: one struct → object; 2+ → array.
    if isinstance(raw_segs, dict):
        raw_segs = [raw_segs]
    segs = tuple(_parse_segment(s) for s in raw_segs)
    k_total = int(data.get("k_total", sum(s.k for s in segs)))
    return Optim2fullRandManifest(
        protocol=str(data.get("protocol", LEDGER_PROTOCOL)),
        rng_seed=int(data.get("rng_seed", 1)),
        plotting=str(data.get("plotting", "omitted")),
        segments=segs,
        k_total=k_total,
        capture_mode=str(data.get("capture_mode", "")),
    )


def validate_ledger_manifest(buf: np.ndarray, manifest: Optim2fullRandManifest) -> None:
    if manifest.protocol != LEDGER_PROTOCOL:
        raise RuntimeError(
            f"ledger protocol={manifest.protocol!r} expected {LEDGER_PROTOCOL!r}"
        )
    if int(buf.size) != int(manifest.k_total):
        raise RuntimeError(
            f"ledger buf size={buf.size} != manifest.k_total={manifest.k_total}"
        )
    covered = 0
    for seg in manifest.segments:
        if seg.start < 0 or seg.k < 0:
            raise RuntimeError(f"bad segment {seg.id}: start={seg.start} k={seg.k}")
        if seg.end > manifest.k_total:
            raise RuntimeError(
                f"segment {seg.id} end={seg.end} exceeds k_total={manifest.k_total}"
            )
        covered += seg.k
    if covered != manifest.k_total:
        raise RuntimeError(
            f"segment k sum={covered} != manifest.k_total={manifest.k_total}"
        )


def assert_optim2full_ledger_ok() -> Optim2fullRandManifest:
    buf, k_mat = load_optim2full_rand_buf()
    manifest = load_optim2full_rand_manifest()
    if k_mat != manifest.k_total:
        raise RuntimeError(f"K_total in mat ({k_mat}) != manifest ({manifest.k_total})")
    validate_ledger_manifest(buf, manifest)
    if manifest.capture_mode and manifest.capture_mode not in (
        "capture_optim2full_rand_ledger",
        "capture_optim2full_f0",
    ):
        raise RuntimeError(f"unexpected capture_mode={manifest.capture_mode!r}")
    return manifest


def optim2full_rand_segment_slice(seg_id: str) -> tuple[np.ndarray, Optim2fullRandSegment]:
    """Return ``(buf[start:start+k], segment)`` for VB / generate ledger replay.

    Used by OPTIM2FULL F5 as ``matlab_rand_buf`` with
    ``spm_MDP_VB_XXX_optim(..., reuse_matlab_draws_drone=True)``.
    Does **not** touch Atari Entry 12 ``vb_rand_buf``.
    """
    buf, _ = load_optim2full_rand_buf()
    seg = load_optim2full_rand_manifest().segment(seg_id)
    if seg.end > int(buf.size):
        raise RuntimeError(
            f"segment {seg_id!r} end={seg.end} exceeds buf size={buf.size}"
        )
    slice_ = np.asarray(buf[seg.start : seg.end], dtype=np.float64).ravel()
    if int(slice_.size) != int(seg.k):
        raise RuntimeError(
            f"segment {seg_id!r} slice size={slice_.size} != k={seg.k}"
        )
    return slice_, seg
