#!/usr/bin/env python3
"""方案展示模块"""


def present_schemes(schemes, inventory):
    """展示多方案对比"""

    output = []
    output.append("")
    output.append("╔══════════════════════════════════════════════════════════╗")
    output.append("║  方案对比                                              ║")
    output.append("╚══════════════════════════════════════════════════════════╝")
    output.append("")

    for key, data in schemes.items():
        name = data["name"]
        scheme = data.get("scheme") or {}

        # 处理 tiles 格式 - 可能是元组列表或字典列表
        tiles = scheme.get("tiles", [])
        if tiles and isinstance(tiles[0], tuple):
            # 元组列表格式: [(w, h), (w, h), ...]
            # 统计每种尺寸的数量
            tile_dict = {}
            for w, h in tiles:
                key_str = f"{w}x{h}"
                tile_dict[key_str] = tile_dict.get(key_str, 0) + 1
            tile_list = [{"width": w, "height": h, "count": c} for (w, h), c in
                        [(tuple(map(int, k.split('x'))), v) for k, v in tile_dict.items()]]
        else:
            tile_list = tiles

        # 独特尺寸
        unique_sizes = len(tile_list)

        # 总瓦片数
        total_tiles = sum(t.get("count", 1) for t in tile_list)

        # 瓦片列表
        tile_strs = []
        for t in tile_list:
            w = t.get("width") or t[0]
            h = t.get("height") or t[1]
            count = t.get("count", 1)
            tile_strs.append(f"{w}×{h}: {count}")

        # 库存信息
        inv_match = scheme.get("inventory_match", {})
        if inv_match and inv_match.get("match_score", 0) > 0:
            from_inv = inv_match.get("from_inventory", {})
            need_print = inv_match.get("need_print", {})
            inv_info = f" (使用库存: {sum(from_inv.values())} 块)"
        else:
            inv_info = ""

        output.append(f"[{key.upper()}] {name}{inv_info}")
        output.append(f"    独特尺寸: {unique_sizes} 种  |  瓦片数: {total_tiles} 块")
        output.append(f"    {', '.join(tile_strs)}")
        output.append("")

    output.append("请选择方案 [A/B/C]: ")

    return "\n".join(output)


def format_scheme_for_display(scheme, inventory=None):
    """格式化单个方案"""
    tiles = scheme.get("tiles", [])

    parts = []
    for t in tiles:
        w = t.get("width") or t[0]
        h = t.get("height") or t[1]
        count = t.get("count", 1)
        parts.append(f"{w}×{h}: {count}")

    return ", ".join(parts)
