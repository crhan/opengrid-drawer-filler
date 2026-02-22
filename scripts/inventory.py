"""Compatibility shim for inventory - re-exports from opengrid.inventory"""
from opengrid.inventory import (
    load_inventory,
    add_inventory,
    deduct_inventory,
    undo_last,
    print_inventory,
    parse_items,
)

# For compatibility - main function wrapper
def main():
    """Legacy entry point - use opengrid CLI instead"""
    from opengrid.cli import main as cli_main
    cli_main()


__all__ = [
    'load_inventory',
    'add_inventory',
    'deduct_inventory',
    'undo_last',
    'print_inventory',
    'parse_items',
    'main',
]
