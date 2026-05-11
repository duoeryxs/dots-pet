"""基于点点真实的16x16水滴形 _BASE 生成升级版sprite。
保持原始轮廓，加上：轮廓线、高光渐变、腮红、眼睛反光。"""
import json, subprocess, os

SCRIPT = os.path.expanduser("~/.claude/skills/pixel-art-gen/scripts/render_pixel_art.py")
OUT_DIR = os.path.expanduser("~/projects/claude-pet/sprites_new")
os.makedirs(OUT_DIR, exist_ok=True)

# 点点的真实 _BASE（水滴形，左边尖）
# 0=透明 1=身体 2=腿 3=眼睛 4=鞋
_BASE = [
    [0,0,0,0,0,1,1,1,1,1,1,0,0,0,0,0],  # 0
    [0,0,0,0,1,1,1,1,1,1,1,1,0,0,0,0],  # 1
    [0,0,0,1,1,1,1,1,1,1,1,1,1,0,0,0],  # 2
    [0,0,1,1,1,1,1,1,1,1,1,1,1,1,0,0],  # 3
    [0,0,1,1,1,1,1,1,1,1,1,1,1,1,0,0],  # 4
    [0,0,1,1,1,1,1,1,1,1,1,1,1,1,0,0],  # 5
    [0,0,1,1,1,3,1,1,1,1,3,1,1,1,0,0],  # 6  眼睛 col5, col10
    [0,0,1,1,1,1,1,1,1,1,1,1,1,1,0,0],  # 7
    [0,1,1,1,1,1,1,1,1,1,1,1,1,0,0,0],  # 8  左宽右收
    [0,1,1,1,1,1,1,1,1,1,1,1,0,0,0,0],  # 9
    [1,1,1,1,1,1,1,1,1,1,1,0,0,0,0,0],  # 10 左小尖
    [0,0,0,0,0,2,0,0,0,2,0,0,0,0,0,0],  # 11 腿
    [0,0,0,0,4,4,0,0,4,4,0,0,0,0,0,0],  # 12 鞋
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],  # 13
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],  # 14
    [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],  # 15
]

# 升级色板（基于原色系扩展）
# 原色: 身体 #8CD7B4, 腿 #6EBE9B, 眼 #1A1A1A, 鞋 #64B496
O  = "#3A7A5C"   # 轮廓线（深薄荷绿）
H  = "#B5E8D0"   # 高光（亮薄荷）
B  = "#8CD7B4"   # 身体基色（原色）
M  = "#6EBE9B"   # 中间色（原腿色）
S  = "#5AA88A"   # 阴影
E  = "#1A1A1A"   # 眼睛
W  = "#FFFFFF"   # 眼睛反光
P  = "#F0B0B0"   # 腮红
K  = "#4A9A7A"   # 鞋子（深色）
_  = None        # 透明

def make_shaded(base_grid, eye_positions=None, blush_positions=None,
                eye_shine_positions=None, extra_overrides=None):
    """把 _BASE 的数字网格转成带渐变的颜色网格。
    光源左上 → 右上高光，左下阴影。"""
    h = len(base_grid)
    w = len(base_grid[0])
    result = [[_ for _ in range(w)] for _ in range(h)]

    # 先找出所有身体像素的边界
    body_pixels = set()
    for y in range(h):
        for x in range(w):
            if base_grid[y][x] in (1, 2, 3, 4):
                body_pixels.add((x, y))

    # 找轮廓：身体像素的四邻有透明的
    outline_pixels = set()
    for (x, y) in body_pixels:
        for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
            nx, ny = x+dx, y+dy
            if (nx, ny) not in body_pixels:
                outline_pixels.add((x, y))
                break

    for y in range(h):
        for x in range(w):
            v = base_grid[y][x]
            if v == 0:
                result[y][x] = _
            elif v == 3:  # 眼睛
                result[y][x] = E
            elif v == 4:  # 鞋
                result[y][x] = K
            elif v == 2:  # 腿
                result[y][x] = M
            elif v == 1:  # 身体
                if (x, y) in outline_pixels:
                    result[y][x] = O
                else:
                    # 渐变：根据位置分配色彩
                    # 右上亮（高光），左下暗（阴影）
                    # 用 x+y 作为简单梯度（越小越亮）
                    grad = x - y  # 右上大，左下小
                    if y <= 2 and x >= 6:  # 右上角高光区
                        result[y][x] = H
                    elif y <= 4 and x >= 5:  # 上部偏亮
                        result[y][x] = H
                    elif y >= 9:  # 下部阴影
                        result[y][x] = S
                    elif y >= 7:  # 中下
                        result[y][x] = M
                    else:
                        result[y][x] = B

    # 眼睛反光
    if eye_shine_positions:
        for (x, y) in eye_shine_positions:
            result[y][x] = W

    # 腮红
    if blush_positions:
        for (x, y) in blush_positions:
            result[y][x] = P

    # 额外覆盖
    if extra_overrides:
        for (x, y), color in extra_overrides.items():
            result[y][x] = color

    return result

