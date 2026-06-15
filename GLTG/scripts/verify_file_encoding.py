"""Verify all GLTG text files are clean ASCII with LF line endings.

Run from the GLTG/ directory:
    uv run python scripts/verify_file_encoding.py

Exits with code 1 and prints offending files if any non-ASCII bytes or
carriage-return characters are found in tracked text files.
"""

import os
import sys

EXTENSIONS = ('.py', '.toml', '.md', '.json', '.txt', '.yml', '.yaml', '.sh')
SKIP_DIRS = {'__pycache__', '.venv', '.git', 'dist', 'build', '.egg-info'}


def check_dir(root_dir: str) -> list[str]:
    problems = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fname in filenames:
            if not any(fname.endswith(ext) for ext in EXTENSIONS):
                continue
            path = os.path.join(dirpath, fname)
            try:
                data = open(path, 'rb').read()
            except OSError:
                continue
            non_ascii = sum(1 for b in data if b > 127)
            cr = data.count(b'\r')
            if non_ascii or cr:
                problems.append(
                    f'{path}: {non_ascii} non-ASCII byte(s), {cr} CR(s)'
                )
    return problems


def main() -> int:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    gltg_root = os.path.dirname(script_dir)

    print(f'Scanning: {gltg_root}')
    problems = check_dir(gltg_root)

    if problems:
        print(f'\nFAIL -- {len(problems)} file(s) with encoding issues:')
        for p in problems:
            print(f'  {p}')
        return 1

    # Count files checked
    total = sum(
        1 for dirpath, dirnames, filenames in os.walk(gltg_root)
        if not any(s in dirpath for s in SKIP_DIRS)
        for fname in filenames
        if any(fname.endswith(ext) for ext in EXTENSIONS)
    )
    print(f'PASS -- all {total} text files are clean ASCII with LF endings.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
