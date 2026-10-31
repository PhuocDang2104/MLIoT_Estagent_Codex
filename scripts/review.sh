#!/usr/bin/env bash
# Codex review một nhánh so với main — dùng cho diff do Claude viết (review khác nhà).
# Dùng: scripts/review.sh <lane>/<id>-<slug>   → tasks/<lane>/<id>.review.md
set -euo pipefail

branch="${1:?dùng: scripts/review.sh <branch>}"
root="$(git rev-parse --show-toplevel)"
base="${BASE:-main}"
wt="$(git -C "$root" worktree list --porcelain | awk -v b="refs/heads/$branch" '/^worktree /{w=substr($0,10)} $0=="branch "b{print w}')"
[ -n "$wt" ] || { echo "nhánh $branch chưa có worktree (tạo bằng scripts/spawn.sh)" >&2; exit 2; }

lane="${branch%%/*}"; id="$(echo "${branch#*/}" | cut -d- -f1-2)"   # task-id = <lane>-<NN>
out="$root/tasks/$lane/$id.review.md"; mkdir -p "$(dirname "$out")"

(cd "$wt" && codex exec review --base "$base" \
  "Soát thay đổi này với AGENTS.md, docs/CONTRACTS.md và task card tasks/$lane/$id.md nếu có.
Báo có vấn đề hay không, kèm căn cứ: lỗi chạy, lệch contract, file ngoài phạm vi lane, thiếu kiểm chứng.
Không có vấn đề thì nói rõ là không có.") >"$out" 2>&1
echo "review: $out"
