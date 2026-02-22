"""Compatibility shim for slicer - re-exports from new CLI"""
# Re-export from opengrid.stl module
from opengrid.stl.generator import generate_stl, generate_all_stls

# Legacy function for compatibility
def open_in_slicer(filepath):
    """Open STL file in slicer (placeholder - requires external tool)"""
    import subprocess
    import os

    # Try to open with default application
    if os.path.exists(filepath):
        subprocess.run(['open', filepath])
        return True
    return False


__all__ = [
    'generate_stl',
    'generate_all_stls',
    'open_in_slicer',
]
