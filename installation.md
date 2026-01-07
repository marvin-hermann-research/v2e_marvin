# Installation Guide

This guide is tested on Ubuntu (apt-based) systems with NVIDIA GPUs. The setup uses **two conda environments** to avoid dependency conflicts between the TensorFlow/FILM stack and the PyTorch+CUDA build for `esim_torch`.

## 0) Prerequisites (system)

Install build tools and common C++ deps (needed to compile ESIM bindings and other native deps):

```bash
sudo apt update
sudo apt install -y build-essential cmake ninja-build libeigen3-dev libboost-all-dev libopencv-dev
```

(Your NVIDIA driver should be installed and working; quick check: `nvidia-smi`.)

Install Miniconda (if not already installed):

```bash
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh
~/miniconda3/bin/conda init bash
```

Restart the shell afterward.

Clone repository (with submodules):

```bash
git clone https://github.com/marvin-hermann-research/v2e_marvin.git --recursive
cd <REPO_DIR>
```

## 1) Get pretrained models (FILM checkpoint bundle)

Download the pretrained models zip and extract it into the repo directory (the repo README expects these models for the example pipeline).
From the **parent directory** of your repo:

```bash
cd ~/PARENT-DIR
wget https://rpg.ifi.uzh.ch/data/VID2E/pretrained_models.zip -O /tmp/pretrained_models.zip
unzip /tmp/pretrained_models.zip -d v2e_marvin/
rm -f /tmp/pretrained_models.zip
```

## 2) Why two conda envs

The repo uses an old TensorFlow stack for the FILM/upsampling part, while the GPU-accelerated ESIM bindings require a modern PyTorch+CUDA toolchain; mixing both in one environment tends to break dependencies.​

- **Env A (`vid2e`)**: TensorFlow/FILM/upsampling (CPU is fine; TF-GPU is optional and often painful).
- **Env B (`vid2e_torch`)**: PyTorch + CUDA + ESIM GPU extentions (esim_torch).

## 3) Env A: `vid2e` (TensorFlow/FILM + upsampling)

Create and activate:

```bash
conda create -n vid2e python=3.9 -y
conda activate vid2e
```

Install pybind11 (needed to compil esim_py later):

```bash
conda install -y -c conda-forge pybind11
```

Install repo requirements (TF 2.6.x, matplotlib, etc. are pinned there):

```bash
python -m pip install -U "pip" "wheel" "setuptools<81"
python -m pip install --no-build-isolation -r requirements.txt
```

Sanity check on version 2.6:

```bash
python -c "import tensorflow as tf; print(tf.__version__)"
```

(Required for GPU upsampling) Enable TensorFlow GPU
Install cuDNN into the environment:

```bash
conda install -c anaconda cudnn
```

## 4) Env B: `vid2e_torch` (PyTorch GPU + ESIM GPU build)

Create and activate:

```bash
conda create -n vid2e_torch python=3.9 -y
conda activate vid2e_torch
```

Install PyTorch with CUDA runtime:

```bash
conda install -y pytorch torchvision torchaudio pytorch-cuda=11.8 -c pytorch -c nvidia
python -c "import torch; print(torch.cuda.is_available(), torch.version.cuda)"
```

Install runtime deps for event generation script (OpenCV + tqdm):

```bash
conda install -y -c conda-forge opencv tqdm
python -c "import cv2, tqdm; print(cv2.__version__); print(tqdm.__version__)"
```

(OpenCV on conda-forge provides the `cv2` module. `tqdm` is also available on conda-forge.)

install matplotlib for event visualization

```bash
conda install -y -c conda-forge matplotlib
```

## 5) Build ESIM bindings

## 5.1 Build `esim_py` (CPU bindings) in both envs

From repo root:

In `vid2e`:

```bash
conda activate vid2e
pip install ./esim_py
```

In `vid2e_torch`:

```bash
conda activate vid2e_torch
pip install ./esim_py
```

## 5.2 If `esim_py` build fails due to `libpython3.9.so` path mismatch

Some builds fail if the environment is not under `~/miniconda3` but the build system expects it. A pragmatic workaround is a symlink:

```bash
ln -s ~/Programme/Miniconda3 ~/miniconda3
ls -l ~/miniconda3/envs/vid2e/lib/libpython3.9.so*
```

Then rebuild (clean build dir):

