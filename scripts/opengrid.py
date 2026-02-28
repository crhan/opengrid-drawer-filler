#!/usr/bin/env -S uv run --script
# /// script
# dependencies = ["PyYAML>=6.0.3", "Jinja2>=3.1.6", "pillow>=12.1.1"]
# ///
"""统一 CLI 入口"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from opengrid.cli import main

if __name__ == "__main__":
    main()
