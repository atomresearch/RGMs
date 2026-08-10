# RGMs Atari DEMO1

Staged Atari structure-learning demo through **Entry 12** + **12PLOT** (first VB call only).

## Setup

1. Clone this repository.
2. Create the conda environment and activate it:

   ```powershell
   conda env create -f rgms-atari.yml
   conda activate rgms-atari
   ```

3. **Parity only:** install MATLAB **2024b** and [MATLAB Engine for Python](https://www.mathworks.com/help/matlab/matlab-engine-for-python.html) (`pip install matlabengine` is listed in `rgms-atari.yml`).

## Run

**Product A — Python-native** (no MATLAB, no fixtures):

```powershell
python python_src/toolbox/DEM/DEM_AtariIII_demo1_python.py
```

**Product B — strict MATLAB–Python parity** (single command, no flags):

```powershell
python python_src/toolbox/DEM/DEM_AtariIII_demo1_parity.py
```

The first parity run generates gitignored fixtures under `tests/demo1/fixtures/` (one `rng(2)` MATLAB ledger when any dump is still missing).

To clear generated `.mat`/`.pkl` dumps before a cold-start re-run:

```powershell
python python_src/toolbox/DEM/DEM_AtariIII_demo1_parity_reset.py
```

Full deliverable plan and output paths: **`DEMO1.md`** (§0 sign-off, §4 quick start).

## OPTIM1 (optimized DEMO1 lane)

Separate fast path — same simulation as DEMO1, isolated under `python_src/optimized/`. Does **not** modify DEMO1. Plan and commands: **`OPTIM1.md`** (§0, §4 quick start).
