"""Package only the clean, accepted main commit; never upload or deploy."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile


ROOT = Path(__file__).resolve().parents[1]
FILES = [
    'server/assistant', 'web/assistant.html', 'web/assistant.css',
    'web/assistant.js', 'web/assets', 'deploy/Dockerfile',
    'deploy/Dockerfile.dockerignore', 'deploy/compose.yaml',
    'deploy/entrypoint.py', 'deploy/smoke.py', 'deploy/.env.example',
]


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, stderr=subprocess.PIPE)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--commit', required=True, help='full SHA accepted by the integrator')
    parser.add_argument('--out-dir', required=True, type=Path, help='outside the shared checkout')
    args = parser.parse_args()
    root = Path(git('rev-parse', '--show-toplevel').decode().strip()).resolve()
    if git('status', '--porcelain', '--untracked-files=all').strip():
        raise ValueError('dirty checkout: integrator must finish and commit before release')
    if git('branch', '--show-current').decode().strip() != 'main':
        raise ValueError('release must be prepared from main')
    sha = git('rev-parse', 'HEAD').decode().strip()
    if args.commit != sha:
        raise ValueError('accepted full commit SHA must equal HEAD')
    if git('rev-parse', 'origin/main').decode().strip() != sha:
        raise ValueError('HEAD must match origin/main; integrator must sync it first')
    out = args.out_dir.resolve()
    if out == root or root in out.parents:
        raise ValueError('out-dir must be outside the checkout')
    source = git('archive', '--format=tar', sha, *FILES)
    manifest = json.dumps({
        'commit': sha, 'scope': FILES,
        'requirements_sha256': hashlib.sha256(git('show', f'{sha}:server/assistant/requirements.txt')).hexdigest(),
    }, indent=2).encode() + b'\n'
    out.mkdir(parents=True, exist_ok=True)
    artifact = out / f'estagent-assistant-{sha}.tar.gz'
    with artifact.open('xb') as target, tarfile.open(fileobj=target, mode='w:gz') as archive:
        with tarfile.open(fileobj=io.BytesIO(source), mode='r:') as original:
            for entry in original:
                archive.addfile(entry, original.extractfile(entry) if entry.isfile() else None)
        entry = tarfile.TarInfo('RELEASE.json')
        entry.size, entry.mode = len(manifest), 0o644
        archive.addfile(entry, io.BytesIO(manifest))
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    artifact.with_suffix(artifact.suffix + '.sha256').write_text(f'{digest}  {artifact.name}\n')
    print(f'RELEASE READY: {artifact.name}\ncommit: {sha}\nsha256: {digest}')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print(f'RELEASE REFUSED: {error if isinstance(error, ValueError) else type(error).__name__}')
        raise SystemExit(2)
