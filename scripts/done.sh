#!/usr/bin/env bash
# Sau khi đã merge: xoá worktree và nhánh của task. git branch -d tự từ chối nếu nhánh chưa merge.
# Dùng: scripts/done.sh <lane>/<id>-<slug>
set -euo pipefail

branch="${1:?dùng: scripts/done.sh <branch>}"
root="$(git rev-parse --show-toplevel)"
wt="$(git -C "$root" worktree list --porcelain | awk -v b="refs/heads/$branch" '/^worktree /{w=substr($0,10)} $0=="branch "b{print w}')"
[ -n "$wt" ] && git -C "$root" worktree remove "$wt"
git -C "$root" branch -d "$branch"
