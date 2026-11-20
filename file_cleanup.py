#!/usr/bin/env python3
"""Run the tool straight from a checkout, with no install step:

    python file_cleanup.py explore "C:\\path\\to\\folder"
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from file_cleanup_tool.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
