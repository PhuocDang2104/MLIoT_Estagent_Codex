# SSH và deploy Studio lên VM Estagent

Push main không tự rollout VM. Host hiện tại: `estagent.duckdns.org`. Repo không
chứa SSH user/port/key; dùng thông tin được quản trị VM cấp. Một assistant replica,
volume riêng `estagent-assistant-checkpoints`; không deploy Vercel.

## Từ PowerShell: SSH và tạo artifact sạch

```powershell
$SshUser = Read-Host 'SSH user của VM'
$SshPort = Read-Host 'SSH port (thường là 22)'
$VmTarget = "${SshUser}@estagent.duckdns.org"
ssh -p $SshPort $VmTarget
# Kiểm tra đúng VM, exit quay về PowerShell trước các lệnh dưới.
```

Tạo clean clone riêng; không xóa/stash file IDE chưa commit để đóng gói release.
Chọn main sau khi commit đã được test và push; giữ full SHA in ra.

```powershell
$ReleaseRoot = Join-Path $env:TEMP ('estagent-release-' + [guid]::NewGuid().ToString('N'))
$Source = Join-Path $ReleaseRoot 'source'
$Out = Join-Path $ReleaseRoot 'artifacts'
git clone --single-branch --branch main https://github.com/PhuocDang2104/MLIoT_Estagent_Codex.git $Source
if ($LASTEXITCODE -ne 0) { throw 'Clone failed' }
$Sha = (git -C $Source rev-parse HEAD).Trim()
python "$Source/deploy/prepare_release.py" --commit $Sha --out-dir $Out
if ($LASTEXITCODE -ne 0) { throw 'Packaging failed' }
scp -P $SshPort "$Out/estagent-assistant-$Sha.tar.gz" "$Out/estagent-assistant-$Sha.tar.gz.sha256" "${VmTarget}:/tmp/"
if ($LASTEXITCODE -ne 0) { throw 'Upload failed' }
$Sha
ssh -p $SshPort $VmTarget
```

## Trên VM: kiểm checksum, build, giữ env cũ

Bash + Docker Compose v2; cần quyền Docker và `/opt/estagent`. Thay SHA bằng
commit được nghiệm thu, không build checkout dirty hoặc image `latest`.

```bash
set -euo pipefail
SHA=PASTE_FULL_SHA
test "${#SHA}" -eq 40
RELEASE="/opt/estagent/assistant/releases/$SHA"
test ! -e "$RELEASE"
mkdir -p "$RELEASE"
cd /tmp
sha256sum -c "estagent-assistant-$SHA.tar.gz.sha256"
tar -xzf "estagent-assistant-$SHA.tar.gz" -C "$RELEASE" --no-same-owner
cd "$RELEASE"
python3 -c 'import json,sys; assert json.load(open("RELEASE.json"))["commit"] == sys.argv[1]' "$SHA"
docker build -f deploy/Dockerfile -t "estagent-assistant:$SHA" .
```

`PREVIOUS_ENV` phải là env **đang dùng thực tế**. Runbook hiện ghi đường dẫn
`preview-346a0ba.env`; nếu operator đã rollout tiếp thì thay đường dẫn đó.
Không in env/key ra terminal/log. Giữ preview nếu chưa có ngân sách live.

```bash
PREVIOUS_ENV=/opt/estagent/runtime/preview-346a0ba.env
test -f "$PREVIOUS_ENV"
PREVIOUS_IMAGE=$(docker inspect --format '{{.Image}}' estagent-assistant-assistant-1)
STUDIO_ENV="/opt/estagent/runtime/studio-$SHA.env"
test ! -e "$STUDIO_ENV"
install -m 600 "$PREVIOUS_ENV" "$STUDIO_ENV"
python3 - "$STUDIO_ENV" "$SHA" <<'PY'
from pathlib import Path
import sys
p = Path(sys.argv[1])
lines = p.read_text().splitlines()
assert sum(line.startswith('ASSISTANT_IMAGE=') for line in lines) == 1
p.write_text('\n'.join('ASSISTANT_IMAGE=estagent-assistant:'+sys.argv[2]
    if line.startswith('ASSISTANT_IMAGE=') else line for line in lines)+'\n')
p.chmod(0o600)
PY
docker network inspect estagent-object-store > /dev/null
docker compose --env-file "$STUDIO_ENV" -f deploy/compose.yaml config --quiet
docker compose --env-file "$STUDIO_ENV" -f deploy/compose.yaml run --rm --no-deps --entrypoint python assistant /app/deploy/entrypoint.py --check-config
printf '%s\n' "$PREVIOUS_IMAGE" > "$RELEASE/PREVIOUS_IMAGE"
chmod 600 "$RELEASE/PREVIOUS_IMAGE"
```

