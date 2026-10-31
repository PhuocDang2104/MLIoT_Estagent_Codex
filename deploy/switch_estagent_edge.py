"""Switch only the existing Estagent Caddy site; preserve inode and other sites.

Run on the authorized VM with explicit config/backup paths. No reload is performed.
Rollback requires the config still match the exact candidate, avoiding stale restores.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

SITE = re.compile(rb'(?ms)^estagent\.duckdns\.org\s*\{\n.*?^\}')
CANDIDATE = b'estagent.duckdns.org {\n    reverse_proxy estagent-assistant-api:5180\n}'


def digest(value):
    return hashlib.sha256(value).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['apply', 'rollback'])
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--backup', type=Path, required=True)
    args = parser.parse_args()
    config, backup = args.config, args.backup
    state = backup.with_suffix('.switch.json')
    current = config.read_bytes()
    if args.mode == 'apply':
        matches = list(SITE.finditer(current))
        if len(matches) != 1:
            raise SystemExit('REFUSED: expected exactly one Estagent site')
        original = matches[0].group()
        if original.strip() != b'estagent.duckdns.org {\n    reverse_proxy estagent-web:8080\n}':
            raise SystemExit('REFUSED: site differs from the verified frontend-only baseline')
        candidate = current[:matches[0].start()] + CANDIDATE + current[matches[0].end():]
        backup.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        with backup.open('xb') as output:
            output.write(current)
        backup.chmod(0o600)
        with state.open('x') as output:
            json.dump({'before': digest(current), 'candidate': digest(candidate)}, output)
        state.chmod(0o600)
        if config.read_bytes() != current:
            raise SystemExit('REFUSED: concurrent config change; backup preserved')
        # Caddy mounts this exact file inode; do not replace it with a rename.
        config.write_bytes(candidate)
        print('APPLIED: only Estagent upstream changed; backup retained')
    else:
        record = json.loads(state.read_text())
        original = backup.read_bytes()
        if digest(current) != record['candidate'] or digest(original) != record['before']:
            raise SystemExit('REFUSED: config changed since rollout; manual site-only reconciliation needed')
        config.write_bytes(original)
        print('ROLLED BACK: exact guarded prior config restored')


if __name__ == '__main__':
    main()