```bash
rm -rf esim_py/build
pip install ./esim_py
```

## 6) Build `esim_torch` (GPU bindings) in `vid2e_torch`

## 6.1 Install nvcc + CUDA toolkit into the env

Your PyTorch runtime doesn’t automatically include `nvcc`, but building CUDA extensions needs it. also check if both versions are 11.8

```bash
conda activate vid2e_torch
conda install -y -c nvidia/label/cuda-11.8.0 cuda-toolkit=11.8.* cuda-nvcc=11.8.*
which nvcc
nvcc -V
python -c "import torch; print('torch cuda', torch.version.cuda)"
```

## 6.2 Persist CUDA_HOME for builds

Conda supports per-env activation scripts.

```bash
mkdir -p "$CONDA_PREFIX/etc/conda/activate.d"
cat > "$CONDA_PREFIX/etc/conda/activate.d/cuda_home.sh" <<'EOF'
export CUDA_HOME="$CONDA_PREFIX"
export PATH="$CUDA_HOME/bin:$PATH"
export LD_LIBRARY_PATH="$CUDA_HOME/lib:$CUDA_HOME/lib64:$LD_LIBRARY_PATH"
EOF

conda deactivate
conda activate vid2e_torch
echo "CUDA_HOME=$CUDA_HOME"
```

## 6.3 Ensure GPU arch + GCC 11 (CUDA 11.8 host compiler constraint)

Check your GPU capability:

```bash
python -c "import torch; print(torch.cuda.get_device_name(0)); print(torch.cuda.get_device_capability(0))"
```

Install GCC 11 toolchain into the env and force it for the build:

```bash
conda install -y -c conda-forge "gcc_linux-64=11.*" "gxx_linux-64=11.*"
export TORCH_CUDA_ARCH_LIST="7.5+PTX"   # Example: GTX 1650 -> (7,5)
export CC="$CONDA_PREFIX/bin/x86_64-conda-linux-gnu-cc"
export CXX="$CONDA_PREFIX/bin/x86_64-conda-linux-gnu-c++"
```

Build/install:

```bash
cd ~/Development/v2e_marvin
rm -rf esim_torch/build
python -m pip install --no-build-isolation -v ./esim_torch
python -c "import esim_torch; print('esim_torch ok')"
```

## 7) (Optional) Make `esim_py` import robust via LD_PRELOAD

If importing `esim_py` fails due to GDAL/TIFF symbol mismatches, you can persist an `LD_PRELOAD` in `vid2e_torch` using activate/deactivate scripts.[](https://guillaume-martin.github.io/saving-environment-variables-in-conda.html)​  
Create the scripts:

```bash
conda activate vid2e_torch
mkdir -p "$CONDA_PREFIX/etc/conda/activate.d" "$CONDA_PREFIX/etc/conda/deactivate.d"

cat > "$CONDA_PREFIX/etc/conda/activate.d/ld_preload_tiff.sh" <<'EOF'
export LD_PRELOAD="/usr/lib/x86_64-linux-gnu/libtiff.so.5${LD_PRELOAD:+:$LD_PRELOAD}"
EOF

cat > "$CONDA_PREFIX/etc/conda/deactivate.d/ld_preload_tiff.sh" <<'EOF'
if [ -n "$LD_PRELOAD" ]; then
  export LD_PRELOAD="$(echo "$LD_PRELOAD" | awk -v RS=: -v ORS=: '$0!="/usr/lib/x86_64-linux-gnu/libtiff.so.5"{print}' | sed 's/:$//')"
fi
EOF
```

Reactivate to apply:

```bash
conda deactivate
conda activate vid2e_torch
```

## final verification

## Env `vid2e_torch`

This verifies (1) GPU torch works and (2) the CUDA extension (`esim_torch`) imports.​

```bash
conda activate vid2e_torch
python -c "import torch; print('cuda available:', torch.cuda.is_available()); print('torch cuda:', torch.version.cuda)" python -c "import esim_torch; print('esim_torch ok')"
```

**Optional** (only if you want `esim_py` too):

```bash
python -c "import esim_py; print('esim_py ok')"
```

…but this may require the `LD_PRELOAD` workaround to be active.
## Env `vid2e`

This verifies TensorFlow/FILM env is intact for upsampling.​

```bash
conda activate
vid2e python -c "import tensorflow as tf; print('tf', tf.__version__)"
```