Bật OpenAI live bằng env riêng: `ESTAGENT_KEYLESS_PREVIEW=0`, key thật,
`API_LIMITS_ENABLED=1` và đầy đủ rate/concurrency/attempt bounds theo
`deploy/.env.example`. Key có cấu hình không chứng minh model/quota hợp lệ.
Geometry URL/token tùy chọn theo [STUDIO-RUNTIME.md](STUDIO-RUNTIME.md).
Giữ cấu hình `STORAGE_LIMITS_*`, `MEDIA_STORAGE_BACKEND` và `MINIO_*` của release
hiện tại; đối chiếu `deploy/.env.example` mới trước check-config. Không dùng
binary cũ hoặc đổi về local để bỏ qua media_refs của MinIO.
Compose main mới yêu cầu network `estagent-object-store` ngay cả khi local mode.
Nếu lệnh inspect trên thất bại, chuẩn bị network/MinIO theo MINIO-INTEGRATION-HANDOFF.md
trước khi stop assistant; không đổi sang stack/network của project khác.

## Stop riêng assistant → backup → cutover → smoke

Có downtime ngắn. Không `down -v`, prune, restart edge hoặc database chung.
Backup cần dung lượng tương đương dữ liệu đang có; kiểm dung lượng trước khi stop.
Nếu đang chọn MinIO, snapshot `/data` chỉ chứa metadata và local media cũ; phải
backup thêm volume `estagent-minio-objects` nhất quán trước cutover, theo
[MinIO integration](MINIO-INTEGRATION-HANDOFF.md) và [rollback safety](ROLLBACK-SAFETY.md).
Giữ MinIO env/network/volume hiện tại; không đổi backend về local khi có media_refs.

```bash
df -h /var/lib/docker
BACKUP_DIR="/opt/estagent/backups/pre-$SHA"
test ! -e "$BACKUP_DIR"
sudo install -d -o 10001 -g 10001 -m 700 "$BACKUP_DIR"
docker compose --env-file "$STUDIO_ENV" -f deploy/compose.yaml stop -t 120 assistant
docker compose --env-file "$STUDIO_ENV" -f deploy/compose.yaml run --rm --no-deps -v "$BACKUP_DIR:/backup" --entrypoint python assistant /app/deploy/backup_data.py --root /data --out-dir /backup --label "pre-$SHA"
docker compose --env-file "$STUDIO_ENV" -f deploy/compose.yaml up -d --no-build --wait --wait-timeout 180 assistant
docker compose --env-file "$STUDIO_ENV" -f deploy/compose.yaml exec -T assistant python /app/deploy/smoke.py --base-url http://127.0.0.1:5180 --origin https://estagent.duckdns.org --check-static
curl --fail --silent --show-error https://estagent.duckdns.org/api/studio/health
curl --fail --silent --show-error --output /dev/null https://estagent.duckdns.org/business/create
```

Smoke không gọi paid model; invalid API requests vẫn tính vào admission ledger.
Nếu đã chạm cap thì chờ cửa sổ reset, không xóa ledger. Kiểm browser Studio
desktop/mobile, reload, proposal → confirm → review, published snapshot cũ.
Thiếu geometry worker thì `waiting_integration` là đúng, không phải 3D hoàn tất.
Lưu SHA/image ID/evidence sau rollout. Local source tests không chứng minh Docker,
TLS hoặc OpenAI live đã pass trên VM.

## Rollback

Giữ image/release/env cũ và volume. Backup tại `/opt/estagent/backups/pre-<SHA>/<timestamp>-pre-<SHA>`
kèm `BACKUP.json`; sao lưu thêm ra nơi operator quản lý. Nếu build/config/backup
lỗi, chạy lại assistant bằng Compose release trước + `PREVIOUS_ENV` (image cũ).
Nếu cutover không healthy, cũng dùng release/env cũ để `up -d --no-build --wait`.
Không dùng env mới đang chứa tag mới để rollback và không restore backup đè dữ
liệu phát sinh sau rollout. Migration chỉ thêm bảng/cột, published schema giữ
nguyên, nhưng binary cũ không chạy checkpoint `edit` mới: pending edits cần
runtime mới/forward fix. Bắt buộc chạy rollback preflight mới trong ROLLBACK-SAFETY.md
cho recorded audio/MinIO refs; không coi binary cũ là tương thích. Docker rollback
release này chưa được diễn tập trên VM.
