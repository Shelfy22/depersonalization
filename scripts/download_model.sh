#!/usr/bin/env sh
set -eu

TARGET_DIR="${1:-./models/privacy_filter}"

mkdir -p "$TARGET_DIR"
cat <<'MSG'
Download the OpenAI Privacy Filter checkpoint on an internet-connected machine, then copy it
into the closed contour.

Suggested source:
  https://huggingface.co/openai/privacy-filter

Place the checkpoint files into:
MSG
printf '  %s\n' "$TARGET_DIR"
cat <<'MSG'

After copying, set:
  OPF_CHECKPOINT=/app/models/privacy_filter
  MODEL_PATH=/app/models/privacy_filter
MSG
