#!/bin/bash
#SBATCH --job-name=build-llama
#SBATCH --partition=MGPU-TC2
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=16G
#SBATCH --time=00:20:00
#SBATCH --output=logs/%x-%j.out
#SBATCH --error=logs/%x-%j.err

set -euo pipefail
mkdir -p logs

cd "$SLURM_SUBMIT_DIR/../runtime"

# ---- toolchain ----
module purge
module load gcc/14.2.0
module load cuda/12.8.0

# ---- ensure we really use module gcc ----
echo "which g++: $(which g++)"
echo "g++ --version: $(g++ --version | head -n 1)"

# g++ knows where its own libstdc++ is
GXX_LIBSTDCPP="$(g++ -print-file-name=libstdc++.so.6)"
echo "libstdc++: $GXX_LIBSTDCPP"

# Put module libstdc++ directory FIRST (runtime + link helper)
export LD_LIBRARY_PATH="$(dirname "$GXX_LIBSTDCPP"):${LD_LIBRARY_PATH:-}"

# sanity: show highest GLIBCXX provided by the chosen libstdc++
echo "GLIBCXX provided by module libstdc++:"
strings -a "$GXX_LIBSTDCPP" | grep GLIBCXX_ | tail -n 5

echo "Node: $(hostname)"
echo "GPU:"
nvidia-smi || true

# Check for CMAKE
if command -v cmake >/dev/null 2>&1; then
    echo "Using system cmake: $(command -v cmake)"

else
    CMAKE_DIR="$HOME/.local/cmake"
    CMAKE_BIN="$CMAKE_DIR/bin/cmake"

    if [ -x "$CMAKE_BIN" ]; then
        echo "Using user cmake: $CMAKE_BIN"
        export PATH="$CMAKE_DIR/bin:$PATH"

    else
        echo "CMake not found. Installing..."

        mkdir -p "$HOME/.local"
        cd "$HOME/.local"

        CMAKE_VERSION=3.30.2
        PKG="cmake-${CMAKE_VERSION}-linux-x86_64.tar.gz"

        wget -q https://github.com/Kitware/CMake/releases/download/v${CMAKE_VERSION}/${PKG}
        tar -xzf ${PKG}
        rm -f ${PKG}

        mv cmake-${CMAKE_VERSION}-linux-x86_64 cmake

        export PATH="$HOME/.local/cmake/bin:$PATH"
    fi
fi

echo "CMake version:"
cmake --version | head -n 1

cd "$SLURM_SUBMIT_DIR/../runtime"

rm -rf llama-cpp/build

cmake -S ./llama-cpp -B llama-cpp/build -DGGML_CUDA=ON \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_C_COMPILER=/cm/local/apps/gcc/14.2.0/bin/gcc \
    -DCMAKE_CXX_COMPILER=/cm/local/apps/gcc/14.2.0/bin/g++ \
    -DCMAKE_CUDA_HOST_COMPILER=/cm/local/apps/gcc/14.2.0/bin/g++

cmake --build llama-cpp/build --target llama-server --config Release -j2

echo "Build done."
