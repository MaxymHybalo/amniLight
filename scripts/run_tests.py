#!/usr/bin/env python3
"""Run all tests with pytest. Execute from project root or from scripts/."""

import subprocess
import sys
from pathlib import Path

# Project root = parent of scripts/
ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-v", *sys.argv[1:]],
        cwd=ROOT,
    )
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
