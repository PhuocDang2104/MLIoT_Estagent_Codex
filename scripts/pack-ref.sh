#!/usr/bin/env bash
# Đóng gói bản tham khảo codex_hack bản gọn (code + docs + 1 tour mẫu) để gửi riêng cho 2 dev còn lại.
# Bên nhận giải nén cạnh repo này để có ../codex_hack. Bản gốc ~1,7 GB, chỉ có trên máy Thái.
# Dùng: scripts/pack-ref.sh [nguồn=../codex_hack] [đích=../codex_hack-ref.tgz]
set -euo pipefail
cd "$(git rev-parse --show-toplevel)/.."
src="${1:-codex_hack}"; dst="${2:-codex_hack-ref.tgz}"
tar -czf "$dst" \
  --exclude='node_modules' --exclude='dist' --exclude='.vercel*' --exclude='__pycache__' \
  --exclude="$src/data" --exclude="$src/tools/brush" --exclude="$src/target" --exclude="$src/web/public/scenes" \
  --exclude="$src/projects/*/work" --exclude="$src/projects/*/input" --exclude="$src/projects/*/scene" \
  --exclude="$src/projects/*/_voice" --exclude="$src/projects/*/voice" --exclude='*.mp3' --exclude='*.wav' \
  "$src"
du -h "$dst"
