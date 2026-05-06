"""Minimal CLI for manual testing; full UX lives in higher-level wrappers."""

import sys
from pj_py import init, PjPyError


def main():
    try:
        p = init(sys.argv[1])
        print(f"Created {p.owner}/{p.repo} at {p.path}")
    except PjPyError as e:
        print(f"pj-py error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
