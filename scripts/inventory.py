#!/usr/bin/env python3
"""Inventory management CLI wrapper

Usage:
    python scripts/inventory.py list
    python scripts/inventory.py add 8x8:5 6x7:3 "入库原因"
    python scripts/inventory.py deduct 8x8:2 "扣减原因"
    python scripts/inventory.py undo
"""
import sys
import os

# Add project root to path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, PROJECT_ROOT)

from opengrid.inventory import main

if __name__ == "__main__":
    main()
