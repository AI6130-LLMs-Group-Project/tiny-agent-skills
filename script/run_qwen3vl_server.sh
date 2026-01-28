#!/bin/bash

# Script to run llama-server with Qwen3VL-2B-Instruct model

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

LLAMA_SERVER="$PROJECT_ROOT/runtime/llama-cpp/build/bin/llama-server"
MODEL_DIR="$PROJECT_ROOT/runtime/models/Qwen3vl-2B"
MODEL="$MODEL_DIR/Qwen3VL-2B-Instruct-Q8_0.gguf"
MMPROJ="$MODEL_DIR/mmproj-Qwen3VL-2B-Instruct-F16.gguf"

# Check if files exist
if [ ! -f "$LLAMA_SERVER" ]; then
    echo "Error: llama-server not found at $LLAMA_SERVER"
    exit 1
fi

if [ ! -f "$MODEL" ]; then
    echo "Error: Model file not found at $MODEL"
    exit 1
fi

if [ ! -f "$MMPROJ" ]; then
    echo "Error: MMProj file not found at $MMPROJ"
    exit 1
fi

echo "Starting llama-server with Qwen3VL-2B-Instruct..."
echo "Model: $MODEL"
echo "MMProj: $MMPROJ"

"$LLAMA_SERVER" \
    -m "$MODEL" \
    --mmproj "$MMPROJ" \
    -c 4096 \
    -ngl 999 \
    --port 1025
