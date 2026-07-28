"""OPTIM2FULL — MATLAB authority presence checks."""

from __future__ import annotations

from pathlib import Path

from tests.demo1.optim2full.optim2full_paths import (
    CAPTURE_OPTIM2FULL_F0,
    CAPTURE_OPTIM2FULL_RAND_LEDGER,
    REQUIRED_LEDGER_SEGMENTS,
    optim2full_fixtures_dir,
)
from tests.demo1.optim2full.optim2full_rand_ledger import (
    assert_optim2full_ledger_ok,
    load_optim2full_rand_manifest,
)


_FULL_FENCE_MATS = tuple(f"DEM_drone_VI_optim2full_F{i}.mat" for i in range(0, 7))


def missing_optim2full_full_ledger_authority(fixtures_dir: Path | None = None) -> list[str]:
    root = fixtures_dir or optim2full_fixtures_dir()
    names = (
        *_FULL_FENCE_MATS,
        "optim2full_dem_drone_rand_buf.mat",
        "optim2full_rand_manifest.json",
    )
    missing: list[str] = []
    for name in names:
        p = root / name
        if not p.is_file():
            missing.append(str(p))
    return missing


def assert_optim2full_full_ledger_authority_present(fixtures_dir: Path | None = None) -> None:
    missing = missing_optim2full_full_ledger_authority(fixtures_dir)
    if missing:
        raise FileNotFoundError(
            "OPTIM2FULL full-order ledger authority missing:\n"
            + "\n".join(f"  - {p}" for p in missing)
            + "\nRun: python tests/demo1/optim2full/optim2full_capture_rand_ledger.py"
        )


def assert_optim2full_full_ledger_ok(fixtures_dir: Path | None = None) -> None:
    """Presence + capture_mode + required segment order (Phase 0c durable product)."""
    assert_optim2full_full_ledger_authority_present(fixtures_dir)
    manifest = assert_optim2full_ledger_ok()
    if manifest.capture_mode != CAPTURE_OPTIM2FULL_RAND_LEDGER:
        raise RuntimeError(
            f"manifest.capture_mode={manifest.capture_mode!r} expected "
            f"{CAPTURE_OPTIM2FULL_RAND_LEDGER!r} (provisional F0-only is not durable)"
        )
    got = tuple(s.id for s in manifest.segments)
    if got != REQUIRED_LEDGER_SEGMENTS:
        raise RuntimeError(
            f"segment order {got} != required {REQUIRED_LEDGER_SEGMENTS}"
        )
    # F0 meta must match full-ledger capture (same session).
    from scipy.io import loadmat

    root = fixtures_dir or optim2full_fixtures_dir()
    raw = loadmat(str(root / "DEM_drone_VI_optim2full_F0.mat"), squeeze_me=True, struct_as_record=False)
    capture = str(getattr(raw["meta"], "capture", "")).strip()
    if capture != CAPTURE_OPTIM2FULL_RAND_LEDGER:
        raise RuntimeError(
            f"F0 meta.capture={capture!r} expected {CAPTURE_OPTIM2FULL_RAND_LEDGER!r}"
        )


# --- Legacy F0-only checks (Phase 0b schema; not durable RNG) ---


def missing_optim2full_f0_authority(fixtures_dir: Path | None = None) -> list[str]:
    root = fixtures_dir or optim2full_fixtures_dir()
    names = (
        "DEM_drone_VI_optim2full_F0.mat",
        "optim2full_dem_drone_rand_buf.mat",
        "optim2full_rand_manifest.json",
    )
    return [str(root / n) for n in names if not (root / n).is_file()]


def assert_optim2full_f0_authority_present(fixtures_dir: Path | None = None) -> None:
    missing = missing_optim2full_f0_authority(fixtures_dir)
    if missing:
        raise FileNotFoundError(
            "OPTIM2FULL F0 authority missing:\n"
            + "\n".join(f"  - {p}" for p in missing)
            + "\nPrefer: python tests/demo1/optim2full/optim2full_capture_rand_ledger.py"
        )


def assert_optim2full_f0_mat_capture_meta(fixtures_dir: Path | None = None) -> str:
    """Accept full-ledger or provisional F0 capture meta on F0 mat."""
    from scipy.io import loadmat

    path = (fixtures_dir or optim2full_fixtures_dir()) / "DEM_drone_VI_optim2full_F0.mat"
    if not path.is_file():
        raise FileNotFoundError(path)
    raw = loadmat(str(path), squeeze_me=True, struct_as_record=False)
    if "meta" not in raw:
        raise KeyError(f"{path.name}: missing meta")
    capture = str(getattr(raw["meta"], "capture", "")).strip()
    allowed = {CAPTURE_OPTIM2FULL_F0, CAPTURE_OPTIM2FULL_RAND_LEDGER}
    if capture not in allowed:
        raise RuntimeError(f"{path.name}: meta.capture={capture!r} not in {allowed}")
    return capture
