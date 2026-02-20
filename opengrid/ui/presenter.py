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

        # 库存信息 - 增强版
        from_inv = scheme.get("from_inventory", {})
        need_print = scheme.get("need_print", {})

        if from_inv or need_print:
            # 收集所有需要的瓦片尺寸
            all_needed = {}
            if from_inv:
                for k, v in from_inv.items():
                    all_needed[k] = all_needed.get(k, 0) + v
            if need_print:
                for k, v in need_print.items():
                    all_needed[k] = all_needed.get(k, 0) + v

            # 计算覆盖率
            covered = 0
            total_sizes = len(all_needed)
            for size_key, need in all_needed.items():
                available = inventory.get(size_key, 0) if inventory else 0
                if available >= need:
                    covered += 1

            coverage = int(covered / total_sizes * 100) if total_sizes > 0 else 0

            # 库存使用详情
            inv_parts = []
            for size_key in sorted(from_inv.keys()):
                w, h = size_key.split('x')
                count = from_inv[size_key]
                inv_parts.append(f"{w}×{h}×{count}")

            # 打印需求详情
            print_parts = []
            for size_key in sorted(need_print.keys()):
                w, h = size_key.split('x')
                count = need_print[size_key]
                print_parts.append(f"{w}×{h}×{count}")

            # 构建库存信息行
            inv_line = ""
            if inv_parts:
                inv_line += f"📦 {'+'.join(inv_parts)}"
            if print_parts:
                if inv_line:
                    inv_line += " | "
                inv_line += f"🖨️ {'+'.join(print_parts)}"

            if coverage > 0:
                inv_line += f" | 💰 节省 {coverage}%"

            output.append(f"[{key.upper()}] {name}")
            if inv_line:
                output.append(f"    {inv_line}")
        else:
            # 无库存时显示简单信息
            output.append(f"[{key.upper()}] {name} (全部需要打印)")

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
