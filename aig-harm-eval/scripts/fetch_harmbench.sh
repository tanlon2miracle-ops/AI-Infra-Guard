#!/usr/bin/env bash
# Download HarmBench behaviors_text dataset (MIT license).
# Usage: bash scripts/fetch_harmbench.sh [out_dir]
set -euo pipefail
OUT="${1:-data_external/harmbench}"
mkdir -p "$OUT"
URL="https://raw.githubusercontent.com/centerforaisafety/HarmBench/main/data/behavior_datasets/harmbench_behaviors_text_all.csv"
echo "Fetching HarmBench behaviors_text_all.csv -> $OUT"
curl -fsSL "$URL" -o "$OUT/harmbench_behaviors_text_all.csv"
echo "Done. Use: aig-eval build-dataset --harmbench $OUT/harmbench_behaviors_text_all.csv"
