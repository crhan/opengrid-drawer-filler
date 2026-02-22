#!/usr/bin/env python3
"""统一 CLI 入口"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from opengrid.cli import main

if __name__ == "__main__":
    main()
