#!/bin/bash

# Script to download Qwen3-VL-2B-Instruct-GGUF and its mmproj
# Files are downloaded from Hugging Face: Qwen/Qwen3-VL-2B-Instruct-GGUF

set -e

# Resolve repo root from this script location, regardless of where it's run.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Configuration
MODEL_DIR="${REPO_ROOT}/runtime/models/Qwen3vl-2B"
HF_REPO="Qwen/Qwen3-VL-2B-Instruct-GGUF"
BASE_URL="https://huggingface.co/${HF_REPO}/resolve/main"

# Model files to download
MODEL_FILE="Qwen3VL-2B-Instruct-Q8_0.gguf"
MMPROJ_FILE="mmproj-Qwen3VL-2B-Instruct-F16.gguf"

# Create model directory if it doesn't exist
mkdir -p "$MODEL_DIR"

echo "Downloading Qwen3-VL-2B-Instruct-GGUF files to $MODEL_DIR"
echo "=============================================="

# Download model file
if [ -f "$MODEL_DIR/$MODEL_FILE" ]; then
    echo "Model file already exists: $MODEL_FILE"
else
    echo "Downloading $MODEL_FILE..."
    curl -L -o "$MODEL_DIR/$MODEL_FILE" "$BASE_URL/$MODEL_FILE"
    echo "Downloaded: $MODEL_FILE"
fi

# Download mmproj file
if [ -f "$MODEL_DIR/$MMPROJ_FILE" ]; then
    echo "mmproj file already exists: $MMPROJ_FILE"
else
    echo "Downloading $MMPROJ_FILE..."
    curl -L -o "$MODEL_DIR/$MMPROJ_FILE" "$BASE_URL/$MMPROJ_FILE"
    echo "Downloaded: $MMPROJ_FILE"
fi

echo ""
echo "Download complete!"
echo "Files are located in: $MODEL_DIR"
ls -lh "$MODEL_DIR"
