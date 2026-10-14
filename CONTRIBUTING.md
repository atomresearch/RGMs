# Contributing to RGMs

This document outlines contribution norms for [https://github.com/atomresearch/RGMs](https://github.com/atomresearch/RGMs). The repository supports the published paper K. Zaghw, A. Pashea, M. Pritsch, W. Nuijten, K. Friston, and L. Da Costa, “Renormalising generative models for active inference: Foundations, derivations, and verification,” arXiv, Aug. 2026. [Online]. Available: [https://arxiv.org/abs/2608.09512](https://arxiv.org/abs/2608.09512). It provides an inspectable Python translation of selected SPM DEM / RGM material, especially the Atari III and Drone VI demonstrations and their supporting library. Contributions must respect that purpose: fidelity to the SPM/MATLAB authority where parity applies, and preservation of **`main`** as the paper-aligned ground-truth tree. The published branch is **`main`**.

How to run the python-native demos, local notebooks, Google Colab notebooks, and parity suites, and how to install runtime dependencies from `requirements.txt`, are outlined in [`README.md`](README.md). This repository is distributed under the GNU General Public License, version 2 or (at your option) any later version; see [`LICENCE`](LICENCE). Contributions are under that license.

## Who may contribute

Contributions that land on **`dev`** or **`main`** must come from registered GitHub accounts, as direct human contributions, after testing and verification. Coding-assistant agents must not push or modify **`dev`** or **`main`**, and must not be the path by which unreviewed agent-generated changes (“vibecoding”) enter those branches. Unreviewed or untested agent-generated changes compromise the integrity and purpose of this repository and are not acceptable. There will be no `AGENTS.md` or similar agent-operating document added to this repository; contribution norms are outlined in this `CONTRIBUTING.md`.

## Branches and the contribution pipeline

**`main`** is live and dedicated to the published paper. Do not treat casual pull requests directly against **`main`** as the normal workflow. **`dev`** is maintained as an equivalent of **`main`** for ongoing integration and is the preferred target for contributor work. The preferred flow is: open an Issue when useful to discuss intent; develop via a pull request targeting **`dev`** (or a short-lived topic branch that will be merged into **`dev`**); thoroughly test; then, only after verification, incorporate into **`dev`** and later into **`main`**.

Only GitHub user **`apashea`** and other authorized users may push to **`dev`**. Other contributors submit changes through pull requests targeting **`dev`**. After testing and verification, **`apashea`** or another authorized user incorporates accepted work into **`dev`**. At the end of the contributions pipeline, **`apashea`** must give final confirmation on all merges and pushes to **`main`**. Changes that affect paper-critical demos or shared library behavior require stronger scrutiny before **`main`**.

## Ground-truth paths, demos, and new files

The core paper-aligned paths include, at minimum: the native demos `python_src/toolbox/DEM/DEM_AtariIII.py` and `python_src/toolbox/DEM/DEM_drone_VI.py` (Python twins of SPM `DEM_AtariIII.m` and `DEM_drone_VI.m`); the supporting live library under `python_src/` used by those demos; local notebooks under `notebooks/` and the Colab surfaces described in `README.md`; and the public parity suites under `tests/dem_atariiii/` and `tests/dem_drone_vi/`. Those demos rely upon the majority of the existing code in RGMs. Any contribution that would alter code or functionality underlying `DEM_AtariIII.py` and `DEM_drone_VI.py` must be transparently clarified in the Issue or pull request: what changed, why, and what behavioral or runtime differences are expected, if any. Prefer preserving equivalent results and runtimes. When exact equivalence is not achievable, **`apashea`** verifies the particular margin-of-error allowances on a case-by-case basis. Do not weaken parity asserts or invent substitute trust mechanisms to obtain a green result.

All existing folder names and file names must be maintained without exception. Contributions either modify current files without changing their names, or add new files. New added files must appear only in separate new folders so that what currently exists remains organized in the same way. Names of new folders and the file structure of new contributions must be verified by **`apashea`** prior to their incorporation into the live **`dev`** branch or **`main`** branch. Prefer additive placement in such new folders over rewriting core demo or library behavior unless the change is a justified fidelity or bug fix with testing.

## Testing (required)

All contributions must be thoroughly tested before they are accepted onto **`dev`**, and again before anything is merged to **`main`**. For work that may affect the demos, the minimum expectation is that the python-native Atari and/or Drone demos still complete successfully with equivalent behavior and runtime, or with differences that have been disclosed and accepted by **`apashea`** case-by-case, and that where relevant the local notebooks remain consistent with that behavior.

Parity uses MATLAB R2024b and the MATLAB Engine for Python, together with fixtures that are not present in the public tree (for size and practicality). Contributors without MATLAB are not expected to mint or store those fixtures. For MATLAB-paired parity when needed, contact **`apashea`** at `andrewpashea@activeinference.institute` or `andrewbpashea@gmail.com`. The workable pattern is: the contributor submits a thoroughly tested pull request targeting **`dev`**; **`apashea`** pulls the changes and runs parity locally when required; then **`apashea`** or another authorized user handles incorporation into **`dev`**, and **`apashea`** gives final confirmation for incorporation into **`main`**.

## Issues and pull requests

Prefer Issues to discuss intent before large changes. Prefer pull requests against **`dev`**, not **`main`**. A pull request description should state what changed, why (for example a fidelity fix versus an additive feature in a new folder), how it was tested, whether the change may affect `DEM_AtariIII.py` or `DEM_drone_VI.py` or the majority of the existing code in RGMs those demos rely upon, any expected behavioral or runtime differences, and whether MATLAB parity is requested from **`apashea`**. Human review is required. Merges into **`dev`** and **`main`** occur only after verification. Merges and pushes to **`main`** additionally require final confirmation from **`apashea`**. When a change addresses a prior Issue, recognizing the Issue author in the discussion is appropriate.

## Environment

Use Python 3.11 or Python 3.12, as stated in `README.md`. Install runtime dependencies from the root `requirements.txt`. Work from the repository root and follow the Quick Start in `README.md` for native scripts, notebooks, Colab, and parity commands.

## Practices that are not acceptable

Do not push to **`dev`** unless you are **`apashea`** or another authorized user. Do not merge or push to **`main`** without final confirmation from **`apashea`**. Do not allow coding-assistant agents to push or modify **`dev`** or **`main`**, and do not merge unreviewed or untested agent-generated changes. Do not skip thorough testing. Do not add `AGENTS.md` or similar agent-operating documents to this repository. Do not treat **`main`** as a casual integration branch. Do not rename existing folders or files. Do not place new files into the existing tree in a way that reorganizes current paths; use separate new folders only, with names and structure verified by **`apashea`** before incorporation into **`dev`** or **`main`**. Do not compromise the paper ground-truth demos for convenience without disclosure, testing, and the review path above.

## Contact

For MATLAB parity and fixture-backed verification, contact **`apashea`** at `andrewpashea@activeinference.institute` or `andrewbpashea@gmail.com`. Broader contribution questions may go through GitHub Issues and pull requests on [https://github.com/atomresearch/RGMs](https://github.com/atomresearch/RGMs).
