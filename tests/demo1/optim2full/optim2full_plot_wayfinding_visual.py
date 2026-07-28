#!/usr/bin/env python3
"""OPTIM2FULL Phase 2b — Wayfinding final-frame visual pair (one site).

Produces:
  - MATLAB PNG from F6.mat QDP + F1.mat PG (Engine + capture .m)
  - Python PNG from F6.pkl QDP + F1.mat PG (``dem_drone_vi_plot_wayfinding``)
  - Side-by-side compare PNG (MATLAB left | Python right)

Usage::

    conda activate rgms
    python tests/demo1/optim2full/optim2full_plot_wayfinding_visual.py
"""
from __future__ import annotations

import pickle
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))


def _capture_matlab_png(fix_dir: Path, out_png: Path) -> Path:
    """Run Engine capture in a child process (avoids pyexpat/matplotlib DLL clobber)."""
    import subprocess
    import textwrap

    out_png.parent.mkdir(parents=True, exist_ok=True)
    child = textwrap.dedent(
        f"""
        import sys
        from pathlib import Path
        repo = Path(r"{_REPO}")
        sys.path.insert(0, str(repo))
        import matlab.engine
        from tests.demo1.demo1_matlab_engine import configure_dem_matlab_engine
        eng = matlab.engine.start_matlab()
        try:
            configure_dem_matlab_engine(eng, repo)
            spm_root = Path(r"C:\\Users\\andre\\Documents\\MATLAB\\spm-main")
            spm_dem = spm_root / "toolbox" / "DEM"
            if spm_root.is_dir():
                eng.addpath(str(spm_root), nargout=0)
            if spm_dem.is_dir():
                eng.addpath(str(spm_dem), nargout=0)
            eng.cd(str(repo / "matlab_custom" / "optim2full"), nargout=0)
            eng.optim2full_capture_wayfinding_plot(
                r"{fix_dir}", r"{out_png}", nargout=0
            )
        finally:
            eng.quit()
        p = Path(r"{out_png}")
        if not p.is_file():
            raise SystemExit(f"missing matlab png: {{p}}")
        print("CHILD_OK", p, flush=True)
        """
    )
    rc = subprocess.call([sys.executable, "-c", child], cwd=str(_REPO))
    if rc != 0:
        raise RuntimeError(f"MATLAB wayfinding capture child failed rc={rc}")
    if not out_png.is_file():
        raise FileNotFoundError(f"MATLAB capture did not write {out_png}")
    return out_png


def _compose_matlab_vs_python(matlab_png: Path, python_png: Path, out_path: Path) -> Path:
    """Side-by-side: MATLAB (left) | Python (right) — OPTIM1FULL visual pattern."""
    from PIL import Image, ImageDraw

    left = Image.open(matlab_png).convert("RGB")
    right = Image.open(python_png).convert("RGB")
    target_h = max(left.height, right.height)

    def _scale(im: Image.Image) -> Image.Image:
        if im.height == target_h:
            return im
        w = int(im.width * target_h / im.height)
        return im.resize((w, target_h), Image.Resampling.LANCZOS)

    left_s, right_s = _scale(left), _scale(right)
    label_h, gap = 28, 16
    w = left_s.width + gap + right_s.width
    canvas = Image.new("RGB", (w, label_h + target_h), (255, 255, 255))
    draw = ImageDraw.Draw(canvas)
    draw.text(
        (8, 4),
        "MATLAB Wayfinding (left)  |  Python Wayfinding (right)",
        fill=(0, 0, 0),
    )
    canvas.paste(left_s, (0, label_h))
    canvas.paste(right_s, (left_s.width + gap, label_h))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out_path)
    return out_path


def _load_pg_from_f1(f1_mat: Path) -> dict:
    from scipy.io import loadmat

    raw = loadmat(str(f1_mat), simplify_cells=True)
    pg = raw["PG"]
    if not isinstance(pg, dict):
        raise TypeError("F1 PG must be dict under simplify_cells")
    return pg


def main() -> int:
    from python_src.toolbox.DEM.dem_drone_vi_plot_wayfinding import (
        dem_drone_vi_plot_wayfinding,
    )
    from tests.demo1.optim2full.optim2full_authority import (
        assert_optim2full_full_ledger_ok,
    )
    from tests.demo1.optim2full.optim2full_paths import (
        optim2full_f1_mat,
        optim2full_f6_pkl,
        optim2full_fixtures_dir,
        optim2full_wayfinding_compare_png,
        optim2full_wayfinding_matlab_png,
        optim2full_wayfinding_python_png,
    )

    print("[optim2full wayfinding] authority check...", flush=True)
    assert_optim2full_full_ledger_ok()

    f6_pkl = optim2full_f6_pkl()
    f1_mat = optim2full_f1_mat()
    if not f6_pkl.is_file():
        print(f"FAIL: missing F6 pkl {f6_pkl} (run --fence-f6 / --spine-e2e)", file=sys.stderr)
        return 1
    if not f1_mat.is_file():
        print(f"FAIL: missing F1.mat {f1_mat}", file=sys.stderr)
        return 1

    mat_png = optim2full_wayfinding_matlab_png()
    py_png = optim2full_wayfinding_python_png()
    cmp_png = optim2full_wayfinding_compare_png()

    # Python plot first (clean process); MATLAB capture in child subprocess.
    print("[optim2full wayfinding] load F6.pkl + F1 PG...", flush=True)
    blob = pickle.load(f6_pkl.open("rb"))
    qdp = blob["QDP"]
    sT = blob["sT"]
    pg = _load_pg_from_f1(f1_mat)

    print(f"[optim2full wayfinding] Python plot -> {py_png}", flush=True)
    saved = dem_drone_vi_plot_wayfinding(
        qdp,
        pg,
        sT,
        save_png=True,
        png_path=py_png,
        fig_title="Wayfinding",
    )
    if saved is None or not Path(saved).is_file():
        print("FAIL: Python plot did not write PNG", file=sys.stderr)
        return 1

    print(f"[optim2full wayfinding] MATLAB capture -> {mat_png}", flush=True)
    _capture_matlab_png(optim2full_fixtures_dir(), mat_png)

    print(f"[optim2full wayfinding] compose side-by-side -> {cmp_png}", flush=True)
    _compose_matlab_vs_python(mat_png, py_png, cmp_png)

    print("OK: OPTIM2FULL Wayfinding visual pair ready", flush=True)
    print(f"  MATLAB : {mat_png}", flush=True)
    print(f"  Python : {py_png}", flush=True)
    print(f"  COMPARE: {cmp_png}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
