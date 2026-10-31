#!/usr/bin/env bash
# Kiểm máy trước giờ G. Chạy trên cả 3 máy; mọi dòng MISS phải xử lý trước H0.
set -uo pipefail
miss=0
chk() { if eval "$2" >/dev/null 2>&1; then echo "ok    $1"; else echo "MISS  $1  ($3)"; miss=1; fi; }

chk git        "command -v git"                 "brew install git"
chk node       "command -v node"                "brew install node"
chk uv         "command -v uv"                  "brew install uv"
chk ffmpeg     "command -v ffmpeg"              "brew install ffmpeg — lane core cần"
chk codex      "command -v codex"               "cài Codex CLI"
chk codex-auth "codex login status"             "codex login"
chk claude     "command -v claude"              "cài Claude Code"
chk gh-auth    "gh auth status"                 "gh auth login (repo private của đội)"
chk worktree   "git worktree list"              "chạy trong repo đã git init"
chk disk-15GB  "[ \$(df -g . | awk 'NR==2{print \$4}') -ge 15 ]" "dọn ổ: worktree + model + cache cần chỗ"

[ $miss -eq 0 ] && echo "DOCTOR OK" || { echo "DOCTOR: còn MISS"; exit 1; }
