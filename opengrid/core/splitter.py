"""Tile splitting algorithms"""
from .constants import MIN_TILE


def split_with_limit(n, parts, max_val, max_results=1000):
    """Split number n into parts, each not exceeding max_val

    Args:
        n: Number to split
        parts: Number of parts
        max_val: Maximum value for each part
        max_results: Maximum number of results to prevent combinatorial explosion
    """
    if parts == 1:
        return [[n]] if n <= max_val else []

    results = []

    def recurse(remaining, current):
        # Early termination: exceeded max results
        if len(results) >= max_results:
            return

        if len(current) == parts - 1:
            if MIN_TILE <= remaining <= max_val:
                current.append(remaining)
                results.append(current[:])
                current.pop()
            return

        # Pruning: not enough remaining for remaining parts
        min_needed = MIN_TILE * (parts - len(current) - 1)
        if remaining < min_needed:
            return

        # Pruning: too much remaining for remaining parts
        max_allowed = max_val * (parts - len(current) - 1)
        if remaining > max_allowed + max_val:
            return

        for i in range(MIN_TILE, min(max_val, remaining - min_needed) + 1):
            current.append(i)
            recurse(remaining - i, current)
            current.pop()
            # Early termination check
            if len(results) >= max_results:
                return

    recurse(n, [])
    return results


def calc_balance(splits):
    """Calculate balance ratio (max/min), lower is more balanced"""
    if not splits or min(splits) == 0:
        return 1
    return max(splits) / min(splits)


def calc_scheme_balance(x_splits, y_splits):
    """Calculate balance score for entire scheme"""
    if not x_splits or not y_splits:
        return 1.0

    x_balance = calc_balance(x_splits)
    y_balance = calc_balance(y_splits)
    return max(x_balance, y_balance)