def grid_to_pixels(grid):
    pixels = []
    for y, row in enumerate(grid):
        for x, c in enumerate(row):
            if c is not None:
                pixels.append({"x": x, "y": y, "color": c})
    return pixels

def save_and_render(name, grid):
    data = {
        "width": len(grid[0]),
        "height": len(grid),
        "background": "transparent",
        "pixel_size": 32,
        "pixels": grid_to_pixels(grid)
    }
    json_path = os.path.join(OUT_DIR, f"{name}.json")
    png_path = os.path.join(OUT_DIR, f"{name}.png")
    with open(json_path, "w") as f:
        json.dump(data, f)
    subprocess.run(["python3", SCRIPT, json_path, "-o", png_path], check=True)
    print(f"  -> {png_path}")

# ============================================================
# 1. Normal - 基于真实 _BASE，加渐变+轮廓+腮红+眼睛反光
# ============================================================
normal = make_shaded(
    _BASE,
    eye_shine_positions=[(5, 5)],            # 左眼上方反光（只一个更自然）
)

# ============================================================
# 2. Stare - 大眼版（2格高眼睛）
# ============================================================
stare_base = [row[:] for row in _BASE]
# 原来眼睛在 row6 col5和col10，加 row5 同位置
stare_base[5][5] = 3
stare_base[5][10] = 3
stare = make_shaded(
    stare_base,
    eye_shine_positions=[(5, 5), (10, 5)],  # 两只眼都有反光
)

# ============================================================
# 3. Happy - 眯眼笑（眼睛变成横线，用中间色表示）
# ============================================================
happy_base = [row[:] for row in _BASE]
happy_base[6][5] = 1   # 去掉原眼睛
happy_base[6][10] = 1
# 眯眯眼用深色横线 row6
happy_grid = make_shaded(
    happy_base,
    extra_overrides={
        (4, 6): E, (5, 6): E, (6, 6): E,    # 左眯眼 ^^
        (9, 6): E, (10, 6): E, (11, 6): E,   # 右眯眼 ^^
    }
)

# ============================================================
# 4. Sleepy - 闭眼 + zzz
# ============================================================
sleepy_base = [row[:] for row in _BASE]
sleepy_base[6][5] = 1   # 去掉眼睛
sleepy_base[6][10] = 1
Z = "#7BA8D4"
sleepy = make_shaded(
    sleepy_base,
    extra_overrides={
        # 闭眼横线
        (5, 6): E, (6, 6): E,
        (10, 6): E, (11, 6): E,
        # zzz 在右上方
        (12, 0): Z, (13, 0): Z, (14, 0): Z,
        (13, 1): Z,
        (12, 2): Z, (13, 2): Z, (14, 2): Z,
    }
)

# ============================================================
# 5. 珍珠奶茶 - 新食物 8x8
# ============================================================
# 0=透明, 用新的颜色ID
boba_grid = [
    [_, _, _, "#E8778A", _, _, _, _],  # 0  吸管
    [_, _, _, "#E8778A", _, _, _, _],  # 1
    [_, O, O, "#E8778A", O, O, _, _],  # 2  杯盖
    [_, O,"#F5E6D0","#E8778A","#F5E6D0", O, _, _],  # 3
    [_, O,"#F5E6D0","#C9A87C","#C9A87C", O, _, _],  # 4  奶茶色
    [_, O,"#C9A87C","#C9A87C","#C9A87C", O, _, _],  # 5
    [_, _, O,"#8B5E3C","#8B5E3C", O, _, _],  # 6  珍珠
    [_, _, _, O, O, _, _, _],           # 7  底
]

print("Generating upgraded sprites (faithful to DianDian)...")
save_and_render("normal_v2", normal)
save_and_render("stare_v2", stare)
save_and_render("happy_v2", happy_grid)
save_and_render("sleepy_v2", sleepy)
save_and_render("boba_tea_v2", boba_grid)
print("Done!")
