#!/usr/bin/env python3
"""OPTIM2FULL Phase 2b Ord 5 — MDP params (``spm_MDP_params``) visual pair.

Produces:
  - MATLAB PNG from F2.mat ``MDP{end}`` (Engine + capture .m)
  - Python PNG from F2.pkl ``MDP[-1]`` (``dem_drone_vi_plot_mdp_params``)
  - Side-by-side compare PNG (MATLAB left | Python right)

Usage::

    conda activate rgms
    python tests/demo1/optim2full/optim2full_plot_mdp_params_visual.py
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
            eng.optim2full_capture_mdp_params_plot(
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
        raise RuntimeError(f"MATLAB mdp_params capture child failed rc={rc}")
    if not out_png.is_file():
        raise FileNotFoundError(f"MATLAB capture did not write {out_png}")
    return out_png


def _compose_matlab_vs_python(matlab_png: Path, python_png: Path, out_path: Path) -> Path:
    """Side-by-side: MATLAB (left) | Python (right)."""
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
        "MATLAB MDP params (left)  |  Python MDP params (right)",
        fill=(0, 0, 0),
    )
    canvas.paste(left_s, (0, label_h))
    canvas.paste(right_s, (left_s.width + gap, label_h))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out_path)
    return out_path


def main() -> int:
    from python_src.toolbox.DEM.dem_drone_vi_plot_mdp_params import (
        dem_drone_vi_plot_mdp_params,
    )
    from tests.demo1.optim2full.optim2full_authority import (
        assert_optim2full_full_ledger_ok,
    )
    from tests.demo1.optim2full.optim2full_paths import (
        optim2full_f2_pkl,
        optim2full_fixtures_dir,
        optim2full_mdp_params_compare_png,
        optim2full_mdp_params_matlab_png,
        optim2full_mdp_params_python_png,
    )

    print("[optim2full mdp_params] authority check...", flush=True)
    assert_optim2full_full_ledger_ok()

    f2_pkl = optim2full_f2_pkl()
    if not f2_pkl.is_file():
        print(f"FAIL: missing F2 pkl {f2_pkl} (run --fence-f2 / --spine-e2e)", file=sys.stderr)
        return 1

    mat_png = optim2full_mdp_params_matlab_png()
    py_png = optim2full_mdp_params_python_png()
    cmp_png = optim2full_mdp_params_compare_png()

    print("[optim2full mdp_params] load F2.pkl...", flush=True)
    blob = pickle.load(f2_pkl.open("rb"))
    if "MDP" not in blob:
        print("FAIL: F2.pkl missing MDP", file=sys.stderr)
        return 1
    mdp = blob["MDP"]
    if not isinstance(mdp, (list, tuple)) or len(mdp) < 1:
        print(f"FAIL: F2.pkl MDP not a non-empty cell-like list ({type(mdp)})", file=sys.stderr)
        return 1
    mdp_end = mdp[-1]
    if not isinstance(mdp_end, dict):
        print(f"FAIL: MDP{{end}} not a dict ({type(mdp_end)})", file=sys.stderr)
        return 1

    fig_title = f"Paramters: level {len(mdp)}"
    print(f"[optim2full mdp_params] Python plot -> {py_png}", flush=True)
    saved = dem_drone_vi_plot_mdp_params(
        mdp_end,
        OPT="norm",
        save_png=True,
        png_path=py_png,
        fig_title=fig_title,
    )
    if saved is None or not Path(saved).is_file():
        print("FAIL: Python plot did not write PNG", file=sys.stderr)
        return 1

    print(f"[optim2full mdp_params] MATLAB capture -> {mat_png}", flush=True)
    _capture_matlab_png(optim2full_fixtures_dir(), mat_png)

    print(f"[optim2full mdp_params] compose side-by-side -> {cmp_png}", flush=True)
    _compose_matlab_vs_python(mat_png, py_png, cmp_png)

    print("OK: OPTIM2FULL mdp_params visual pair ready", flush=True)
    print(f"  MATLAB : {mat_png}", flush=True)
    print(f"  Python : {py_png}", flush=True)
    print(f"  COMPARE: {cmp_png}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
