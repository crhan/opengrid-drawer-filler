// openGrid 瓦片 STL 生成入口
// 参数全部通过 OpenSCAD CLI 用 -D 注入，generator.py 内部就这么调：
//
//   openscad -o out.stl \
//     -D 'Board_Width=7' -D 'Board_Height=5' -D 'Stack_Count=2' \
//     -D 'Tile_Type="Full"' -D 'Tile_Size=28' -D 'Tile_Thickness=6.8' \
//     -D 'Stack_Gap=0.4' \
//     opengrid/stl/wrapper.scad
//
// 直接跑 `openscad wrapper.scad`（无 -D）时：
//   - Board_Width / Board_Height / Stack_Count / Tile_Size / Tile_Thickness
//     由 include 进来的 openGrid.scad 自带的 customizer 默认值兜底，
//     不在本文件重复声明（重复声明会被 OpenSCAD 报 "overwritten" warning）
//   - Tile_Type 和 Stack_Gap 是 wrapper-only 概念，必须在这里声明默认值

include <BOSL2/std.scad>
include <../../vendor/QuackWorks/openGrid/openGrid.scad>

// 仅声明 openGrid.scad 没有的两个 wrapper-only 参数
Tile_Type = "Full";   // "Full" | "Lite" | "Heavy"
Stack_Gap = 0.4;      // 这里默认值跟 opengrid/core/constants.py 的 STACK_GAP_MM
                      // 保持一致，CLI 模式下由 generator.py 用 -D 注入相同值

for (i = [0 : Stack_Count - 1]) {
    translate([0, 0, i * (Tile_Thickness + Stack_Gap)]) {
        if (Tile_Type == "Lite") {
            openGridLite(Board_Width, Board_Height, tileSize = Tile_Size);
        } else if (Tile_Type == "Heavy") {
            openGridHeavy(Board_Width, Board_Height, tileSize = Tile_Size);
        } else {
            openGrid(Board_Width, Board_Height,
                     tileSize = Tile_Size,
                     Tile_Thickness = Tile_Thickness);
        }
    }
}
