#!/usr/bin/env python3
"""Reject Claude/Anthropic co-author trailers, preserving human attribution."""
import argparse
from pathlib import Path
import re
import subprocess
import sys

TRAILER = re.compile(r'^\s*co-authored-by\s*:\s*(.*)$', re.I)
CLAUDE = re.compile(r'\bclaude\b|anthropic', re.I)


def forbidden(message):
    return any(match and CLAUDE.search(match.group(1))
               for line in message.splitlines()
               for match in [TRAILER.match(line)])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--message-file', type=Path)
    source.add_argument('--all', action='store_true', help='Check history reachable from HEAD')
    args = parser.parse_args()
    if args.message_file:
        bad = forbidden(args.message_file.read_text(encoding='utf-8', errors='replace'))
    else:
        result = subprocess.run(['git', 'log', 'HEAD', '--format=%H%x00%B%x00'],
                                check=True, capture_output=True, text=True)
        fields = result.stdout.split('\0')
        commits = [fields[i].strip() for i in range(0, len(fields) - 1, 2)
                   if forbidden(fields[i + 1])]
        bad = bool(commits)
        for sha in commits:
            print(f'FAIL: Claude/Anthropic co-author trailer in {sha}', file=sys.stderr)
    if bad:
        print('Remove only the Claude/Anthropic Co-Authored-By trailer; '
              'keep human authors and AI-use declarations.', file=sys.stderr)
        return 1
    print('Attribution check OK')
    return 0


if __name__ == '__main__':
    sys.exit(main())
