#!/usr/bin/env bash
# Tạo worktree + nhánh riêng cho một task card rồi chạy Codex worker headless.
# Dùng: scripts/spawn.sh tasks/<lane>/<id>.md      (lead chạy ở chế độ nền)
#   CODEX_DRY=1     chỉ dựng worktree + in prompt, không gọi Codex
#   CODEX_MODEL=..  ép model; BASE=main nhánh gốc; SKIP_SMOKE=1 bỏ gate smoke
set -euo pipefail

card="${1:?dùng: scripts/spawn.sh tasks/<lane>/<id>.md}"
[ -f "$card" ] || { echo "không thấy card: $card" >&2; exit 2; }
root="$(git rev-parse --show-toplevel)"
card="$(cd "$(dirname "$card")" && pwd)/$(basename "$card")"

field() { sed -n "s/^$1:[[:space:]]*\([^[:space:]]*\).*/\1/p" "$card" | head -1; }
id="$(basename "$card" .md)"
lane="$(field Lane)"; slug="$(field Slug)"; net="$(field Network)"
case "$lane" in web|core|ai) ;; *) echo "card thiếu 'Lane: web|core|ai'" >&2; exit 2 ;; esac
[ -n "$slug" ] || { echo "card thiếu 'Slug:'" >&2; exit 2; }

branch="$lane/$id-$slug"
wt="$(dirname "$root")/$(basename "$root")-wt/$id"
base="${BASE:-main}"
out="$root/tasks/$lane"; mkdir -p "$out"
report="$out/$id.report.md"; log="$out/$id.log"

if [ ! -d "$wt" ]; then
  git -C "$root" worktree add -q -b "$branch" "$wt" "$base"
  # .env* không nằm trong git: chép sang để gate/worker chạy được giống checkout chính
  for f in "$root"/.env "$root"/.env.local; do [ -f "$f" ] && cp "$f" "$wt/"; done
  # dùng chung node_modules khi lockfile trùng, đỡ npm install mỗi worktree
  for pkg in "$root"/package.json "$root"/*/package.json; do
    [ -f "$pkg" ] || continue
    d="$(dirname "$pkg")"; rel="${d#"$root"}"
    if [ -d "$d/node_modules" ] && [ ! -e "$wt$rel/node_modules" ] && cmp -s "$d/package-lock.json" "$wt$rel/package-lock.json"; then
      ln -s "$d/node_modules" "$wt$rel/node_modules"
    fi
  done
fi

if [ -z "${SKIP_SMOKE:-}" ] && ! (cd "$wt" && scripts/gate.sh "$lane" >"$out/$id.smoke.log" 2>&1); then
  echo "SMOKE FAIL: môi trường worktree chưa chạy được gate, xem $out/$id.smoke.log" >&2; exit 3
fi

prompt="$(mktemp)"; trap 'rm -f "$prompt"' EXIT
cat "$root/docs/briefs/WORKER-PREAMBLE.md" "$card" >"$prompt"

if [ -n "${CODEX_DRY:-}" ]; then
  echo "DRY  branch=$branch  worktree=$wt  network=${net:-no}"; head -5 "$card"; exit 0
fi

args=(exec -C "$wt" -s workspace-write
      --add-dir "$(git -C "$root" rev-parse --path-format=absolute --git-common-dir)"  # cho phép git commit trong worktree
      -o "$report")
[ -n "${CODEX_MODEL:-}" ] && args+=(-m "$CODEX_MODEL")
[ "$net" = "yes" ] && args+=(-c sandbox_workspace_write.network_access=true)

echo "▶ $id  $branch  ($(date +%H:%M))"
rc=0; codex "${args[@]}" - <"$prompt" >"$log" 2>&1 || rc=$?

# hậu kiểm: file đổi phải nằm trong Paths của card
paths="$(awk '/^## Paths/{f=1;next} /^## /{f=0} f' "$card" | sed -n 's/^- `\([^`]*\)`.*/\1/p')"
changed="$( { git -C "$wt" diff --name-only "$base"...HEAD; git -C "$wt" status --porcelain | cut -c4-; } | sort -u)"
oos=""
for f in $changed; do
  ok=""; for p in $paths; do case "$f" in "$p"|"${p%/}"/*) ok=1 ;; esac; done
  [ -n "$ok" ] || oos="$oos $f"
done

echo "■ $id  codex_exit=$rc  $(grep -m1 '^STATUS:' "$report" 2>/dev/null || echo 'STATUS: (không có báo cáo)')"
git -C "$wt" log --oneline "$base"..HEAD | sed 's/^/  commit /'
[ -n "$oos" ] && echo "  OUT_OF_SCOPE:$oos"
[ -n "$(git -C "$wt" status --porcelain)" ] && echo "  UNCOMMITTED: còn thay đổi chưa commit"
echo "  report=$report  log=$log  worktree=$wt"
exit "$rc"
