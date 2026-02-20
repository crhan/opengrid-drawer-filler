"""STL generation using OpenSCAD"""
import os
import subprocess
from pathlib import Path

# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_OPENSCAD = "/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD"


def get_max_stacks(max_z=325, full_thickness=7.2):
    """Calculate max stacks"""
    return int(max_z // full_thickness)


def generate_stl(width, height, stacks, verbose=False, force=False):
    """Generate single STL file using OpenSCAD"""
    # Placeholder - actual implementation would use OpenSCAD
    return None, None


def generate_all_stls(scheme, copies=1, verbose=False, force=False):
    """Generate all STL files for a scheme"""
    # Placeholder
    return []
