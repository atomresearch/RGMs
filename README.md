# RGMs

K. Zaghw, A. Pashea, M. Pritsch, W. Nuijten, K. Friston, and L. Da Costa, “Renormalising generative models for active inference: Foundations, derivations, and verification,” arXiv, Aug. 2026. [Online]. Available: [https://arxiv.org/abs/2608.09512](https://arxiv.org/abs/2608.09512).

## Overview

**RGMs**: This repository provides a Python-native library for Renormalising Generative Models (RGMs) via careful translation of selected routines from the open-source [SPM](https://github.com/spm/spm) (Statistical Parametric Mapping) toolbox. Bringing RGM procedures into Python supports reproducibility with respect to the original RGM introductions ([“From pixels to planning: scale-free active inference”](https://www.frontiersin.org/journals/network-physiology/articles/10.3389/fnetp.2025.1521963/full), [“Gradient-free de novo learning”](https://www.mdpi.com/1099-4300/27/9/992)), as well as further experimentation, optimization, and research applications in an accessible open-source language. The repository comprises an inspectable Python translation of selected SPM DEM / RGM demonstrations, with MATLAB-paired parity tests that compare the live Python library against the original MATLAB authority.

**Current status**: The live compute library lives under `python_src/` (canonical MATLAB-matching module names). Two primary end-to-end simulations are available here. Each has a **python-native** script, a **local notebook**, a **Google Colab** notebook, and a **parity** suite against MATLAB R2024b:

| Simulation (SPM) | Native Python script | Local notebook | Google Colab | Parity entry |
|------------------|----------------------|----------------|--------------|--------------|
| `DEM_AtariIII.m` | `python_src/toolbox/DEM/DEM_AtariIII.py` | `notebooks/DEM_AtariIII.ipynb` | [Atari III on Colab](https://colab.research.google.com/drive/1V3S5esW--CsQmOy70VNFVSDiqD66f9E-?usp=sharing) | `tests/dem_atariiii/dem_atariiii_parity_demo.py` |
| `DEM_drone_VI.m` | `python_src/toolbox/DEM/DEM_drone_VI.py` | `notebooks/DEM_drone_VI.ipynb` | [Drone VI on Colab](https://colab.research.google.com/drive/1hTjHvros5RwxWdYemaiX4SGp-il1fDwg?usp=sharing) | `tests/dem_drone_vi/dem_drone_vi_parity_demo.py` |

Native success markers (`COLAB1_LOCAL_PASS` / `COLAB2_LOCAL_PASS`) mean the full MATLAB-matching script completed without MATLAB. They are **not** the same as MATLAB-paired parity. Parity capture and compare steps use MATLAB Engine (see Quick Start). Public parity for both demos was last verified **2026-08-05** (PASS).

This repository has been thoroughly tested for **Python 3.11** and **Python 3.12**.

**Updates**: Translation and testing used MATLAB **R2024b** (parity authority) together with a conda Python environment (`rgms`). Hosted Colab notebooks clone this repository and install dependencies from `requirements.txt` in Cell 0. Archives under `python_src/fidelity/` and `python_src/optimized/` are retention only—they are **not** runtime import roots for the native demos, notebooks, or parity suites.

**Contributions**: Community contributions, within stated guidelines, will be made explicit and encouraged. Contact information for active developers can be provided by request for more involved contribution proposals.

**License**: This repository is distributed under the **GNU General Public License, version 2 or (at your option) any later version**, matching SPM’s GPL conditions. See the root [`LICENCE`](LICENCE) file. Copyright (C) 2026 Andrew Pashea, Karim Zaghw. The tree includes works based on SPM, copyright the Functional Imaging Laboratory / Wellcome Centre for Human Neuroimaging.

<img
  src="https://drive.google.com/uc?export=view&id=18NgPuDKhvl8iiK7hdwepEI8ZUF9qtJ4C"
  alt="RGMs illustration"
  width="700"
/>

## Quick Start

### 1. Local environment (once)

1. Obtain this repository and open a terminal at its root directory (the directory that contains `requirements.txt` and `python_src/`).
2. Create and activate a conda environment. Example name: `rgms`.
3. Install the pinned runtime dependencies:

```powershell
conda activate rgms
python -m pip install -r requirements.txt
```

For **parity** only, also install MATLAB **R2024b** and [MATLAB Engine for Python](https://www.mathworks.com/help/matlab/matlab-engine-for-python.html).

### 2. Run a simulation

All local commands below assume the repository root and an activated environment with `requirements.txt` already installed.

#### Python-native (no MATLAB)

```powershell
python python_src/toolbox/DEM/DEM_AtariIII.py
python python_src/toolbox/DEM/DEM_drone_VI.py
```

Expect `COLAB1_LOCAL_PASS` / `COLAB2_LOCAL_PASS`. Figures (and for Drone, the behaviour MP4) are written under `visualizations/` (local; that tree is gitignored).

#### Local notebooks (no MATLAB)

Open with Jupyter, VS Code, Cursor, or another notebook front-end, using the same Python environment:

- `notebooks/DEM_AtariIII.ipynb`
- `notebooks/DEM_drone_VI.ipynb`

Open the notebook from this repository (so the setup cell can locate `python_src/` and `requirements.txt`). The setup cell does **not** clone the repository and does **not** run `pip install`; it only puts the repository root on `sys.path` and imports library modules.

Later cells—especially Atari’s active-inference loop of 32 training and structure merging episodes—are computationally heavy; expect a long run for a full notebook pass. Drone structure learning and variational message passing likewise dominate later cells; expect a nontrivial run for a full notebook pass.

#### Parity (MATLAB Engine required)

Atari:

```powershell
python tests/dem_atariiii/dem_atariiii_parity_demo.py --capture-ledger
python tests/dem_atariiii/dem_atariiii_parity_demo.py --capture-plot-fixtures
python tests/dem_atariiii/dem_atariiii_parity_demo.py
```

Drone:

```powershell
python tests/dem_drone_vi/dem_drone_vi_parity_demo.py --capture-ledger
python tests/dem_drone_vi/dem_drone_vi_parity_demo.py --capture-f0
python tests/dem_drone_vi/dem_drone_vi_parity_demo.py --capture-fsl-rgm-g
python tests/dem_drone_vi/dem_drone_vi_parity_demo.py
```

Individual Atari witnesses after capture: `--pairing-audit`, `--tier3g`, `--plot-parity`. Drone spine witness: `--spine-e2e` (F0→F6). `--check-authority` only checks that fixtures are present; it does not establish compute parity. A bare (no-flag) run is the full public witness for that simulation. Pass criterion: process exit code **0**.

#### Google Colab

Use the Colab links in the Overview table. Hosted Cell 0 clones `https://github.com/apashea/RGMs.git`, installs from `requirements.txt`, and imports library modules. **Do not** `import DEM_AtariIII` or `import DEM_drone_VI` to obtain helpers—those modules execute the full simulation at import time. Drone Cell 0 must import shared helpers from `python_src.toolbox.DEM.dem_drone_vi_lib` (see **Using the Python translations** below).

## Repository Layout

```text
RGMs/
|-- LICENCE                 # GPL-2.0-or-later (SPM-aligned) + project copyright
|-- README.md               # this file
|-- requirements.txt        # pinned runtime dependencies (native / notebooks / Colab)
|-- matlab_compat.py        # shared MATLAB/Python mechanical compatibility helpers
|-- matlab_src/             # staged SPM / MATLAB sources used as translation authority
|-- notebooks/
|   |-- DEM_AtariIII.ipynb  # local Atari III notebook
|   `-- DEM_drone_VI.ipynb  # local Drone VI notebook
|-- python_src/
|   |-- toolbox/DEM/        # canonical live library + native demo scripts
|   |-- fidelity/           # archive only (not a demo/parity import root)
|   `-- optimized/          # archive only (not a demo/parity import root)
|-- tests/
|   |-- dem_atariiii/       # Atari parity suite
|   |-- dem_drone_vi/       # Drone VI parity suite
|   |-- oracle/             # per-file MATLAB↔Python oracle tests (development)
|   `-- helpers/            # shared test utilities (e.g. MATLAB Engine session helpers)
`-- visualizations/         # local figure and video output (gitignored)
```

Historical development trees (for example under `tests/demo1/optim*full/`) may remain on disk. Prefer the native `DEM_*.py` scripts, `notebooks/`, and `tests/dem_*` suites above.

## What The Code Covers

The companion paper discusses SPM DEM toolbox demonstrations that exercise RGM structure learning and active inference. This repository’s **primary** end-to-end surfaces are:

- **Atari III** (`DEM_AtariIII.m` ↔ `DEM_AtariIII.py`): a simplified Pong-like task with pixel streams, rewards, costs, actions, trajectory selection, active inference, learning, and model compression.
- **Drone VI** (`DEM_drone_VI.m` ↔ `DEM_drone_VI.py`): a dynamic three-dimensional scene with a moving object, fast structure learning, recursive-model construction, surveillance, and wayfinding (including a behaviour movie on the native path).

Related SPM demos (for example Drone V) informed the translation programme; the native scripts, notebooks, and parity suites above are the primary surfaces documented here.

## Verification Model

MATLAB remains the source of truth for **parity**. Parity suites drive the live library under `python_src/` against MATLAB-owned fixtures and declared injects (for example random ledgers, and MATLAB spectral / sort steps where the Python toolchain cannot match MATLAB `eig(...,'nobalance')` semantics).

What is compared depends on the witness, and typically includes:

- array shapes and numeric values;
- sparse versus dense storage where it matters;
- nested structs, cells, and model objects;
- RNG-sensitive stages (via captured ledgers on parity paths);
- scene / process-model construction;
- structure-learning and RDP / VB stages;
- plot-site fingerprints where the Atari parity suite includes `--plot-parity`.

**Native** and **notebook** runs are MATLAB-free full-script executions and intentionally omit some parity injects. Treat native/notebook completion and parity PASS as separate claims.

Oracle-style per-file tests under `tests/oracle/` remain useful during translation development. They are not a substitute for the `tests/dem_*` demos when the question is whether the Atari / Drone spine matches MATLAB.

## Atari III And Drone VI

### Key paths

```text
python_src/toolbox/DEM/DEM_AtariIII.py          # native Atari script
python_src/toolbox/DEM/run_dem_atariiii.py      # staged Entries 1–12 spine (parity / FSL callers)
python_src/toolbox/DEM/DEM_drone_VI.py          # native Drone VI script
python_src/toolbox/DEM/dem_drone_vi_lib.py      # durable drone helpers + parity fence APIs
notebooks/DEM_AtariIII.ipynb                    # local Atari notebook
notebooks/DEM_drone_VI.ipynb                    # local Drone notebook
tests/dem_atariiii/dem_atariiii_parity_demo.py  # Atari parity entry
tests/dem_drone_vi/dem_drone_vi_parity_demo.py  # Drone VI parity entry
matlab_src/toolbox/DEM/                         # staged MATLAB / SPM sources
requirements.txt                                # pinned runtime dependencies
```

### Import details (important)

- **Do not** import `DEM_AtariIII` or `DEM_drone_VI` as libraries to obtain helpers; importing them runs the full simulation as a side effect. Run them as scripts (`python …/DEM_AtariIII.py`, `python …/DEM_drone_VI.py`).
- Atari **parity** uses `run_dem_atariiii` for staged spine stops; the **native** Atari script and local Atari notebook do **not** import that module for their walks.
- Drone **native**, Colab, local notebook, and **parity** share helpers from `dem_drone_vi_lib`. Users must import those helpers from `dem_drone_vi_lib`.

### Current public parity status (2026-08-05)

| Witness | Result |
|---------|--------|
| Atari `--pairing-audit` | PASS |
| Atari `--tier3g` + `--plot-parity` | PASS |
| Drone `--spine-e2e` (F0→F6) | PASS |

## Using The Python Translations

Run Python from the repository root so `python_src` imports resolve.

Small SPM-style helper:

```python
import numpy as np

from python_src.spm_log import spm_log

A = np.array([0.5, 1.0, 2.0])
y = spm_log(A)
```

DEM helper:

```python
from python_src.toolbox.DEM.spm_MDP_size import spm_MDP_size

Nf, Ns, Nu, Ng, No = spm_MDP_size(mdp)
```

Drone shared helpers (same names Colab Cell 0 should bind):

```python
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
```

Raw one-dimensional NumPy arrays are treated as MATLAB row vectors unless explicitly shaped otherwise. If MATLAB behaviour depends on column orientation, pass an explicit column shape:

```python
np.array([[0.5], [1.0], [2.0]])
```

Expect MATLAB-like data structures in the translations: dictionaries for structs, Python lists or object arrays for cells, SciPy sparse matrices for sparse values, and one-based values where the MATLAB data itself stores one-based indices. Shared mechanical helpers live in `matlab_compat.py`.

## Changing Or Extending The Code

Default workflow for faithful translation work:

1. Read the MATLAB source under `matlab_src/` (SPM remains the authority; do not treat the external SPM install as a writable tree).
2. Update the matching live module under `python_src/` (prefer MATLAB-matching names and control flow).
3. Preserve shapes, ordering, indexing conventions, and nested object structure where they affect behaviour.
4. Add or update an oracle test under `tests/oracle/` when translating a discrete function.
5. If the change touches an end-to-end demo path, re-run the relevant **native** script, **notebook**, and/or **`tests/dem_*`** parity demo—not only a small helper pytest.
6. Do not import or “fix” demos by routing through `python_src/fidelity/` or `python_src/optimized/` archives.

Avoid redesigning or optimizing during a faithful translation pass. Native/notebook runs and MATLAB-paired parity are separate claims: do not weaken parity asserts, and do not treat native or notebook completion as proof of MATLAB equivalence.
