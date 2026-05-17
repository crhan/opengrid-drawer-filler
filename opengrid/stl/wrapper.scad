// openGrid 瓦片 STL 生成入口
// 参数由 OpenSCAD CLI 用 -D 注入；下面的默认值仅在直接 `openscad wrapper.scad` 时使用
//
// 调用样例（generator.py 内部就是这么拼的）：
//   openscad -o out.stl \
//     -D 'Board_Width=7' -D 'Board_Height=5' -D 'Stack_Count=2' \
//     -D 'Tile_Type="Full"' -D 'Tile_Size=28' -D 'Tile_Thickness=6.8' \
//     -D 'Stack_Gap=0.4' \
//     opengrid/stl/wrapper.scad

Board_Width   = 1;
Board_Height  = 1;
Stack_Count   = 1;
Tile_Type     = "Full";   // "Full" | "Lite" | "Heavy"
Tile_Size     = 28;
Tile_Thickness = 6.8;     // Full=6.8 / Lite=4.0 / Heavy=13.8（Python 端按 Tile_Type 透传）
Stack_Gap     = 0.4;      // 这里的默认值只在直接跑 wrapper.scad 时用；CLI 模式下 Python 端
                          // 用 -D 注入 opengrid/core/constants.py 里的 STACK_GAP_MM

Layer_Step = Tile_Thickness + Stack_Gap;

include <BOSL2/std.scad>
include <../../vendor/QuackWorks/openGrid/openGrid.scad>

for (i = [0 : Stack_Count - 1]) {
    translate([0, 0, i * Layer_Step]) {
        if (Tile_Type == "Lite") {
            openGridLite(Board_Width, Board_Height, tileSize = Tile_Size);
        } else if (Tile_Type == "Heavy") {
            openGridHeavy(Board_Width, Board_Height, tileSize = Tile_Size);
        } else {
            // 默认 Full
            openGrid(Board_Width, Board_Height,
                     tileSize = Tile_Size,
                     Tile_Thickness = Tile_Thickness);
        }
    }
}
