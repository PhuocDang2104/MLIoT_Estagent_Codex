"""Validate production configuration without displaying values, then run one worker."""
import os
from pathlib import Path
import sys
from urllib.parse import urlsplit


def validate():
    names = (
        'OPENAI_API_KEY', 'OPENAI_MODEL_TEXT', 'OPENAI_MODEL_REALTIME',
        'OPENAI_MODEL_TRANSCRIBE', 'ASSISTANT_ORIGIN',
        'ASSISTANT_REQUIRED_FIELDS', 'ASSISTANT_DB',
    )
    for name in names:
        value = os.environ.get(name, '')
        if not value.strip() or value != value.strip() or any(
            marker in value.upper() for marker in ('REPLACE_', 'CHANGE_ME', '<YOUR_')
        ):
            raise ValueError(f'{name}: missing, placeholder, or surrounding whitespace')
    origin = urlsplit(os.environ['ASSISTANT_ORIGIN'])
    if (origin.scheme != 'https' or not origin.hostname or origin.username or
            origin.password or origin.path or origin.query or origin.fragment):
        raise ValueError('ASSISTANT_ORIGIN: require an exact HTTPS origin without path')
    # Reuse the application vocabulary; do not introduce a new profile contract.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from server.assistant.graph import LABELS
    fields = [item.strip() for item in os.environ['ASSISTANT_REQUIRED_FIELDS'].split(',')]
    if not fields or any(item not in LABELS for item in fields) or len(set(fields)) != len(fields):
        raise ValueError('ASSISTANT_REQUIRED_FIELDS: invalid or duplicate application field')
    db = Path(os.environ['ASSISTANT_DB'])
    if not db.is_absolute():
        raise ValueError('ASSISTANT_DB: require an absolute path on the dedicated data volume')
    db.parent.mkdir(parents=True, exist_ok=True)
    if not os.access(db.parent, os.W_OK) or (db.exists() and not os.access(db, os.W_OK)):
        raise ValueError('ASSISTANT_DB: checkpoint path is not writable by this runtime user')


if __name__ == '__main__':
    try:
        validate()
    except (ValueError, OSError) as error:
        # No environment values, upstream response bodies, or credentials in output.
        print(f'CONFIG ERROR: {error if isinstance(error, ValueError) else "checkpoint filesystem unavailable"}', file=sys.stderr)
        raise SystemExit(2)
    if sys.argv[1:] == ['--check-config']:
        print('CONFIG OK (presence/format only; model access and quota not verified)')
    elif sys.argv[1:]:
        raise SystemExit('Usage: entrypoint.py [--check-config]')
    else:
        os.execv(sys.executable, [
            sys.executable, '-m', 'uvicorn', 'server.assistant.app:app',
            '--host', '0.0.0.0', '--port', '5180', '--workers', '1',
            '--no-proxy-headers', '--no-access-log',
        ])
