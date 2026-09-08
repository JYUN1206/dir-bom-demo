#!/usr/bin/env python3
"""把 main.py 的真实运行输出与 reject_list.xlsx 渲染成 PNG 截图（数据全部来自实际运行，非摆拍）。"""
import subprocess
import pandas as pd
from PIL import Image, ImageDraw, ImageFont

FONT_PATH = "/System/Library/Fonts/Hiragino Sans GB.ttc"  # macOS 自带中文字体


def load_font(size, index=0):
    return ImageFont.truetype(FONT_PATH, size, index=index)


# ---------- 图 1：终端运行输出（真实命令 + 真实输出） ----------
cmd = ".venv/bin/python main.py --input data/orders.xlsx --outdir output/ --db output/bom.db"
run = subprocess.run(
    [".venv/bin/python", "main.py", "--input", "data/orders.xlsx",
     "--outdir", "output/", "--db", "output/bom.db"],
    capture_output=True, text=True)
lines = [f"$ {cmd}"] + run.stdout.rstrip("\n").split("\n")

font = load_font(20)
lh, pad, pl = 30, 24, 28
probe = ImageDraw.Draw(Image.new("RGB", (10, 10)))
W = max(width_of := max(probe.textbbox((0, 0), ln, font=font)[2] for ln in lines) + pl * 2, 900)
H = pad * 2 + lh * len(lines) + 40  # 底部标题栏
img = Image.new("RGB", (W, H), (30, 30, 34))
d = ImageDraw.Draw(img)
for i, ln in enumerate(lines):
    color = (240, 240, 240)
    if ln.startswith("$"):
        color = (120, 220, 120)
    elif "拦截" in ln and "合规" in ln or "耗时" in ln:
        color = (250, 200, 90)
    d.text((pl, pad + i * lh), ln, font=font, fill=color)
cap = load_font(14)
d.text((pl, H - 30), "全屋定制拆单自动化 · 端到端运行（50 单：48 合规 + 2 拦截）—— 个人项目 / 模拟数据",
       font=cap, fill=(150, 150, 155))
img.save("screenshots/reject_terminal.png")
print("saved screenshots/reject_terminal.png")

# ---------- 图 2：reject_list.xlsx 表格渲染 ----------
df = pd.read_excel("output/reject_list.xlsx")
cols = list(df.columns)
font_h = load_font(19)
font_c = load_font(18)

# 列宽按内容测
def width_of(s, f):
    b = d.textbbox((0, 0), str(s), font=f)
    return b[2] - b[0]

probe = ImageDraw.Draw(Image.new("RGB", (10, 10)))
col_w = [max(width_of(c, font_h), max(width_of(df.iloc[r][c], font_c) for r in range(len(df)))) + 28
         for c in cols]
row_h, top = 42, 60
W2 = sum(col_w) + 2
H2 = top + row_h * (len(df) + 1) + 50
img2 = Image.new("RGB", (W2, H2), (255, 255, 255))
d2 = ImageDraw.Draw(img2)
# 标题行
d2.rectangle([0, 0, W2, top], fill=(47, 84, 150))
x = 1
for c, w in zip(cols, col_w):
    d2.text((x + 14, 16), c, font=font_h, fill=(255, 255, 255))
    x += w
# 数据行（斑马纹）
for r in range(len(df)):
    y = top + row_h * r
    if r % 2 == 1:
        d2.rectangle([0, y, W2, y + row_h], fill=(238, 242, 250))
    x = 1
    for c, w in zip(cols, col_w):
        v = str(df.iloc[r][c])
        fill = (200, 40, 40) if c == "原因" else (40, 40, 40)
        d2.text((x + 14, y + 10), v, font=font_c, fill=fill)
        x += w
# 网格线
y = top
for r in range(len(df) + 1):
    d2.line([0, y, W2, y], fill=(190, 190, 190), width=1)
    y += row_h
x = 0
for w in col_w + [0]:
    d2.line([x, top, x, top + row_h * (len(df) + 1)], fill=(190, 190, 190), width=1)
    x += w
d2.text((14, H2 - 36), "output/reject_list.xlsx · 工艺拦截清单（50 单模拟数据中埋雷 2 条）—— 个人项目 / 模拟数据",
        font=cap, fill=(120, 120, 125))
img2.save("screenshots/reject_excel.png")
print("saved screenshots/reject_excel.png")
